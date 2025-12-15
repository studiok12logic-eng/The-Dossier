from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import CustomUser

class CustomUserChangeForm(UserChangeForm):
    password = None # Exclude password field from this simple profile form
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'email': forms.EmailInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
        }
