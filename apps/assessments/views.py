import csv
import io
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.users.models import User
from apps.courses.models import Course
from .models import (
    Attendance, Assignment, AssignmentSubmission,
    Quiz, QuizScore, LabActivity, LabParticipation,
)


class CSVUploadView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        csv_file = request.FILES.get('file')
        data_type = request.data.get('type')  # attendance, assignment_scores, quiz_scores, lab_scores
        course_code = request.data.get('course_code')

        if not csv_file:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)
        if not csv_file.name.endswith('.csv'):
            return Response({'error': 'File must be a CSV.'}, status=status.HTTP_400_BAD_REQUEST)
        if not data_type:
            return Response({'error': 'type is required (attendance, assignment_scores, quiz_scores, lab_scores).'}, status=status.HTTP_400_BAD_REQUEST)
        if not course_code:
            return Response({'error': 'course_code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            course = Course.objects.get(course_code=course_code)
        except Course.DoesNotExist:
            return Response({'error': f'Course {course_code} not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            decoded = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded))
            rows = list(reader)
        except Exception as e:
            return Response({'error': f'Failed to parse CSV: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        if not rows:
            return Response({'error': 'CSV file is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        handler = {
            'attendance': self._handle_attendance,
            'assignment_scores': self._handle_assignment_scores,
            'quiz_scores': self._handle_quiz_scores,
            'lab_scores': self._handle_lab_scores,
        }.get(data_type)

        if not handler:
            return Response(
                {'error': f'Invalid type: {data_type}. Must be one of: attendance, assignment_scores, quiz_scores, lab_scores.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return handler(rows, course)

    def _get_student(self, student_id):
        try:
            return User.objects.get(student_id=student_id, user_type='student')
        except User.DoesNotExist:
            return None

    def _handle_attendance(self, rows, course):
        """
        Expected CSV columns: student_id, date, week_number, status, section
        - student_id: the student's student_id field
        - date: YYYY-MM-DD
        - week_number: integer
        - status: present or absent
        - section: first-section, second-section, third-section, fourth-section
        """
        required = {'student_id', 'date', 'week_number', 'status', 'section'}
        missing = required - set(rows[0].keys())
        if missing:
            return Response({'error': f'Missing columns: {", ".join(missing)}'}, status=status.HTTP_400_BAD_REQUEST)

        created, updated, errors = 0, 0, []
        for i, row in enumerate(rows, start=2):  # row 2 in CSV (after header)
            student = self._get_student(row['student_id'].strip())
            if not student:
                errors.append(f'Row {i}: student_id {row["student_id"]} not found.')
                continue

            try:
                date = datetime.strptime(row['date'].strip(), '%Y-%m-%d').date()
            except ValueError:
                errors.append(f'Row {i}: invalid date format (expected YYYY-MM-DD).')
                continue

            obj, was_created = Attendance.objects.update_or_create(
                student=student,
                course=course,
                date=date,
                section=row['section'].strip(),
                defaults={
                    'week_number': int(row['week_number']),
                    'status': row['status'].strip(),
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return Response({
            'message': f'Attendance upload complete. Created: {created}, Updated: {updated}.',
            'errors': errors,
        })

    def _handle_assignment_scores(self, rows, course):
        """
        Expected CSV columns: student_id, assignment_title, score, status
        """
        required = {'student_id', 'assignment_title', 'score'}
        missing = required - set(rows[0].keys())
        if missing:
            return Response({'error': f'Missing columns: {", ".join(missing)}'}, status=status.HTTP_400_BAD_REQUEST)

        created, updated, errors = 0, 0, []
        for i, row in enumerate(rows, start=2):
            student = self._get_student(row['student_id'].strip())
            if not student:
                errors.append(f'Row {i}: student_id {row["student_id"]} not found.')
                continue

            try:
                assignment = Assignment.objects.get(course=course, title=row['assignment_title'].strip())
            except Assignment.DoesNotExist:
                errors.append(f'Row {i}: assignment "{row["assignment_title"]}" not found in course.')
                continue

            row_status = row.get('status', 'graded').strip() or 'graded'
            obj, was_created = AssignmentSubmission.objects.update_or_create(
                assignment=assignment,
                student=student,
                defaults={
                    'score': float(row['score']),
                    'status': row_status,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return Response({
            'message': f'Assignment scores upload complete. Created: {created}, Updated: {updated}.',
            'errors': errors,
        })

    def _handle_quiz_scores(self, rows, course):
        """
        Expected CSV columns: student_id, quiz_title, score, status
        """
        required = {'student_id', 'quiz_title', 'score'}
        missing = required - set(rows[0].keys())
        if missing:
            return Response({'error': f'Missing columns: {", ".join(missing)}'}, status=status.HTTP_400_BAD_REQUEST)

        created, updated, errors = 0, 0, []
        for i, row in enumerate(rows, start=2):
            student = self._get_student(row['student_id'].strip())
            if not student:
                errors.append(f'Row {i}: student_id {row["student_id"]} not found.')
                continue

            try:
                quiz = Quiz.objects.get(course=course, title=row['quiz_title'].strip())
            except Quiz.DoesNotExist:
                errors.append(f'Row {i}: quiz "{row["quiz_title"]}" not found in course.')
                continue

            row_status = row.get('status', 'graded').strip() or 'graded'
            obj, was_created = QuizScore.objects.update_or_create(
                quiz=quiz,
                student=student,
                defaults={
                    'score': float(row['score']),
                    'status': row_status,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return Response({
            'message': f'Quiz scores upload complete. Created: {created}, Updated: {updated}.',
            'errors': errors,
        })

    def _handle_lab_scores(self, rows, course):
        """
        Expected CSV columns: student_id, lab_title, date, score, max_score, attendance, remark
        """
        required = {'student_id', 'lab_title', 'score'}
        missing = required - set(rows[0].keys())
        if missing:
            return Response({'error': f'Missing columns: {", ".join(missing)}'}, status=status.HTTP_400_BAD_REQUEST)

        created, updated, errors = 0, 0, []
        for i, row in enumerate(rows, start=2):
            student = self._get_student(row['student_id'].strip())
            if not student:
                errors.append(f'Row {i}: student_id {row["student_id"]} not found.')
                continue

            try:
                lab = LabActivity.objects.get(course=course, title=row['lab_title'].strip())
            except LabActivity.DoesNotExist:
                errors.append(f'Row {i}: lab "{row["lab_title"]}" not found in course.')
                continue

            defaults = {
                'score': float(row['score']),
                'max_score': float(row.get('max_score', lab.max_score)),
                'attendance': row.get('attendance', 'true').strip().lower() in ('true', '1', 'yes'),
                'remark': row.get('remark', '').strip(),
            }
            if row.get('date'):
                defaults['date'] = datetime.strptime(row['date'].strip(), '%Y-%m-%d').date()
            else:
                defaults['date'] = lab.date

            obj, was_created = LabParticipation.objects.update_or_create(
                lab=lab,
                student=student,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return Response({
            'message': f'Lab scores upload complete. Created: {created}, Updated: {updated}.',
            'errors': errors,
        })
