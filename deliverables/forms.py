from django import forms
from django.core.exceptions import ValidationError
from .models import Deliverable


class DeliverableForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
    
    class Meta:
        model = Deliverable
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Video 1, Kitchen wall, Landing page'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Optional description...',
                'rows': 4
            }),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and self.project:
            # Check for duplicate name within the same project
            queryset = Deliverable.objects.filter(project=self.project, name=name)
            # If editing, exclude the current instance
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError('A deliverable with this name already exists for this project.')
        
        return name


