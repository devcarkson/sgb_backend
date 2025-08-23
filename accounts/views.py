from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from .serializers import UserSerializer, LoginSerializer, AddressSerializer, UserSettingsSerializer, ContactMessageSerializer
from .models import ContactMessage
from .email_service import EmailService
from .models import Address, UserSettings
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate, login  # Added login import
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
import logging

logger = logging.getLogger(__name__)

class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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

@method_decorator(never_cache, name='dispatch')
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
        try:
            # Send notification email to admins using EmailService
            EmailService.send_contact_form_notification(instance)
            logger.info(f"Contact form notification sent for message from {instance.email}")
        except Exception as e:
            logger.error(f"Failed to send contact form notification: {str(e)}")

# Address CRUD
@method_decorator(never_cache, name='dispatch')
class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@method_decorator(never_cache, name='dispatch')
class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

# UserSettings retrieve/update
@method_decorator(never_cache, name='dispatch')
class UserSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Ensure settings exist for user
        settings, _ = UserSettings.objects.get_or_create(user=self.request.user)
        return settings
    

    
@method_decorator(never_cache, name='dispatch')
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