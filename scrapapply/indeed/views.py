from django.shortcuts import render

# indeed scrapper
def indeed_scrapper(request):
    return render(request,'indeed/indeed.html')