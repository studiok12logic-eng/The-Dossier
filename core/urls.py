from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('targets/', views.target_list, name='target_list'),
    path('targets/add/', views.TargetCreateView.as_view(), name='target_add'),
    path('targets/<uuid:pk>/edit/', views.TargetUpdateView.as_view(), name='target_edit'), # Edit route
    path('targets/<uuid:pk>/delete/', views.TargetDeleteView.as_view(), name='target_delete'), # Delete route
    path('api/groups/create/', views.TargetGroupCreateView.as_view(), name='group_add'), # Group API
    path('api/groups/<int:pk>/edit/', views.TargetGroupUpdateView.as_view(), name='group_edit'),
    path('api/groups/<int:pk>/delete/', views.TargetGroupDeleteView.as_view(), name='group_delete'),
    path('intelligence/log/', views.IntelligenceLogView.as_view(), name='intelligence_log'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # Ensure static served
