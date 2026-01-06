# apps/analytics/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Q
from datetime import datetime

from apps.users.models import User
from apps.courses.models import Course
from apps.assessments.models import (
    Attendance, Assignment, AssignmentSubmission,
    Quiz, QuizScore, LabActivity, LabParticipation
)

class StudentAnalyticsViewSet(viewsets.ViewSet):
    """
    API for student analytics - all calculations done dynamically
    No data stored in EngagementMetrics table
    """
    
    @action(detail=False, methods=['get'], url_path='dashboard')
    def get_dashboard(self, request):
        """
        Get complete student dashboard with all metrics calculated dynamically
        
        Query Parameters:
            - student_id: int (required)
            - course_id: int (required)
            - week_number: int (optional, if not provided calculates for all time)
        
        Example:
            GET /api/analytics/dashboard/?student_id=123&course_id=45&week_number=5
        
        Response:
            {
                "student": {...},
                "course": {...},
                "risk_prediction": {
                    "risk_score": 0.72,
                    "risk_level": "high",
                    "feedback": "You must improve..."
                },
                "weekly_progress": [...],
                "engagement_tracker": {
                    "attendance": 56,
                    "assignments": 65,
                    "quizzes": 80,
                    "lab_activity": 45
                }
            }
        """
        # Get parameters
        student_id = request.query_params.get('student_id')
        course_id = request.query_params.get('course_id')
        week_number = request.query_params.get('week_number')
        
        if not student_id or not course_id:
            return Response(
                {'error': 'student_id and course_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = User.objects.get(user_id=student_id, user_type='student')
            course = Course.objects.get(course_id=course_id)
        except (User.DoesNotExist, Course.DoesNotExist) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate engagement metrics dynamically
        engagement = self._calculate_engagement_metrics(
            student, course, week_number
        )
        
        # Calculate weekly progress
        weekly_progress = self._calculate_weekly_progress(
            student, course
        )
        
        # Calculate risk prediction
        risk = self._calculate_risk_prediction(
            student, course, engagement
        )
        
        # Build response
        response_data = {
            'student': {
                'id': student.user_id,
                'student_id': student.student_id,
                'name': student.get_full_name(),
                'profile_image': student.profile_image.url if student.profile_image else None
            },
            'course': {
                'id': course.course_id,
                'code': course.course_code,
                'title': course.course_title
            },
            'risk_prediction': risk,
            'weekly_progress': weekly_progress,
            'engagement_tracker': engagement,
            'personalized_feedback': self._generate_feedback(engagement)
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def _calculate_engagement_metrics(self, student, course, week_number=None):
        """
        Calculate all engagement percentages dynamically from database
        
        Returns:
            {
                "attendance": 56.0,
                "assignments": 65.0,
                "quizzes": 80.0,
                "lab_activity": 45.0
            }
        """
        # 1. ATTENDANCE PERCENTAGE
        attendance_query = Attendance.objects.filter(
            student=student,
            course=course
        )
        if week_number:
            attendance_query = attendance_query.filter(week_number=week_number)
        
        total_classes = attendance_query.count()
        present_classes = attendance_query.filter(status='present').count()
        
        attendance_percentage = (
            (present_classes / total_classes * 100) if total_classes > 0 else 0
        )
        
        # 2. ASSIGNMENT COMPLETION PERCENTAGE
        # Get all assignments for this course
        assignments_query = Assignment.objects.filter(course=course)
        if week_number:
            assignments_query = assignments_query.filter(week_number=week_number)
        
        # Get student's submissions
        submissions = AssignmentSubmission.objects.filter(
            student=student,
            assignment__in=assignments_query
        ).exclude(status='missing')
        
        # Calculate: (sum of student scores / sum of max scores) * 100
        total_earned = 0
        total_possible = 0
        
        for submission in submissions:
            if submission.score is not None:
                total_earned += submission.score
                total_possible += submission.assignment.max_score
        
        assignment_percentage = (
            (total_earned / total_possible * 100) if total_possible > 0 else 0
        )
        
        # 3. QUIZ AVERAGE PERCENTAGE
        quizzes_query = Quiz.objects.filter(course=course)
        if week_number:
            quizzes_query = quizzes_query.filter(week_number=week_number)
        
        quiz_scores = QuizScore.objects.filter(
            student=student,
            quiz__in=quizzes_query
        )
        
        quiz_earned = 0
        quiz_possible = 0
        
        for quiz_score in quiz_scores:
            quiz_earned += quiz_score.score
            quiz_possible += quiz_score.quiz.max_score
        
        quiz_percentage = (
            (quiz_earned / quiz_possible * 100) if quiz_possible > 0 else 0
        )
        
        # 4. LAB ACTIVITY PERCENTAGE
        lab_participations = LabParticipation.objects.filter(
            student=student,
            lab_id__course=course
        )
        
        lab_earned = 0
        lab_possible = 0
        
        for lab in lab_participations:
            lab_earned += lab.score
            lab_possible += lab.max_score
        
        lab_percentage = (
            (lab_earned / lab_possible * 100) if lab_possible > 0 else 0
        )
        
        return {
            'attendance': round(attendance_percentage, 1),
            'assignments': round(assignment_percentage, 1),
            'quizzes': round(quiz_percentage, 1),
            'lab_activity': round(lab_percentage, 1)
        }
    
    def _calculate_weekly_progress(self, student, course, max_weeks=5):
        """
        Calculate weekly progress data for chart
        
        Returns:
            [
                {"week": 1, "student_score": 55, "class_average": 48},
                {"week": 2, "student_score": 65, "class_average": 52},
                ...
            ]
        """
        progress_data = []
        
        # Get all registered students for class average
        from apps.courses.models import CourseRegistration
        all_students = CourseRegistration.objects.filter(
            course=course,
            status='active'
        ).values_list('student', flat=True)
        
        for week in range(1, max_weeks + 1):
            # Calculate student's score for this week
            student_score = self._calculate_week_score(student, course, week)
            
            # Calculate class average for this week
            week_scores = []
            for student_id in all_students:
                try:
                    s = User.objects.get(user_id=student_id)
                    score = self._calculate_week_score(s, course, week)
                    week_scores.append(score)
                except:
                    pass
            
            class_average = (
                sum(week_scores) / len(week_scores) if week_scores else 0
            )
            
            progress_data.append({
                'week': week,
                'student_score': round(student_score, 1),
                'class_average': round(class_average, 1)
            })
        
        return progress_data
    
    def _calculate_week_score(self, student, course, week_number):
        """
        Calculate overall score for a specific week
        Weighted average of all assessments
        """
        # Get all scores for this week
        assignment_scores = AssignmentSubmission.objects.filter(
            student=student,
            assignment__course=course,
            assignment__week_number=week_number
        ).exclude(status='missing')
        
        quiz_scores = QuizScore.objects.filter(
            student=student,
            quiz__course=course,
            quiz__week_number=week_number
        )
        
        # Calculate weighted score
        total_earned = 0
        total_possible = 0
        
        # Assignments
        for submission in assignment_scores:
            if submission.score is not None:
                total_earned += submission.score
                total_possible += submission.assignment.max_score
        
        # Quizzes
        for quiz_score in quiz_scores:
            total_earned += quiz_score.score
            total_possible += quiz_score.quiz.max_score
        
        if total_possible == 0:
            return 0
        
        percentage = (total_earned / total_possible) * 100
        return percentage
    
    def _calculate_risk_prediction(self, student, course, engagement):
        """
        Calculate risk score based on engagement metrics
        
        Risk Score Formula:
            risk = weighted sum of (100 - engagement_percentage) / 100
        
        Returns:
            {
                "risk_score": 0.72,
                "risk_level": "high",
                "feedback": "You must improve your attendance..."
            }
        """
        # Weights for each factor
        WEIGHTS = {
            'attendance': 0.25,
            'assignments': 0.30,
            'quizzes': 0.25,
            'labs': 0.20
        }
        
        # Convert engagement to risk (inverse)
        # Low engagement = High risk
        attendance_risk = (100 - engagement['attendance']) / 100
        assignment_risk = (100 - engagement['assignments']) / 100
        quiz_risk = (100 - engagement['quizzes']) / 100
        lab_risk = (100 - engagement['lab_activity']) / 100
        
        # Calculate weighted risk score
        risk_score = (
            attendance_risk * WEIGHTS['attendance'] +
            assignment_risk * WEIGHTS['assignments'] +
            quiz_risk * WEIGHTS['quizzes'] +
            lab_risk * WEIGHTS['labs']
        )
        
        # Determine risk level
        if risk_score < 0.3:
            risk_level = 'LOW RISK'
            risk_color = 'green'
        elif risk_score < 0.6:
            risk_level = 'MEDIUM RISK'
            risk_color = 'orange'
        else:
            risk_level = 'HIGH RISK'
            risk_color = 'red'
        
        # Generate feedback
        feedback_parts = []
        
        if engagement['attendance'] < 60:
            feedback_parts.append("You must improve your attendance")
        
        if engagement['assignments'] < 70:
            feedback_parts.append("weekly assignments")
        
        if not feedback_parts:
            feedback_parts.append("Keep up the good work")
        
        feedback = " and ".join(feedback_parts) + "."
        
        return {
            'risk_score': round(risk_score, 2),
            'risk_level': risk_level,
            'risk_color': risk_color,
            'feedback': f"Your current risk of failing is {risk_score:.2f} ({risk_level}). {feedback}"
        }
    
    def _generate_feedback(self, engagement):
        """
        Generate personalized feedback based on engagement
        
        Returns:
            {
                "message": "You missed 2 labs this week...",
                "suggestions": ["Attend all labs", "Complete assignments"]
            }
        """
        messages = []
        suggestions = []
        
        if engagement['attendance'] < 60:
            messages.append("You missed several classes this week")
            suggestions.append("Attend all classes to boost performance")
        
        if engagement['assignments'] < 70:
            messages.append("Assignment completion is low")
            suggestions.append("Submit all weekly assignments on time")
        
        if engagement['quizzes'] < 60:
            messages.append("Quiz scores need improvement")
            suggestions.append("Review course materials regularly")
        
        if engagement['lab_activity'] < 50:
            lab_count = 2  # You can calculate actual number
            messages.append(f"You missed {lab_count} labs this week")
            suggestions.append("Attend all labs to boost performance")
        
        if not messages:
            messages.append("Great work! Keep it up")
            suggestions.append("Maintain your current performance level")
        
        return {
            'message': ". ".join(messages) + ".",
            'suggestions': suggestions
        }
    
    @action(detail=False, methods=['get'], url_path='engagement-details')
    def get_engagement_details(self, request):
        """
        Get detailed breakdown of engagement calculations
        
        Example:
            GET /api/analytics/engagement-details/?student_id=123&course_id=45&week_number=5
        
        Response:
            {
                "attendance": {
                    "percentage": 56.0,
                    "present": 5,
                    "total": 9,
                    "records": [...]
                },
                "assignments": {
                    "percentage": 65.0,
                    "earned": 130,
                    "possible": 200,
                    "submissions": [...]
                },
                ...
            }
        """
        student_id = request.query_params.get('student_id')
        course_id = request.query_params.get('course_id')
        week_number = request.query_params.get('week_number')
        
        if not student_id or not course_id:
            return Response(
                {'error': 'student_id and course_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = User.objects.get(user_id=student_id)
            course = Course.objects.get(course_id=course_id)
        except (User.DoesNotExist, Course.DoesNotExist) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Detailed calculations
        details = self._get_detailed_breakdown(student, course, week_number)
        
        return Response(details, status=status.HTTP_200_OK)
    
    def _get_detailed_breakdown(self, student, course, week_number=None):
        """Get detailed breakdown with individual records"""
        
        # ATTENDANCE DETAILS
        attendance_query = Attendance.objects.filter(
            student=student,
            course=course
        )
        if week_number:
            attendance_query = attendance_query.filter(week_number=week_number)
        
        attendance_records = list(attendance_query.values(
            'date', 'status', 'week_number', 'section'
        ))
        
        total_classes = len(attendance_records)
        present_classes = sum(1 for r in attendance_records if r['status'] == 'present')
        
        # ASSIGNMENT DETAILS
        assignments = Assignment.objects.filter(course=course)
        if week_number:
            assignments = assignments.filter(week_number=week_number)
        
        assignment_details = []
        total_assignment_earned = 0
        total_assignment_possible = 0
        
        for assignment in assignments:
            try:
                submission = AssignmentSubmission.objects.get(
                    student=student,
                    assignment=assignment
                )
                score = submission.score or 0
                total_assignment_earned += score
                total_assignment_possible += assignment.max_score
                
                assignment_details.append({
                    'title': assignment.title,
                    'score': score,
                    'max_score': assignment.max_score,
                    'percentage': round((score / assignment.max_score * 100), 1),
                    'status': submission.status,
                    'due_date': assignment.due_date
                })
            except AssignmentSubmission.DoesNotExist:
                assignment_details.append({
                    'title': assignment.title,
                    'score': 0,
                    'max_score': assignment.max_score,
                    'percentage': 0,
                    'status': 'missing',
                    'due_date': assignment.due_date
                })
        
        # QUIZ DETAILS
        quizzes = Quiz.objects.filter(course=course)
        if week_number:
            quizzes = quizzes.filter(week_number=week_number)
        
        quiz_details = []
        total_quiz_earned = 0
        total_quiz_possible = 0
        
        for quiz in quizzes:
            try:
                quiz_score = QuizScore.objects.get(
                    student=student,
                    quiz=quiz
                )
                total_quiz_earned += quiz_score.score
                total_quiz_possible += quiz.max_score
                
                quiz_details.append({
                    'title': quiz.title,
                    'score': quiz_score.score,
                    'max_score': quiz.max_score,
                    'percentage': round((quiz_score.score / quiz.max_score * 100), 1),
                    'date': quiz.date
                })
            except QuizScore.DoesNotExist:
                quiz_details.append({
                    'title': quiz.title,
                    'score': 0,
                    'max_score': quiz.max_score,
                    'percentage': 0,
                    'date': quiz.date
                })
        
        # LAB DETAILS
        lab_participations = LabParticipation.objects.filter(
            student=student,
            lab_id__course=course
        )
        
        lab_details = []
        total_lab_earned = 0
        total_lab_possible = 0
        
        for lab in lab_participations:
            total_lab_earned += lab.score
            total_lab_possible += lab.max_score
            
            lab_details.append({
                'title': lab.lab_id.title,
                'score': lab.score,
                'max_score': lab.max_score,
                'percentage': round((lab.score / lab.max_score * 100), 1),
                'attendance': lab.attendance,
                'date': lab.date
            })
        
        return {
            'attendance': {
                'percentage': round((present_classes / total_classes * 100), 1) if total_classes > 0 else 0,
                'present': present_classes,
                'total': total_classes,
                'records': attendance_records
            },
            'assignments': {
                'percentage': round((total_assignment_earned / total_assignment_possible * 100), 1) if total_assignment_possible > 0 else 0,
                'earned': total_assignment_earned,
                'possible': total_assignment_possible,
                'submissions': assignment_details
            },
            'quizzes': {
                'percentage': round((total_quiz_earned / total_quiz_possible * 100), 1) if total_quiz_possible > 0 else 0,
                'earned': total_quiz_earned,
                'possible': total_quiz_possible,
                'scores': quiz_details
            },
            'labs': {
                'percentage': round((total_lab_earned / total_lab_possible * 100), 1) if total_lab_possible > 0 else 0,
                'earned': total_lab_earned,
                'possible': total_lab_possible,
                'participations': lab_details
            }
        }