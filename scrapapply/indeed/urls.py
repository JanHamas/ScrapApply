from django.urls import path
from . import views
urlpatterns=[
    path('',views.indeed_scrapper,name='indeed_scrapper')
]