from rest_framework import serializers
from .models import Assignment, AssignmentSubmission, Quiz, QuizScore

class AssignmentSerializer(serializers.ModelSerializer):
    submission_status = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    max_score = serializers.IntegerField()
    
    class Meta:
        model = Assignment
        fields = [
            'assignment_id', 
            'title', 
            'description', 
            'due_date', 
            'week_number',
            'max_score',
            'submission_status',
            'score'
        ]
    
    def get_submission_status(self, obj):
        """Get submission status for current student"""
        request = self.context.get('request')
        if request and request.user:
            try:
                submission = AssignmentSubmission.objects.get(
                    assignment=obj,
                    student=request.user
                )
                return submission.status  # 'submitted', 'graded', 'missing'
            except AssignmentSubmission.DoesNotExist:
                return 'not_submitted'
        return 'not_submitted'
    
    def get_score(self, obj):
        """Get score for current student"""
        request = self.context.get('request')
        if request and request.user:
            try:
                submission = AssignmentSubmission.objects.get(
                    assignment=obj,
                    student=request.user
                )
                return submission.score
            except AssignmentSubmission.DoesNotExist:
                return None
        return None


class QuizSerializer(serializers.ModelSerializer):
    submission_status = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    max_score = serializers.IntegerField()
    
    class Meta:
        model = Quiz
        fields = [
            'quiz_id',
            'title',
            'description',
            'quiz_date',
            'week_number',
            'max_score',
            'submission_status',
            'score'
        ]
    
    def get_submission_status(self, obj):
        """Get submission status for current student"""
        request = self.context.get('request')
        if request and request.user:
            try:
                quiz_score = QuizScore.objects.get(
                    quiz=obj,
                    student=request.user
                )
                return 'completed'
            except QuizScore.DoesNotExist:
                return 'not_taken'
        return 'not_taken'
    
    def get_score(self, obj):
        """Get score for current student"""
        request = self.context.get('request')
        if request and request.user:
            try:
                quiz_score = QuizScore.objects.get(
                    quiz=obj,
                    student=request.user
                )
                return quiz_score.score
            except QuizScore.DoesNotExist:
                return None
        return None