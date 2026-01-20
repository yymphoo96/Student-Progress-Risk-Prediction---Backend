# apps/analytics/views.py - UPDATE student_dashboard method

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.assessments.models import (
    Attendance, Assignment, AssignmentSubmission,
    Quiz, QuizScore, LabParticipation
)
from apps.courses.models import Course, CourseRegistration, CourseTeaching
from .ml_predictor import ml_predictor

class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def student_dashboard(self, request):
        course_id = request.query_params.get('course_id')
        
        if not course_id:
            return Response({'error': 'course_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        student = request.user
        
        try:
            course = Course.objects.get(course_id=course_id)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=404)
        
        # Get course info
        teacher_name = 'Not Assigned'
        teaching = CourseTeaching.objects.filter(course=course).first()
        if teaching:
            teacher_name = teaching.teacher.get_full_name() or teaching.teacher.username
        
        current_week = self._get_current_week(student, course_id)
        
        # Calculate engagement metrics
        engagement = {
            'attendance': self._calc_attendance(student, course_id),
            'assignments': self._calc_assignments(student, course_id),
            'quizzes': self._calc_quizzes(student, course_id),
            'lab_activity': self._calc_labs(student, course_id)
        }
        
        # Overall engagement (exclude labs)
        overall_engagement = round(
            (engagement['attendance'] + engagement['assignments'] + engagement['quizzes']) / 3,
            1
        )
        
        # ✅ Get gender from student profile
        # Female = 0, Male = 1
        gender = self._get_gender(student)
        
        # ✅ Use ML model for risk prediction with gender
        risk = ml_predictor.predict_risk(
            quiz_avg=engagement['quizzes'],
            assignment_avg=engagement['assignments'],
            attendance_rate=engagement['attendance'],
            gender=gender
        )
        
        weekly = self._calc_weekly_progress(student, course_id)
        
        return Response({
            'course_info': {
                'course_code': course.course_code,
                'course_title': course.course_title,
                'teacher_name': teacher_name,
                'year': course.year,
                'term': course.term,
                'current_week': current_week,
                'total_weeks': 7
            },
            'student': {
                'name': student.get_full_name() or student.username,
                'student_id': student.student_id or 'N/A',
                'email': student.email,
                'gender': 'Female' if gender == 0 else 'Male'  # Optional: include in response
            },
            'engagement': engagement,
            'overall_engagement': overall_engagement,
            'risk': risk,
            'weekly_progress': weekly
        })
    
    def _get_gender(self, student):
        """
        Get gender from student profile
        Returns: 0 for Female, 1 for Male
        """
        # Check if student has gender field
        if hasattr(student, 'gender'):
            gender_value = student.gender
            
            # Handle different formats
            if isinstance(gender_value, str):
                gender_lower = gender_value.lower().strip()
                if gender_lower in ['female', 'f', 'woman', '0']:
                    return 0
                elif gender_lower in ['male', 'm', 'man', '1']:
                    return 1
            elif isinstance(gender_value, int):
                return 0 if gender_value == 0 else 1
        
        # Default to Male if not specified (or you can default to Female)
        return 1
    
    def _get_current_week(self, student, course_id):
        latest = Attendance.objects.filter(
            student=student,
            course_id=course_id
        ).order_by('-week_number').first()
        
        return latest.week_number if latest else 1
    
    def _calc_attendance(self, student, course_id):
        total = Attendance.objects.filter(student=student, course_id=course_id).count()
        present = Attendance.objects.filter(student=student, course_id=course_id, status='present').count()
        return round((present / total * 100) if total > 0 else 0, 1)
    
    def _calc_assignments(self, student, course_id):
        subs = AssignmentSubmission.objects.filter(
            student=student, assignment__course_id=course_id
        ).exclude(status='missing')
        earned = sum(s.score or 0 for s in subs)
        possible = sum(s.assignment.max_score for s in subs)
        return round((earned / possible * 100) if possible > 0 else 0, 1)
    
    def _calc_quizzes(self, student, course_id):
        scores = QuizScore.objects.filter(student=student, quiz__course_id=course_id)
        earned = sum(s.score for s in scores)
        possible = sum(s.quiz.max_score for s in scores)
        return round((earned / possible * 100) if possible > 0 else 0, 1)
    
    def _calc_labs(self, student, course_id):
        labs = LabParticipation.objects.filter(student=student, lab__course_id=course_id)
        earned = sum(l.score for l in labs)
        possible = sum(l.max_score for l in labs)
        return round((earned / possible * 100) if possible > 0 else 0, 1)
    
    def _calc_weekly_progress(self, student, course_id):
        """Calculate weekly progress for 7 weeks"""
        result = []
        
        all_students = CourseRegistration.objects.filter(
            course_id=course_id,
            status='active'
        ).values_list('student_id', flat=True)
        
        has_week_2_data = (
            AssignmentSubmission.objects.filter(
                student=student, assignment__course_id=course_id, assignment__week_number=2
            ).exists() or
            QuizScore.objects.filter(
                student=student, quiz__course_id=course_id, quiz__week_number=2
            ).exists()
        )
        
        has_week_3_data = (
            AssignmentSubmission.objects.filter(
                student=student, assignment__course_id=course_id, assignment__week_number=3
            ).exists() or
            QuizScore.objects.filter(
                student=student, quiz__course_id=course_id, quiz__week_number=3
            ).exists()
        )
        
        show_data = has_week_2_data or has_week_3_data
        
        for week in range(1, 8):
            student_score = self._calc_week_score(student, course_id, week)
            
            week_scores = []
            for sid in all_students:
                score = self._calc_week_score_for_student(sid, course_id, week)
                if score is not None:
                    week_scores.append(score)
            
            class_avg = sum(week_scores) / len(week_scores) if week_scores else None
            
            if show_data and student_score is not None:
                result.append({
                    'week': week,
                    'student_score': round(student_score, 1),
                    'class_average': round(class_avg, 1) if class_avg is not None else round(student_score, 1),
                    'has_data': True
                })
            else:
                result.append({
                    'week': week,
                    'student_score': None,
                    'class_average': None,
                    'has_data': False
                })
        
        return result
    
    def _calc_week_score(self, student, course_id, week_number):
        assignment_subs = AssignmentSubmission.objects.filter(
            student=student,
            assignment__course_id=course_id,
            assignment__week_number=week_number
        ).exclude(status='missing')
        
        quiz_scores = QuizScore.objects.filter(
            student=student,
            quiz__course_id=course_id,
            quiz__week_number=week_number
        )
        
        scores = []
        
        for sub in assignment_subs:
            if sub.score is not None:
                percentage = (sub.score / sub.assignment.max_score * 100) if sub.assignment.max_score > 0 else 0
                scores.append(percentage)
        
        for qs in quiz_scores:
            percentage = (qs.score / qs.quiz.max_score * 100) if qs.quiz.max_score > 0 else 0
            scores.append(percentage)
        
        return sum(scores) / len(scores) if scores else None
    
    def _calc_week_score_for_student(self, student_id, course_id, week_number):
        from apps.users.models import User
        try:
            student = User.objects.get(user_id=student_id)
            return self._calc_week_score(student, course_id, week_number)
        except:
            return None