from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from .models import FormData
from .tasks import run_scraper  # Import Celery task

# Global variables
scraper_complete_message = ""

@csrf_exempt
def indeed_scrapper(request):
    global scraper_complete_message

    if request.method == 'POST':
        # Check if the scraper task is already running
        # Note: Celery tasks don't need to track a running flag
        #       because Celery handles background tasks
        scraper_complete_message = "Scraping has started!"

        # Get form data
        about_me = request.POST.get('Aboutme', '').strip()
        job_urls = request.POST.get('job_urls', '').strip()
        ignore_companies = request.POST.get('ignore_companies', '').strip()
        jobs_per_company = request.POST.get('jobs_per_company', '3').strip()
        max_items = request.POST.get('max_items', '50').strip()

        job_urls_list = [url.strip() for url in job_urls.split('\n') if url.strip()]
        ignore_companies_list = [comp.strip() for comp in ignore_companies.split('\n') if comp.strip()]

        try:
            jobs_per_company = int(jobs_per_company)
            max_items = int(max_items)
        except ValueError:
            jobs_per_company = 3
            max_items = 50

        # Save the form data into the database
        FormData.objects.all().delete()
        FormData.objects.create(
            about_me=about_me,
            job_urls="\n".join(job_urls_list),
            ignore_companies="\n".join(ignore_companies_list),
            jobs_per_company=jobs_per_company,
            max_items=max_items
        )

        # Start Celery task for scraping in the background
        run_scraper.delay(  # Use .delay() to call the Celery task
            about_me=about_me,
            job_urls_list=job_urls_list,
            ignore_companies_list=ignore_companies_list,
            jobs_per_company=jobs_per_company,
            max_items=max_items
        )

        return redirect('indeed_scrapper')

    form_data = FormData.objects.last()

    return render(request, 'indeed/indeed_scrapper.html', {
        'form_data': form_data,
        'scraper_complete_message': scraper_complete_message,
    })


# View to check scraper status
def check_scraper_status(request):
    return JsonResponse({
        'message': scraper_complete_message
    })
