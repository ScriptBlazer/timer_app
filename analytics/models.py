from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator


class WorkspaceAggregate(models.Model):
    """Overall workspace-level totals (one record per workspace)"""
    owner = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='workspace_aggregate',
        help_text='Workspace owner (one aggregate per workspace)'
    )
    total_time_seconds = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total tracked time in seconds'
    )
    total_sessions = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total completed sessions'
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total cost across all sessions'
    )
    total_timers = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total number of timers in workspace'
    )
    total_customers = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total number of customers in workspace'
    )
    total_deliverables = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total number of deliverables in workspace'
    )
    active_projects = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of active projects'
    )
    completed_projects = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of completed projects'
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text='Last time this aggregate was updated'
    )

    class Meta:
        db_table = 'analytics_workspaceaggregate'
        ordering = ['-last_updated']
        indexes = [
            models.Index(fields=['owner']),
        ]

    def __str__(self):
        return f"Workspace Aggregate: {self.owner.username}"


class DailyAggregate(models.Model):
    """Daily statistics for time-based charts (last 30 days)"""
    workspace_owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='daily_aggregates',
        help_text='Workspace owner'
    )
    date = models.DateField(
        help_text='Aggregation date'
    )
    total_time_seconds = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total time tracked on this date (seconds)'
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total cost on this date'
    )
    session_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of sessions on this date'
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text='Last time this aggregate was updated'
    )

    class Meta:
        db_table = 'analytics_dailyaggregate'
        unique_together = ['workspace_owner', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['workspace_owner', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"Daily Aggregate: {self.workspace_owner.username} - {self.date}"


class TimerAggregate(models.Model):
    """Per-timer statistics (for 'Top Timers' chart)"""
    timer = models.ForeignKey(
        'timer.Timer',
        on_delete=models.CASCADE,
        related_name='timer_aggregate',
        help_text='The timer this aggregate represents'
    )
    workspace_owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='timer_aggregates',
        help_text='Workspace owner'
    )
    total_time_seconds = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total time tracked for this timer (seconds)'
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total cost for this timer'
    )
    session_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of sessions for this timer'
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text='Last time this aggregate was updated'
    )

    class Meta:
        db_table = 'analytics_timeraggregate'
        unique_together = ['timer', 'workspace_owner']
        ordering = ['-total_time_seconds']
        indexes = [
            models.Index(fields=['workspace_owner', 'total_time_seconds']),
            models.Index(fields=['timer']),
        ]

    def __str__(self):
        return f"Timer Aggregate: {self.timer.task_name} - {self.workspace_owner.username}"


class ProjectAggregate(models.Model):
    """Per-project statistics"""
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='project_aggregate',
        help_text='The project this aggregate represents'
    )
    total_time_seconds = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total time tracked for this project (seconds)'
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total cost for this project'
    )
    session_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of sessions for this project'
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text='Last time this aggregate was updated'
    )

    class Meta:
        db_table = 'analytics_projectaggregate'
        ordering = ['-total_time_seconds']
        indexes = [
            models.Index(fields=['project']),
            models.Index(fields=['total_time_seconds']),
        ]

    def __str__(self):
        return f"Project Aggregate: {self.project.name}"


class CustomerAggregate(models.Model):
    """Per-customer statistics"""
    customer = models.OneToOneField(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='customer_aggregate',
        help_text='The customer this aggregate represents'
    )
    total_time_seconds = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total time tracked for this customer (seconds)'
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total cost for this customer'
    )
    session_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of sessions for this customer'
    )
    project_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of projects for this customer'
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text='Last time this aggregate was updated'
    )

    class Meta:
        db_table = 'analytics_customeraggregate'
        ordering = ['-total_time_seconds']
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['total_time_seconds']),
        ]

    def __str__(self):
        return f"Customer Aggregate: {self.customer.name}"


class DeliverableAggregate(models.Model):
    """Per-deliverable statistics"""
    deliverable = models.OneToOneField(
        'deliverables.Deliverable',
        on_delete=models.CASCADE,
        related_name='deliverable_aggregate',
        help_text='The deliverable this aggregate represents'
    )
    total_time_seconds = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total time tracked for this deliverable (seconds)'
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total cost for this deliverable'
    )
    session_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of sessions for this deliverable'
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text='Last time this aggregate was updated'
    )

    class Meta:
        db_table = 'analytics_deliverableaggregate'
        ordering = ['-total_time_seconds']
        indexes = [
            models.Index(fields=['deliverable']),
            models.Index(fields=['total_time_seconds']),
        ]

    def __str__(self):
        return f"Deliverable Aggregate: {self.deliverable.name}"


class UserAggregate(models.Model):
    """Per-user statistics within workspace (team member stats)"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_aggregates',
        help_text='The user (team member) this aggregate represents'
    )
    workspace_owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='team_member_aggregates',
        help_text='Workspace owner'
    )
    total_time_seconds = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total time tracked by this user (seconds)'
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Total cost for this user'
    )
    session_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Number of sessions created by this user'
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text='Last time this aggregate was updated'
    )

    class Meta:
        db_table = 'analytics_useraggregate'
        unique_together = ['user', 'workspace_owner']
        ordering = ['-total_time_seconds']
        indexes = [
            models.Index(fields=['workspace_owner', 'total_time_seconds']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"User Aggregate: {self.user.username} - {self.workspace_owner.username}"