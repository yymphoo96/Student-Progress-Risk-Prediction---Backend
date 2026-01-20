from django.contrib import admin
from .models import Course, CourseRegistration, CourseTeaching

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'course_title', 'year', 'term', 'created_at']
    list_filter = ['year', 'term']
    search_fields = ['course_code', 'course_title']

@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'enrolled_date', 'status']
    list_filter = ['status', 'enrolled_date','student','course']
    search_fields = ['student__email', 'student__student_id', 'course__course_code']

@admin.register(CourseTeaching)
class CourseTeachingAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'course', 'term']
    list_filter = ['term','teacher']
    search_fields = ['teacher__email', 'course__course_code']