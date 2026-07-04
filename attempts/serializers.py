from django.utils import timezone

from rest_framework import serializers
from .models import QuizAttempt, UserAnswer
from quizzes.models import Quiz, Question, Choice

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
        
        # Update the instances
        instance.score = score
        instance.status = 'completed'
        instance.end_time = timezone.now()
        instance.save()
        
        return instance

class SubmitAnswerSerializer(serializers.Serializer):
    """Serializer for submitting an answer"""
    
    attempt_id = serializers.IntegerField(required=True)
    question_id = serializers.IntegerField(required=True)
    selected_choice_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text="List of choice IDs for MCQ/True-False questions"
    )
    text_answer = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        attempt_id = attrs.get('attempt_id')
        question_id = attrs.get('question_id')
        selected_choice_ids = attrs.get('selected_choice_ids', [])
        text_answer = attrs.get('text_answer')
        
        # Get question to check its type
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            raise serializers.ValidationError({'question_id': 'Question does not exist.'})
        
        # Validate based on question type
        if question.question_type in ['mcq', 'true_false']:
            # For MCQ/True-False, selected_choice_ids is required
            if not selected_choice_ids:
                raise serializers.ValidationError({
                    'selected_choice_ids': 'This field is required for MCQ and True/False questions.'
                })
            
            # Check if all choices belong to the question
            choices = Choice.objects.filter(id__in=selected_choice_ids, question=question)
            if choices.count() != len(selected_choice_ids):
                raise serializers.ValidationError({
                    'selected_choice_ids': 'One or more choices do not belong to this question.'
                })
            
            # For True/False, only allow 1 choice
            if question.question_type == 'true_false' and len(selected_choice_ids) != 1:
                raise serializers.ValidationError({
                    'selected_choice_ids': 'True/False questions only allow one selection.'
                })
            
            attrs['choices'] = choices
            
        elif question.question_type == 'short_answer':
            # For Short Answer, text_answer is required
            if not text_answer:
                raise serializers.ValidationError({
                    'text_answer': 'This field is required for short answer questions.'
                })
        
        attrs['question'] = question
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