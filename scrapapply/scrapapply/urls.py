from django.contrib import admin
from django.urls import path, include
from indeed import views as indeed_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("store.urls"), name="store"),
    path('indeed-scrapper/', include('indeed.urls'), name='indeed_scrapper'),
    path('check-scraper-status/', indeed_views.check_scraper_status, name='check_scraper_status'),  # <-- Corrected here
]
