from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login  # Add this import

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'phone', 'address')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

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