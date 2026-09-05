from django.utils import timezone

from rest_framework import serializers
from .models import QuizAttempt, UserAnswer
from quizzes.models import Quiz, Question, Choice, Answer

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
        if question.question_type == 'mcq':
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
            
            attrs['choices'] = choices
            
        elif question.question_type in ['short_answer', question.question_type == 'true_false']:
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

class ChoiceSerializer(serializers.ModelSerializer):
    """Serializer for choice options"""
    class Meta:
        model = Choice
        fields = ('id', 'choice_text', 'is_correct')

class AnswerSerializer(serializers.ModelSerializer):
    """Serializer for correct answer (for short answer questions)"""
    class Meta:
        model = Answer
        fields = ('id', 'correct_answer_text')

class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for questions with choices and correct answer"""
    choices = ChoiceSerializer(many=True, read_only=True)
    correct_answer = AnswerSerializer(read_only=True)
    
    class Meta:
        model = Question
        fields = (
            'id', 
            'question_text', 
            'question_type', 
            'points', 
            'order_index',
            'choices',
            'correct_answer'
        )

class UserAnswerSerializer(serializers.ModelSerializer):
    """Serializer for user's answers"""
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    selected_choice_text = serializers.SerializerMethodField()
    selected_choice_ids = serializers.JSONField(read_only=True)
    
    class Meta:
        model = UserAnswer
        fields = (
            'id',
            'question',
            'question_text',
            'selected_choice',
            'selected_choice_ids',
            'selected_choice_text',
            'text_answer',
            'is_correct',
            'answered_at'
        )
    
    def get_selected_choice_text(self, obj):
        """Get the text of the selected choice(s)"""
        if obj.selected_choice:
            return obj.selected_choice.choice_text
        elif obj.selected_choice_ids:
            choices = Choice.objects.filter(id__in=obj.selected_choice_ids)
            return [choice.choice_text for choice in choices]
        return None
    
class QuizAttemptResultSerializer(serializers.ModelSerializer):
    """Main serializer for quiz attempt results"""
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    quiz_description = serializers.CharField(source='quiz.description', read_only=True)
    quiz_category = serializers.CharField(source='quiz.category', read_only=True)
    creator_name = serializers.SerializerMethodField()
    total_questions = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    correct_answers = serializers.SerializerMethodField()
    incorrect_answers = serializers.SerializerMethodField()
    unanswered_questions = serializers.SerializerMethodField()
    score_percentage = serializers.SerializerMethodField()
    time_taken = serializers.SerializerMethodField()
    questions_with_answers = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizAttempt
        fields = (
            'id',
            'quiz',
            'quiz_title',
            'quiz_description',
            'quiz_category',
            'creator_name',
            'user',
            'start_time',
            'end_time',
            'time_taken',
            'score',
            'score_percentage',
            'status',
            'total_questions',
            'total_points',
            'correct_answers',
            'incorrect_answers',
            'unanswered_questions',
            'questions_with_answers'
        )
    
    def get_creator_name(self, obj):
        """Get the name of the quiz creator"""
        creator = obj.quiz.creator
        if creator.first_name and creator.last_name:
            return f"{creator.first_name} {creator.last_name}"
        return creator.username
    
    def get_total_questions(self, obj):
        return obj.quiz.question_count
    
    def get_total_points(self, obj):
        return obj.quiz.total_points
    
    def get_correct_answers(self, obj):
        return obj.answers.filter(is_correct=True).count()
    
    def get_incorrect_answers(self, obj):
        return obj.answers.filter(is_correct=False).count()
    
    def get_unanswered_questions(self, obj):
        total = obj.quiz.question_count
        answered = obj.answers.count()
        return total - answered
    
    def get_score_percentage(self, obj):
        total_points = obj.quiz.total_points
        if total_points == 0:
            return 0
        return (obj.score / total_points) * 100
    
    def get_time_taken(self, obj):
        """Calculate time taken to complete the quiz"""
        if obj.end_time and obj.start_time:
            duration = obj.end_time - obj.start_time
            minutes = duration.total_seconds() // 60
            seconds = duration.total_seconds() % 60
            return {
                'minutes': int(minutes),
                'seconds': int(seconds),
                'total_seconds': duration.total_seconds()
            }
        return None
    
    def get_questions_with_answers(self, obj):
        """Get all questions with user's answers"""
        questions = obj.quiz.get_questions_ordered().prefetch_related('choices', 'correct_answer')
        user_answers = {answer.question_id: answer for answer in obj.answers.all()}
        
        question_data = []
        for question in questions:
            user_answer = user_answers.get(question.id)
            
            data = {
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'points': question.points,
                'order_index': question.order_index,
                'choices': ChoiceSerializer(question.choices.all(), many=True).data,
                'correct_answer': AnswerSerializer(question.correct_answer).data if hasattr(question, 'correct_answer') else None,
                'user_answer': UserAnswerSerializer(user_answer).data if user_answer else None,
                'is_correct': user_answer.is_correct if user_answer else None,
                'correct_choices': [
                    {'id': choice.id, 'choice_text': choice.choice_text} 
                    for choice in question.choices.filter(is_correct=True)
                ] if question.question_type in ['mcq', 'true_false'] else None,
                'status': self._get_question_status(question, user_answer)
            }
            question_data.append(data)
        
        return question_data
    
    def _get_question_status(self, question, user_answer):
        """Determine the status of a question"""
        if not user_answer:
            return 'unanswered'
        if user_answer.is_correct:
            return 'correct'
        return 'incorrect'

