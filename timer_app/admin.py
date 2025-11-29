from django.contrib import admin
from .models import Customer, Project, Timer, ProjectTimer, TimerSession, TeamMember, PendingRegistration

admin.site.register(Customer)
admin.site.register(Project)
admin.site.register(Timer)
admin.site.register(ProjectTimer)
admin.site.register(TimerSession)
admin.site.register(TeamMember)
admin.site.register(PendingRegistration)
