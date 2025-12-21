"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.views.generic import TemplateView, RedirectView
import os

def service_worker(request):
    sw_path = os.path.join(settings.BASE_DIR, 'theme/static/sw.js')
    response = HttpResponse(open(sw_path).read(), content_type='application/javascript')
    return response

urlpatterns = [
    path('admin/', admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
    path('accounts/', include('accounts.urls')),
    path('', include('core.urls')),
    path('sw.js', service_worker, name='service_worker'),
    path('offline/', TemplateView.as_view(template_name="offline.html"), name='offline'),
    path('favicon.ico', RedirectView.as_view(url='/static/dossier_icon.png', permanent=True), name='favicon'),
]