class QuizAttemptSummarySerializer(serializers.ModelSerializer):
    """
    Serializer for quiz attempt summary with student details
    """
    # Student details
    student_id = serializers.IntegerField(source='user.id')
    student_name = serializers.SerializerMethodField()
    student_email = serializers.EmailField(source='user.email')
    
    # Quiz details
    quiz_title = serializers.CharField(source='quiz.title')
    total_questions = serializers.IntegerField(source='quiz.question_count')
    total_points = serializers.IntegerField(source='quiz.total_points')
    
    # Attempt statistics
    correct_answers = serializers.SerializerMethodField()
    incorrect_answers = serializers.SerializerMethodField()
    unanswered_questions = serializers.SerializerMethodField()
    score_percentage = serializers.SerializerMethodField()
    time_taken_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizAttempt
        fields = [
            'id',
            'student_id',
            'student_name',
            'student_email',
            'quiz_title',
            'score',
            'score_percentage',
            'status',
            'start_time',
            'end_time',
            'time_taken_minutes',
            'total_questions',
            'total_points',
            'correct_answers',
            'incorrect_answers',
            'unanswered_questions',
        ]
    
    def get_student_name(self, obj):
        """Get student's full name"""
        user = obj.user
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username
    
    def get_correct_answers(self, obj):
        """Get number of correct answers"""
        return obj.answers.filter(is_correct=True).count()
    
    def get_incorrect_answers(self, obj):
        """Get number of incorrect answers"""
        return obj.answers.filter(is_correct=False).count()
    
    def get_unanswered_questions(self, obj):
        """Get number of unanswered questions"""
        total = obj.quiz.question_count
        answered = obj.answers.count()
        return total - answered
    
    def get_score_percentage(self, obj):
        """Get score as percentage"""
        total_points = obj.quiz.total_points
        if total_points == 0:
            return 0.0
        return round((obj.score / total_points) * 100, 2)
    
    def get_time_taken_minutes(self, obj):
        """Get time taken in minutes"""
        if obj.end_time and obj.start_time:
            duration = obj.end_time - obj.start_time
            return round(duration.total_seconds() / 60, 2)
        return None

class StudentAttemptListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing student's quiz attempts
    """
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    quiz_description = serializers.CharField(source='quiz.description', read_only=True)
    quiz_category = serializers.CharField(source='quiz.category', read_only=True)
    instructor_name = serializers.SerializerMethodField()
    total_questions = serializers.IntegerField(source='quiz.question_count', read_only=True)
    total_points = serializers.IntegerField(source='quiz.total_points', read_only=True)
    correct_answers = serializers.SerializerMethodField()
    incorrect_answers = serializers.SerializerMethodField()
    unanswered_questions = serializers.SerializerMethodField()
    score_percentage = serializers.SerializerMethodField()
    time_taken = serializers.SerializerMethodField()
    attempt_number = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizAttempt
        fields = (
            'id',
            'quiz',
            'quiz_title',
            'quiz_description',
            'quiz_category',
            'instructor_name',
            'status',
            'score',
            'score_percentage',
            'total_questions',
            'total_points',
            'correct_answers',
            'incorrect_answers',
            'unanswered_questions',
            'start_time',
            'end_time',
            'time_taken',
            'attempt_number',
        )
    
    def get_instructor_name(self, obj):
        """Get the name of the quiz creator/instructor"""
        creator = obj.quiz.creator
        if creator.first_name and creator.last_name:
            return f"{creator.first_name} {creator.last_name}"
        return creator.username
    
    def get_correct_answers(self, obj):
        """Get number of correct answers"""
        return obj.answers.filter(is_correct=True).count()
    
    def get_incorrect_answers(self, obj):
        """Get number of incorrect answers"""
        return obj.answers.filter(is_correct=False).count()
    
    def get_unanswered_questions(self, obj):
        """Get number of unanswered questions"""
        total = obj.quiz.question_count
        answered = obj.answers.count()
        return total - answered
    
    def get_score_percentage(self, obj):
        """Get score as percentage"""
        total_points = obj.quiz.total_points
        if total_points == 0:
            return 0.0
        return round((obj.score / total_points) * 100, 2)
    
    def get_time_taken(self, obj):
        """Calculate time taken to complete the quiz"""
        if obj.end_time and obj.start_time:
            duration = obj.end_time - obj.start_time
            return {
                'minutes': int(duration.total_seconds() // 60),
                'seconds': int(duration.total_seconds() % 60),
                'total_seconds': duration.total_seconds()
            }
        return None
    
    def get_attempt_number(self, obj):
        """Get the attempt number for this quiz"""
        # Count how many attempts the user has made for this quiz
        attempts = QuizAttempt.objects.filter(
            user=obj.user,
            quiz=obj.quiz
        ).order_by('start_time')
        
        for index, attempt in enumerate(attempts, 1):
            if attempt.id == obj.id:
                return index
        return None


class UserAnswerDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for user answers with question details
    """
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    question_type_display = serializers.CharField(source='question.get_question_type_display', read_only=True)
    points = serializers.IntegerField(source='question.points', read_only=True)
    order_index = serializers.IntegerField(source='question.order_index', read_only=True)
    selected_choice_text = serializers.SerializerMethodField()
    selected_choice_ids = serializers.JSONField(read_only=True)
    correct_choices = serializers.SerializerMethodField()
    correct_answer_text = serializers.SerializerMethodField()
    all_choices = serializers.SerializerMethodField()
    
    class Meta:
        model = UserAnswer
        fields = (
            'id',
            'question',
            'question_text',
            'question_type',
            'question_type_display',
            'points',
            'order_index',
            'selected_choice',
            'selected_choice_ids',
            'selected_choice_text',
            'text_answer',
            'is_correct',
            'answered_at',
            'all_choices',
            'correct_choices',
            'correct_answer_text',
        )
    
    def get_selected_choice_text(self, obj):
        """Get the text of the selected choice(s)"""
        if obj.selected_choice:
            return obj.selected_choice.choice_text
        elif obj.selected_choice_ids:
            choices = Choice.objects.filter(id__in=obj.selected_choice_ids)
            return [choice.choice_text for choice in choices]
        return None
    
    def get_all_choices(self, obj):
        """Get all choices for the question"""
        choices = obj.question.choices.all()
        return ChoiceSerializer(choices, many=True).data
    
    def get_correct_choices(self, obj):
        """Get the correct choice(s) for MCQ/TrueFalse questions"""
        question = obj.question
        if question.question_type in ['mcq', 'true_false']:
            correct_choices = question.choices.filter(is_correct=True)
            return ChoiceSerializer(correct_choices, many=True).data
        return None
    
    def get_correct_answer_text(self, obj):
        """Get the correct answer text for short answer questions"""
        question = obj.question
        if question.question_type == 'short_answer' and hasattr(question, 'correct_answer'):
            return question.correct_answer.correct_answer_text
        return None


class StudentAttemptDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a specific student attempt with all answers
    """
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    quiz_description = serializers.CharField(source='quiz.description', read_only=True)
    quiz_category = serializers.CharField(source='quiz.category', read_only=True)
    instructor_name = serializers.SerializerMethodField()
    total_questions = serializers.IntegerField(source='quiz.question_count', read_only=True)
    total_points = serializers.IntegerField(source='quiz.total_points', read_only=True)
    correct_answers = serializers.SerializerMethodField()
    incorrect_answers = serializers.SerializerMethodField()
    unanswered_questions = serializers.SerializerMethodField()
    score_percentage = serializers.SerializerMethodField()
    time_taken = serializers.SerializerMethodField()
    attempt_number = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizAttempt
        fields = (
            'id',
            'quiz',
            'quiz_title',
            'quiz_description',
            'quiz_category',
            'instructor_name',
            'status',
            'score',
            'score_percentage',
            'total_questions',
            'total_points',
            'correct_answers',
            'incorrect_answers',
            'unanswered_questions',
            'start_time',
            'end_time',
            'time_taken',
            'attempt_number',
            'answers',
        )
    
    def get_instructor_name(self, obj):
        creator = obj.quiz.creator
        if creator.first_name and creator.last_name:
            return f"{creator.first_name} {creator.last_name}"
        return creator.username
    
    def get_correct_answers(self, obj):
        return obj.answers.filter(is_correct=True).count()
    
    def get_incorrect_answers(self, obj):
        return obj.answers.filter(is_correct=False).count()
    
    def get_unanswered_questions(self, obj):
        total = obj.quiz.question_count
        answered = obj.answers.count()
        return total - answered
    
    def get_score_percentage(self, obj):
        total_points = obj.quiz.total_points
        if total_points == 0:
            return 0.0
        return round((obj.score / total_points) * 100, 2)
    
    def get_time_taken(self, obj):
        if obj.end_time and obj.start_time:
            duration = obj.end_time - obj.start_time
            return {
                'minutes': int(duration.total_seconds() // 60),
                'seconds': int(duration.total_seconds() % 60),
                'total_seconds': duration.total_seconds()
            }
        return None
    
    def get_attempt_number(self, obj):
        """Get the attempt number for this quiz"""
        attempts = QuizAttempt.objects.filter(
            user=obj.user,
            quiz=obj.quiz
        ).order_by('start_time')
        
        for index, attempt in enumerate(attempts, 1):
            if attempt.id == obj.id:
                return index
        return None
    
    def get_answers(self, obj):
        """Get all answers with question details"""
        # Get all answers for this attempt
        user_answers = obj.answers.all().select_related('question', 'selected_choice')
        
        # Get all questions for the quiz (including unanswered)
        all_questions = obj.quiz.get_questions_ordered()
        answered_question_ids = [answer.question_id for answer in user_answers]
        
        # Build response with all questions
        answers_data = []
        
        # Add answered questions
        for answer in user_answers:
            answers_data.append(UserAnswerDetailSerializer(answer).data)
        
        # Add unanswered questions
        for question in all_questions:
            if question.id not in answered_question_ids:
                answers_data.append({
                    'question': question.id,
                    'question_text': question.question_text,
                    'question_type': question.question_type,
                    'question_type_display': question.get_question_type_display(),
                    'points': question.points,
                    'order_index': question.order_index,
                    'selected_choice': None,
                    'selected_choice_ids': None,
                    'selected_choice_text': None,
                    'text_answer': None,
                    'is_correct': None,
                    'answered_at': None,
                    'all_choices': ChoiceSerializer(question.choices.all(), many=True).data if question.has_choices else [],
                    'correct_choices': ChoiceSerializer(question.choices.filter(is_correct=True), many=True).data if question.question_type in ['mcq', 'true_false'] else None,
                    'correct_answer_text': question.correct_answer.correct_answer_text if question.question_type == 'short_answer' and hasattr(question, 'correct_answer') else None,
                    'status': 'unanswered'
                })
        
        # Sort by order_index
        answers_data.sort(key=lambda x: x.get('order_index', 0))
        
        return answers_data

class QuestionForEvaluationSerializer(serializers.ModelSerializer):
    """
    Serializer for questions in evaluation context
    """
    choices = ChoiceSerializer(many=True, read_only=True)
    correct_answer = AnswerSerializer(read_only=True)
    
    class Meta:
        model = Question
        fields = (
            'id',
            'question_text',
            'question_type',
            'question_type_display',
            'points',
            'order_index',
            'choices',
            'correct_answer',
            'has_choices',
        )

class UserAnswerForEvaluationSerializer(serializers.ModelSerializer):
    """
    Serializer for user answers in evaluation context
    """
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    points = serializers.IntegerField(source='question.points', read_only=True)
    max_points = serializers.IntegerField(source='question.points', read_only=True)
    selected_choice_text = serializers.SerializerMethodField()
    correct_choices = serializers.SerializerMethodField()
    correct_answer_text = serializers.SerializerMethodField()
    all_choices = serializers.SerializerMethodField()
    
    class Meta:
        model = UserAnswer
        fields = (
            'id',
            'question',
            'question_text',
            'question_type',
            'points',
            'max_points',
            'selected_choice',
            'selected_choice_ids',
            'selected_choice_text',
            'text_answer',
            'is_correct',
            'answered_at',
            'all_choices',
            'correct_choices',
            'correct_answer_text',
            'score_awarded',  # Custom field for instructor to set score
        )
        read_only_fields = ('is_correct',)
    
    def get_selected_choice_text(self, obj):
        if obj.selected_choice:
            return obj.selected_choice.choice_text
        elif obj.selected_choice_ids:
            choices = Choice.objects.filter(id__in=obj.selected_choice_ids)
            return [choice.choice_text for choice in choices]
        return None
    
    def get_all_choices(self, obj):
        choices = obj.question.choices.all()
        return ChoiceSerializer(choices, many=True).data
    
    def get_correct_choices(self, obj):
        question = obj.question
        if question.question_type in ['mcq', 'true_false']:
            correct_choices = question.choices.filter(is_correct=True)
            return ChoiceSerializer(correct_choices, many=True).data
        return None
    
    def get_correct_answer_text(self, obj):
        question = obj.question
        if question.question_type == 'short_answer' and hasattr(question, 'correct_answer'):
            return question.correct_answer.correct_answer_text
        return None


class QuizAttemptForEvaluationSerializer(serializers.ModelSerializer):
    """
    Serializer for quiz attempt in evaluation context
    """
    student_id = serializers.IntegerField(source='user.id', read_only=True)
    student_name = serializers.SerializerMethodField()
    student_email = serializers.EmailField(source='user.email', read_only=True)
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    quiz_description = serializers.CharField(source='quiz.description', read_only=True)
    total_questions = serializers.IntegerField(source='quiz.question_count', read_only=True)
    total_points = serializers.IntegerField(source='quiz.total_points', read_only=True)
    answers = serializers.SerializerMethodField()
    score_percentage = serializers.SerializerMethodField()
    time_taken = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizAttempt
        fields = (
            'id',
            'student_id',
            'student_name',
            'student_email',
            'quiz',
            'quiz_title',
            'quiz_description',
            'status',
            'score',
            'score_percentage',
            'total_questions',
            'total_points',
            'start_time',
            'end_time',
            'time_taken',
            'answers',
        )
    
    def get_student_name(self, obj):
        user = obj.user
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username
    
    def get_score_percentage(self, obj):
        total_points = obj.quiz.total_points
        if total_points == 0:
            return 0.0
        return round((obj.score / total_points) * 100, 2)
    
    def get_time_taken(self, obj):
        if obj.end_time and obj.start_time:
            duration = obj.end_time - obj.start_time
            return {
                'minutes': int(duration.total_seconds() // 60),
                'seconds': int(duration.total_seconds() % 60),
                'total_seconds': duration.total_seconds()
            }
        return None
    
    def get_answers(self, obj):
        """Get all answers with evaluation data"""
        user_answers = obj.answers.all().select_related('question', 'selected_choice')
        
        # Get all questions (including unanswered)
        all_questions = obj.quiz.get_questions_ordered()
        answered_question_ids = [answer.question_id for answer in user_answers]
        
        answers_data = []
        
        # Add answered questions
        for answer in user_answers:
            data = UserAnswerForEvaluationSerializer(answer).data
            # Add score_awarded field (default to points if correct, 0 if incorrect)
            if answer.is_correct:
                data['score_awarded'] = answer.question.points
            else:
                data['score_awarded'] = 0
            answers_data.append(data)
        
        # Add unanswered questions
        for question in all_questions:
            if question.id not in answered_question_ids:
                answers_data.append({
                    'id': None,
                    'question': question.id,
                    'question_text': question.question_text,
                    'question_type': question.question_type,
                    'points': question.points,
                    'max_points': question.points,
                    'selected_choice': None,
                    'selected_choice_ids': None,
                    'selected_choice_text': None,
                    'text_answer': None,
                    'is_correct': None,
                    'answered_at': None,
                    'all_choices': ChoiceSerializer(question.choices.all(), many=True).data if question.has_choices else [],
                    'correct_choices': ChoiceSerializer(question.choices.filter(is_correct=True), many=True).data if question.question_type in ['mcq', 'true_false'] else None,
                    'correct_answer_text': question.correct_answer.correct_answer_text if question.question_type == 'short_answer' and hasattr(question, 'correct_answer') else None,
                    'score_awarded': 0,
                    'status': 'unanswered'
                })
        
        # Sort by order_index
        answers_data.sort(key=lambda x: x.get('order_index', 0) if 'order_index' in x else 0)
        
        return answers_data


class QuizAttemptEvaluationUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating scores and feedback for individual answers
    """
    answer_id = serializers.IntegerField(required=True)
    score_awarded = serializers.FloatField(required=True, min_value=0)
    feedback = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_score_awarded(self, value):
        """Validate that score doesn't exceed max points"""
        if value < 0:
            raise serializers.ValidationError("Score cannot be negative")
        return value

class BulkQuizAttemptEvaluationUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk updating scores and feedback
    """
    scores = serializers.ListField(
        child=QuizAttemptEvaluationUpdateSerializer(),
        allow_empty=False
    )
    
    def validate(self, data):
        """Validate all scores"""
        scores = data.get('scores', [])
        if not scores:
            raise serializers.ValidationError("At least one score must be provided")
        return data

class QuizEvaluationStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for quiz evaluation status
    """
    total_attempts = serializers.IntegerField()
    pending_evaluation = serializers.IntegerField()
    evaluated = serializers.IntegerField()

    # Use SerializerMethodField for computed fields
    needs_attention = serializers.SerializerMethodField()
    latest_attempt = serializers.SerializerMethodField()
    total_questions = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = (
            'id',
            'title',
            'description',
            'category',
            'total_questions',
            'total_points',
            'created_at',
            'total_attempts',
            'pending_evaluation',
            'evaluated',
            'needs_attention',
            'latest_attempt',
        )
    
    def get_total_questions(self, obj):
        """Get total questions count"""
        return obj.question_count  # Using the property
    
    def get_total_points(self, obj):
        """Get total points"""
        return obj.total_points  # Using the property
    
    def get_latest_attempt(self, obj):
        """Get the latest attempt that needs evaluation"""
        latest = QuizAttempt.objects.filter(
            quiz=obj,
            status='completed',
            is_evaluated=False
        ).select_related('user').order_by('-end_time').first()
        
        if latest:
            return {
                'attempt_id': latest.id,
                'student_name': latest.user.get_full_name() or latest.user.username,
                'student_email': latest.user.email,
                'completed_at': latest.end_time,
            }
        return None

    def get_needs_attention(self, obj):
        """Determine if quiz needs attention"""
        # Check if there are pending evaluations
        if hasattr(obj, 'pending_evaluation'):
            return obj.pending_evaluation > 0
        return False