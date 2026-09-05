from django.db import models
from django.conf import settings
from django.utils import timezone
from quizzes.models import Quiz, Question, Choice

class QuizAttempt(models.Model):
    STATUS_CHOICES = (
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')

    # NEW FIELDS FOR EVALUATION
    is_evaluated = models.BooleanField(
        default=False,
        help_text="Whether the attempt has been evaluated by an instructor"
    )
    evaluated_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When the attempt was evaluated"
    )
    evaluated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evaluated_attempts',
        help_text="Instructor who evaluated this attempt"
    )
    manual_score = models.FloatField(
        null=True, 
        blank=True,
        help_text="Manually adjusted total score (if different from auto-calculated)"
    )
    evaluation_notes = models.TextField(
        blank=True,
        help_text="Notes from the instructor about this evaluation"
    )

    class Meta:
        db_table = 'quiz_attempts'
        ordering = ['-start_time']

    def get_total_possible_score(self):
        """Get the total possible score for this quiz"""
        return self.quiz.total_points
    
    def calculate_auto_score(self):
        """Calculate the automatic score based on correct answers"""
        return self.answers.filter(is_correct=True).aggregate(
            total=models.Sum('question__points')
        )['total'] or 0
    
    def recalculate_score(self):
        """Recalculate the total score (including manual adjustments)"""
        if self.is_evaluated and self.manual_score is not None:
            self.score = self.manual_score
        else:
            # Auto-calculate from correct answers
            auto_score = self.calculate_auto_score()
            self.score = auto_score
        self.save()
        return self.score

class UserAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    text_answer = models.TextField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)
    selected_choice_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of selected choice IDs"
    )

    # NEW FIELDS FOR EVALUATION
    score_awarded = models.FloatField(
        null=True, 
        blank=True,
        help_text="Manually awarded score for this answer (overrides auto-calculation)"
    )
    is_manually_graded = models.BooleanField(
        default=False,
        help_text="Whether this answer was manually graded by an instructor"
    )
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_answers',
        help_text="Instructor who graded this answer"
    )
    graded_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this answer was manually graded"
    )
    feedback = models.TextField(
        blank=True,
        help_text="Instructor feedback for this answer"
    )

    class Meta:
        db_table = 'user_answers'
        unique_together = ['attempt', 'question']

    def get_max_points(self):
        """Get the maximum points for this question"""
        return self.question.points
    
    def get_awarded_score(self):
        """Get the awarded score (manual or auto)"""
        if self.is_manually_graded and self.score_awarded is not None:
            return self.score_awarded
        return self.question.points if self.is_correct else 0
    
    def auto_grade(self):
        """Auto-grade the answer based on question type"""
        question = self.question
        
        if question.question_type == 'mcq':
            # Multiple choice: check if selected choice is correct
            if self.selected_choice:
                self.is_correct = self.selected_choice.is_correct
            else:
                self.is_correct = False
                
        elif question.question_type == 'true_false':
            # True/False: check if selected choice is correct
            if self.selected_choice:
                self.is_correct = self.selected_choice.is_correct
            else:
                self.is_correct = False
                
        elif question.question_type == 'short_answer':
            # Short answer: needs manual grading by default
            self.is_correct = False
            self.is_manually_graded = False
            
        self.save()
        return self.is_correct
    
    def grade_manually(self, score_awarded, grader, feedback=""):
        """Manually grade this answer"""
        max_points = self.get_max_points()
        
        if score_awarded > max_points:
            raise ValueError(f"Score {score_awarded} exceeds maximum points {max_points}")
        
        self.score_awarded = score_awarded
        self.is_manually_graded = True
        self.graded_by = grader
        self.graded_at = timezone.now()
        self.feedback = feedback
        self.is_correct = score_awarded > 0  # Consider any positive score as correct
        self.save()
        
        return self.score_awarded