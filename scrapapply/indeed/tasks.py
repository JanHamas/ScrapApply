from celery import shared_task
from .indeed_scrapper import JobScrapper

@shared_task
def run_scraper(about_me, job_urls_list, ignore_companies_list, jobs_per_company, max_items):
    scraper = JobScrapper()
    scraper.scrap_jobs(
        about_me=about_me,
        job_urls_list=job_urls_list,
        ignore_companies_list=ignore_companies_list,
        jobs_per_company=jobs_per_company,
        max_items=max_items
    )
    print("🔍 Scraper running in background...")
    return "✅ Scraper finished!"

