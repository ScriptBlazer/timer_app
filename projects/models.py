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

