from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .models import User, UserProfile
from .tokens import generate_verification_token
from .email_utils import send_verification_email

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'account_status', 'email_verified', 'date_joined')
        read_only_fields = ('id', 'date_joined', 'account_status', 'email_verified')

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('bio', 'specialization', 'preferred_language', 'notification_settings')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        
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
            # Build verification URL using request
            verification_url = request.build_absolute_uri(
                f'/api/auth/verify-email/{token}/'
            )
            # Or using reverse
            # from django.urls import reverse
            # verification_url = request.build_absolute_uri(
            #     reverse('verify-email', kwargs={'token': token})
            # )
            # else:
            #     # Fallback: build using settings
            #     from django.conf import settings
            #     verification_url = f"{settings.BACKEND_URL}/api/auth/verify-email/{token}/"
        
            # Pass the full URL to email utility
            send_verification_email(user, verification_url)
            
            return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        # Check if user exists
        try:
            user = User.objects.get(username=username)
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
        from .tokens import generate_verification_token
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
