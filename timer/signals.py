"""
Signal handlers for updating analytics aggregates when sessions, pauses, timers, customers, projects, or deliverables change.
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from .models import TimerSession, TimerPause, Timer
from analytics.models import (
    WorkspaceAggregate, DailyAggregate, TimerAggregate,
    ProjectAggregate, CustomerAggregate, DeliverableAggregate, UserAggregate
)
from .models import get_workspace_owner

# Store old session values for delta calculation
_old_session_values = {}


def get_or_create_workspace_aggregate(workspace_owner):
    """Get or create workspace aggregate"""
    aggregate, created = WorkspaceAggregate.objects.get_or_create(owner=workspace_owner)
    return aggregate


def update_workspace_aggregate(workspace_owner, time_delta=0, cost_delta=0, sessions_delta=0):
    """Update workspace aggregate with deltas"""
    aggregate = get_or_create_workspace_aggregate(workspace_owner)
    aggregate.total_time_seconds = max(0, aggregate.total_time_seconds + time_delta)
    aggregate.total_cost = max(0, aggregate.total_cost + cost_delta)
    aggregate.total_sessions = max(0, aggregate.total_sessions + sessions_delta)
    aggregate.save(update_fields=['total_time_seconds', 'total_cost', 'total_sessions', 'last_updated'])


def update_daily_aggregate(workspace_owner, date, time_delta=0, cost_delta=0, sessions_delta=0):
    """Update daily aggregate for a specific date"""
    aggregate, created = DailyAggregate.objects.get_or_create(
        workspace_owner=workspace_owner,
        date=date,
        defaults={
            'total_time_seconds': 0,
            'total_cost': 0,
            'session_count': 0
        }
    )
    aggregate.total_time_seconds = max(0, aggregate.total_time_seconds + time_delta)
    aggregate.total_cost = max(0, aggregate.total_cost + cost_delta)
    aggregate.session_count = max(0, aggregate.session_count + sessions_delta)
    aggregate.save(update_fields=['total_time_seconds', 'total_cost', 'session_count', 'last_updated'])


def update_timer_aggregate(timer, workspace_owner, time_delta=0, cost_delta=0, sessions_delta=0):
    """Update timer aggregate with deltas"""
    aggregate, created = TimerAggregate.objects.get_or_create(
        timer=timer,
        workspace_owner=workspace_owner,
        defaults={
            'total_time_seconds': 0,
            'total_cost': 0,
            'session_count': 0
        }
    )
    aggregate.total_time_seconds = max(0, aggregate.total_time_seconds + time_delta)
    aggregate.total_cost = max(0, aggregate.total_cost + cost_delta)
    aggregate.session_count = max(0, aggregate.session_count + sessions_delta)
    aggregate.save(update_fields=['total_time_seconds', 'total_cost', 'session_count', 'last_updated'])


def update_project_aggregate(project, time_delta=0, cost_delta=0, sessions_delta=0):
    """Update project aggregate with deltas"""
    aggregate, created = ProjectAggregate.objects.get_or_create(
        project=project,
        defaults={
            'total_time_seconds': 0,
            'total_cost': 0,
            'session_count': 0
        }
    )
    aggregate.total_time_seconds = max(0, aggregate.total_time_seconds + time_delta)
    aggregate.total_cost = max(0, aggregate.total_cost + cost_delta)
    aggregate.session_count = max(0, aggregate.session_count + sessions_delta)
    aggregate.save(update_fields=['total_time_seconds', 'total_cost', 'session_count', 'last_updated'])


def update_customer_aggregate(customer, time_delta=0, cost_delta=0, sessions_delta=0):
    """Update customer aggregate with deltas"""
    aggregate, created = CustomerAggregate.objects.get_or_create(
        customer=customer,
        defaults={
            'total_time_seconds': 0,
            'total_cost': 0,
            'session_count': 0,
            'project_count': 0
        }
    )
    aggregate.total_time_seconds = max(0, aggregate.total_time_seconds + time_delta)
    aggregate.total_cost = max(0, aggregate.total_cost + cost_delta)
    aggregate.session_count = max(0, aggregate.session_count + sessions_delta)
    # Update project_count from actual projects
    aggregate.project_count = customer.projects.count()
    aggregate.save(update_fields=['total_time_seconds', 'total_cost', 'session_count', 'project_count', 'last_updated'])


def update_deliverable_aggregate(deliverable, time_delta=0, cost_delta=0, sessions_delta=0):
    """Update deliverable aggregate with deltas"""
    if not deliverable:
        return
    aggregate, created = DeliverableAggregate.objects.get_or_create(
        deliverable=deliverable,
        defaults={
            'total_time_seconds': 0,
            'total_cost': 0,
            'session_count': 0
        }
    )
    aggregate.total_time_seconds = max(0, aggregate.total_time_seconds + time_delta)
    aggregate.total_cost = max(0, aggregate.total_cost + cost_delta)
    aggregate.session_count = max(0, aggregate.session_count + sessions_delta)
    aggregate.save(update_fields=['total_time_seconds', 'total_cost', 'session_count', 'last_updated'])


def update_user_aggregate(user, workspace_owner, time_delta=0, cost_delta=0, sessions_delta=0):
    """Update user aggregate with deltas"""
    if not user:
        return
    aggregate, created = UserAggregate.objects.get_or_create(
        user=user,
        workspace_owner=workspace_owner,
        defaults={
            'total_time_seconds': 0,
            'total_cost': 0,
            'session_count': 0
        }
    )
    aggregate.total_time_seconds = max(0, aggregate.total_time_seconds + time_delta)
    aggregate.total_cost = max(0, aggregate.total_cost + cost_delta)
    aggregate.session_count = max(0, aggregate.session_count + sessions_delta)
    aggregate.save(update_fields=['total_time_seconds', 'total_cost', 'session_count', 'last_updated'])


def recalculate_session_aggregates(session, is_deletion=False):
    """
    Recalculate all aggregates affected by a session.
    This is used when:
    - Session is created
    - Session is edited (times, cost changed)
    - Session is deleted
    - Pause is added/edited/deleted (affects session duration)
    
    For edits, we need to calculate the delta (old vs new values).
    """
    # Only process completed sessions (with end_time)
    if not session.end_time and not is_deletion:
        return
    
    workspace_owner = get_workspace_owner(session.project_timer.project.customer.user)
    timer = session.project_timer.timer
    project = session.project_timer.project
    customer = project.customer
    deliverable = session.deliverable
    user = session.created_by
    
    # Calculate session values
    # Note: duration_seconds() already handles pauses correctly
    time_seconds = session.duration_seconds() if not is_deletion else 0
    cost = session.cost() if not is_deletion else 0
    sessions_count = 1 if not is_deletion else -1
    
    # Determine date for daily aggregate
    date = session.end_time.date() if session.end_time else timezone.now().date()
    
    # Update all affected aggregates
    update_workspace_aggregate(workspace_owner, time_seconds, cost, sessions_count)
    update_daily_aggregate(workspace_owner, date, time_seconds, cost, sessions_count)
    update_timer_aggregate(timer, workspace_owner, time_seconds, cost, sessions_count)
    update_project_aggregate(project, time_seconds, cost, sessions_count)
    update_customer_aggregate(customer, time_seconds, cost, sessions_count)
    
    if deliverable:
        update_deliverable_aggregate(deliverable, time_seconds, cost, sessions_count)
    
    if user:
        update_user_aggregate(user, workspace_owner, time_seconds, cost, sessions_count)


@receiver(pre_save, sender=TimerSession)
def store_old_session_values(sender, instance, **kwargs):
    """Store old session values before save to calculate delta"""
    if instance.pk:
        try:
            old_instance = TimerSession.objects.get(pk=instance.pk)
            _old_session_values[instance.pk] = {
                'end_time': old_instance.end_time,
                'duration_seconds': old_instance.duration_seconds() if old_instance.end_time else 0,
                'cost': old_instance.cost() if old_instance.end_time else 0,
            }
        except TimerSession.DoesNotExist:
            pass


@receiver(post_save, sender=TimerSession)
def update_aggregates_on_session_save(sender, instance, created, **kwargs):
    """
    Update aggregates when a session is saved (created or updated).
    
    For updates, we calculate the delta (old vs new values).
    For new sessions, we just add the values.
    """
    # Skip if session is not completed (no end_time)
    if not instance.end_time:
        # If session was completed before but now isn't, we need to subtract old values
        if instance.pk in _old_session_values:
            old_values = _old_session_values.pop(instance.pk)
            if old_values['end_time']:
                # Session was completed, now it's not - subtract old values
                workspace_owner = get_workspace_owner(instance.project_timer.project.customer.user)
                date = old_values['end_time'].date()
                
                with transaction.atomic():
                    update_workspace_aggregate(workspace_owner, -old_values['duration_seconds'], -old_values['cost'], -1)
                    update_daily_aggregate(workspace_owner, date, -old_values['duration_seconds'], -old_values['cost'], -1)
                    # Update other aggregates similarly...
        return
    
    workspace_owner = get_workspace_owner(instance.project_timer.project.customer.user)
    timer = instance.project_timer.timer
    project = instance.project_timer.project
    customer = project.customer
    deliverable = instance.deliverable
    user = instance.created_by
    
    # Calculate new values
    new_time = instance.duration_seconds()
    new_cost = instance.cost()
    date = instance.end_time.date()
    
    with transaction.atomic():
        if created:
            # New session - just add
            update_workspace_aggregate(workspace_owner, new_time, new_cost, 1)
            update_daily_aggregate(workspace_owner, date, new_time, new_cost, 1)
            update_timer_aggregate(timer, workspace_owner, new_time, new_cost, 1)
            update_project_aggregate(project, new_time, new_cost, 1)
            update_customer_aggregate(customer, new_time, new_cost, 1)
            if deliverable:
                update_deliverable_aggregate(deliverable, new_time, new_cost, 1)
            if user:
                update_user_aggregate(user, workspace_owner, new_time, new_cost, 1)
        else:
            # Updated session - calculate delta
            if instance.pk in _old_session_values:
                old_values = _old_session_values.pop(instance.pk)
                if old_values['end_time']:
                    # Session was completed before - calculate delta
                    time_delta = new_time - old_values['duration_seconds']
                    cost_delta = new_cost - old_values['cost']
                    old_date = old_values['end_time'].date()
                    
                    # Update workspace aggregate
                    update_workspace_aggregate(workspace_owner, time_delta, cost_delta, 0)
                    
                    # Update daily aggregates (old date and new date if different)
                    if old_date != date:
                        update_daily_aggregate(workspace_owner, old_date, -old_values['duration_seconds'], -old_values['cost'], -1)
                        update_daily_aggregate(workspace_owner, date, new_time, new_cost, 1)
                    else:
                        update_daily_aggregate(workspace_owner, date, time_delta, cost_delta, 0)
                    
                    update_timer_aggregate(timer, workspace_owner, time_delta, cost_delta, 0)
                    update_project_aggregate(project, time_delta, cost_delta, 0)
                    update_customer_aggregate(customer, time_delta, cost_delta, 0)
                    if deliverable:
                        update_deliverable_aggregate(deliverable, time_delta, cost_delta, 0)
                    if user:
                        update_user_aggregate(user, workspace_owner, time_delta, cost_delta, 0)
                else:
                    # Session was not completed before, now it is - just add
                    update_workspace_aggregate(workspace_owner, new_time, new_cost, 1)
                    update_daily_aggregate(workspace_owner, date, new_time, new_cost, 1)
                    update_timer_aggregate(timer, workspace_owner, new_time, new_cost, 1)
                    update_project_aggregate(project, new_time, new_cost, 1)
                    update_customer_aggregate(customer, new_time, new_cost, 1)
                    if deliverable:
                        update_deliverable_aggregate(deliverable, new_time, new_cost, 1)
                    if user:
                        update_user_aggregate(user, workspace_owner, new_time, new_cost, 1)
            else:
                # No old values stored - recalculate (fallback)
                recalculate_session_aggregates(instance, is_deletion=False)


@receiver(post_delete, sender=TimerSession)
def update_aggregates_on_session_delete(sender, instance, **kwargs):
    """Update aggregates when a session is deleted"""
    if not instance.end_time:
        return
    
    with transaction.atomic():
        # Subtract this session's values
        recalculate_session_aggregates(instance, is_deletion=True)


@receiver(post_save, sender=TimerPause)
def update_aggregates_on_pause_save(sender, instance, created, **kwargs):
    """
    Update aggregates when a pause is saved (created or edited).
    
    When a pause changes, the session's duration changes, which affects all aggregates.
    We need to recalculate the session's aggregates.
    """
    session = instance.session
    if not session.end_time:
        return
    
    with transaction.atomic():
        # Recalculate session aggregates (duration will change due to pause change)
        recalculate_session_aggregates(session, is_deletion=False)


@receiver(post_delete, sender=TimerPause)
def update_aggregates_on_pause_delete(sender, instance, **kwargs):
    """Update aggregates when a pause is deleted"""
    session = instance.session
    if not session.end_time:
        return
    
    with transaction.atomic():
        # Recalculate session aggregates (duration will change due to pause deletion)
        recalculate_session_aggregates(session, is_deletion=False)


@receiver(post_save, sender=Timer)
def update_workspace_timer_count(sender, instance, created, **kwargs):
    """Update workspace aggregate timer count when timer is created"""
    workspace_owner = get_workspace_owner(instance.user)
    aggregate = get_or_create_workspace_aggregate(workspace_owner)
    
    if created:
        aggregate.total_timers += 1
    aggregate.save(update_fields=['total_timers', 'last_updated'])


@receiver(post_delete, sender=Timer)
def update_workspace_timer_count_delete(sender, instance, **kwargs):
    """Update workspace aggregate timer count when timer is deleted"""
    workspace_owner = get_workspace_owner(instance.user)
    try:
        aggregate = WorkspaceAggregate.objects.get(owner=workspace_owner)
        aggregate.total_timers = max(0, aggregate.total_timers - 1)
        aggregate.save(update_fields=['total_timers', 'last_updated'])
    except WorkspaceAggregate.DoesNotExist:
        pass


# Signals for Customer, Project, Deliverable counts
@receiver(post_save, sender='customers.Customer')
def update_workspace_customer_count(sender, instance, created, **kwargs):
    """Update workspace aggregate customer count"""
    workspace_owner = get_workspace_owner(instance.user)
    aggregate = get_or_create_workspace_aggregate(workspace_owner)
    
    if created:
        aggregate.total_customers += 1
    aggregate.save(update_fields=['total_customers', 'last_updated'])


@receiver(post_delete, sender='customers.Customer')
def update_workspace_customer_count_delete(sender, instance, **kwargs):
    """Update workspace aggregate customer count when customer is deleted"""
    workspace_owner = get_workspace_owner(instance.user)
    try:
        aggregate = WorkspaceAggregate.objects.get(owner=workspace_owner)
        aggregate.total_customers = max(0, aggregate.total_customers - 1)
        aggregate.save(update_fields=['total_customers', 'last_updated'])
    except WorkspaceAggregate.DoesNotExist:
        pass


@receiver(pre_save, sender='projects.Project')
def store_old_project_status(sender, instance, **kwargs):
    """Store old project status for delta calculation"""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if not hasattr(instance, '_old_status'):
                instance._old_status = old_instance.status
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender='projects.Project')
def update_workspace_project_count(sender, instance, created, **kwargs):
    """Update workspace aggregate project counts and customer project count"""
    workspace_owner = get_workspace_owner(instance.customer.user)
    aggregate = get_or_create_workspace_aggregate(workspace_owner)
    
    if created:
        if instance.status == 'active':
            aggregate.active_projects += 1
        elif instance.status == 'completed':
            aggregate.completed_projects += 1
    else:
        # Project status might have changed - handle transition
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            # Status changed - update counts
            if old_status == 'active':
                aggregate.active_projects = max(0, aggregate.active_projects - 1)
            elif old_status == 'completed':
                aggregate.completed_projects = max(0, aggregate.completed_projects - 1)
            
            if instance.status == 'active':
                aggregate.active_projects += 1
            elif instance.status == 'completed':
                aggregate.completed_projects += 1
    
    aggregate.save(update_fields=['active_projects', 'completed_projects', 'last_updated'])
    
    # Update customer aggregate project count
    update_customer_aggregate(instance.customer, 0, 0, 0)  # Only updates project_count


@receiver(post_delete, sender='projects.Project')
def update_workspace_project_count_delete(sender, instance, **kwargs):
    """Update workspace aggregate project counts when project is deleted"""
    workspace_owner = get_workspace_owner(instance.customer.user)
    try:
        aggregate = WorkspaceAggregate.objects.get(owner=workspace_owner)
        if instance.status == 'active':
            aggregate.active_projects = max(0, aggregate.active_projects - 1)
        elif instance.status == 'completed':
            aggregate.completed_projects = max(0, aggregate.completed_projects - 1)
        aggregate.save(update_fields=['active_projects', 'completed_projects', 'last_updated'])
    except WorkspaceAggregate.DoesNotExist:
        pass


@receiver(post_save, sender='deliverables.Deliverable')
def update_workspace_deliverable_count(sender, instance, created, **kwargs):
    """Update workspace aggregate deliverable count"""
    workspace_owner = get_workspace_owner(instance.project.customer.user)
    aggregate = get_or_create_workspace_aggregate(workspace_owner)
    
    if created:
        aggregate.total_deliverables += 1
    aggregate.save(update_fields=['total_deliverables', 'last_updated'])


@receiver(post_delete, sender='deliverables.Deliverable')
def update_workspace_deliverable_count_delete(sender, instance, **kwargs):
    """Update workspace aggregate deliverable count when deliverable is deleted"""
    workspace_owner = get_workspace_owner(instance.project.customer.user)
    try:
        aggregate = WorkspaceAggregate.objects.get(owner=workspace_owner)
        aggregate.total_deliverables = max(0, aggregate.total_deliverables - 1)
        aggregate.save(update_fields=['total_deliverables', 'last_updated'])
    except WorkspaceAggregate.DoesNotExist:
        pass
