# apps/assessments/admin.py

import csv
import io
from datetime import datetime

from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html

from .models import (
    Attendance, Assignment, AssignmentSubmission,
    Quiz, QuizScore, LabActivity, LabParticipation
)
from ..users.models import User
from ..courses.models import Course


class CSVUploadMixin:
    """Mixin that adds a CSV upload page to any ModelAdmin."""
    change_list_template = 'admin/assessments/change_list_with_csv.html'

    # Subclasses must define these
    csv_expected_columns = ''
    csv_example = ''

    def get_urls(self):
        custom_urls = [
            path(
                'upload-csv/',
                self.admin_site.admin_view(self.csv_upload_view),
                name=f'{self.model._meta.model_name}-csv-upload',
            ),
        ]
        return custom_urls + super().get_urls()

    def csv_upload_view(self, request):
        if request.method == 'POST':
            csv_file = request.FILES.get('csv_file')
            if not csv_file:
                messages.error(request, 'Please select a CSV file.')
                return redirect('..')

            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'File must be a .csv file.')
                return redirect('..')

            try:
                decoded = csv_file.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(decoded))
                rows = list(reader)
            except Exception as e:
                messages.error(request, f'Failed to parse CSV: {e}')
                return redirect('..')

            if not rows:
                messages.error(request, 'CSV file is empty.')
                return redirect('..')

            created, updated, errors = self.process_csv_rows(rows)

            context = {
                **self.admin_site.each_context(request),
                'model_name': self.model._meta.verbose_name_plural.title(),
                'expected_columns': self.csv_expected_columns,
                'example_csv': self.csv_example,
                'errors': errors,
                'success_message': f'Upload complete. Created: {created}, Updated: {updated}.',
            }
            return render(request, 'admin/assessments/csv_upload.html', context)

        context = {
            **self.admin_site.each_context(request),
            'model_name': self.model._meta.verbose_name_plural.title(),
            'expected_columns': self.csv_expected_columns,
            'example_csv': self.csv_example,
            'errors': None,
            'success_message': None,
        }
        return render(request, 'admin/assessments/csv_upload.html', context)

    def process_csv_rows(self, rows):
        """Override in subclass. Return (created, updated, errors_list)."""
        raise NotImplementedError

    @staticmethod
    def get_student(student_id):
        try:
            return User.objects.get(student_id=student_id, user_type='student')
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_course(course_code):
        try:
            return Course.objects.get(course_code=course_code)
        except Course.DoesNotExist:
            return None


@admin.register(Attendance)
class AttendanceAdmin(CSVUploadMixin, admin.ModelAdmin):
    list_display = ['student_name', 'course_code', 'date', 'week_number', 'status_badge', 'show_section']
    list_filter = ['status', 'week_number', 'date', 'section', 'student', 'course']
    search_fields = ['student__email', 'student__username', 'student__first_name', 'student__last_name', 'course__course_code']
    date_hierarchy = 'date'

    @admin.display(description='Student', ordering='student__first_name')
    def student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    @admin.display(description='Course', ordering='course__course_code')
    def course_code(self, obj):
        return obj.course.course_code

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {'present': '#065F46', 'absent': '#991B1B'}
        bg = {'present': '#D1FAE5', 'absent': '#FEE2E2'}
        color = colors.get(obj.status, '#111827')
        background = bg.get(obj.status, '#F3F4F6')
        return format_html(
            '<span style="background:{bg}; color:{c}; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700;">{t}</span>',
            bg=background, c=color, t=obj.get_status_display()
        )

    @admin.display(description='Section', ordering='section')
    def show_section(self, obj):
        return obj.get_section_display()

    csv_expected_columns = 'student_id, course_code, date, week_number, status, section'
    csv_example = (
        'student_id,course_code,date,week_number,status,section\n'
        'STU001,CS101,2026-02-20,1,present,first-section\n'
        'STU002,CS101,2026-02-20,1,absent,first-section'
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "student":
            kwargs["queryset"] = User.objects.filter(
                user_type='student'
            ).select_related().order_by('first_name', 'last_name')
        if db_field.name == "course":
            kwargs["queryset"] = Course.objects.filter(
                courseregistration__status='active'
            ).distinct().order_by('course_code')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['student'].help_text = 'Select a student (teachers and admins are filtered out)'
        form.base_fields['course'].help_text = 'Select the course for this attendance record'
        return form

    def process_csv_rows(self, rows):
        required = {'student_id', 'course_code', 'date', 'week_number', 'status', 'section'}
        missing = required - set(rows[0].keys())
        if missing:
            return 0, 0, [f'Missing columns: {", ".join(missing)}']

        created, updated, errors = 0, 0, []
        for i, row in enumerate(rows, start=2):
            student = self.get_student(row['student_id'].strip())
            if not student:
                errors.append(f'Row {i}: student_id "{row["student_id"]}" not found.')
                continue

            course = self.get_course(row['course_code'].strip())
            if not course:
                errors.append(f'Row {i}: course_code "{row["course_code"]}" not found.')
                continue

            try:
                date = datetime.strptime(row['date'].strip(), '%Y-%m-%d').date()
            except ValueError:
                errors.append(f'Row {i}: invalid date "{row["date"]}" (expected YYYY-MM-DD).')
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
            created += was_created
            updated += not was_created

        return created, updated, errors


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'show_course', 'due_date', 'max_score', 'week_number']
    list_filter = ['course', 'week_number', 'due_date']
    search_fields = ['title', 'course__course_code']
    date_hierarchy = 'due_date'

    @admin.display(description='Course', ordering='course__course_code')
    def show_course(self, obj):
        return obj.course.course_code


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(CSVUploadMixin, admin.ModelAdmin):
    list_display = ['student_name', 'assignment_title', 'score_display', 'status_badge', 'submission_date']
    list_filter = ['status', 'submission_date', 'student', 'assignment']
    search_fields = ['student__email', 'student__username', 'student__first_name', 'student__last_name', 'assignment__title']
    date_hierarchy = 'submission_date'

    @admin.display(description='Student', ordering='student__first_name')
    def student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    @admin.display(description='Assignment', ordering='assignment__title')
    def assignment_title(self, obj):
        return obj.assignment.title

    @admin.display(description='Score', ordering='score')
    def score_display(self, obj):
        if obj.score is None:
            return '—'
        color = '#059669' if obj.score >= 80 else '#92400E' if obj.score >= 60 else '#DC2626'
        return format_html(
            '<span style="color:{c}; font-weight:700;">{s}</span>',
            c=color, s=obj.score
        )

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        color_map = {
            'graded': ('#065F46', '#D1FAE5'),
            'submitted': ('#1E3A5F', '#DBEAFE'),
            'late-submitted': ('#92400E', '#FEF3C7'),
            'Not Submitted': ('#991B1B', '#FEE2E2'),
        }
        color, bg = color_map.get(obj.status, ('#111827', '#F3F4F6'))
        return format_html(
            '<span style="background:{bg}; color:{c}; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700;">{t}</span>',
            bg=bg, c=color, t=obj.get_status_display()
        )

    csv_expected_columns = 'student_id, course_code, assignment_title, score, status'
    csv_example = (
        'student_id,course_code,assignment_title,score,status\n'
        'STU001,CS101,Homework 1,85,graded\n'
        'STU002,CS101,Homework 1,90,graded'
    )

    def process_csv_rows(self, rows):
        required = {'student_id', 'course_code', 'assignment_title', 'score'}
        missing = required - set(rows[0].keys())
        if missing:
            return 0, 0, [f'Missing columns: {", ".join(missing)}']

        created, updated, errors = 0, 0, []
        for i, row in enumerate(rows, start=2):
            student = self.get_student(row['student_id'].strip())
            if not student:
                errors.append(f'Row {i}: student_id "{row["student_id"]}" not found.')
                continue

            course = self.get_course(row['course_code'].strip())
            if not course:
                errors.append(f'Row {i}: course_code "{row["course_code"]}" not found.')
                continue

            try:
                assignment = Assignment.objects.get(course=course, title=row['assignment_title'].strip())
            except Assignment.DoesNotExist:
                errors.append(f'Row {i}: assignment "{row["assignment_title"]}" not found in {course.course_code}.')
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
            created += was_created
            updated += not was_created

        return created, updated, errors


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'show_course', 'date', 'max_score', 'week_number']
    list_filter = ['course', 'week_number', 'date']
    search_fields = ['title', 'course__course_code']
    date_hierarchy = 'date'

    @admin.display(description='Course', ordering='course__course_code')
    def show_course(self, obj):
        return obj.course.course_code


@admin.register(QuizScore)
class QuizScoreAdmin(CSVUploadMixin, admin.ModelAdmin):
    list_display = ['student_name', 'quiz_title', 'score_display', 'submitted_date']
    list_filter = ['quiz__course', 'submitted_date', 'student', 'quiz']
    search_fields = ['student__email', 'student__username', 'student__first_name', 'student__last_name', 'quiz__title']
    date_hierarchy = 'submitted_date'

    @admin.display(description='Student', ordering='student__first_name')
    def student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    @admin.display(description='Quiz', ordering='quiz__title')
    def quiz_title(self, obj):
        return obj.quiz.title

    @admin.display(description='Score', ordering='score')
    def score_display(self, obj):
        color = '#059669' if obj.score >= 80 else '#92400E' if obj.score >= 60 else '#DC2626'
        return format_html(
            '<span style="color:{c}; font-weight:700;">{s}</span>',
            c=color, s=obj.score
        )

    csv_expected_columns = 'student_id, course_code, quiz_title, score, status'
    csv_example = (
        'student_id,course_code,quiz_title,score,status\n'
        'STU001,CS101,Quiz 1,45,graded\n'
        'STU002,CS101,Quiz 1,38,graded'
    )

    def process_csv_rows(self, rows):
        required = {'student_id', 'course_code', 'quiz_title', 'score'}
        missing = required - set(rows[0].keys())
        if missing:
            return 0, 0, [f'Missing columns: {", ".join(missing)}']

        created, updated, errors = 0, 0, []
        for i, row in enumerate(rows, start=2):
            student = self.get_student(row['student_id'].strip())
            if not student:
                errors.append(f'Row {i}: student_id "{row["student_id"]}" not found.')
                continue

            course = self.get_course(row['course_code'].strip())
            if not course:
                errors.append(f'Row {i}: course_code "{row["course_code"]}" not found.')
                continue

            try:
                quiz = Quiz.objects.get(course=course, title=row['quiz_title'].strip())
            except Quiz.DoesNotExist:
                errors.append(f'Row {i}: quiz "{row["quiz_title"]}" not found in {course.course_code}.')
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
            created += was_created
            updated += not was_created

        return created, updated, errors


