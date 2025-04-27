# models.py
from django.db import models

class FormData(models.Model):
    about_me = models.TextField()
    job_urls = models.TextField()
    ignore_companies = models.TextField(blank=True, null=True)
    jobs_per_company = models.IntegerField(blank=True, null=True)
    max_items = models.IntegerField(blank=True, null=True) 
    
    def __str__(self):
        return self.about_me[:50]  # just showing first 50 characters
