from django.shortcuts import render

def dashboard(request):
    return render(request, 'dashboard.html')

def target_list(request):
    return render(request, 'target_list.html')
