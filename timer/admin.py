from django.contrib import admin
from .models import Timer, ProjectTimer, TimerSession, TimerPause, TeamMember, PendingRegistration
from customers.models import Customer
from projects.models import Project

admin.site.register(Customer)
admin.site.register(Project)
admin.site.register(Timer)
admin.site.register(ProjectTimer)
admin.site.register(TimerSession)
admin.site.register(TimerPause)
admin.site.register(TeamMember)
admin.site.register(PendingRegistration)
