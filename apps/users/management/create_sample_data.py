# apps/users/management/commands/create_sample_data.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.courses.models import Course, CourseRegistration
from apps.assessments.models import Attendance, Assignment, AssignmentSubmission, Quiz, QuizScore
from datetime import datetime, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample data for testing'
    
    def handle(self, *args, **kwargs):
        self.stdout.write('Creating sample data...')
        
        # Create teacher
        teacher, created = User.objects.get_or_create(
            email='teacher@example.com',
            defaults={
                'username': 'teacher',
                'first_name': 'Teacher',
                'last_name': 'One',
                'user_type': 'teacher',
                'is_staff': True
            }
        )
        if created:
            teacher.set_password('teacher123')
            teacher.save()
            self.stdout.write(self.style.SUCCESS('Teacher created'))
        
        # Create student
        student, created = User.objects.get_or_create(
            email='john.smith@example.com',
            defaults={
                'username': 'johnsmith',
                'first_name': 'John',
                'last_name': 'Smith',
                'student_id': '123456',
                'user_type': 'student',
                'phone': '+1234567890',
                'country': 'Myanmar'
            }
        )
        if created:
            student.set_password('student123')
            student.save()
            self.stdout.write(self.style.SUCCESS('Student created'))
        
        # Create course
        course, created = Course.objects.get_or_create(
            course_code='CS101',
            defaults={
                'course_title': 'Data Science',
                'year': 2024,
                'term': 'Fall 2024',
                'description': 'Introduction to Data Science'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Course created'))
        
        # Enroll student
        CourseRegistration.objects.get_or_create(
            student=student,
            course=course,
            defaults={'status': 'active'}
        )
        
        # Create attendance records
        for week in range(1, 6):
            for day in range(1, 4):
                date = datetime.now().date() - timedelta(days=(5-week)*7 + (3-day))
                Attendance.objects.get_or_create(
                    student=student,
                    course=course,
                    date=date,
                    defaults={
                        'week_number': week,
                        'status': random.choice(['present', 'present', 'absent']),
                        'section': 'section-one'
                    }
                )
        
        # Create assignments
        for week in range(1, 6):
            assignment, created = Assignment.objects.get_or_create(
                course=course,
                title=f'Week {week} Assignment',
                defaults={
                    'description': f'Assignment for week {week}',
                    'due_date': datetime.now() + timedelta(days=week*7),
                    'max_score': 100,
                    'week_number': week
                }
            )
            
            # Create submission
            AssignmentSubmission.objects.get_or_create(
                student=student,
                assignment=assignment,
                defaults={
                    'score': random.randint(50, 95),
                    'status': 'graded'
                }
            )
        
        # Create quizzes
        for week in range(1, 6):
            quiz, created = Quiz.objects.get_or_create(
                course=course,
                title=f'Week {week} Quiz',
                defaults={
                    'date': datetime.now().date() - timedelta(days=(5-week)*7),
                    'max_score': 100,
                    'week_number': week
                }
            )
            
            QuizScore.objects.get_or_create(
                student=student,
                quiz=quiz,
                defaults={
                    'score': random.randint(60, 100)
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))