@admin.register(LabActivity)
class LabActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'course_code', 'teacher_name', 'date', 'max_score', 'week_number']
    list_filter = ['course', 'week_number', 'date']
    search_fields = ['title', 'course__course_code', 'teacher__username']
    date_hierarchy = 'date'

    @admin.display(description='Course', ordering='course__course_code')
    def course_code(self, obj):
        return obj.course.course_code

    @admin.display(description='Teacher', ordering='teacher__first_name')
    def teacher_name(self, obj):
        return obj.teacher.get_full_name() or obj.teacher.username


@admin.register(LabParticipation)
class LabParticipationAdmin(CSVUploadMixin, admin.ModelAdmin):
    list_display = ['student_name', 'lab_title', 'date', 'score_display', 'max_score', 'attendance_badge']
    list_filter = ['attendance', 'date', 'lab__course']
    search_fields = ['student__email', 'student__username', 'student__first_name', 'student__last_name', 'lab__title']
    date_hierarchy = 'date'

    @admin.display(description='Student', ordering='student__first_name')
    def student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    @admin.display(description='Lab', ordering='lab__title')
    def lab_title(self, obj):
        return obj.lab.title

    @admin.display(description='Score', ordering='score')
    def score_display(self, obj):
        pct = (obj.score / obj.max_score * 100) if obj.max_score else 0
        color = '#059669' if pct >= 80 else '#92400E' if pct >= 60 else '#DC2626'
        return format_html(
            '<span style="color:{c}; font-weight:700;">{s}</span>',
            c=color, s=obj.score
        )

    @admin.display(description='Attended', ordering='attendance')
    def attendance_badge(self, obj):
        if obj.attendance:
            return format_html(
                '<span style="background:#D1FAE5; color:#065F46; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700;">Yes</span>'
            )
        return format_html(
            '<span style="background:#FEE2E2; color:#991B1B; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700;">No</span>'
        )

    csv_expected_columns = 'student_id, course_code, lab_title, date, score, max_score, attendance, remark'
    csv_example = (
        'student_id,course_code,lab_title,date,score,max_score,attendance,remark\n'
        'STU001,CS101,Lab 1,2026-02-20,80,100,true,Good work\n'
        'STU002,CS101,Lab 1,2026-02-20,75,100,true,'
    )

    def process_csv_rows(self, rows):
        required = {'student_id', 'course_code', 'lab_title', 'score'}
        missing = required - set(rows[0].keys())
        if missing:
            return 0, 0, [f'Missing columns: {", ".join(missing)}']

        created, updated, errors = 0, 0, []
        for i, row in enumerate(rows, start=2):
            student = self.get_student(row['student_id'].strip())
            if not student:
                errors.append(f'Row {i}: student_id "{row["student_id"]}" not found.')
                continue

            course = self.get_course(row['course_code'].strip())
            if not course:
                errors.append(f'Row {i}: course_code "{row["course_code"]}" not found.')
                continue

            try:
                lab = LabActivity.objects.get(course=course, title=row['lab_title'].strip())
            except LabActivity.DoesNotExist:
                errors.append(f'Row {i}: lab "{row["lab_title"]}" not found in {course.course_code}.')
                continue

            defaults = {
                'score': float(row['score']),
                'max_score': float(row.get('max_score', lab.max_score) or lab.max_score),
                'attendance': row.get('attendance', 'true').strip().lower() in ('true', '1', 'yes'),
                'remark': row.get('remark', '').strip(),
            }
            if row.get('date', '').strip():
                try:
                    defaults['date'] = datetime.strptime(row['date'].strip(), '%Y-%m-%d').date()
                except ValueError:
                    errors.append(f'Row {i}: invalid date "{row["date"]}" (expected YYYY-MM-DD).')
                    continue
            else:
                defaults['date'] = lab.date

            obj, was_created = LabParticipation.objects.update_or_create(
                lab=lab,
                student=student,
                defaults=defaults,
            )
            created += was_created
            updated += not was_created

        return created, updated, errors
