from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('targets/', views.target_list, name='target_list'),
    path('targets/add/', views.TargetCreateView.as_view(), name='target_add'),
]
