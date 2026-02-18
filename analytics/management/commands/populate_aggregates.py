"""
Management command to populate analytics aggregates from existing data.

This command should be run:
1. After initial migration (to backfill existing sessions)
2. If aggregates get out of sync
3. After bulk data imports

Usage:
    python manage.py populate_aggregates              # Populate all workspaces
    python manage.py populate_aggregates --workspace-owner username  # Specific workspace
    python manage.py populate_aggregates --dry-run   # Show what would be done
    python manage.py populate_aggregates --force     # Recalculate even if aggregates exist
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from collections import defaultdict

from timer.models import TimerSession, Timer, get_workspace_owner, get_workspace_users
from customers.models import Customer
from projects.models import Project
from deliverables.models import Deliverable
from analytics.models import (
    WorkspaceAggregate, DailyAggregate, TimerAggregate,
    ProjectAggregate, CustomerAggregate, DeliverableAggregate, UserAggregate
)


class Command(BaseCommand):
    help = 'Populate analytics aggregates from existing data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace-owner',
            type=str,
            default=None,
            help='Username of workspace owner to populate (default: all workspaces)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recalculate aggregates even if they already exist'
        )

    def populate_workspace_aggregate(self, workspace_owner, dry_run=False, force=False):
        """Populate workspace aggregate for a specific workspace owner"""
        workspace_users = get_workspace_users(workspace_owner)
        
        # Get or create workspace aggregate
        if not dry_run:
            aggregate, created = WorkspaceAggregate.objects.get_or_create(owner=workspace_owner)
            if not force and not created and aggregate.total_sessions > 0:
                self.stdout.write(f'  ⏭️  Workspace aggregate already exists for {workspace_owner.username}, skipping (use --force to recalculate)')
                return
        else:
            aggregate = None
            created = True
        
        # Get all completed sessions for this workspace
        completed_sessions = TimerSession.objects.filter(
            project_timer__project__customer__user__in=workspace_users,
            end_time__isnull=False
        ).select_related(
            'project_timer', 'project_timer__timer', 
            'project_timer__project', 'project_timer__project__customer'
        )
        
        # Calculate totals using database aggregations (efficient!)
        session_stats = completed_sessions.aggregate(
            total_sessions=Count('id'),
            total_time=Sum('id')  # We'll calculate this differently
        )
        
        # Calculate time and cost (need to iterate but use database aggregations where possible)
        total_time_seconds = 0
        total_cost = 0
        session_count = completed_sessions.count()
        
        # Use iterator for memory efficiency with large datasets
        for session in completed_sessions.iterator(chunk_size=1000):
            total_time_seconds += session.duration_seconds()
            total_cost += session.cost()
        
        # Count entities
        total_timers = Timer.objects.filter(user__in=workspace_users).count()
        total_customers = Customer.objects.filter(user__in=workspace_users).count()
        total_deliverables = Deliverable.objects.filter(
            project__customer__user__in=workspace_users
        ).count()
        
        projects = Project.objects.filter(customer__user__in=workspace_users)
        active_projects = projects.filter(status='active').count()
        completed_projects = projects.filter(status='completed').count()
        
        if dry_run:
            self.stdout.write(f'  📊 Would create/update workspace aggregate for {workspace_owner.username}:')
            self.stdout.write(f'     • Sessions: {session_count}')
            self.stdout.write(f'     • Time: {total_time_seconds / 3600:.2f} hours')
            self.stdout.write(f'     • Cost: ${total_cost:.2f}')
            self.stdout.write(f'     • Timers: {total_timers}')
            self.stdout.write(f'     • Customers: {total_customers}')
            self.stdout.write(f'     • Deliverables: {total_deliverables}')
            self.stdout.write(f'     • Projects: {active_projects} active, {completed_projects} completed')
            return
        
        # Update workspace aggregate
        aggregate.total_time_seconds = total_time_seconds
        aggregate.total_sessions = session_count
        aggregate.total_cost = total_cost
        aggregate.total_timers = total_timers
        aggregate.total_customers = total_customers
        aggregate.total_deliverables = total_deliverables
        aggregate.active_projects = active_projects
        aggregate.completed_projects = completed_projects
        aggregate.save()
        
        self.stdout.write(f'  ✅ Workspace aggregate: {session_count} sessions, {total_time_seconds / 3600:.2f}h, ${total_cost:.2f}')

    def populate_daily_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Populate daily aggregates for last 30 days"""
        workspace_users = get_workspace_users(workspace_owner)
        
        # Get completed sessions in last 30 days
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        completed_sessions = TimerSession.objects.filter(
            project_timer__project__customer__user__in=workspace_users,
            end_time__isnull=False,
            end_time__gte=thirty_days_ago
        ).select_related('project_timer', 'project_timer__timer')
        
        # Group by date
        daily_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        
        for session in completed_sessions.iterator(chunk_size=1000):
            date = session.end_time.date()
            daily_stats[date]['time'] += session.duration_seconds()
            daily_stats[date]['cost'] += session.cost()
            daily_stats[date]['count'] += 1
        
        if dry_run:
            self.stdout.write(f'  📅 Would create/update {len(daily_stats)} daily aggregates')
            return
        
        # Create/update daily aggregates
        created_count = 0
        updated_count = 0
        for date, stats in daily_stats.items():
            aggregate, created = DailyAggregate.objects.get_or_create(
                workspace_owner=workspace_owner,
                date=date,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count']
                }
            )
            if not created:
                if force:
                    aggregate.total_time_seconds = stats['time']
                    aggregate.total_cost = stats['cost']
                    aggregate.session_count = stats['count']
                    aggregate.save()
                    updated_count += 1
                else:
                    continue
            else:
                created_count += 1
        
        self.stdout.write(f'  ✅ Daily aggregates: {created_count} created, {updated_count} updated')

    def populate_timer_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Populate timer aggregates"""
        workspace_users = get_workspace_users(workspace_owner)
        timers = Timer.objects.filter(user__in=workspace_users)
        
        completed_sessions = TimerSession.objects.filter(
            project_timer__project__customer__user__in=workspace_users,
            end_time__isnull=False
        ).select_related('project_timer', 'project_timer__timer')
        
        # Group by timer
        timer_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        
        for session in completed_sessions.iterator(chunk_size=1000):
            timer = session.project_timer.timer
            timer_stats[timer]['time'] += session.duration_seconds()
            timer_stats[timer]['cost'] += session.cost()
            timer_stats[timer]['count'] += 1
        
        if dry_run:
            self.stdout.write(f'  ⏱️  Would create/update {len(timer_stats)} timer aggregates')
            return
        
        created_count = 0
        updated_count = 0
        for timer, stats in timer_stats.items():
            aggregate, created = TimerAggregate.objects.get_or_create(
                timer=timer,
                workspace_owner=workspace_owner,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count']
                }
            )
            if not created:
                if force:
                    aggregate.total_time_seconds = stats['time']
                    aggregate.total_cost = stats['cost']
                    aggregate.session_count = stats['count']
                    aggregate.save()
                    updated_count += 1
            else:
                created_count += 1
        
        self.stdout.write(f'  ✅ Timer aggregates: {created_count} created, {updated_count} updated')

    def populate_project_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Populate project aggregates"""
        workspace_users = get_workspace_users(workspace_owner)
        projects = Project.objects.filter(customer__user__in=workspace_users)
        
        completed_sessions = TimerSession.objects.filter(
            project_timer__project__customer__user__in=workspace_users,
            end_time__isnull=False
        ).select_related('project_timer', 'project_timer__project')
        
        # Group by project
        project_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        
        for session in completed_sessions.iterator(chunk_size=1000):
            project = session.project_timer.project
            project_stats[project]['time'] += session.duration_seconds()
            project_stats[project]['cost'] += session.cost()
            project_stats[project]['count'] += 1
        
        if dry_run:
            self.stdout.write(f'  📁 Would create/update {len(project_stats)} project aggregates')
            return
        
        created_count = 0
        updated_count = 0
        for project, stats in project_stats.items():
            aggregate, created = ProjectAggregate.objects.get_or_create(
                project=project,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count']
                }
            )
            if not created:
                if force:
                    aggregate.total_time_seconds = stats['time']
                    aggregate.total_cost = stats['cost']
                    aggregate.session_count = stats['count']
                    aggregate.save()
                    updated_count += 1
            else:
                created_count += 1
        
        self.stdout.write(f'  ✅ Project aggregates: {created_count} created, {updated_count} updated')

    def populate_customer_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Populate customer aggregates"""
        workspace_users = get_workspace_users(workspace_owner)
        customers = Customer.objects.filter(user__in=workspace_users)
        
        completed_sessions = TimerSession.objects.filter(
            project_timer__project__customer__user__in=workspace_users,
            end_time__isnull=False
        ).select_related('project_timer', 'project_timer__project', 'project_timer__project__customer')
        
        # Group by customer
        customer_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        
        for session in completed_sessions.iterator(chunk_size=1000):
            customer = session.project_timer.project.customer
            customer_stats[customer]['time'] += session.duration_seconds()
            customer_stats[customer]['cost'] += session.cost()
            customer_stats[customer]['count'] += 1
        
        if dry_run:
            self.stdout.write(f'  👤 Would create/update {len(customer_stats)} customer aggregates')
            return
        
        created_count = 0
        updated_count = 0
        for customer, stats in customer_stats.items():
            aggregate, created = CustomerAggregate.objects.get_or_create(
                customer=customer,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count'],
                    'project_count': customer.projects.count()
                }
            )
            if not created:
                if force:
                    aggregate.total_time_seconds = stats['time']
                    aggregate.total_cost = stats['cost']
                    aggregate.session_count = stats['count']
                    aggregate.project_count = customer.projects.count()
                    aggregate.save()
                    updated_count += 1
            else:
                created_count += 1
        
        self.stdout.write(f'  ✅ Customer aggregates: {created_count} created, {updated_count} updated')

    def populate_deliverable_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Populate deliverable aggregates"""
        workspace_users = get_workspace_users(workspace_owner)
        
        completed_sessions = TimerSession.objects.filter(
            project_timer__project__customer__user__in=workspace_users,
            end_time__isnull=False,
            deliverable__isnull=False
        ).select_related('deliverable')
        
        # Group by deliverable
        deliverable_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        
        for session in completed_sessions.iterator(chunk_size=1000):
            if session.deliverable:
                deliverable_stats[session.deliverable]['time'] += session.duration_seconds()
                deliverable_stats[session.deliverable]['cost'] += session.cost()
                deliverable_stats[session.deliverable]['count'] += 1
        
        if dry_run:
            self.stdout.write(f'  📦 Would create/update {len(deliverable_stats)} deliverable aggregates')
            return
        
        created_count = 0
        updated_count = 0
        for deliverable, stats in deliverable_stats.items():
            aggregate, created = DeliverableAggregate.objects.get_or_create(
                deliverable=deliverable,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count']
                }
            )
            if not created:
                if force:
                    aggregate.total_time_seconds = stats['time']
                    aggregate.total_cost = stats['cost']
                    aggregate.session_count = stats['count']
                    aggregate.save()
                    updated_count += 1
            else:
                created_count += 1
        
        self.stdout.write(f'  ✅ Deliverable aggregates: {created_count} created, {updated_count} updated')

    def populate_user_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Populate user aggregates (team member stats)"""
        workspace_users = get_workspace_users(workspace_owner)
        
        # Only populate if there are multiple users in workspace
        if workspace_users.count() <= 1:
            if dry_run:
                self.stdout.write(f'  👥 Skipping user aggregates (single user workspace)')
            return
        
        completed_sessions = TimerSession.objects.filter(
            project_timer__project__customer__user__in=workspace_users,
            end_time__isnull=False,
            created_by__isnull=False
        ).select_related('created_by')
        
        # Group by user
        user_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        
        for session in completed_sessions.iterator(chunk_size=1000):
            if session.created_by:
                user_stats[session.created_by]['time'] += session.duration_seconds()
                user_stats[session.created_by]['cost'] += session.cost()
                user_stats[session.created_by]['count'] += 1
        
        if dry_run:
            self.stdout.write(f'  👥 Would create/update {len(user_stats)} user aggregates')
            return
        
        created_count = 0
        updated_count = 0
        for user, stats in user_stats.items():
            aggregate, created = UserAggregate.objects.get_or_create(
                user=user,
                workspace_owner=workspace_owner,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count']
                }
            )
            if not created:
                if force:
                    aggregate.total_time_seconds = stats['time']
                    aggregate.total_cost = stats['cost']
                    aggregate.session_count = stats['count']
                    aggregate.save()
                    updated_count += 1
            else:
                created_count += 1
        
        self.stdout.write(f'  ✅ User aggregates: {created_count} created, {updated_count} updated')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        workspace_owner_username = options.get('workspace_owner')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))
        
        # Get workspace owners to process
        if workspace_owner_username:
            try:
                workspace_owner = User.objects.get(username=workspace_owner_username)
                workspace_owners = [workspace_owner]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{workspace_owner_username}" not found.'))
                return
        else:
            # Get all unique workspace owners
            # A workspace owner is a user who is not a team member
            from timer.models import TeamMember
            team_member_ids = TeamMember.objects.values_list('member_id', flat=True)
            workspace_owners = User.objects.exclude(id__in=team_member_ids)
        
        self.stdout.write(f'\n📊 Populating aggregates for {len(workspace_owners)} workspace(s)...\n')
        
        for workspace_owner in workspace_owners:
            self.stdout.write(f'\n🏢 Workspace: {workspace_owner.username}')
            
            with transaction.atomic():
                self.populate_workspace_aggregate(workspace_owner, dry_run, force)
                self.populate_daily_aggregates(workspace_owner, dry_run, force)
                self.populate_timer_aggregates(workspace_owner, dry_run, force)
                self.populate_project_aggregates(workspace_owner, dry_run, force)
                self.populate_customer_aggregates(workspace_owner, dry_run, force)
                self.populate_deliverable_aggregates(workspace_owner, dry_run, force)
                self.populate_user_aggregates(workspace_owner, dry_run, force)
            
            if not dry_run:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Completed workspace: {workspace_owner.username}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Population complete!'))
        if dry_run:
            self.stdout.write(self.style.WARNING('\n💡 Run without --dry-run to apply changes'))
