from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

# URL Configuration

urlpatterns = [
    path('', views.IntelligenceLogView.as_view(), name='home'), # Homepage is now Intelligence Log
    path('dashboard/', views.dashboard, name='dashboard'), # Dashboard moved
    path('targets/', views.target_list, name='target_list'),
    path('targets/add/', views.TargetCreateView.as_view(), name='target_add'),
    path('targets/detail/', views.TargetDetailView.as_view(), name='target_detail'), # Query param style
    path('targets/<uuid:pk>/edit/', views.TargetUpdateView.as_view(), name='target_edit'), # Edit route
    path('targets/<uuid:pk>/export_csv/', views.TargetExportView.as_view(), name='target_export_csv'),
    path('targets/<uuid:pk>/delete/', views.TargetDeleteView.as_view(), name='target_delete'), # Delete route
    path('api/groups/create/', views.TargetGroupCreateView.as_view(), name='group_add'), # Group API
    path('api/groups/<int:pk>/edit/', views.TargetGroupUpdateView.as_view(), name='group_edit'),
    path('api/groups/<int:pk>/delete/', views.TargetGroupDeleteView.as_view(), name='group_delete'),
    path('api/target/state-toggle/', views.TargetStateToggleView.as_view(), name='target_state_toggle'),
    path('intelligence/log/', views.IntelligenceLogView.as_view(), name='intelligence_log'),
    
    # Question Management
    path('questions/', views.QuestionListView.as_view(), name='question_list'),
    path('questions/detail/', views.QuestionDetailView.as_view(), name='question_detail'),
    path('questions/add/', views.QuestionCreateView.as_view(), name='question_add'),
    path('questions/<int:pk>/edit/', views.QuestionUpdateView.as_view(), name='question_edit'),
    path('questions/<int:pk>/delete/', views.QuestionDeleteView.as_view(), name='question_delete'),
    path('questions/export/', views.QuestionExportView.as_view(), name='question_export'),
    path('questions/import/', views.QuestionImportView.as_view(), name='question_import'),
    path('api/questions/category/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('api/questions/rank/add/', views.RankCreateView.as_view(), name='rank_add'),
    
    # Timeline
    path('api/timeline/', views.TimelineListAPIView.as_view(), name='timeline_list'),
    path('api/tags/', views.TagListAPIView.as_view(), name='tag_list_api'),
    path('api/questions/', views.QuestionListAPIView.as_view(), name='api_questions'),
    path('help/', views.HelpView.as_view(), name='help'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # Ensure static served
