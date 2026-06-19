from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from auth_api.models import User, UserProfile
from auth_api.tokens import generate_verification_token, generate_verification_token
from auth_api.email_utils import send_verification_email

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
            verification_url = request.build_absolute_uri(
                f'/api/auth/verify-email/{token}/'
            )
            # else:
            #     from django.conf import settings
            #     verification_url = f"{settings.BACKEND_URL}/api/auth/verify-email/{token}/"
        
            # Send verification email (plain text)
            send_verification_email(user, verification_url)
            
            return user

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
        
            # Resend verification email (plain text)
            send_verification_email(user, verification_url)
            
            attrs['message'] = 'Verification email has been resent. Please check your inbox.'
            return attrs