# apps/analytics/urls.py - CREATE NEW FILE

from django.urls import path
from .views import DashboardViewSet

dashboard_view = DashboardViewSet.as_view({
    'get': 'student_dashboard'
})

urlpatterns = [
    path('dashboard/student_dashboard/', dashboard_view, name='student-dashboard'),
]