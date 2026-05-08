from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, FitnessGroup, GroupMessage

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = CustomUser
        fields = ['username', 'email']

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'age', 'height', 'weight', 'activity_level', 'profile_picture']


class FitnessGroupForm(forms.ModelForm):
    class Meta:
        model = FitnessGroup
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Example: Morning Walk Crew'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Who is this group for?'}),
        }


class GroupMessageForm(forms.ModelForm):
    class Meta:
        model = GroupMessage
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Share your workout, ask a question, or cheer someone on'}),
        }
