from rest_framework import serializers
from .models import QuizAttempt, UserAnswer
from quizzes.models import Quiz

class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    
    class Meta:
        model = QuizAttempt
        fields = ('id', 'user', 'quiz', 'quiz_title', 'start_time', 'end_time', 'score', 'status')
        read_only_fields = ('id', 'user', 'start_time')

class QuizCompleteSerializer(serializers.ModelSerializer):
    """Serializer specifically for completing a quiz attempt"""
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    total_questions = serializers.SerializerMethodField()
    correct_answers = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizAttempt
        fields = [
            'id', 
            'user', 
            'quiz', 
            'quiz_title', 
            'start_time', 
            'end_time', 
            'score', 
            'status',
            'total_questions',
            'correct_answers',
            'percentage'
        ]
        read_only_fields = [
            'id', 
            'user', 
            'quiz', 
            'quiz_title', 
            'start_time', 
            'end_time', 
            'score', 
            'status',
            'total_questions',
            'correct_answers',
            'percentage'
        ]
    
    def get_total_questions(self, obj):
        """Get total number of questions in the quiz"""
        return obj.quiz.questions.count()
    
    def get_correct_answers(self, obj):
        """Get number of correct answers"""
        return obj.answers.filter(is_correct=True).count()
    
    def get_percentage(self, obj):
        """Calculate percentage score"""
        total = obj.quiz.questions.count()
        if total == 0:
            return 0
        correct = obj.answers.filter(is_correct=True).count()
        return round((correct / total) * 100, 2)
    
    def update(self, instance, validated_data):
        """
        Update the quiz attempt to mark it as completed.
        This method is called when using the serializer with .save()
        """
        # Check if already completed
        if instance.status == 'completed':
            raise serializers.ValidationError("Quiz already completed")
        
        # Calculate final score
        total_questions = instance.quiz.questions.count()
        correct_answers = instance.answers.filter(is_correct=True).count()
        score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Update the instance
        instance.score = score
        instance.status = 'completed'
        instance.end_time = timezone.now()
        instance.save()
        
        return instance
        
class SubmitAnswerSerializer(serializers.Serializer):
    attempt_id = serializers.IntegerField()
    question_id = serializers.IntegerField()
    selected_choice_id = serializers.IntegerField(required=False, allow_null=True)
    text_answer = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get('selected_choice_id') and not attrs.get('text_answer'):
            raise serializers.ValidationError("Either selected_choice_id or text_answer is required")
        return attrs

class QuizResultSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title')
    total_questions = serializers.SerializerMethodField()
    correct_answers = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizAttempt
        fields = ('id', 'quiz_title', 'score', 'start_time', 'end_time', 'total_questions', 'correct_answers', 'status')
    
    def get_total_questions(self, obj):
        return obj.quiz.questions.count()
    
    def get_correct_answers(self, obj):
        return obj.answers.filter(is_correct=True).count()