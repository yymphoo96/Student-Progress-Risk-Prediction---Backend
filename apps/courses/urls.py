# apps/courses/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentCourseViewSet

router = DefaultRouter()
router.register(r'courses', StudentCourseViewSet, basename='courses')

urlpatterns = [
    path('', include(router.urls)),
]