from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Timer, ProjectTimer, TimerSession


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class TimerForm(forms.ModelForm):
    class Meta:
        model = Timer
        fields = ['task_name', 'price_per_hour', 'header_color']
        widgets = {
            'task_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Task name'}),
            'price_per_hour': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Price per hour', 'step': '0.01'}),
            'header_color': forms.TextInput(attrs={'class': 'form-input color-input', 'type': 'color'}),
        }


class SessionNoteForm(forms.ModelForm):
    class Meta:
        model = TimerSession
        fields = ['note']
        widgets = {
            'note': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Describe what you worked on...', 'rows': 4}),
        }


class SessionEditForm(forms.ModelForm):
    class Meta:
        model = TimerSession
        fields = ['start_time', 'end_time', 'note']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'note': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Describe what you worked on...', 'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Format datetime fields for HTML5 datetime-local input
        if self.instance and self.instance.pk:
            if self.instance.start_time:
                self.initial['start_time'] = self.instance.start_time.strftime('%Y-%m-%dT%H:%M')
            if self.instance.end_time:
                self.initial['end_time'] = self.instance.end_time.strftime('%Y-%m-%dT%H:%M')

