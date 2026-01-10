from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Timer, ProjectTimer, TimerSession, TimerPause


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
        fields = ['start_time', 'end_time', 'note', 'deliverable']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'note': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Describe what you worked on...', 'rows': 4}),
            'deliverable': forms.Select(attrs={'class': 'form-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Format datetime fields for HTML5 datetime-local input
        if self.instance and self.instance.pk:
            if self.instance.start_time:
                self.initial['start_time'] = self.instance.start_time.strftime('%Y-%m-%dT%H:%M')
            if self.instance.end_time:
                self.initial['end_time'] = self.instance.end_time.strftime('%Y-%m-%dT%H:%M')
        
        # Filter deliverables by project
        if self.instance and self.instance.pk:
            project = self.instance.project_timer.project
            from deliverables.models import Deliverable
            self.fields['deliverable'].queryset = Deliverable.objects.filter(project=project).order_by('name')
            self.fields['deliverable'].required = False
            self.fields['deliverable'].empty_label = 'No deliverable'


class PauseForm(forms.ModelForm):
    class Meta:
        model = TimerPause
        fields = ['pause_start_time', 'pause_end_time']
        widgets = {
            'pause_start_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'pause_end_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Format datetime fields for HTML5 datetime-local input
        if self.instance and self.instance.pk:
            if self.instance.pause_start_time:
                self.initial['pause_start_time'] = self.instance.pause_start_time.strftime('%Y-%m-%dT%H:%M')
            if self.instance.pause_end_time:
                self.initial['pause_end_time'] = self.instance.pause_end_time.strftime('%Y-%m-%dT%H:%M')


# Inline formset for pauses
PauseFormSet = inlineformset_factory(
    TimerSession,
    TimerPause,
    form=PauseForm,
    extra=0,  # No extra forms by default - user clicks "Add Pause" to add one
    can_delete=True,
    fields=['pause_start_time', 'pause_end_time']
)

