from django.db import models
from django.contrib.auth.models import User
from projects.models import Project


class Deliverable(models.Model):
    """A deliverable item within a project (e.g., 'Video 1', 'Kitchen wall', 'Landing page')"""
    name = models.CharField(max_length=200)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='deliverables')
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'timer_app_deliverable'  # Use existing table naming convention
        unique_together = ['project', 'name']  # Prevent duplicate names within a project

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    def total_duration_seconds(self):
        """Calculate total duration across all sessions linked to this deliverable"""
        from timer.models import TimerSession
        total = 0
        for session in TimerSession.objects.filter(deliverable=self, end_time__isnull=False):
            total += session.duration_seconds()
        return total

    def total_cost(self):
        """Calculate total cost across all sessions linked to this deliverable"""
        from timer.models import TimerSession
        total = 0
        for session in TimerSession.objects.filter(deliverable=self, end_time__isnull=False):
            total += session.cost()
        return round(total, 2)

    def session_count(self):
        """Get count of sessions linked to this deliverable"""
        from timer.models import TimerSession
        return TimerSession.objects.filter(deliverable=self, end_time__isnull=False).count()


