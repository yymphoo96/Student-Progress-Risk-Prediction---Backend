from collections import defaultdict

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Avg, Count

from apps.courses.models import Course, CourseTeaching, CourseRegistration
from .models import Survey, Question


def _require_teacher(view_func):
    """Allow staff OR teacher/admin user_type."""
    from functools import wraps
    from django.contrib.auth.decorators import login_required

    @login_required(login_url='/admin/login/')
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if u.is_staff or getattr(u, 'user_type', '') in ('teacher', 'admin'):
            return view_func(request, *args, **kwargs)
        return redirect('/admin/login/')
    return _wrapped


@_require_teacher
def survey_dashboard(request):
    user = request.user
    if getattr(user, 'user_type', '') == 'admin' or user.is_staff:
        courses = Course.objects.all().order_by('course_code')
    else:
        course_ids = CourseTeaching.objects.filter(
            teacher=user
        ).values_list('course_id', flat=True)
        courses = Course.objects.filter(
            course_id__in=course_ids
        ).order_by('course_code')

    return render(request, 'dashboard/survey_dashboard.html', {'courses': courses})


@_require_teacher
def survey_dashboard_data(request):
    course_id = request.GET.get('course_id')
    if not course_id:
        return JsonResponse({'error': 'course_id required'}, status=400)

    try:
        course = Course.objects.get(course_id=course_id)
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)

    # ── Single query: one average per (week_number × question) ──────────────
    # grouping at DB level guarantees NO duplicates and NO per-record leakage
    raw = (
        Survey.objects
        .filter(course=course, done=True, score__isnull=False)
        .values('week_number', 'question__title')
        .annotate(
            avg_score=Avg('score'),
            resp_count=Count('student', distinct=True),
        )
        .order_by('week_number', 'question__title')
    )

    # Build {week_number: {metric_title: avg}}  and  {week_number: resp_count}
    week_metric = defaultdict(dict)   # {1: {'Engagement': 4.5, ...}, 2: {...}}
    week_resp   = defaultdict(int)    # {1: 12, 2: 10, ...}

    for row in raw:
        w      = row['week_number']
        metric = row['question__title']
        avg    = round(float(row['avg_score'] or 0), 2)
        week_metric[w][metric] = avg
        week_resp[w] = max(week_resp[w], row['resp_count'])

    # Sorted unique weeks (dict keys are already unique)
    weeks = sorted(week_metric.keys())

    if not weeks:
        return JsonResponse({
            'course_code':    course.course_code,
            'course_title':   course.course_title,
            'weeks':          [],
            'data':           {},
            'student_count':  0,
            'response_counts': [],
        })

    # ── Build output arrays (one value per week) ─────────────────────────────
    direct_metrics = ['Engagement', 'Difficulty', 'Satisfaction', 'Clarity']
    data = {m: [] for m in direct_metrics}
    data['TEI'] = []
    response_counts = []

    for w in weeks:
        avgs = week_metric[w]
        response_counts.append(week_resp[w])

        for metric in direct_metrics:
            data[metric].append(avgs.get(metric, 0))

        # TEI = 0.3×Engagement + 0.2×Satisfaction + 0.3×Clarity − 0.2×Difficulty
        tei = round(
            0.3 * avgs.get('Engagement',   0)
            + 0.2 * avgs.get('Satisfaction', 0)
            + 0.3 * avgs.get('Clarity',      0)
            - 0.2 * avgs.get('Difficulty',   0),
            2,
        )
        data['TEI'].append(tei)

    student_count = CourseRegistration.objects.filter(
        course=course, status='active'
    ).count()

    return JsonResponse({
        'course_code':    course.course_code,
        'course_title':   course.course_title,
        'weeks':          [f'Week {w}' for w in weeks],
        'data':           data,
        'student_count':  student_count,
        'response_counts': response_counts,
    })


@_require_teacher
def survey_dashboard_records(request):
    """Done-only records organised by field. TEI is computed per student per week."""
    course_id = request.GET.get('course_id')
    if not course_id:
        return JsonResponse({'error': 'course_id required'}, status=400)

    try:
        course = Course.objects.get(course_id=course_id)
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)

    direct_metrics = ['Engagement', 'Difficulty', 'Satisfaction', 'Clarity']
    fields_data = {}

    # One list per direct metric — done=True only
    for metric in direct_metrics:
        rows = (
            Survey.objects
            .filter(course=course, done=True, question__title=metric)
            .select_related('student')
            .order_by('week_number', 'student__last_name', 'student__first_name')
        )
        fields_data[metric] = [
            {
                'week':       r.week_number,
                'student':    f"{r.student.first_name} {r.student.last_name}".strip()
                              or r.student.email,
                'student_id': r.student.student_id or '—',
                'score':      round(float(r.score), 2) if r.score is not None else None,
            }
            for r in rows
        ]

    # TEI per student per week: 0.3×Eng + 0.2×Sat + 0.3×Clar − 0.2×Diff
    all_done = (
        Survey.objects
        .filter(course=course, done=True, question__title__in=direct_metrics)
        .values(
            'week_number', 'student_id',
            'student__first_name', 'student__last_name',
            'student__student_id', 'student__email',
            'question__title', 'score',
        )
        .order_by('week_number', 'student__last_name', 'student__first_name')
    )

    student_week_scores = defaultdict(dict)   # {(week, student_id): {metric: score}}
    student_info = {}

    for row in all_done:
        key = (row['week_number'], row['student_id'])
        student_week_scores[key][row['question__title']] = float(row['score'] or 0)
        if row['student_id'] not in student_info:
            name = (f"{row['student__first_name']} {row['student__last_name']}").strip()
            student_info[row['student_id']] = {
                'name':       name or row['student__email'],
                'student_id': row['student__student_id'] or '—',
            }

    tei_records = []
    for (week, sid), scores in sorted(student_week_scores.items()):
        if len(scores) < len(direct_metrics):
            continue   # skip if any metric is missing
        tei = round(
            0.3 * scores.get('Engagement',   0)
            + 0.2 * scores.get('Satisfaction', 0)
            + 0.3 * scores.get('Clarity',      0)
            - 0.2 * scores.get('Difficulty',   0),
            2,
        )
        info = student_info[sid]
        tei_records.append({
            'week':       week,
            'student':    info['name'],
            'student_id': info['student_id'],
            'score':      tei,
        })

    fields_data['TEI'] = tei_records
    return JsonResponse({'fields': fields_data})
