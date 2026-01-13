# apps/courses/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Course, CourseRegistration
from .serializers import CourseSerializer, MyCourseSerializer

class StudentCourseViewSet(viewsets.ViewSet):
    """Student course endpoints"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_courses(self, request):
        """
        Get all courses for current student
        
        GET /api/courses/my_courses/
        Headers: Authorization: Token <token>
        """
        # Get student's enrolled courses
        registrations = CourseRegistration.objects.filter(
            student=request.user,
            status='active'
        ).select_related('course')
        
        courses_data = []
        for reg in registrations:
            course = reg.course
            courses_data.append({
                'course_id': course.course_id,
                'course_code': course.course_code,
                'course_title': course.course_title,
                'year': course.year,
                'term': course.term,
                'description': course.description,
                'enrolled_date': reg.enrolled_date,
                'status': reg.status
            })
        
        return Response({
            'total_courses': len(courses_data),
            'courses': courses_data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def course_detail(self, request):
        """
        Get specific course details
        
        GET /api/courses/course_detail/?course_id=45
        Headers: Authorization: Token <token>
        """
        course_id = request.query_params.get('course_id')
        
        if not course_id:
            return Response(
                {'error': 'course_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course = Course.objects.get(course_id=course_id)
            
            # Check if student is enrolled
            is_enrolled = CourseRegistration.objects.filter(
                student=request.user,
                course=course,
                status='active'
            ).exists()
            
            return Response({
                'course': CourseSerializer(course).data,
                'is_enrolled': is_enrolled
            }, status=status.HTTP_200_OK)
        
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )