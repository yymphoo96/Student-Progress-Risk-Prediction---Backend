from django.contrib import admin
from django.db.models import Avg, Count
from django.utils.html import format_html
from .models import Question, Survey


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'detail_preview', 'created_at']
    search_fields = ['title', 'detail']
    readonly_fields = ['created_at']
    ordering = ['question_id']

    fieldsets = (
        ('Question Content', {
            'fields': ('title', 'detail'),
            'description': 'Title is the short label (e.g. "Engagement"). '
                           'Detail is the full question shown to students.',
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def detail_preview(self, obj):
        return obj.detail[:80] + '…' if len(obj.detail) > 80 else obj.detail
    detail_preview.short_description = 'Detail'


class ScoreBadge:
    """Helper to render a coloured badge for a score value."""
    @staticmethod
    def render(score):
        if score is None:
            return '—'
        if score >= 4.0:
            color, bg = '#1a7f37', '#d1f0da'
        elif score >= 3.0:
            color, bg = '#7a5500', '#fff3cd'
        else:
            color, bg = '#b91c1c', '#fee2e2'
        return format_html(
            '<span style="background:{bg};color:{color};padding:3px 10px;'
            'border-radius:12px;font-weight:700;font-size:13px;">{score}</span>',
            bg=bg, color=color, score=f'{score:.1f}',
        )


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = [
        'survey_id', 'course_link', 'week_number', 'student_email',
        'question_title', 'score_badge', 'done_badge', 'created_at',
    ]
    list_filter = ['course', 'week_number', 'question', 'done']
    search_fields = ['student__email', 'student__first_name', 'student__last_name',
                     'course__course_code', 'question__title']
    readonly_fields = ['created_at', 'score_badge']
    ordering = ['-created_at']
    list_per_page = 40

    fieldsets = (
        ('Survey Entry', {
            'fields': ('course', 'question', 'student', 'week_number'),
        }),
        ('Result', {
            'fields': ('score', 'done'),
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    # --- Custom display columns ---

    def course_link(self, obj):
        return format_html(
            '<b>{}</b><br><small style="color:#666">{}</small>',
            obj.course.course_code,
            obj.course.course_title[:40],
        )
    course_link.short_description = 'Course'
    course_link.admin_order_field = 'course__course_code'

    def student_email(self, obj):
        name = f"{obj.student.first_name} {obj.student.last_name}".strip()
        return format_html(
            '{}<br><small style="color:#888">{}</small>',
            name or obj.student.username,
            obj.student.email,
        )
    student_email.short_description = 'Student'
    student_email.admin_order_field = 'student__email'

    def question_title(self, obj):
        return obj.question.title
    question_title.short_description = 'Question'
    question_title.admin_order_field = 'question__title'

    def score_badge(self, obj):
        return ScoreBadge.render(obj.score)
    score_badge.short_description = 'Score'
    score_badge.allow_tags = True

    def done_badge(self, obj):
        if obj.done:
            return format_html(
                '<span style="color:#1a7f37;font-weight:700;">✓ Done</span>'
            )
        return format_html(
            '<span style="color:#b91c1c;font-weight:700;">✗ Pending</span>'
        )
    done_badge.short_description = 'Status'
    done_badge.admin_order_field = 'done'

    # --- Summary change list (per-week averages) shown via custom header ---

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Build a quick per-week average table for context
        summary = (
            Survey.objects
            .filter(done=True)
            .values('course__course_code', 'week_number', 'question__title')
            .annotate(avg_score=Avg('score'), count=Count('survey_id'))
            .order_by('course__course_code', 'week_number', 'question__title')
        )
        extra_context['survey_summary'] = list(summary)
        return super().changelist_view(request, extra_context=extra_context)
