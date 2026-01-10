from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid


class PendingRegistration(models.Model):
    """Stores pending user registrations awaiting approval"""
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField()
    password_hash = models.CharField(max_length=128)  # Store hashed password
    approval_token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'timer_app_pendingregistration'  # Use existing table name
    
    def __str__(self):
        return f"Pending: {self.username}"


class TeamMember(models.Model):
    """Links team members to workspace owners"""
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('member', 'Member'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_owner')
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_member')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['owner', 'member']
        ordering = ['-created_at']
        db_table = 'timer_app_teammember'  # Use existing table name
    
    def __str__(self):
        return f"{self.member.username} in {self.owner.username}'s workspace"


class CustomColor(models.Model):
    """Custom colors saved by workspace owners"""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_colors')
    color = models.CharField(max_length=7, help_text='Hex color code')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['owner', 'color']
        ordering = ['-created_at']
        db_table = 'timer_app_customcolor'  # Use existing table name
    
    def __str__(self):
        return f"{self.owner.username}: {self.color}"


class Timer(models.Model):
    """A global timer template belonging to a user"""
    task_name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timers')
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    header_color = models.CharField(max_length=7, default='#3498db', help_text='Hex color code for timer card header')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['task_name']
        db_table = 'timer_app_timer'  # Use existing table name

    def __str__(self):
        return self.task_name


class ProjectTimer(models.Model):
    """Junction table linking timers to projects"""
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='project_timers')
    timer = models.ForeignKey(Timer, on_delete=models.CASCADE, related_name='project_timers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['project', 'timer']
        ordering = ['-created_at']
        db_table = 'timer_app_projecttimer'  # Use existing table name

    def __str__(self):
        return f"{self.timer.task_name} on {self.project.name}"

    def is_running(self):
        """Check if this timer has an active session on this project"""
        return self.sessions.filter(end_time__isnull=True).exists()

    def is_paused(self):
        """Check if this timer is currently paused"""
        active_session = self.active_session()
        return active_session and active_session.is_paused()

    def active_session(self):
        """Get the active session if any"""
        return self.sessions.filter(end_time__isnull=True).first()

    def current_duration_seconds(self):
        """Get current duration in seconds if timer is running (excluding pauses)"""
        session = self.active_session()
        if session:
            return session.duration_seconds()
        return 0

    def total_duration_seconds(self):
        """Calculate total duration across all completed sessions in seconds"""
        total = 0
        for session in self.sessions.filter(end_time__isnull=False):
            duration = (session.end_time - session.start_time).total_seconds()
            total += duration
        return total

    def total_cost(self):
        """Calculate total cost across all completed sessions using their snapshot prices"""
        total = 0
        for session in self.sessions.filter(end_time__isnull=False):
            total += session.cost()
        return round(total, 2)


class TimerSession(models.Model):
    """A single session of a timer (start to stop)"""
    project_timer = models.ForeignKey(ProjectTimer, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)  # Snapshot of price at session start
    note = models.TextField(blank=True, default='')
    deliverable = models.ForeignKey('deliverables.Deliverable', on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions_created')
    pause_start_time = models.DateTimeField(null=True, blank=True, help_text='Time when timer was paused (active pause, not resumed yet)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']
        db_table = 'timer_app_timersession'  # Use existing table name

    def __str__(self):
        return f"{self.project_timer.timer.task_name} - {self.start_time}"

    def is_paused(self):
        """Check if this session is currently paused"""
        return self.pause_start_time is not None and self.end_time is None

    def paused_duration_seconds(self):
        """Calculate total duration of all completed pauses in seconds"""
        total = 0
        for pause in self.pauses.all():
            total += pause.duration_seconds()
        return total

    def duration_seconds(self):
        """Calculate duration in seconds, excluding completed pauses"""
        # Determine effective end time
        if self.end_time:
            effective_end = self.end_time
        elif self.is_paused():
            # If paused, duration is up to pause time
            effective_end = self.pause_start_time
        else:
            # Still running
            effective_end = timezone.now()
        
        base_duration = (effective_end - self.start_time).total_seconds()
        # Subtract completed pause durations
        pause_duration = self.paused_duration_seconds()
        return max(0, base_duration - pause_duration)

    def cost(self):
        """Calculate cost for this session using the snapshot price"""
        if self.end_time:
            hours = self.duration_seconds() / 3600
            return round(float(self.price_per_hour) * hours, 2)
        return 0

    def clean(self):
        """Validate that only one session per project_timer can be active"""
        if not self.end_time:
            active_sessions = TimerSession.objects.filter(
                project_timer=self.project_timer,
                end_time__isnull=True
            )
            if self.pk:
                active_sessions = active_sessions.exclude(pk=self.pk)
            if active_sessions.exists():
                raise ValidationError("This timer already has an active session")


class TimerPause(models.Model):
    """A completed pause period (pause that was resumed)"""
    session = models.ForeignKey(TimerSession, on_delete=models.CASCADE, related_name='pauses')
    pause_start_time = models.DateTimeField()
    pause_end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['pause_start_time']
        db_table = 'timer_app_timerpause'  # Use existing table name

    def __str__(self):
        return f"Pause: {self.pause_start_time} - {self.pause_end_time}"

    def duration_seconds(self):
        """Calculate pause duration in seconds"""
        return (self.pause_end_time - self.pause_start_time).total_seconds()

    def clean(self):
        """Validate pause times"""
        # Skip validation if fields are None (empty form in formset)
        if self.pause_start_time is None or self.pause_end_time is None:
            return
        
        if self.pause_end_time <= self.pause_start_time:
            raise ValidationError("Pause end time must be after start time")
        
        # Validate pause is within session bounds
        if self.session:
            if self.pause_start_time < self.session.start_time:
                raise ValidationError("Pause cannot start before session start")
            if self.session.end_time and self.pause_end_time > self.session.end_time:
                raise ValidationError("Pause cannot end after session end")


# Helper functions for workspace management
def get_workspace_owner(user):
    """Get the workspace owner for a user (could be the user themselves or their owner)"""
    # Check if user is a team member
    team_membership = TeamMember.objects.filter(member=user).first()
    if team_membership:
        return team_membership.owner
    # User is their own owner
    return user


def is_workspace_owner(user):
    """Check if user is a workspace owner (not a team member)"""
    return not TeamMember.objects.filter(member=user).exists()


def get_workspace_users(user):
    """Get all users in the workspace (owner + team members)"""
    owner = get_workspace_owner(user)
    # Get all team members
    team_members = TeamMember.objects.filter(owner=owner).values_list('member', flat=True)
    # Return owner + all team members
    return User.objects.filter(models.Q(pk=owner.pk) | models.Q(pk__in=team_members))
