from django.urls import path
from .views import QuizViewSet, QuestionViewSet, ChoiceViewSet

from django.urls import path
from .views import (
    QuizViewSet, QuestionViewSet, ChoiceViewSet
)
from .views import QuizViewSet, QuestionViewSet, ChoiceViewSet


# Define explicit URLs for Quiz endpoints
quiz_list = QuizViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

quiz_detail = QuizViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

quiz_publish = QuizViewSet.as_view({
    'post': 'publish'
})

quiz_duplicate = QuizViewSet.as_view({
    'post': 'duplicate'
})

quiz_add_question = QuizViewSet.as_view({
    'post': 'add_question'
})

quiz_my_quizzes = QuizViewSet.as_view({
    'get': 'my_quizzes'
})

# Define explicit URLs for Question endpoints
question_list = QuestionViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

question_detail = QuestionViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

# Define explicit URLs for Choice endpoints
choice_list = ChoiceViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

choice_detail = ChoiceViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    # Quiz URLs
    path('quizzes/', quiz_list, name='quiz-list'),
    path('quizzes/<int:pk>/', quiz_detail, name='quiz-detail'),
    path('quizzes/<int:pk>/publish/', quiz_publish, name='quiz-publish'),
    path('quizzes/<int:pk>/duplicate/', quiz_duplicate, name='quiz-duplicate'),
    path('quizzes/<int:pk>/add_question/', quiz_add_question, name='quiz-add-question'),
    path('quizzes/my_quizzes/', quiz_my_quizzes, name='quiz-my-quizzes'),
    
    # Question URLs
    path('questions/', question_list, name='question-list'),
    path('questions/<int:pk>/', question_detail, name='question-detail'),
    
    # Choice URLs
    path('choices/', choice_list, name='choice-list'),
    path('choices/<int:pk>/', choice_detail, name='choice-detail'),
]