from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    # No need to add settings or addresses here; use related models
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True)
    type = models.CharField(max_length=20, default='home')  # home, work, other
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name}, {self.street}, {self.city}"

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    order_updates = models.BooleanField(default=True)
    promotional_emails = models.BooleanField(default=True)
    two_factor_auth = models.BooleanField(default=False)
    language = models.CharField(max_length=10, default='en')
    currency = models.CharField(max_length=10, default='NGN')
    theme = models.CharField(max_length=20, default='light')

    def __str__(self):
        return f"Settings for {self.user.email}"