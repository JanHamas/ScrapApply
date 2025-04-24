from django.urls import path
from . import views
urlpatterns=[
    path('',views.store_app,name='store')
]