from django.urls import path, include
from .views import RegisterView, LoginView, UserProfileView, AddressListCreateView, AddressDetailView, UserSettingsView, UserStatsView, ContactMessageCreateView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password-reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    # Address endpoints
    path('addresses/', AddressListCreateView.as_view(), name='address-list-create'),
    path('addresses/<int:pk>/', AddressDetailView.as_view(), name='address-detail'),
    # User settings endpoint
    path('settings/', UserSettingsView.as_view(), name='user-settings'),
    path('profile/stats/', UserStatsView.as_view(), name='user-stats'),
    path('contact/', ContactMessageCreateView.as_view(), name='contact-message'),
]
