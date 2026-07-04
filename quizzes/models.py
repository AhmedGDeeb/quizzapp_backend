from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Quiz(models.Model):
    """
    Quiz model representing a test/quiz created by an instructor
    """

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='created_quizzes'
    )
    category = models.CharField(max_length=100)
    time_limit = models.IntegerField(
        help_text="Time limit in minutes", 
        null=True, 
        blank=True
    )
    attempts_allowed = models.IntegerField(default=1)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quizzes'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def question_count(self):
        """Return the number of questions in this quiz"""
        return self.questions.count()

    @property
    def total_points(self):
        """Return total points available in this quiz"""
        return sum(question.points for question in self.questions.all())

    def get_questions_ordered(self):
        """Return questions ordered by order_index"""
        return self.questions.all().order_by('order_index')


class Question(models.Model):
    """
    Question model representing a single question in a quiz
    """
    QUESTION_TYPES = (
        ('mcq', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
    )
    
    quiz = models.ForeignKey(
        Quiz, 
        on_delete=models.CASCADE, 
        related_name='questions',
        null=True,
        blank=True
    )
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='mcq')
    points = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    order_index = models.IntegerField(default=0)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_questions',
        null=True,  # Allow for existing questions
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'questions'
        ordering = ['order_index']

    def __str__(self):
        quiz_title = self.quiz.title if self.quiz else "Standalone"
        return f"{quiz_title} - Q{self.order_index + 1}: {self.question_text[:50]}"

    @property
    def has_choices(self):
        """Check if this question type has choices (MCQ or True/False)"""
        return self.question_type in ['mcq', 'true_false']

    @property
    def choices_count(self):
        """Return number of choices for this question"""
        return self.choices.count()
    
    @property
    def is_standalone(self):
        """Check if this question is not assigned to any quiz"""
        return self.quiz is None


class Choice(models.Model):
    """
    Choice model for multiple choice questions
    """
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name='choices'
    )
    choice_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = 'choices'
        ordering = ['id']

    def __str__(self):
        return f"{self.question.question_text[:30]} - {self.choice_text[:30]}"


class Answer(models.Model):
    """
    Answer model for short answer questions (stores the correct answer)
    """
    question = models.OneToOneField(
        Question, 
        on_delete=models.CASCADE, 
        related_name='correct_answer'
    )
    correct_answer_text = models.TextField()

    class Meta:
        db_table = 'answers'

    def __str__(self):
        return f"Answer for: {self.question.question_text[:30]}"