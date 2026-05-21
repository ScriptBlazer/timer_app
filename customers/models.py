from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.contrib.auth.models import User


class Customer(models.Model):
    """A customer/client that belongs to a user"""
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        db_table = 'timer_app_customer'  # Use existing table name

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

    def _customer_aggregate(self):
        try:
            return self.customer_aggregate
        except ObjectDoesNotExist:
            return None

    def display_total_time_seconds(self):
        """UI total time: prefer analytics aggregate, fallback to live calculation."""
        aggregate = self._customer_aggregate()
        if aggregate is not None:
            return aggregate.total_time_seconds
        return self.total_duration_seconds()

    def display_total_cost(self):
        """UI total cost: prefer analytics aggregate, fallback to live calculation."""
        aggregate = self._customer_aggregate()
        if aggregate is not None:
            return float(aggregate.total_cost)
        return self.total_cost()

    def display_project_count(self):
        """UI project count: prefer analytics aggregate, fallback to live count."""
        aggregate = self._customer_aggregate()
        if aggregate is not None:
            return aggregate.project_count
        return self.projects.count()

