# apps/analytics/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentAnalyticsViewSet

router = DefaultRouter()
router.register(r'analytics', StudentAnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('', include(router.urls)),
]

# Main urls.py
# urlpatterns += [
#     path('api/', include('apps.analytics.urls')),
# ]