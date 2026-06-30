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
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from django.http import JsonResponse

from rest_framework_simplejwt.views import TokenRefreshView

from auth_api.views import (
    RegisterView, LoginView, LogoutView, ProfileView, ChangePasswordView,
    VerifyEmailView, ResendVerificationView, RequestAccountDeletionView,
    ReactivateAccountView, AccountStatusView, PasswordResetRequestView, 
    PasswordResetConfirmView, PasswordResetCompleteView
)

from quizzes.views import QuizViewSet, QuestionViewSet, ChoiceViewSet, QuizQuestionsView

router = DefaultRouter()

# Quizzes app router registrations
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'choices', ChoiceViewSet, basename='choice')

def server_status(request):
    return JsonResponse(
             data={'server status': 'up',
                   'server datetime': datetime.datetime.now().ctime()}
             , status=200)


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

quiz_questions_view = QuizQuestionsView.as_view()


urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('api/auth/register/', RegisterView.as_view()),
    path('api/auth/login/', LoginView.as_view()),
    path('api/auth/refresh/', TokenRefreshView.as_view()),
    path('api/auth/logout/', LogoutView.as_view()),
    path('api/auth/profile/', ProfileView.as_view()),
    path('api/auth/change-password/', ChangePasswordView.as_view()),

    # Email Verification
    path('api/auth/verify-email/<str:token>/', VerifyEmailView.as_view()),
    path('api/auth/resend-verification/', ResendVerificationView.as_view()),
    
    # Account Deletion & Reactivation
    path('api/auth/request-deletion/', RequestAccountDeletionView.as_view()),
    path('api/auth/reactivate/<str:token>/', ReactivateAccountView.as_view()),
    path('api/auth/account-status/', AccountStatusView.as_view()),

    # Account password reset
    path('api/auth/reset-password/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('api/auth/reset-password/<str:token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Files
    path('api/files/<int:file_id>/extracted-text/', lambda request: JsonResponse({}, status=200)),
    
    # quizzes
    # Quiz URLs
    path('api/quizzes/', quiz_list, name='quiz-list'),
    path('api/quizzes/<int:pk>/', quiz_detail, name='quiz-detail'),
    path('api/quizzes/<int:pk>/publish/', quiz_publish, name='quiz-publish'),
    path('api/quizzes/<int:pk>/duplicate/', quiz_duplicate, name='quiz-duplicate'),
    path('api/quizzes/<int:pk>/add_question/', quiz_add_question, name='quiz-add-question'),
    path('api/quizzes/my_quizzes/', quiz_my_quizzes, name='quiz-my-quizzes'),
    path('api/quizzes/<int:quiz_id>/questions/', quiz_questions_view, name='quiz-questions'),

    # Question URLs
    path('api/questions/', question_list, name='question-list'),
    path('api/questions/<int:pk>/', question_detail, name='question-detail'),
    
    # Choice URLs
    path('api/choices/', choice_list, name='choice-list'),
    path('api/choices/<int:pk>/', choice_detail, name='choice-detail'),

    # Attempts
    # path('api/quizzes/<int:quiz_id>/start/', lambda request: JsonResponse({}, status=200)),
    # path('api/attempts/submit-answer/', lambda request: JsonResponse({}, status=200)),
    # path('api/attempts/<int:attempt_id>/complete/',lambda request: JsonResponse({}, status=200)),
    # path('api/attempts/', lambda request: JsonResponse({}, status=200)),
    # path('api/attempts/<int:attempt_id>/result/', lambda request: JsonResponse({}, status=200)),
    # path('api/quizzes/<int:quiz_id>/leaderboard/', lambda request: JsonResponse({}, status=200)),
    
    # # Statistics
    # path('api/statistics/quizzes/<int:quiz_id>/', lambda request: JsonResponse({}, status=200)),
    # path('api/statistics/my-performance/', lambda request: JsonResponse({}, status=200)),
    # path('api/statistics/admin/', lambda request: JsonResponse({}, status=200)),

    # Router URLs
    path('api/', include(router.urls)),

    # check server status
    path('api/status', server_status),
]
