from django.urls import path
from . import views, dashboard_views

urlpatterns = [
    # Web dashboard
    path('survey-dashboard/', dashboard_views.survey_dashboard, name='survey-dashboard'),
    path('survey-dashboard/data/', dashboard_views.survey_dashboard_data, name='survey-dashboard-data'),
    path('survey-dashboard/records/', dashboard_views.survey_dashboard_records, name='survey-dashboard-records'),

    path('surveys/questions/', views.list_questions, name='survey-questions'),
    path('surveys/submit/', views.submit_survey, name='survey-submit'),
    path('surveys/status/', views.survey_status, name='survey-status'),
    path('surveys/any_pending/', views.any_pending, name='survey-any-pending'),
    path('surveys/analytics/', views.analytics, name='survey-analytics'),
    path('surveys/teacher_courses/', views.teacher_courses, name='survey-teacher-courses'),
    path('surveys/week_status/', views.week_status, name='survey-week-status'),
    path('surveys/release/', views.release_survey, name='survey-release'),
]
