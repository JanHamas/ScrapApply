from django.shortcuts import render


def store_app(request):
    return render(request,'store/store.html')
