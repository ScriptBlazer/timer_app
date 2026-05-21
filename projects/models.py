from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from customers.models import Customer


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
        db_table = 'timer_app_project'  # Use existing table name

    def __str__(self):
        return f"{self.name} ({self.customer.name})"

    def total_duration_seconds(self):
        """Calculate total duration across all timers in seconds"""
        total = 0
        for project_timer in self.project_timers.all():
            total += project_timer.total_duration_seconds()
        return total

    def total_cost(self):
        """Calculate total cost across all timers"""
        total = 0
        for project_timer in self.project_timers.all():
            total += project_timer.total_cost()
        return round(total, 2)

    def _project_aggregate(self):
        try:
            return self.project_aggregate
        except ObjectDoesNotExist:
            return None

    def display_total_time_seconds(self):
        """UI total time: prefer analytics aggregate, fallback to live calculation."""
        aggregate = self._project_aggregate()
        if aggregate is not None:
            return aggregate.total_time_seconds
        return self.total_duration_seconds()

    def display_total_cost(self):
        """UI total cost: prefer analytics aggregate, fallback to live calculation."""
        aggregate = self._project_aggregate()
        if aggregate is not None:
            return float(aggregate.total_cost)
        return self.total_cost()

    def display_timer_count(self):
        """UI timer count: use annotate(timer_count) when present, else query."""
        if hasattr(self, 'timer_count'):
            return self.timer_count
        return self.project_timers.count()

