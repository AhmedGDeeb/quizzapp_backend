from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count

from .models import QuizAttempt, UserAnswer
from .serializers import (
    QuizAttemptSerializer,
    SubmitAnswerSerializer,
    QuizResultSerializer,
    QuizCompleteSerializer,
    QuizAttemptResultSerializer,
    QuizAttemptSummarySerializer,
)

from quizzes.models import Quiz, Question, Choice

class StartQuizView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = QuizAttemptSerializer

    def post(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id, is_published=True)
        
        # Check attempts limit
        attempts_count = QuizAttempt.objects.filter(user=request.user, quiz=quiz).count()
        if attempts_count >= quiz.attempts_allowed:
            return Response({'error': 'Maximum attempts reached'}, status=status.HTTP_400_BAD_REQUEST)
        
        attempt = QuizAttempt.objects.create(user=request.user, quiz=quiz)
        serializer = QuizAttemptSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# views.py - Enhanced version with all correct choices

class SubmitAnswerView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubmitAnswerSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        attempt = get_object_or_404(
            QuizAttempt, 
            id=serializer.validated_data['attempt_id'], 
            user=request.user
        )
        
        if attempt.status != 'in_progress':
            return Response(
                {'error': 'Quiz already completed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        question = serializer.validated_data['question']
        
        # Check if answer already exists
        existing_answer = UserAnswer.objects.filter(
            attempt=attempt, 
            question=question
        ).first()
        
        selected_choice_ids = serializer.validated_data.get('selected_choice_ids', [])

        # Initialize variables
        is_correct = False
        selected_choice_ids = []
        text_answer = None
        correct_answer_text = None
        user_answer_text = None
        
        # Handle based on question type
        if question.question_type in ['mcq', 'true_false']:
            # Get all correct choices for this question
            correct_choices = question.choices.filter(is_correct=True)
            correct_choice_ids = set(correct_choices.values_list('id', flat=True))
            selected_choice_ids_set = set(selected_choice_ids)
            
            # Check if selected choices match correct choices exactly
            is_correct = selected_choice_ids_set == correct_choice_ids

            # Create user answer text (join selected choices)
            selected_choices = Choice.objects.filter(id__in=selected_choice_ids)
            
            # Create user answer text (join selected choices)
            user_answer_text = ", ".join([choice.choice_text for choice in selected_choices])
            
            # Get correct answer text
            if correct_choices.exists():
                correct_answer_text = ", ".join([c.choice_text for c in correct_choices])
            else:
                correct_answer_text = None
                
        else:
            # Handle short answer
            text_answer = serializer.validated_data.get('text_answer', '').strip()
            user_answer_text = text_answer
            
            # Get correct answer for short answer
            if hasattr(question, 'correct_answer') and question.correct_answer:
                correct_answer_text = question.correct_answer.correct_answer_text.strip()
                # Case-insensitive comparison
                is_correct = text_answer.lower() == correct_answer_text.lower()
            else:
                is_correct = False
        
        # Store selected choice IDs as comma-separated string
        selected_choice_ids = serializer.validated_data.get('selected_choice_ids', [])
        
        # Update or create answer
        if existing_answer:
            existing_answer.selected_choice = None
            existing_answer.selected_choice_ids = selected_choice_ids
            existing_answer.text_answer = user_answer_text
            existing_answer.is_correct = is_correct
            existing_answer.save()
        else:
            UserAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_choice=None,
                selected_choice_ids=selected_choice_ids,
                text_answer=user_answer_text,
                is_correct=is_correct
            )
        
        # Calculate statistics
        total_correct = UserAnswer.objects.filter(
            attempt=attempt, 
            is_correct=True
        ).count()
        
        total_answered = UserAnswer.objects.filter(
            attempt=attempt
        ).count()
        
        # Build response based on question type
        response_data = {
            'correct': is_correct,
            'message': 'Answer recorded',
            'user_answer': user_answer_text,
            'correct_answer': correct_answer_text,
            'attempt_id': attempt.id,
            'question_id': question.id,
            'question_type': question.question_type,
            'total_correct': total_correct,
            'total_answered': total_answered,
            'total_questions': attempt.quiz.questions.count()
        }
        
        # Add question-type specific fields
        if question.question_type in ['mcq', 'true_false']:
            response_data['selected_choice_ids'] = selected_choice_ids
        else:
            response_data['text_answer'] = text_answer
        
        return Response(response_data, status=status.HTTP_200_OK)
    
class CompleteQuizView(generics.GenericAPIView):
    """
    API view to complete a quiz attempt.
    Uses QuizCompleteSerializer with QuizAttempt model.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = QuizCompleteSerializer
    
    def post(self, request, attempt_id):
        # Get the quiz attempt
        attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
        
        # Check if already completed
        if attempt.status == 'completed':
            return Response(
                {'error': 'Quiz already completed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use the serializer to update the attempt
        serializer = self.get_serializer(attempt, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Save the updated attempt (this calls the update method in serializer)
        updated_attempt = serializer.save()
        
        # Return the serialized data
        return Response(serializer.data, status=status.HTTP_200_OK)

class AttemptHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = QuizAttemptSerializer

    def get_queryset(self):
        return QuizAttempt.objects.filter(user=self.request.user)

class QuizResultView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = QuizResultSerializer

    def get_object(self):
        attempt_id = self.kwargs.get('attempt_id')
        return get_object_or_404(QuizAttempt, id=attempt_id, user=self.request.user)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leaderboard(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    attempts = QuizAttempt.objects.filter(quiz=quiz, status='completed').order_by('-score')[:10]
    data = []
    for attempt in attempts:
        data.append({
            'username': attempt.user.username,
            'score': attempt.score,
            'completed_at': attempt.end_time
        })
    return Response(data)

class QuizAttemptResultView(generics.RetrieveAPIView):
    """
    API view to get detailed quiz attempt results for a specific quiz and attempt.
    URL: /api/quizzes/<quiz_id>/attempts/<attempt_id>/result/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = QuizAttemptResultSerializer
    lookup_field = 'id'  # The field on the model to lookup
    lookup_url_kwarg = 'attempt_id'  # The URL keyword argument name
    
    def get_queryset(self):
        """
        Get the specific quiz attempt for the logged-in user.
        """
        quiz_id = self.kwargs.get('quiz_id')
        user = self.request.user
        
        # Staff can see all attempts, regular users only their own
        if user.is_staff:
            return QuizAttempt.objects.filter(quiz_id=quiz_id)
        return QuizAttempt.objects.filter(quiz_id=quiz_id, user=user)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific quiz attempt result.
        """
        try:
            # Get the attempt by ID
            attempt = self.get_object()
            
            # Verify the attempt belongs to the logged-in user (unless staff)
            if attempt.user_id != request.user.id and not request.user.is_staff:
                return Response(
                    {'error': 'You do not have permission to view this result'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if quiz is completed
            if attempt.status != 'completed':
                return Response(
                    {'error': 'Quiz attempt is not completed yet'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Serialize and return result
            serializer = self.get_serializer(attempt)
            return Response(serializer.data)
            
        except QuizAttempt.DoesNotExist:
            return Response(
                {'error': 'Quiz attempt not found for this quiz'},
                status=status.HTTP_404_NOT_FOUND
            )

class InstructorQuizResultsView(generics.GenericAPIView):
    """
    API view for instructors to see all student results for their quiz.
    URL: /api/instructor/quizzes/<quiz_id>/results/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = QuizAttemptSummarySerializer
    
    def get_queryset(self):
        """
        Get all completed attempts for the instructor's quiz.
        """
        quiz_id = self.kwargs.get('quiz_id')
        quiz = get_object_or_404(Quiz, id=quiz_id)
        
        # Verify the instructor is the creator of the quiz
        if quiz.creator != self.request.user:
            return QuizAttempt.objects.none()
        
        queryset = QuizAttempt.objects.filter(
            quiz_id=quiz_id,
            status='completed'
        ).select_related('user', 'quiz')
        
        # Optional student_id filter
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(user_id=student_id)
        
        return queryset.order_by('-score', 'end_time')
    
    def get(self, request, quiz_id):
        """
        Get all student attempts for a quiz created by the instructor.
        """
        quiz = get_object_or_404(Quiz, id=quiz_id)
        
        # Verify the instructor is the creator of the quiz
        if quiz.creator != request.user:
            return Response(
                {'error': 'You can only view results for quizzes you created'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        # Calculate statistics
        total_students = queryset.count()
        stats = queryset.aggregate(
            average=Avg('score'),
            highest=Max('score'),
            lowest=Min('score')
        )
        
        # Calculate pass/fail (60% passing threshold)
        passing_score_percentage = 60
        passing_score = (passing_score_percentage / 100) * quiz.total_points
        passed = queryset.filter(score__gte=passing_score).count()
        failed = total_students - passed
        
        # Serialize attempts
        serializer = self.get_serializer(queryset, many=True)
        
        # Prepare response
        response_data = {
            'quiz': {
                'id': quiz.id,
                'title': quiz.title,
                'description': quiz.description,
                'category': quiz.category,
                'total_questions': quiz.question_count,
                'total_points': quiz.total_points,
                'created_at': quiz.created_at,
            },
            'statistics': {
                'total_students': total_students,
                'average_score': round(stats['average'] or 0, 2),
                'highest_score': round(stats['highest'] or 0, 2),
                'lowest_score': round(stats['lowest'] or 0, 2),
                'passed': passed,
                'failed': failed,
                'passing_percentage': round((passed / total_students * 100) if total_students > 0 else 0, 2),
            },
            'attempts': serializer.data
        }
        
        return Response(response_data)
