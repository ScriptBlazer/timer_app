from django.contrib import admin
from .models import Customer, Project, Timer, TimerSession

admin.site.register(Customer)
admin.site.register(Project)
admin.site.register(Timer)
admin.site.register(TimerSession)
