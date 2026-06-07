from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404

from django.db.models import Max
from apps.courses.models import Course, CourseRegistration, CourseTeaching
from apps.assessments.models import Attendance
from .models import Question, Survey
from .serializers import QuestionSerializer, SurveySubmitSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_questions(request):
    """Return all survey questions."""
    questions = Question.objects.all()
    return Response(QuestionSerializer(questions, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_survey(request):
    """
    Student submits answers for all questions for a given course + week.
    Body: { course_id, week_number, answers: [{question_id, score}, ...] }
    Creates Survey rows (done=True) for each answer.
    """
    student = request.user
    serializer = SurveySubmitSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    course = get_object_or_404(Course, course_id=data['course_id'])
    week_number = data['week_number']

    if not CourseRegistration.objects.filter(
        student=student, course=course, status='active'
    ).exists():
        return Response({'error': 'Not enrolled in this course.'}, status=status.HTTP_403_FORBIDDEN)

    created, updated = 0, 0
    for item in data['answers']:
        question = get_object_or_404(Question, question_id=int(item['question_id']))
        obj, is_new = Survey.objects.update_or_create(
            course=course,
            question=question,
            student=student,
            week_number=week_number,
            defaults={'score': item['score'], 'done': True},
        )
        if is_new:
            created += 1
        else:
            updated += 1

    return Response(
        {'message': f'Survey submitted. {created} created, {updated} updated.'},
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def survey_status(request):
    """
    Returns whether a student has completed the survey for a course+week.
    Query params: course_id, week_number
    Returns: { done: true/false, total_questions, answered }
    """
    student = request.user
    course_id = request.query_params.get('course_id')
    week_number = request.query_params.get('week_number')

    if not course_id or not week_number:
        return Response({'error': 'course_id and week_number are required.'}, status=status.HTTP_400_BAD_REQUEST)

    course = get_object_or_404(Course, course_id=course_id)
    total = Question.objects.count()
    answered = Survey.objects.filter(
        course=course, student=student,
        week_number=int(week_number), done=True,
    ).count()

    return Response({'done': answered >= total and total > 0, 'total_questions': total, 'answered': answered})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def any_pending(request):
    """
    Returns the first week that has been released but not yet answered by this student.
    Query param: course_id
    Returns: { pending: bool, week_number: int|null }
    """
    student = request.user
    course_id = request.query_params.get('course_id')
    if not course_id:
        return Response({'error': 'course_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    course = get_object_or_404(Course, course_id=course_id)

    first_pending = (
        Survey.objects.filter(course=course, student=student, done=False)
        .order_by('week_number')
        .values_list('week_number', flat=True)
        .first()
    )

    return Response({
        'pending': first_pending is not None,
        'week_number': first_pending,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_courses(request):
    """Return courses the logged-in teacher is assigned to teach."""
    user = request.user
    if user.user_type not in ('teacher', 'admin'):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    teachings = CourseTeaching.objects.filter(teacher=user).select_related('course')
    courses = []
    for t in teachings:
        student_count = CourseRegistration.objects.filter(
            course=t.course, status='active'
        ).count()
        current_week = Attendance.objects.filter(
            course=t.course
        ).aggregate(max=Max('week_number'))['max'] or 0
        courses.append({
            'course_id': t.course.course_id,
            'course_code': t.course.course_code,
            'course_title': t.course.course_title,
            'term': t.course.term,
            'year': t.course.year,
            'student_count': student_count,
            'current_week': current_week,
        })
    return Response(courses)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def week_status(request):
    """
    Returns a list of weeks (from attendance) for a course, each with release status.
    Query param: course_id
    Returns: { max_week, weeks: [{week, released, student_count}] }
    """
    user = request.user
    if user.user_type not in ('teacher', 'admin'):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    course_id = request.query_params.get('course_id')
    if not course_id:
        return Response({'error': 'course_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    course = get_object_or_404(Course, course_id=course_id)

    max_week = Attendance.objects.filter(course=course).aggregate(
        max=Max('week_number')
    )['max'] or 0

    student_count = CourseRegistration.objects.filter(course=course, status='active').count()
    total_questions = Question.objects.count()

    weeks = []
    for w in range(1, max_week + 1):
        released = Survey.objects.filter(course=course, week_number=w).exists()
        done_count = 0
        if released and total_questions > 0:
            # Count students who answered every question (all done=True)
            done_count = (
                Survey.objects.filter(course=course, week_number=w, done=True)
                .values('student')
                .annotate(q_done=Count('question'))
                .filter(q_done=total_questions)
                .count()
            )
        weeks.append({
            'week': w,
            'released': released,
            'student_count': student_count,
            'done_count': done_count,
        })

    return Response({'max_week': max_week, 'student_count': student_count, 'weeks': weeks})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def release_survey(request):
    """
    Release survey for a course week: creates done=False Survey rows for all
    enrolled students × all questions.
    Body: { course_id, week_number }
    """
    user = request.user
    if user.user_type not in ('teacher', 'admin'):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    course_id = request.data.get('course_id')
    week_number = request.data.get('week_number')

    if not course_id or not week_number:
        return Response({'error': 'course_id and week_number are required.'}, status=status.HTTP_400_BAD_REQUEST)

    course = get_object_or_404(Course, course_id=int(course_id))

    if Survey.objects.filter(course=course, week_number=int(week_number)).exists():
        return Response({'error': 'Survey already released for this week.'}, status=status.HTTP_400_BAD_REQUEST)

    students = CourseRegistration.objects.filter(
        course=course, status='active'
    ).select_related('student')
    questions = Question.objects.all()

    rows = [
        Survey(course=course, question=q, student=reg.student,
               week_number=int(week_number), score=None, done=False)
        for reg in students
        for q in questions
    ]
    Survey.objects.bulk_create(rows)

    return Response(
        {'message': f'Survey released for Week {week_number}. {len(rows)} entries created.'},
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics(request):
    """
    Per-week, per-question average scores for a course (teacher/admin only).
    Query param: course_id
    """
    user = request.user
    if user.user_type not in ('teacher', 'admin'):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    course_id = request.query_params.get('course_id')
    if not course_id:
        return Response({'error': 'course_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    course = get_object_or_404(Course, course_id=course_id)
    questions = Question.objects.all()

    weeks = (
        Survey.objects.filter(course=course, done=True)
        .values_list('week_number', flat=True)
        .distinct()
        .order_by('week_number')
    )

    result = []
    for week in weeks:
        week_data = {'week': week, 'response_count': 0, 'scores': {}}
        for q in questions:
            agg = Survey.objects.filter(
                course=course, question=q, week_number=week, done=True
            ).aggregate(avg=Avg('score'))
            count = Survey.objects.filter(
                course=course, question=q, week_number=week, done=True
            ).count()
            week_data['scores'][q.title] = round(agg['avg'] or 0, 2)
            week_data['response_count'] = max(week_data['response_count'], count)
        result.append(week_data)

    return Response({
        'course_id': course.course_id,
        'course_code': course.course_code,
        'questions': [q.title for q in questions],
        'weeks': result,
    })
