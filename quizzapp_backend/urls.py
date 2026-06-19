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

from auth_api.views import (
    RegisterView, LoginView, LogoutView, ProfileView, ChangePasswordView,
    VerifyEmailView, ResendVerificationView, RequestAccountDeletionView,
    ReactivateAccountView, AccountStatusView
)

from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()

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
    path('api/auth/reactivate/', ReactivateAccountView.as_view()),
    path('api/auth/account-status/', AccountStatusView.as_view()),

    # Files
    path('api/files/<int:file_id>/extracted-text/', lambda request: JsonResponse({}, status=200)),
    
    # Attempts
    path('api/quizzes/<int:quiz_id>/start/', lambda request: JsonResponse({}, status=200)),
    path('api/attempts/submit-answer/', lambda request: JsonResponse({}, status=200)),
    path('api/attempts/<int:attempt_id>/complete/',lambda request: JsonResponse({}, status=200)),
    path('api/attempts/', lambda request: JsonResponse({}, status=200)),
    path('api/attempts/<int:attempt_id>/result/', lambda request: JsonResponse({}, status=200)),
    path('api/quizzes/<int:quiz_id>/leaderboard/', lambda request: JsonResponse({}, status=200)),
    
    # Statistics
    path('api/statistics/quizzes/<int:quiz_id>/', lambda request: JsonResponse({}, status=200)),
    path('api/statistics/my-performance/', lambda request: JsonResponse({}, status=200)),
    path('api/statistics/admin/', lambda request: JsonResponse({}, status=200)),

    # Router URLs
    path('api/', include(router.urls)),

    # check server status
    path('api/status', 
         lambda request: JsonResponse(
             data={'server status': 'up',
                   'server datetime': datetime.datetime.now().ctime()}
             , status=200)),
]
