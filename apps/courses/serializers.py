# apps/courses/serializers.py - REPLACE

from rest_framework import serializers
from .models import Course, CourseRegistration

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['course_id', 'course_code', 'course_title', 'year', 'term', 'description']

class MyCourseSerializer(serializers.ModelSerializer):
    # Flatten the course data directly
    course_id = serializers.IntegerField(source='course.course_id')
    course_code = serializers.CharField(source='course.course_code')
    course_title = serializers.CharField(source='course.course_title')
    year = serializers.IntegerField(source='course.year')
    term = serializers.CharField(source='course.term')
    description = serializers.CharField(source='course.description')
    
    class Meta:
        model = CourseRegistration
        fields = ['registration_id', 'course_id', 'course_code', 'course_title', 
                  'year', 'term', 'description', 'enrolled_date', 'status']