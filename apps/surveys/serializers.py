from rest_framework import serializers
from .models import Question, Survey


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['question_id', 'title', 'detail']


class SurveySubmitSerializer(serializers.Serializer):
    """Accepts a list of {question_id, score} pairs for one week submission."""
    course_id = serializers.IntegerField()
    week_number = serializers.IntegerField(min_value=1, max_value=52)
    answers = serializers.ListField(
        child=serializers.DictField(child=serializers.FloatField()),
        min_length=1,
    )

    def validate_answers(self, answers):
        for item in answers:
            if 'question_id' not in item or 'score' not in item:
                raise serializers.ValidationError(
                    "Each answer must have 'question_id' and 'score'."
                )
            score = item['score']
            if not (1 <= score <= 5):
                raise serializers.ValidationError("Score must be between 1 and 5.")
        return answers


class SurveySerializer(serializers.ModelSerializer):
    question_title = serializers.CharField(source='question.title', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    course_code = serializers.CharField(source='course.course_code', read_only=True)

    class Meta:
        model = Survey
        fields = [
            'survey_id', 'course', 'course_code',
            'question', 'question_title',
            'student', 'student_email',
            'score', 'week_number', 'done', 'created_at',
        ]
