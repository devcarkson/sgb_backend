from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login  # Add this import
from .models import Address, ContactMessage, UserSettings

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'first_name', 'last_name', 'phone')  # address removed
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'email': {'required': False, 'allow_blank': True},
            'username': {'required': False, 'allow_blank': True},
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
            'phone': {'required': False, 'allow_blank': True},
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({"password": ["This field is required."]})
        
        # Ensure username is set (required by Django's User model)
        if not validated_data.get('username'):
            validated_data['username'] = validated_data.get('email', '')
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'first_name', 'last_name', 'street', 'city', 'state', 'zip_code',
            'phone', 'type', 'is_default'
        ]

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = [
            'email_notifications', 'sms_notifications', 'order_updates',
            'promotional_emails', 'two_factor_auth', 'language', 'currency', 'theme'
        ]

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = '__all__'

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False, required=False)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        request = self.context.get('request')  # Get request from context
        
        if email and password:
            user = authenticate(request=request, username=email, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled")
                
                # Create session (for session auth)
                login(request, user)
                
                # Set session expiration based on remember_me
                if data.get('remember_me'):
                    request.session.set_expiry(1209600)  # 2 weeks
                else:
                    request.session.set_expiry(86400)  # 1 day
                
                # Generate JWT tokens (for token auth)
                refresh = RefreshToken.for_user(user)
                
                data['user'] = user
                data['tokens'] = {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
                return data
            raise serializers.ValidationError("Unable to log in with provided credentials")
        raise serializers.ValidationError("Must include 'email' and 'password'")