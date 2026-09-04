import logging

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .models import User, UserProfile
from .tokens import generate_verification_token
from .email_utils import send_verification_email, send_password_reset_email

logger = logging.getLogger(__name__)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'account_status', 'email_verified', 'date_joined')
        read_only_fields = ('id', 'date_joined', 'account_status', 'email_verified')

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    class Meta:
        model = UserProfile
        fields = ('username', 'email', 'bio', 'specialization', 'preferred_language', 'notification_settings', 'profile_image')
    def get_username(self, obj):
        return obj.user.username
    
    def get_email(self, obj):
        return obj.user.email
    
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2')
        extra_kwargs = {
            'email': {
                'required': True,
                'allow_blank': False,
            }
        }

    def validate_email(self, value):
        """Check if email already exists (case-insensitive)"""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'A user with this email address already exists.'
            )
        return value.lower()  # Normalize email to lowercase


    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        try:
            validated_data.pop('password2')
            
            # Ensure email is lowercase
            validated_data['email'] = validated_data['email'].lower()

            token = generate_verification_token()
            
            user = User.objects.create_user(
                **validated_data,
                account_status='pending',
                email_verified=False,
                verification_token=token,
                verification_token_created_at=timezone.now()
            )
            UserProfile.objects.create(user=user)
            
            # Get request from context to build full URL
            request = self.context.get('request')
            if request:
                verification_url = request.build_absolute_uri(
                    f'/api/auth/verify-email/{token}/'
                )
                send_verification_email(user, verification_url)
                
                return user
        except Exception as e:
            logger.exception("Error creating new user : %s", e)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        login_field = attrs.get('username') # can be username or email
        password = attrs.get('password')
        # Check if user exists
        try:
            try:
                user = User.objects.get(username=login_field)
            except User.DoesNotExist:
                user = None
            if not user:
                user = User.objects.filter(email__iexact=login_field).first()
            if not user:
                raise serializers.ValidationError({
                'error': 'Invalid credentials',
                'code': 'invalid_credentials'
            })
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'Invalid credentials',
                'code': 'invalid_credentials'
            })
        
        # Check account status
        if user.is_deleted:
            raise serializers.ValidationError({
                'error': 'This account has been permanently deleted.',
                'code': 'account_deleted'
            })
        
        if user.account_status == 'pending':
            raise serializers.ValidationError({
                'error': 'Please verify your email address before logging in.',
                'code': 'email_not_verified',
                'email': user.email,
                'can_resend_verification': True
            })
        
        if user.account_status == 'deactivated':
            if user.can_reactivate():
                days_remaining = user.get_deletion_grace_period_remaining()
                raise serializers.ValidationError({
                    'error': 'Your account has been deactivated and is scheduled for deletion.',
                    'code': 'account_deactivated',
                    'can_reactivate': True,
                    'days_remaining': days_remaining['days_remaining'] if days_remaining else 0,
                    'deletion_date': user.deletion_scheduled_date
                })
            else:
                raise serializers.ValidationError({
                    'error': 'Your account has been permanently deleted.',
                    'code': 'account_deleted',
                    'can_reactivate': False
                })
            
        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError({
                'error': 'Invalid credentials',
                'code': 'invalid_credentials'
            })
        
        # Check if account is active
        if not user.is_account_active():
            raise serializers.ValidationError({
                'error': 'Account is not active.',
                'code': 'account_inactive',
                'account_status': user.account_status
            })

        attrs['user'] = user
        
        return attrs
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords don't match."})
        return attrs

class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)

class AccountDeletionSerializer(serializers.Serializer):
    password = serializers.CharField(required=True, write_only=True)
    confirm = serializers.BooleanField(required=True)

class AccountReactivationSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)

class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        user = User.objects.filter(email=email, account_status='pending', email_verified=False).first()
        
        if not user:
            raise serializers.ValidationError({
                'email': 'No pending account found with this email'
            })
        
        # Generate new token
        
        token = generate_verification_token()
        user.verification_token = token
        user.verification_token_created_at = timezone.now()
        user.save()
        
        # Get request from context to build full URL
        request = self.context.get('request')
        if request:
            verification_url = request.build_absolute_uri(
                f'/api/auth/verify-email/{token}/'
            )
            # else:
            #     from django.conf import settings
            #     verification_url = f"{settings.BACKEND_URL}/api/auth/verify-email/{token}/"
        
            # Resend verification email
            from .email_utils import send_verification_email
            send_verification_email(user, verification_url)
            
            attrs['message'] = 'Verification email has been resent. Please check your inbox.'
            return attrs

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting password reset
    """
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        value = value.lower()
        user = User.objects.filter(email__iexact=value).first()
        
        if not user:
            raise serializers.ValidationError(
                'No user found with this email address.'
            )
        
        # Check if user is active
        if user.is_deleted:
            raise serializers.ValidationError(
                'This account has been permanently deleted.'
            )
        
        if user.account_status == 'deactivated':
            raise serializers.ValidationError(
                'This account is deactivated. Please reactivate your account first.'
            )
        
        return value

    def create(self, validated_data):
        email = validated_data['email']
        user = User.objects.get(email=email)
        
        # Generate reset token
        token = generate_verification_token()
        user.reset_password_token = token
        user.reset_password_token_created_at = timezone.now()
        user.save()
        
        # Build reset URL
        request = self.context.get('request')
        if request:
            reset_url = request.build_absolute_uri(
                f'/api/auth/reset-password/{token}/'
            )
        else:
            from django.conf import settings
            reset_url = f"{settings.BACKEND_URL}/api/auth/reset-password/{token}/"
        
        # Send email
        send_password_reset_email(user, reset_url)
        
        return {'message': 'Password reset email has been sent.'}


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming password reset with token
    """
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    class Meta:
        fields = ['token', 'new_password', 'confirm_password']
        
    def validate(self, attrs):
        token = attrs.get('token')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        # Check if passwords match
        if new_password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        
        # Find user with this token
        user = User.objects.filter(
            reset_password_token=token
        ).first()
        
        if not user:
            raise serializers.ValidationError({
                'token': 'Invalid or expired reset token.'
            })
        
        # Check if token is expired (24 hours)
        if not user.is_reset_token_valid():
            raise serializers.ValidationError({
                'token': 'Reset token has expired. Please request a new password reset.'
            })
        
        # Check account status
        if user.is_deleted:
            raise serializers.ValidationError({
                'error': 'This account has been permanently deleted.'
            })
        
        if user.account_status == 'deactivated':
            raise serializers.ValidationError({
                'error': 'This account is deactivated. Please reactivate your account first.'
            })
        
        # Store user for later use
        attrs['user'] = user
        return attrs


class PasswordResetCompleteSerializer(serializers.Serializer):
    """
    Serializer for completing password reset
    """
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate(self, attrs):
        token = attrs.get('token')
        
        # Find user with this token
        user = User.objects.filter(
            reset_password_token=token
        ).first()
        
        if not user:
            raise serializers.ValidationError({
                'token': 'Invalid or expired reset token.'
            })
        
        # Check if token is expired (24 hours)
        if not user.is_reset_token_valid():
            raise serializers.ValidationError({
                'token': 'Reset token has expired. Please request a new password reset.'
            })
        
        attrs['user'] = user
        return attrs

class InstructorListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing instructors"""
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'profile',
            'date_joined',
            'account_status',
        ]