from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Customer, Project, Timer, TimerSession


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Customer name'}),
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Project name'}),
        }


class TimerForm(forms.ModelForm):
    class Meta:
        model = Timer
        fields = ['task_name', 'price_per_hour']
        widgets = {
            'task_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Task name'}),
            'price_per_hour': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Price per hour', 'step': '0.01'}),
        }


class SessionNoteForm(forms.ModelForm):
    class Meta:
        model = TimerSession
        fields = ['note']
        widgets = {
            'note': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Describe what you worked on...', 'rows': 4}),
        }

