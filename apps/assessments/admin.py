# apps/assessments/admin.py

from django.contrib import admin
from .models import (
    Attendance, Assignment, AssignmentSubmission,
    Quiz, QuizScore, LabActivity, LabParticipation
)
from ..users.models import User

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'date', 'week_number', 'status', 'section']
    list_filter = ['status', 'week_number', 'date', 'section']
    search_fields = ['student__email', 'student__username', 'course__course_code']
    date_hierarchy = 'date'
    
    #Filter student dropdown to show only students
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "student":
            kwargs["queryset"] = User.objects.filter(
                user_type='student'
            ).select_related().order_by('first_name', 'last_name')
        
        #show only active courses
        if db_field.name == "course":
            from apps.courses.models import Course
            kwargs["queryset"] = Course.objects.filter(
                courseregistration__status='active'
            ).distinct().order_by('course_code')
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    # ✅ Add helpful text in admin form
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Add help text
        form.base_fields['student'].help_text = 'Select a student (teachers and admins are filtered out)'
        form.base_fields['course'].help_text = 'Select the course for this attendance record'
        
        return form

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'due_date', 'max_score', 'week_number']
    list_filter = ['course', 'week_number', 'due_date']
    search_fields = ['title', 'course__course_code']
    date_hierarchy = 'due_date'

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'assignment', 'score', 'status', 'submission_date']
    list_filter = ['status', 'submission_date']
    search_fields = ['student__email', 'student__username', 'assignment__title']
    date_hierarchy = 'submission_date'

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'date', 'max_score', 'week_number']
    list_filter = ['course', 'week_number', 'date']
    search_fields = ['title', 'course__course_code']
    date_hierarchy = 'date'

@admin.register(QuizScore)
class QuizScoreAdmin(admin.ModelAdmin):
    list_display = ['student', 'quiz', 'score', 'submitted_date']
    list_filter = ['quiz__course', 'submitted_date']
    search_fields = ['student__email', 'student__username', 'quiz__title']
    date_hierarchy = 'submitted_date'

# ✅ FIXED: LabActivityAdmin with correct fields
@admin.register(LabActivity)
class LabActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'teacher', 'date', 'max_score', 'week_number']
    list_filter = ['course', 'week_number', 'date']
    search_fields = ['title', 'course__course_code', 'teacher__username']
    date_hierarchy = 'date'

# ✅ FIXED: LabParticipationAdmin with correct fields
@admin.register(LabParticipation)
class LabParticipationAdmin(admin.ModelAdmin):
    list_display = ['student', 'lab', 'date', 'score', 'max_score', 'attendance']
    list_filter = ['attendance', 'date', 'lab__course']
    search_fields = ['student__email', 'student__username', 'lab__title']
    date_hierarchy = 'date'