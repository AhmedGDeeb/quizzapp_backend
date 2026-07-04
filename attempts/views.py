from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import QuizAttempt, UserAnswer
from .serializers import QuizAttemptSerializer, SubmitAnswerSerializer, QuizResultSerializer, QuizCompleteSerializer
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
        
        # Initialize variables
        is_correct = False
        selected_choice = None
        text_answer = None
        correct_answer_text = None
        correct_choices_data = []
        
        # Handle MCQ and True/False
        if question.question_type in ['mcq', 'true_false']:
            selected_choice = serializer.validated_data.get('choice')
            if selected_choice:
                is_correct = selected_choice.is_correct
                text_answer = selected_choice.choice_text
                
                # Get all correct choices for MCQ/True/False
                correct_choices = question.choices.filter(is_correct=True)
                correct_choices_data = [
                    {
                        'id': c.id,
                        'choice_text': c.choice_text
                    } 
                    for c in correct_choices
                ]
                
                if correct_choices.exists():
                    correct_answer_text = ", ".join([c.choice_text for c in correct_choices])
                else:
                    correct_answer_text = None
        else:
            # Handle short answer
            text_answer = serializer.validated_data.get('text_answer', '').strip()
            
            # Get correct answer for short answer
            if hasattr(question, 'correct_answer') and question.correct_answer:
                correct_answer_text = question.correct_answer.correct_answer_text.strip()
                correct_choices_data = [
                    {
                        'id': question.correct_answer.id,
                        'correct_answer_text': correct_answer_text
                    }
                ]
                # Case-insensitive comparison
                is_correct = text_answer.lower() == correct_answer_text.lower()
            else:
                # If no correct answer defined, mark as incorrect
                is_correct = False
        
        # Update or create answer
        if existing_answer:
            existing_answer.selected_choice = selected_choice
            existing_answer.text_answer = text_answer
            existing_answer.is_correct = is_correct
            existing_answer.save()
            answer = existing_answer
        else:
            answer = UserAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_choice=selected_choice,
                text_answer=text_answer,
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
        
        return Response({
            'correct': is_correct,
            'message': 'Answer recorded',
            'user_answer': text_answer,
            'correct_answer': correct_answer_text,
            'correct_choices': correct_choices_data,  # Detailed correct choices
            'attempt_id': attempt.id,
            'question_id': question.id,
            'question_type': question.question_type,
            'total_correct': total_correct,
            'total_answered': total_answered,
            'total_questions': attempt.quiz.questions.count()
        }, status=status.HTTP_200_OK)
    
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