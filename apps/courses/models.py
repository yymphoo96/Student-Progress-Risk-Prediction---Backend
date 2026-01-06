# models.py

from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from ..users.models import User

class Course(models.Model):
    """Course Information"""
    course_id = models.AutoField(primary_key=True)
    course_code = models.CharField(max_length=20, unique=True)
    course_title = models.CharField(max_length=200)
    year = models.IntegerField()
    term = models.CharField(max_length=20)  # e.g., "Fall 2024"
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'courses'
    
    def __str__(self):
        return f"{self.course_code} - {self.course_title}"

class CourseRegistration(models.Model):
    """Student-Course Registration (Many-to-Many)"""
    registration_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='active')  # active, dropped, completed
    
    class Meta:
        db_table = 'course_registrations'
        unique_together = ('student', 'course')

class CourseTeaching(models.Model):
    """Teacher-Course Assignment"""
    teaching_id = models.AutoField(primary_key=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'teacher'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    term = models.CharField(max_length=20)
    
    class Meta:
        db_table = 'course_teaching'