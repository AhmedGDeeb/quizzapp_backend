from rest_framework import serializers
from .models import Quiz, Question, Choice, Answer

class ChoiceSerializer(serializers.ModelSerializer):
    """Serializer for Choice model"""
    
    class Meta:
        model = Choice
        fields = ('id', 'choice_text', 'is_correct')
        read_only_fields = ('id',)


class AnswerSerializer(serializers.ModelSerializer):
    """Serializer for Answer model (short answer)"""
    
    class Meta:
        model = Answer
        fields = ('id', 'correct_answer_text')
        read_only_fields = ('id',)


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question model with nested choices and answer"""
    
    choices = ChoiceSerializer(many=True, read_only=True)
    correct_answer = AnswerSerializer(read_only=True)
    
    class Meta:
        model = Question
        fields = ('id', 'question_text', 'question_type', 'points', 'quiz' , 
                  'order_index', 'choices', 'correct_answer', 'has_choices')
        read_only_fields = ('id', 'has_choices')


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating questions with choices"""
    
    choices = ChoiceSerializer(many=True, required=False)
    correct_answer = AnswerSerializer(required=False)

    class Meta:
        model = Question
        fields = ('id', 'quiz', 'question_text', 'question_type', 'points', 
                  'order_index', 'choices', 'correct_answer')
        read_only_fields = ('id',)
        
    def validate(self, attrs):
        question_type = attrs.get('question_type')
        choices = attrs.get('choices', [])
        correct_answer = attrs.get('correct_answer')
        
        # Validate MCQ questions must have choices
        if question_type == 'mcq' and not choices:
            raise serializers.ValidationError({
                'choices': 'MCQ questions must have at least one choice.'
            })
        
        # Validate MCQ must have at least one correct choice
        if question_type == 'mcq' and choices:
            has_correct = any(choice.get('is_correct', False) for choice in choices)
            if not has_correct:
                raise serializers.ValidationError({
                    'choices': 'MCQ questions must have at least one correct choice.'
                })
        
        # Validate True/False must have exactly 2 choices
        if question_type == 'true_false' and choices:
            if len(choices) != 2:
                raise serializers.ValidationError({
                    'choices': 'True/False questions must have exactly 2 choices.'
                })
            # Check if choices are True and False
            choice_texts = [choice.get('choice_text', '').lower() for choice in choices]
            if 'true' not in choice_texts or 'false' not in choice_texts:
                raise serializers.ValidationError({
                    'choices': 'True/False questions must have "True" and "False" as choices.'
                })
        
        # Validate short answer must have correct_answer
        if question_type == 'short_answer' and not correct_answer:
            raise serializers.ValidationError({
                'correct_answer': 'Short answer questions must have a correct answer.'
            })
        
        return attrs

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        correct_answer_data = validated_data.pop('correct_answer', None)
        
        question = Question.objects.create(**validated_data)
        
        # Create choices
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        
        # Create correct answer for short answer
        if correct_answer_data:
            Answer.objects.create(question=question, **correct_answer_data)
        
        return question

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)
        correct_answer_data = validated_data.pop('correct_answer', None)
        
        # Update question fields
        instance.question_text = validated_data.get('question_text', instance.question_text)
        instance.question_type = validated_data.get('question_type', instance.question_type)
        instance.points = validated_data.get('points', instance.points)
        instance.order_index = validated_data.get('order_index', instance.order_index)
        instance.save()
        
        # Update choices (delete existing and create new)
        if choices_data is not None:
            instance.choices.all().delete()
            for choice_data in choices_data:
                Choice.objects.create(question=instance, **choice_data)
        
        # Update correct answer for short answer
        if correct_answer_data is not None:
            if hasattr(instance, 'correct_answer'):
                instance.correct_answer.delete()
            Answer.objects.create(question=instance, **correct_answer_data)
        
        return instance

class StandaloneQuestionSerializer(serializers.ModelSerializer):
    """Serializer for questions that are not assigned to a quiz"""
    
    choices = ChoiceSerializer(many=True, read_only=True)
    correct_answer = AnswerSerializer(read_only=True)
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    is_standalone = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Question
        fields = ('id', 'question_text', 'question_type', 'points', 
                  'order_index', 'choices', 'correct_answer', 
                  'has_choices', 'is_standalone', 'creator_name',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'has_choices', 'is_standalone', 
                           'creator_name', 'created_at', 'updated_at')


class StandaloneQuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating standalone questions"""
    
    choices = ChoiceSerializer(many=True, required=False)
    correct_answer = AnswerSerializer(required=False)

    class Meta:
        model = Question
        fields = ('id', 'question_text', 'question_type', 'points', 
                  'order_index', 'choices', 'correct_answer')

    def validate(self, attrs):
        question_type = attrs.get('question_type')
        choices = attrs.get('choices', [])
        correct_answer = attrs.get('correct_answer')
        
        # Validate MCQ questions must have choices
        if question_type == 'mcq' and not choices:
            raise serializers.ValidationError({
                'choices': 'MCQ questions must have at least one choice.'
            })
        
        # Validate MCQ must have at least one correct choice
        if question_type == 'mcq' and choices:
            has_correct = any(choice.get('is_correct', False) for choice in choices)
            if not has_correct:
                raise serializers.ValidationError({
                    'choices': 'MCQ questions must have at least one correct choice.'
                })
        
        # Validate True/False must have exactly 2 choices
        if question_type == 'true_false' and choices:
            if len(choices) != 2:
                raise serializers.ValidationError({
                    'choices': 'True/False questions must have exactly 2 choices.'
                })
            # Check if choices are True and False
            choice_texts = [choice.get('choice_text', '').lower() for choice in choices]
            if 'true' not in choice_texts or 'false' not in choice_texts:
                raise serializers.ValidationError({
                    'choices': 'True/False questions must have "True" and "False" as choices.'
                })
        
        # Validate short answer must have correct_answer
        if question_type == 'short_answer' and not correct_answer:
            raise serializers.ValidationError({
                'correct_answer': 'Short answer questions must have a correct answer.'
            })
        
        return attrs

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        correct_answer_data = validated_data.pop('correct_answer', None)
        
        # Set quiz to None for standalone question
        question = Question.objects.create(
            **validated_data
        )
        
        # Create choices
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        
        # Create correct answer for short answer
        if correct_answer_data:
            Answer.objects.create(question=question, **correct_answer_data)
        
        return question
    
class AssignQuestionSerializer(serializers.Serializer):
    """Serializer for assigning a single question to a quiz"""
    
    question_id = serializers.IntegerField(help_text="ID of the question to assign to the quiz")
    quiz_id = serializers.IntegerField(help_text="ID of the quiz to assign the question to")

    def validate(self, attrs):
        question_id = attrs.get('question_id')
        quiz_id = attrs.get('quiz_id')
        
        # Check if question exists
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            raise serializers.ValidationError({
                'question_id': f'Question with ID {question_id} does not exist.'
            })
        
        # Check if quiz exists
        try:
            quiz = Quiz.objects.get(id=quiz_id)
        except Quiz.DoesNotExist:
            raise serializers.ValidationError({
                'quiz_id': f'Quiz with ID {quiz_id} does not exist.'
            })
        
        # Check if question is already assigned to a quiz
        if question.quiz is not None:
            raise serializers.ValidationError({
                'question_id': f'Question with ID {question_id} is already assigned to quiz "{question.quiz.title}".'
            })
        
        # Store validated objects for use in view
        attrs['question'] = question
        attrs['quiz'] = quiz
        
        return attrs


class UnassignQuestionSerializer(serializers.Serializer):
    """Serializer for unassigning a single question from a quiz"""
    
    question_id = serializers.IntegerField(help_text="ID of the question to unassign from its quiz")

    def validate_question_id(self, value):
        # Check if question exists
        try:
            question = Question.objects.get(id=value)
        except Question.DoesNotExist:
            raise serializers.ValidationError(
                f'Question with ID {value} does not exist.'
            )
        
        # Check if question is assigned to a quiz
        if question.quiz is None:
            raise serializers.ValidationError(
                f'Question with ID {value} is not assigned to any quiz.'
            )
        
        # Store question object for use in view
        self.context['question'] = question
        
        return value
    
class QuizSerializer(serializers.ModelSerializer):
    """Serializer for Quiz model (list view)"""
    
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    total_points = serializers.IntegerField(read_only=True)

    class Meta:
        model = Quiz
        fields = ('id', 'title', 'description', 'creator_name', 'category', 
                  'time_limit', 'attempts_allowed', 'is_published', 
                  'created_at', 'updated_at', 'question_count', 'total_points')
        read_only_fields = ('id', 'created_at', 'updated_at', 'question_count', 'total_points')


class QuizDetailSerializer(serializers.ModelSerializer):
    """Serializer for Quiz model (detail view with questions)"""
    
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    total_points = serializers.IntegerField(read_only=True)

    class Meta:
        model = Quiz
        fields = ('id', 'title', 'description', 'creator_name', 'category', 
                  'time_limit', 'attempts_allowed', 'is_published', 
                  'created_at', 'updated_at', 'question_count', 'total_points', 'questions')
        read_only_fields = ('id', 'created_at', 'updated_at', 'question_count', 'total_points')


class QuizCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating quizzes"""
    
    class Meta:
        model = Quiz
        fields = ('title', 'description', 'category', 
                  'time_limit', 'attempts_allowed', 'is_published')

    def validate(self, attrs):
        # Validate time_limit is positive
        time_limit = attrs.get('time_limit')
        if time_limit is not None and time_limit <= 0:
            raise serializers.ValidationError({
                'time_limit': 'Time limit must be a positive number.'
            })
        
        # Validate attempts_allowed is positive
        attempts_allowed = attrs.get('attempts_allowed')
        if attempts_allowed is not None and attempts_allowed <= 0:
            raise serializers.ValidationError({
                'attempts_allowed': 'Attempts allowed must be a positive number.'
            })
        
        return attrs


class QuizPublishSerializer(serializers.Serializer):
    """Serializer for publishing/unpublishing a quiz"""
    
    publish = serializers.BooleanField(required=True)