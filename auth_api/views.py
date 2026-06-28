from datetime import timedelta

from django.utils import timezone

from .tokens import generate_verification_token
from .email_utils import (
    send_reactivation_email, send_account_deletion_notification,
    send_account_deleted_notification
)

from django.contrib.auth import login, logout

from rest_framework import views, generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from auth_api.models import User
from auth_api.serializers import (
    AccountReactivationSerializer, EmailVerificationSerializer, UserSerializer, UserProfileSerializer, RegisterSerializer,
    LoginSerializer, ChangePasswordSerializer, AccountDeletionSerializer, ResendVerificationSerializer
)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        # First, try to find the user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({
                'error': 'Invalid credentials',
                'code': 'invalid_credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if account is deleted
        if user.is_deleted:
            return Response({
                'error': 'This account has been permanently deleted.',
                'code': 'account_deleted'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check account status
        if user.account_status == 'pending':
            return Response({
                'error': 'Please verify your email address before logging in.',
                'code': 'email_not_verified',
                'email': user.email,
                'can_resend_verification': True
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.account_status == 'deactivated':
            # Check if within 90-day grace period
            if user.can_reactivate():
                days_remaining = user.get_deletion_grace_period_remaining()
                return Response({
                    'error': 'Your account has been deactivated and is scheduled for deletion.',
                    'code': 'account_deactivated',
                    'can_reactivate': True,
                    'days_remaining': days_remaining['days_remaining'] if days_remaining else 0,
                    'deletion_date': user.deletion_scheduled_date,
                    'message': f'You have {days_remaining["days_remaining"] if days_remaining else 0} days to reactivate your account.'
                }, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({
                    'error': 'Your account has been permanently deleted.',
                    'code': 'account_deleted',
                    'can_reactivate': False,
                    'message': 'The 90-day grace period has expired.'
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Account is active, check password
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response({
                'error': 'Invalid credentials',
                'code': 'invalid_credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if user is still active (might have been deactivated during authentication)
        if not user.is_account_active():
            return Response({
                'error': 'Account is not active.',
                'code': 'account_inactive',
                'account_status': user.account_status
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)

        # login
        login(request, user)

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'account_status': user.account_status,
                'email_verified': user.email_verified,
                'role': user.role,
            }
        })

class LogoutView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # logout from session
            logout(request)

            return Response({'message': 'Logged out successfully'})
        except Exception as e:
            print(e)
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user.profile
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'old_password': 'Wrong password'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Password changed successfully'})
    
class ResendVerificationView(generics.GenericAPIView):
    serializer_class = ResendVerificationSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class VerifyEmailView(generics.GenericAPIView):
    serializer_class = EmailVerificationSerializer
    permission_classes = [AllowAny]

    def get(self, request, token=None):
        """Handle GET request with token in URL"""
        if not token:
            return Response({
                'error': 'Verification token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return self.verify_token(request, token)

    def post(self, request):
        """Handle POST request with token in body"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        return self.verify_token(request, token)

    def verify_token(self, request, token):
        """Common verification logic"""
        user = User.objects.filter(
            verification_token=token,
            account_status='pending',
            email_verified=False
        ).first()
        
        if not user:
            return Response({
                'error': 'Invalid or expired verification token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if user.verification_token_created_at:
            token_age = timezone.now() - user.verification_token_created_at
            if token_age > timedelta(hours=24):
                return Response({
                    'error': 'Verification token has expired. Please request a new one.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        user.account_status = 'active'
        user.email_verified = True
        user.verification_token = None
        user.verification_token_created_at = None
        user.save()
        
        return Response({
            'message': 'Email verified successfully! Your account is now active.',
            'user': UserSerializer(user).data
        })


class ResendVerificationView(generics.GenericAPIView):
    serializer_class = ResendVerificationSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        """Pass request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)

class RequestAccountDeletionView(generics.GenericAPIView):
    serializer_class = AccountDeletionSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        """Pass request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        if not user.check_password(serializer.validated_data['password']):
            return Response({
                'error': 'Incorrect password'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not serializer.validated_data['confirm']:
            return Response({
                'error': 'Please confirm account deletion'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if user.account_status == 'deactivated':
            return Response({
                'error': 'Account already deactivated and scheduled for deletion',
                'deletion_scheduled_date': user.deletion_scheduled_date
            }, status=status.HTTP_400_BAD_REQUEST)
        
        deletion_date = timezone.now() + timedelta(days=90)
        reactivation_token = generate_verification_token()
        
        user.account_status = 'deactivated'
        user.is_deleted = False
        user.deactivation_date = timezone.now()
        user.deletion_scheduled_date = deletion_date
        user.reactivation_token = reactivation_token
        user.reactivation_token_created_at = timezone.now()
        user.original_email = user.email
        user.save()
        
        # Send email
        send_account_deletion_notification(user, reactivation_token, request)
        
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        
        return Response({
            'message': 'Account has been deactivated and scheduled for permanent deletion in 90 days.',
            'deletion_scheduled_date': deletion_date,
            'can_reactivate': True,
            'reactivation_token_sent': True
        })

class ReactivateAccountView(generics.GenericAPIView):
    serializer_class = AccountReactivationSerializer
    permission_classes = [AllowAny]

    def get(self, request, token=None):
        if not token:
            return Response({
                'error': 'Reactivation token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return self.reactivate(request, token)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        return self.reactivate(request, token)

    def reactivate(self, request, token):
        user = User.objects.filter(
            reactivation_token=token,
            account_status='deactivated',
            is_deleted=False
        ).first()
        
        if not user:
            return Response({
                'error': 'Invalid or expired reactivation token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.can_reactivate():
            days_passed = (timezone.now() - user.deactivation_date).days
            return Response({
                'error': f'Reactivation window has expired. Account was deactivated {days_passed} days ago.',
                'days_passed': days_passed
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.account_status = 'active'
        user.email_verified = True
        user.is_deleted = False
        user.deactivation_date = None
        user.deletion_scheduled_date = None
        user.reactivation_token = None
        user.reactivation_token_created_at = None
        
        if user.original_email:
            user.email = user.original_email
            user.original_email = None
        
        user.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Account reactivated successfully!',
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        })

class AccountStatusView(generics.RetrieveAPIView):
    """
    Get detailed account status information for the authenticated user.
    Returns comprehensive information about account status, verification,
    and deletion grace period if applicable.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Base response
        response = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'account_status': user.account_status,
            'account_status_display': user.get_account_status_display(),
            'email_verified': user.email_verified,
            'is_active': user.is_account_active(),
            'is_deleted': user.is_deleted,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
        }
        
        # Add status-specific information
        if user.account_status == 'pending':
            response.update({
                'verification_required': True,
                'verification_token_exists': bool(user.verification_token),
                'can_resend_verification': True,
                'message': 'Please verify your email address to activate your account.'
            })
            
            # Check if token is expired
            if user.verification_token_created_at:
                token_age = timezone.now() - user.verification_token_created_at
                is_expired = token_age > timedelta(hours=24)
                response['verification_token_expired'] = is_expired
                if is_expired:
                    response['message'] = 'Your verification token has expired. Please request a new one.'
        
        elif user.account_status == 'active':
            response.update({
                'verification_required': False,
                'message': 'Your account is active and fully functional.',
                'can_request_deletion': True
            })
        
        elif user.account_status == 'deactivated':
            # Grace period information
            grace_period = user.get_deletion_grace_period_remaining()
            can_reactivate = user.can_reactivate()
            
            response.update({
                'can_reactivate': can_reactivate,
                'deactivation_date': user.deactivation_date,
                'deletion_scheduled_date': user.deletion_scheduled_date,
                'reactivation_token_exists': bool(user.reactivation_token),
                'message': 'Your account is deactivated and scheduled for permanent deletion.' if can_reactivate else 'Your account has been permanently deleted.',
            })
            
            if grace_period:
                response['grace_period'] = {
                    'days_passed': grace_period['days_passed'],
                    'days_remaining': grace_period['days_remaining'],
                    'deletion_date': grace_period['deletion_date'],
                    'total_grace_period_days': 90,
                    'percentage_remaining': round((grace_period['days_remaining'] / 90) * 100, 2)
                }
                
                if can_reactivate:
                    response['message'] = f'Your account is deactivated. You have {grace_period["days_remaining"]} days remaining to reactivate before permanent deletion.'
                    response['action_required'] = 'reactivation'
                else:
                    response['message'] = 'Your account has been permanently deleted. The 90-day grace period has expired.'
                    response['action_required'] = 'none'
        
        elif user.account_status == 'deleted':
            response.update({
                'message': 'This account has been permanently deleted.',
                'action_required': 'none'
            })
        
        # Add profile information if exists
        if hasattr(user, 'profile'):
            response['profile'] = {
                'bio': user.profile.bio,
                'specialization': user.profile.specialization,
                'preferred_language': user.profile.preferred_language,
                'notification_settings': user.profile.notification_settings
            }
        
        # Add statistics if available
        # try:
        #     from auth.attempts.models import QuizAttempt
        #     total_attempts = QuizAttempt.objects.filter(user=user).count()
        #     completed_attempts = QuizAttempt.objects.filter(user=user, status='completed').count()
            
        #     if completed_attempts > 0:
        #         from django.db.models import Avg
        #         avg_score = QuizAttempt.objects.filter(user=user, status='completed').aggregate(Avg('score'))['score__avg']
        #         response['statistics'] = {
        #             'total_quiz_attempts': total_attempts,
        #             'completed_attempts': completed_attempts,
        #             'average_score': round(avg_score, 2) if avg_score else 0
        #         }
        #     else:
        #         response['statistics'] = {
        #             'total_quiz_attempts': 0,
        #             'completed_attempts': 0,
        #             'average_score': 0
        #         }
        # except Exception:
        #     # If attempts app doesn't exist or error
        #     pass
        
        # Add available actions based on status
        response['available_actions'] = self._get_available_actions(user)
        
        return Response(response)
    
    def _get_available_actions(self, user):
        """
        Determine what actions are available to the user based on their account status
        """
        actions = []
        
        if user.account_status == 'pending':
            actions.append({
                'action': 'resend_verification',
                'method': 'POST',
                'endpoint': '/api/auth/resend-verification/',
                'description': 'Resend verification email'
            })
            actions.append({
                'action': 'resend_verification_with_email',
                'method': 'POST',
                'endpoint': '/api/auth/resend-verification/',
                'body': {'email': user.email},
                'description': 'Resend verification email (with email)'
            })
        
        elif user.account_status == 'active':
            actions.append({
                'action': 'request_deletion',
                'method': 'POST',
                'endpoint': '/api/auth/request-deletion/',
                'description': 'Request account deletion (deactivates account with 90-day grace period)',
                'requires_password': True,
                'requires_confirm': True
            })
            actions.append({
                'action': 'change_password',
                'method': 'POST',
                'endpoint': '/api/auth/change-password/',
                'description': 'Change account password',
                'requires_old_password': True
            })
            actions.append({
                'action': 'update_profile',
                'method': 'PUT/PATCH',
                'endpoint': '/api/auth/profile/',
                'description': 'Update user profile'
            })
        
        elif user.account_status == 'deactivated':
            if user.can_reactivate():
                actions.append({
                    'action': 'reactivate_account',
                    'method': 'GET/POST',
                    'endpoint': f'/api/auth/reactivate/{user.reactivation_token}/' if user.reactivation_token else '/api/auth/reactivate/',
                    'description': 'Reactivate account (within 90-day grace period)',
                    'requires_token': True
                })
            actions.append({
                'action': 'account_deleted',
                'method': 'N/A',
                'endpoint': 'N/A',
                'description': 'Account is permanently deleted',
                'requires_new_registration': True
            })
        
        elif user.account_status == 'deleted':
            actions.append({
                'action': 'register_new',
                'method': 'POST',
                'endpoint': '/api/auth/register/',
                'description': 'Create a new account',
                'requires_new_registration': True
            })
        
        return actions