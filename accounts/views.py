from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer, LoginSerializer, AddressSerializer, UserSettingsSerializer, ContactMessageSerializer
from .models import ContactMessage
from django.core.mail import mail_admins
from .models import Address, UserSettings
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate, login  # Added login import
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


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

class ContactMessageCreateView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        instance = serializer.save()
        mail_admins(
            subject=f"New Contact Message: {instance.subject}",
            message=f"From: {instance.first_name} {instance.last_name} <{instance.email}>\n\n{instance.message}",
        )

# Address CRUD
class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

# UserSettings retrieve/update
class UserSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Ensure settings exist for user
        settings, _ = UserSettings.objects.get_or_create(user=self.request.user)
        return settings
    

    
class UserStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Example logic, adjust according to your models
        total_orders = getattr(user, 'orders', []).count() if hasattr(user, 'orders') else 0
        total_spent = sum(order.total for order in getattr(user, 'orders', []).all()) if hasattr(user, 'orders') else 0
        wishlist_items = getattr(user, 'wishlist', []).count() if hasattr(user, 'wishlist') else 0
        member_since = user.date_joined.strftime('%Y-%m-%d') if hasattr(user, 'date_joined') else ''

        return Response({
            'totalOrders': total_orders,
            'totalSpent': total_spent,
            'wishlistItems': wishlist_items,
            'memberSince': member_since,
        })