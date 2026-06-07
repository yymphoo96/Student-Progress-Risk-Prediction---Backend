from django.db import models
from apps.users.models import User
from apps.courses.models import Course


class Question(models.Model):
    """A survey question that can be reused across weeks and courses."""
    question_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)   # short label, e.g. "Engagement"
    detail = models.TextField()                 # full question text shown to student
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'survey_questions'
        ordering = ['question_id']

    def __str__(self):
        return self.title


class Survey(models.Model):
    """One student's answer to one question for a specific course week."""
    survey_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='survey_entries')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='survey_entries')
    student = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='survey_entries',
        limit_choices_to={'user_type': 'student'},
    )
    score = models.FloatField(null=True, blank=True)  # null until student submits
    week_number = models.IntegerField()
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'surveys'
        unique_together = ('course', 'question', 'student', 'week_number')
        ordering = ['week_number', 'question']

    def __str__(self):
        return f"{self.student.email} | {self.course.course_code} | W{self.week_number} | {self.question.title}"
