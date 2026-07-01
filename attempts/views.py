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

class SubmitAnswerView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubmitAnswerSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        attempt = get_object_or_404(QuizAttempt, id=serializer.validated_data['attempt_id'], user=request.user)
        
        if attempt.status != 'in_progress':
            return Response({'error': 'Quiz already completed'}, status=status.HTTP_400_BAD_REQUEST)
        
        question = get_object_or_404(Question, id=serializer.validated_data['question_id'], quiz=attempt.quiz)
        
        # Check if answer already exists
        existing_answer = UserAnswer.objects.filter(attempt=attempt, question=question).first()
        
        # Determine if answer is correct
        is_correct = False
        selected_choice = None
        if serializer.validated_data.get('selected_choice_id'):
            selected_choice = get_object_or_404(Choice, id=serializer.validated_data['selected_choice_id'], question=question)
            is_correct = selected_choice.is_correct
            text_answer = None
        else:
            text_answer = serializer.validated_data.get('text_answer')
            # For short answer, check against correct answer
            if question.correct_answer:
                is_correct = text_answer.strip().lower() == question.correct_answer.correct_answer_text.strip().lower()
        
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
        
        return Response({'correct': is_correct, 'message': 'Answer recorded'})

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