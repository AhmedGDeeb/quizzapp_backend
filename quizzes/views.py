from rest_framework import viewsets, status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db import models as django_models
from .models import Quiz, Question, Choice
from .serializers import (
    QuizSerializer, QuizDetailSerializer, QuizCreateUpdateSerializer,
    QuestionSerializer, QuestionCreateSerializer, ChoiceSerializer,
    QuizPublishSerializer
)
from .permissions import IsInstructor, IsAdminUser

class QuizViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Quiz CRUD operations
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin can see all quizzes
        if user.role == 'admin':
            return Quiz.objects.all()
        
        # Instructor can see their own quizzes plus published ones
        if user.role == 'instructor':
            return Quiz.objects.filter(
                django_models.Q(creator=user) | django_models.Q(is_published=True)
            ).distinct()
        
        # Students can only see published quizzes
        return Quiz.objects.filter(is_published=True)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return QuizDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return QuizCreateUpdateSerializer
        return QuizSerializer

    def perform_create(self, serializer):
        """Create quiz with the current user as creator"""
        serializer.save(creator=self.request.user)

    def get_permissions(self):
        """
        Custom permissions:
        - Admin can do anything
        - Instructor can create/update/delete their own quizzes
        - Students can only view
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsInstructor]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Publish or unpublish a quiz
        """
        quiz = self.get_object()
        serializer = QuizPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        quiz.is_published = serializer.validated_data['publish']
        quiz.save()
        
        return Response({
            'message': f'Quiz {"published" if quiz.is_published else "unpublished"} successfully.',
            'is_published': quiz.is_published
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicate an existing quiz with all its questions
        """
        original_quiz = self.get_object()
        
        with transaction.atomic():
            # Create copy of quiz
            new_quiz = Quiz.objects.create(
                title=f"Copy of {original_quiz.title}",
                description=original_quiz.description,
                creator=request.user,
                category=original_quiz.category,
                difficulty=original_quiz.difficulty,
                time_limit=original_quiz.time_limit,
                attempts_allowed=original_quiz.attempts_allowed,
                is_published=False
            )
            
            # Copy questions
            for question in original_quiz.questions.all():
                new_question = Question.objects.create(
                    quiz=new_quiz,
                    question_text=question.question_text,
                    question_type=question.question_type,
                    points=question.points,
                    order_index=question.order_index
                )
                
                # Copy choices (for MCQ and True/False)
                for choice in question.choices.all():
                    Choice.objects.create(
                        question=new_question,
                        choice_text=choice.choice_text,
                        is_correct=choice.is_correct
                    )
                
                # Copy answer (for short answer)
                if hasattr(question, 'correct_answer'):
                    Answer.objects.create(
                        question=new_question,
                        correct_answer_text=question.correct_answer.correct_answer_text
                    )
        
        serializer = QuizSerializer(new_quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def my_quizzes(self, request):
        """
        Get quizzes created by the current user
        """
        quizzes = Quiz.objects.filter(creator=request.user)
        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_question(self, request, pk=None):
        """
        Add a question to a quiz
        """
        quiz = self.get_object()
        serializer = QuestionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(quiz=quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Question CRUD operations
    """
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionSerializer

    def get_queryset(self):
        """
        Only return questions for quizzes the user has access to
        """
        user = self.request.user
        
        if user.role == 'admin':
            return Question.objects.all()
        
        if user.role == 'instructor':
            return Question.objects.filter(quiz__creator=user)
        
        # Students can only see questions from published quizzes
        return Question.objects.filter(quiz__is_published=True)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return QuestionCreateSerializer
        return QuestionSerializer

    def get_permissions(self):
        """
        Only instructors and admins can modify questions
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsInstructor]
        return super().get_permissions()

    def perform_create(self, serializer):
        """Create question with quiz from request data"""
        quiz_id = self.request.data.get('quiz')
        if quiz_id:
            quiz = get_object_or_404(Quiz, id=quiz_id)
            serializer.save(quiz=quiz)


class ChoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Choice CRUD operations
    """
    permission_classes = [IsAuthenticated, IsInstructor]
    serializer_class = ChoiceSerializer
    queryset = Choice.objects.all()