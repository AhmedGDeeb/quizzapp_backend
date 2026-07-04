"""
URL configuration for quizzapp_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import datetime

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# Auth imports
from auth_api.views import (
    RegisterView, LoginView, LogoutView, ProfileView, ChangePasswordView,
    VerifyEmailView, ResendVerificationView, RequestAccountDeletionView,
    ReactivateAccountView, AccountStatusView, PasswordResetRequestView, 
    PasswordResetConfirmView, PasswordResetCompleteView
)

# Quiz imports
from quizzes.views import (
    QuizViewSet, 
    QuestionViewSet, 
    ChoiceViewSet, 
    QuizQuestionsView,
    StandaloneQuestionViewSet,
    AssignQuestionToQuizView,
    UnassignQuestionFromQuizView,
    AssignQuestionToQuizFromDetailView,
    UnassignQuestionFromQuizDetailView,
    MyQuestionsView, 
    AvailableQuestionsView
)

# Attempts imports
from attempts.views import (
    StartQuizView, 
    SubmitAnswerView, 
    CompleteQuizView, 
    AttemptHistoryView, 
    QuizResultView, 
    leaderboard
)

# ==================== Router Registration ====================
router = DefaultRouter()

# Quizzes app router registrations
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'choices', ChoiceViewSet, basename='choice')
router.register(r'standalone-questions', StandaloneQuestionViewSet, basename='standalone-question')

# ==================== Helper Views ====================
def server_status(request):
    return JsonResponse(
        data={
            'server status': 'up',
            'server datetime': datetime.datetime.now().ctime()
        },
        status=200
    )

# ==================== Quiz ViewSet Explicit URLs ====================
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

# ==================== Question ViewSet Explicit URLs ====================
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

# ==================== Choice ViewSet Explicit URLs ====================
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

# ==================== Standalone Question ViewSet Explicit URLs ====================
standalone_question_list = StandaloneQuestionViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

standalone_question_detail = StandaloneQuestionViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

# ==================== Quiz Questions Views ====================
quiz_questions_view = QuizQuestionsView.as_view()

# ==================== URL Patterns ====================
urlpatterns = [
    # ==================== Admin ====================
    path('admin/', admin.site.urls),

    # ==================== Authentication ====================
    # Authentication endpoints
    path('api/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('api/auth/profile/', ProfileView.as_view(), name='auth-profile'),
    path('api/auth/change-password/', ChangePasswordView.as_view(), name='auth-change-password'),

    # Email Verification
    path('api/auth/verify-email/<str:token>/', VerifyEmailView.as_view(), name='auth-verify-email'),
    path('api/auth/resend-verification/', ResendVerificationView.as_view(), name='auth-resend-verification'),
    
    # Account Deletion & Reactivation
    path('api/auth/request-deletion/', RequestAccountDeletionView.as_view(), name='auth-request-deletion'),
    path('api/auth/reactivate/<str:token>/', ReactivateAccountView.as_view(), name='auth-reactivate'),
    path('api/auth/account-status/', AccountStatusView.as_view(), name='auth-account-status'),

    # Password Reset
    path('api/auth/reset-password/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('api/auth/reset-password/<str:token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # ==================== Quiz Endpoints ====================
    # Quiz CRUD
    path('api/quizzes/', quiz_list, name='quiz-list'),
    path('api/quizzes/<int:pk>/', quiz_detail, name='quiz-detail'),
    
    # Quiz Actions
    path('api/quizzes/<int:pk>/publish/', quiz_publish, name='quiz-publish'),
    path('api/quizzes/<int:pk>/duplicate/', quiz_duplicate, name='quiz-duplicate'),
    path('api/quizzes/<int:pk>/add_question/', quiz_add_question, name='quiz-add-question'),
    path('api/quizzes/my_quizzes/', quiz_my_quizzes, name='quiz-my-quizzes'),
    
    # Quiz Questions
    path('api/quizzes/<int:quiz_id>/questions/', quiz_questions_view, name='quiz-questions'),
    path('api/quizzes/<int:quiz_id>/available-questions/', AvailableQuestionsView.as_view(), name='available-questions'),
    
    # Quiz Question Assignment (with quiz ID in URL)
    path('api/quizzes/<int:quiz_id>/assign-question/', AssignQuestionToQuizFromDetailView.as_view(), name='assign-question-to-quiz'),
    path('api/quizzes/<int:quiz_id>/unassign-question/', UnassignQuestionFromQuizDetailView.as_view(), name='unassign-question-from-quiz'),

    # ==================== Question Endpoints ====================
    # Question CRUD
    path('api/questions/', question_list, name='question-list'),
    path('api/questions/<int:pk>/', question_detail, name='question-detail'),
    
    # My Questions (all questions created by user)
    # path('api/questions/my-questions/', MyQuestionsView.as_view(), name='my-questions'),
    
    # Question Assignment (quiz ID in request body)
    path('api/questions/assign/', AssignQuestionToQuizView.as_view(), name='assign-question'),
    path('api/questions/unassign/', UnassignQuestionFromQuizView.as_view(), name='unassign-question'),
    
    # ==================== Standalone Question Endpoints ====================
    path('api/standalone-questions/', standalone_question_list, name='standalone-question-list'),
    path('api/standalone-questisons/<int:pk>/', standalone_question_detail, name='standalone-question-detail'),

    # ==================== Choice Endpoints ====================
    path('api/choices/', choice_list, name='choice-list'),
    path('api/choices/<int:pk>/', choice_detail, name='choice-detail'),

    # ==================== Attempt Endpoints ====================
    path('api/quizzes/<int:quiz_id>/start/', StartQuizView.as_view(), name='start-quiz'),
    path('api/attempts/submit-answer/', SubmitAnswerView.as_view(), name='submit-answer'),
    path('api/attempts/<int:attempt_id>/complete/', CompleteQuizView.as_view(), name='complete-quiz'),
    path('api/attempts/', AttemptHistoryView.as_view(), name='attempt-history'),
    path('api/attempts/<int:attempt_id>/result/', QuizResultView.as_view(), name='quiz-result'),
    path('api/quizzes/<int:quiz_id>/leaderboard/', leaderboard, name='leaderboard'),

    # ==================== Router URLs ====================
    path('api/', include(router.urls)),

    # ==================== Server Status ====================
    path('api/status', server_status, name='server-status'),
]