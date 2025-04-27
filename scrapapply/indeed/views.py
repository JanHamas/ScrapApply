from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .scrapper import IndeedJobScraper
from .models import FormData
from django.contrib import messages
import threading

# Global variables
is_scraper_running = False
scraper_complete_message = ""

@csrf_exempt
def indeed_scrapper(request):
    global is_scraper_running, scraper_complete_message

    if request.method == 'POST':
        if is_scraper_running:
            messages.error(request, 'Scraper is already running. Please wait!')
            return redirect('indeed_scrapper')

        is_scraper_running = True

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

        FormData.objects.all().delete()
        form_data = FormData.objects.create(
            about_me=about_me,
            job_urls="\n".join(job_urls_list),
            ignore_companies="\n".join(ignore_companies_list),
            jobs_per_company=jobs_per_company,
            max_items=max_items
        )

        def run_scraper():
            global is_scraper_running, scraper_complete_message
            try:
                scraper = IndeedJobScraper()
                scraper.extract_jobs(
                    about_me=about_me,
                    job_urls_list=job_urls_list,
                    ignore_companies_list=ignore_companies_list,
                    jobs_per_company=jobs_per_company,
                    max_items=max_items
                )
                scraper_complete_message = "Scraping completed successfully!"
            except Exception as e:
                scraper_complete_message = f"Scraping failed: {str(e)}"
            finally:
                is_scraper_running = False

        threading.Thread(target=run_scraper).start()
        return redirect('indeed_scrapper')

    form_data = FormData.objects.last()

    return render(request, 'indeed/indeed.html', {
        'form_data': form_data,
        'is_scraper_running': is_scraper_running,
        'scraper_complete_message': scraper_complete_message,
    })

# New view to check scraper status
def check_scraper_status(request):
    global is_scraper_running, scraper_complete_message
    return JsonResponse({
        'running': is_scraper_running,
        'message': scraper_complete_message
    })
