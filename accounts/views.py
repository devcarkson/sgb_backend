from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer, LoginSerializer
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate, login  # Added login import

class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request}  # Pass request for session auth
        )
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        remember_me = serializer.validated_data.get('remember_me', False)
        
        if not user.is_active:
            return Response(
                {"detail": "Account is disabled"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create session (for session-based auth)
        login(request, user)
        
        # Set session expiration based on remember_me
        if remember_me:
            request.session.set_expiry(1209600)  # 2 weeks
        else:
            request.session.set_expiry(86400)  # 1 day
        
        # Generate JWT tokens (for token-based auth)
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'sessionid': request.session.session_key,  # For debugging
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class MyTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]