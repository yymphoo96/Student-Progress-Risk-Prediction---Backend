from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from ..users.models import User
from ..courses.models import Course


# apps/assessments/models.py

from django.db import models
from apps.users.models import User
from apps.courses.models import Course

class Attendance(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField()
    week_number = models.IntegerField()
    status = models.CharField(max_length=10, choices=[
        ('present', 'Present'),
        ('absent', 'Absent'),
    ])
    section = models.CharField(max_length=20, default='first-section', choices=[
        ('first-section', 'First Section'),
        ('second-section', 'Second Section'),
        ('third-section', 'Third Section'),
        ('fourth-section', 'Fourth Section'),
    ])
    
    class Meta:
        db_table = 'attendance'
        unique_together = ('student', 'course', 'date','section')
    
    def __str__(self):
        return f"{self.student.username} - {self.course.course_code} - {self.date}"

class Assignment(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField()
    max_score = models.FloatField()
    week_number = models.IntegerField()
    
    class Meta:
        db_table = 'assignments'
    
    def __str__(self):
        return f"{self.title} - {self.course.course_code}"

class AssignmentSubmission(models.Model):
    submission_id = models.AutoField(primary_key=True)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    submission_date = models.DateTimeField(auto_now_add=True)
    score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, default='submitted',
choices=[
        ('submitted', 'Submitted'),
        ('late-submitted', 'Late Submitted'),
        ('Not Submitted', 'Not Submitted')
    ])
    class Meta:
        db_table = 'assignment_submissions'
    
    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"

class Quiz(models.Model):
    quiz_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    date = models.DateField()
    max_score = models.FloatField()
    week_number = models.IntegerField()
    
    class Meta:
        db_table = 'quizzes'
    
    def __str__(self):
        return f"{self.title} - {self.course.course_code}"

class QuizScore(models.Model):
    quiz_score_id = models.AutoField(primary_key=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.FloatField()
    submitted_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'quiz_scores'
    
    def __str__(self):
        return f"{self.student.username} - {self.quiz.title}"

# ✅ FIXED: LabActivity with all required fields
class LabActivity(models.Model):
    lab_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        limit_choices_to={'user_type': 'teacher'}
    )
    title = models.CharField(max_length=200)
    date = models.DateField()
    max_score = models.FloatField()
    week_number = models.IntegerField()
    
    class Meta:
        db_table = 'lab_activities'
    
    def __str__(self):
        return f"{self.title} - {self.course.course_code}"

# ✅ FIXED: LabParticipation with correct foreign key
class LabParticipation(models.Model):
    participation_id = models.AutoField(primary_key=True)
    lab = models.ForeignKey(LabActivity, on_delete=models.CASCADE)  # Changed from lab_id
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    score = models.FloatField()
    max_score = models.FloatField()
    attendance = models.BooleanField(default=True)
    remark = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = 'lab_participation'
    
    def __str__(self):
        return f"{self.student.username} - {self.lab.title}"

# ===================== WEEKLY PROGRESS =====================

class WeeklyProgress(models.Model):
    """Track weekly progress for charts"""
    progress_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    week_number = models.IntegerField()
    student_score = models.FloatField()
    class_average = models.FloatField()
    calculated_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'weekly_progress'
        unique_together = ('student', 'course', 'week_number')