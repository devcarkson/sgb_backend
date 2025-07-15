from django.urls import include, path
from .views import RegisterView, LoginView, UserProfileView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('password-reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),

]