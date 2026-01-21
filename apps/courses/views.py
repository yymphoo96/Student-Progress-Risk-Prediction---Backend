# apps/courses/views.py - FIX course_details endpoint

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Course, CourseRegistration
from apps.assessments.models import Assignment, Quiz
from apps.assessments.serializers import AssignmentSerializer, QuizSerializer

class CourseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_courses(self, request):
        """Get courses enrolled by current student"""
        student = request.user
        
        registrations = CourseRegistration.objects.filter(
            student=student,
            status='active'
        ).select_related('course')
        
        courses = []
        for reg in registrations:
            courses.append({
                'course_id': reg.course.course_id,
                'course_code': reg.course.course_code,
                'course_title': reg.course.course_title,
                'term': reg.course.term,
                'year': reg.course.year,
                'enrolled_date': reg.enrolled_date,
                'status': reg.status
            })
        
        return Response(courses)
    
    @action(detail=True, methods=['get'], url_path='course_details')
    def course_details(self, request, pk=None):
        """Get course details with assignments and quizzes"""
        student = request.user
        
        # Get course
        course = get_object_or_404(Course, course_id=pk)
        
        # Check if student is enrolled
        if not CourseRegistration.objects.filter(
            student=student,
            course=course,
            status='active'
        ).exists():
            return Response(
                {'error': 'Not enrolled in this course'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get assignments
        assignments = Assignment.objects.filter(
            course=course
        ).order_by('week_number', 'due_date')
        
        # Serialize assignments
        assignment_data = []
        for assignment in assignments:
            from apps.assessments.models import AssignmentSubmission
            
            # Get submission status
            try:
                submission = AssignmentSubmission.objects.get(
                    assignment=assignment,
                    student=student
                )
                submission_status = submission.status
                score = submission.score
            except AssignmentSubmission.DoesNotExist:
                submission_status = 'not_submitted'
                score = None
            
            assignment_data.append({
                'assignment_id': assignment.assignment_id,
                'title': assignment.title,
                'description': assignment.description,
                'due_date': assignment.due_date,
                'week_number': assignment.week_number,
                'max_score': assignment.max_score,
                'submission_status': submission_status,
                'score': score
            })
        
        # Get quizzes
        quizzes = Quiz.objects.filter(
            course=course
        ).order_by('week_number', 'date')
        
        # Serialize quizzes
        quiz_data = []
        for quiz in quizzes:
            from apps.assessments.models import QuizScore
            
            # Get quiz score
            try:
                quiz_score = QuizScore.objects.get(
                    quiz=quiz,
                    student=student
                )
                submission_status = quiz_score.status
                score = quiz_score.score
            except QuizScore.DoesNotExist:
                submission_status = 'not_taken'
                score = None
            
            quiz_data.append({
                'quiz_id': quiz.quiz_id,
                'title': quiz.title,
                'description': quiz.description,
                'quiz_date': quiz.date,
                'week_number': quiz.week_number,
                'max_score': quiz.max_score,
                'submission_status': submission_status,
                'score': score
            })
        
        return Response({
            'course': {
                'course_id': course.course_id,
                'course_code': course.course_code,
                'course_title': course.course_title,
                'term': course.term,
                'year': course.year,
            },
            'assignments': assignment_data,
            'quizzes': quiz_data
        })