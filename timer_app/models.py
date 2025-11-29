from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone


class Customer(models.Model):
    """A customer/client that belongs to a user"""
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def total_duration_seconds(self):
        """Calculate total duration across all projects in seconds"""
        total = 0
        for project in self.projects.all():
            total += project.total_duration_seconds()
        return total

    def total_cost(self):
        """Calculate total cost across all projects"""
        total = 0
        for project in self.projects.all():
            total += project.total_cost()
        return round(total, 2)


class Project(models.Model):
    """A project belonging to a customer"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]
    
    name = models.CharField(max_length=200)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='projects')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.customer.name})"

    def total_duration_seconds(self):
        """Calculate total duration across all timers in seconds"""
        total = 0
        for timer in self.timers.all():
            total += timer.total_duration_seconds()
        return total

    def total_cost(self):
        """Calculate total cost across all timers"""
        total = 0
        for timer in self.timers.all():
            total += timer.total_cost()
        return round(total, 2)


class Timer(models.Model):
    """A timer/task belonging to a project"""
    task_name = models.CharField(max_length=200)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='timers')
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task_name} - {self.project.name}"

    def is_running(self):
        """Check if this timer has an active session"""
        return self.sessions.filter(end_time__isnull=True).exists()

    def active_session(self):
        """Get the active session if any"""
        return self.sessions.filter(end_time__isnull=True).first()

    def current_duration_seconds(self):
        """Get current duration in seconds if timer is running"""
        session = self.active_session()
        if session:
            return (timezone.now() - session.start_time).total_seconds()
        return 0

    def total_duration_seconds(self):
        """Calculate total duration across all completed sessions in seconds"""
        total = 0
        for session in self.sessions.filter(end_time__isnull=False):
            duration = (session.end_time - session.start_time).total_seconds()
            total += duration
        return total

    def total_cost(self):
        """Calculate total cost across all completed sessions"""
        total_hours = self.total_duration_seconds() / 3600
        return round(float(self.price_per_hour) * total_hours, 2)


class TimerSession(models.Model):
    """A single session of a timer (start to stop)"""
    timer = models.ForeignKey(Timer, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.timer.task_name} - {self.start_time}"

    def duration_seconds(self):
        """Calculate duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (timezone.now() - self.start_time).total_seconds()

    def cost(self):
        """Calculate cost for this session"""
        if self.end_time:
            hours = self.duration_seconds() / 3600
            return round(float(self.timer.price_per_hour) * hours, 2)
        return 0

    def clean(self):
        """Validate that only one session per timer can be active"""
        if not self.end_time:
            active_sessions = TimerSession.objects.filter(
                timer=self.timer,
                end_time__isnull=True
            )
            if self.pk:
                active_sessions = active_sessions.exclude(pk=self.pk)
            if active_sessions.exists():
                raise ValidationError("This timer already has an active session")
