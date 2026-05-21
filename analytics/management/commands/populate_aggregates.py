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
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from collections import defaultdict

from timer.models import TimerSession, Timer, get_workspace_users
from customers.models import Customer
from projects.models import Project
from deliverables.models import Deliverable
from analytics.models import (
    WorkspaceAggregate, DailyAggregate, TimerAggregate,
    ProjectAggregate, CustomerAggregate, DeliverableAggregate, UserAggregate
)


ZERO_SESSION_STATS = {'time': 0, 'cost': 0, 'count': 0}


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

    def _completed_sessions(self, workspace_users):
        return TimerSession.objects.filter(
            project_timer__project__customer__user__in=workspace_users,
            end_time__isnull=False,
        )

    def _session_totals(self, completed_sessions):
        """Iterate completed sessions and return total time, cost, and count."""
        total_time_seconds = 0
        total_cost = Decimal('0')
        session_count = 0
        for session in completed_sessions.iterator(chunk_size=1000):
            total_time_seconds += session.duration_seconds()
            total_cost += Decimal(str(session.cost()))
            session_count += 1
        return total_time_seconds, total_cost, session_count

    def populate_workspace_aggregate(self, workspace_owner, dry_run=False, force=False):
        """Populate workspace aggregate for a specific workspace owner."""
        workspace_users = get_workspace_users(workspace_owner)

        if not dry_run:
            aggregate, created = WorkspaceAggregate.objects.get_or_create(owner=workspace_owner)
            if not force and not created and aggregate.total_sessions > 0:
                self.stdout.write(
                    f'  ⏭️  Workspace aggregate already exists for {workspace_owner.username}, '
                    f'skipping (use --force to recalculate)'
                )
                return

        completed_sessions = self._completed_sessions(workspace_users).select_related(
            'project_timer',
            'project_timer__timer',
            'project_timer__project',
            'project_timer__project__customer',
        )
        total_time_seconds, total_cost, session_count = self._session_totals(completed_sessions)

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
            self.stdout.write(f'     • Cost: ${float(total_cost):.2f}')
            self.stdout.write(f'     • Timers: {total_timers}')
            self.stdout.write(f'     • Customers: {total_customers}')
            self.stdout.write(f'     • Deliverables: {total_deliverables}')
            self.stdout.write(f'     • Projects: {active_projects} active, {completed_projects} completed')
            return

        aggregate.total_time_seconds = total_time_seconds
        aggregate.total_sessions = session_count
        aggregate.total_cost = total_cost
        aggregate.total_timers = total_timers
        aggregate.total_customers = total_customers
        aggregate.total_deliverables = total_deliverables
        aggregate.active_projects = active_projects
        aggregate.completed_projects = completed_projects
        aggregate.save()

        self.stdout.write(
            f'  ✅ Workspace aggregate: {session_count} sessions, '
            f'{total_time_seconds / 3600:.2f}h, ${float(total_cost):.2f}'
        )

    def populate_daily_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Populate daily aggregates for last 30 days."""
        workspace_users = get_workspace_users(workspace_owner)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        min_date = timezone.localdate(thirty_days_ago)

        completed_sessions = self._completed_sessions(workspace_users).filter(
            end_time__gte=thirty_days_ago,
        )

        daily_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        for session in completed_sessions.iterator(chunk_size=1000):
            date = timezone.localdate(session.end_time)
            daily_stats[date]['time'] += session.duration_seconds()
            daily_stats[date]['cost'] += session.cost()
            daily_stats[date]['count'] += 1

        if dry_run:
            existing = DailyAggregate.objects.filter(
                workspace_owner=workspace_owner,
                date__gte=min_date,
            ).count()
            self.stdout.write(
                f'  📅 Would update daily aggregates: {len(daily_stats)} day(s) with sessions; '
                f'{existing} existing row(s) in last 30 days'
                + (' (--force resets stale days to 0)' if force else '')
            )
            return

        created_count = 0
        updated_count = 0
        for date, stats in daily_stats.items():
            aggregate, created = DailyAggregate.objects.update_or_create(
                workspace_owner=workspace_owner,
                date=date,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count'],
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        if force:
            zeroed_count = 0
            for aggregate in DailyAggregate.objects.filter(
                workspace_owner=workspace_owner,
                date__gte=min_date,
            ):
                if aggregate.date not in daily_stats:
                    aggregate.total_time_seconds = 0
                    aggregate.total_cost = 0
                    aggregate.session_count = 0
                    aggregate.save(
                        update_fields=[
                            'total_time_seconds',
                            'total_cost',
                            'session_count',
                            'last_updated',
                        ]
                    )
                    zeroed_count += 1
            if zeroed_count:
                self.stdout.write(f'  ✅ Daily aggregates: {created_count} created, {updated_count} updated, {zeroed_count} zeroed (stale)')
                return

        self.stdout.write(f'  ✅ Daily aggregates: {created_count} created, {updated_count} updated')

    def populate_timer_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Ensure every workspace timer has a TimerAggregate (zero totals if no sessions)."""
        workspace_users = get_workspace_users(workspace_owner)
        timers = Timer.objects.filter(user__in=workspace_users)
        timer_count = timers.count()

        timer_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        completed_sessions = self._completed_sessions(workspace_users).select_related(
            'project_timer',
            'project_timer__timer',
        )
        for session in completed_sessions.iterator(chunk_size=1000):
            timer_id = session.project_timer.timer_id
            timer_stats[timer_id]['time'] += session.duration_seconds()
            timer_stats[timer_id]['cost'] += session.cost()
            timer_stats[timer_id]['count'] += 1

        with_sessions = len(timer_stats)
        if dry_run:
            self.stdout.write(
                f'  ⏱️  Would ensure {timer_count} timer aggregate(s) '
                f'({with_sessions} with sessions, {timer_count - with_sessions} zero)'
                + (' [force: recalculate all]' if force else ' [create missing only]')
            )
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0
        for timer in timers.iterator():
            stats = timer_stats.get(timer.pk, ZERO_SESSION_STATS)
            aggregate, created = TimerAggregate.objects.get_or_create(
                timer=timer,
                workspace_owner=workspace_owner,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count'],
                },
            )
            if created:
                created_count += 1
            elif force:
                aggregate.total_time_seconds = stats['time']
                aggregate.total_cost = stats['cost']
                aggregate.session_count = stats['count']
                aggregate.save(
                    update_fields=[
                        'total_time_seconds',
                        'total_cost',
                        'session_count',
                        'last_updated',
                    ]
                )
                updated_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            f'  ✅ Timer aggregates: {created_count} created, {updated_count} updated'
            + (f', {skipped_count} unchanged' if skipped_count else '')
        )

    def populate_project_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Ensure every workspace project has a ProjectAggregate (zero totals if no sessions)."""
        workspace_users = get_workspace_users(workspace_owner)
        projects = Project.objects.filter(customer__user__in=workspace_users)
        project_count = projects.count()

        project_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        completed_sessions = self._completed_sessions(workspace_users).select_related(
            'project_timer',
            'project_timer__project',
        )
        for session in completed_sessions.iterator(chunk_size=1000):
            project_id = session.project_timer.project_id
            project_stats[project_id]['time'] += session.duration_seconds()
            project_stats[project_id]['cost'] += session.cost()
            project_stats[project_id]['count'] += 1

        with_sessions = len(project_stats)
        if dry_run:
            self.stdout.write(
                f'  📁 Would ensure {project_count} project aggregate(s) '
                f'({with_sessions} with sessions, {project_count - with_sessions} zero)'
                + (' [force: recalculate all]' if force else ' [create missing only]')
            )
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0
        for project in projects.iterator():
            stats = project_stats.get(project.pk, ZERO_SESSION_STATS)
            aggregate, created = ProjectAggregate.objects.get_or_create(
                project=project,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count'],
                },
            )
            if created:
                created_count += 1
            elif force:
                aggregate.total_time_seconds = stats['time']
                aggregate.total_cost = stats['cost']
                aggregate.session_count = stats['count']
                aggregate.save(
                    update_fields=[
                        'total_time_seconds',
                        'total_cost',
                        'session_count',
                        'last_updated',
                    ]
                )
                updated_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            f'  ✅ Project aggregates: {created_count} created, {updated_count} updated'
            + (f', {skipped_count} unchanged' if skipped_count else '')
        )

    def populate_customer_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Ensure every workspace customer has a CustomerAggregate (zero totals if no sessions)."""
        workspace_users = get_workspace_users(workspace_owner)
        customers = Customer.objects.filter(user__in=workspace_users)
        customer_count = customers.count()

        customer_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        completed_sessions = self._completed_sessions(workspace_users).select_related(
            'project_timer',
            'project_timer__project',
            'project_timer__project__customer',
        )
        for session in completed_sessions.iterator(chunk_size=1000):
            customer_id = session.project_timer.project.customer_id
            customer_stats[customer_id]['time'] += session.duration_seconds()
            customer_stats[customer_id]['cost'] += session.cost()
            customer_stats[customer_id]['count'] += 1

        with_sessions = len(customer_stats)
        if dry_run:
            self.stdout.write(
                f'  👤 Would ensure {customer_count} customer aggregate(s) '
                f'({with_sessions} with sessions, {customer_count - with_sessions} zero); '
                f'project_count set for all'
                + (' [force: recalculate all]' if force else ' [create missing only]')
            )
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0
        for customer in customers.iterator():
            stats = customer_stats.get(customer.pk, ZERO_SESSION_STATS)
            project_count = customer.projects.count()
            aggregate, created = CustomerAggregate.objects.get_or_create(
                customer=customer,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count'],
                    'project_count': project_count,
                },
            )
            if created:
                created_count += 1
            elif force:
                aggregate.total_time_seconds = stats['time']
                aggregate.total_cost = stats['cost']
                aggregate.session_count = stats['count']
                aggregate.project_count = project_count
                aggregate.save(
                    update_fields=[
                        'total_time_seconds',
                        'total_cost',
                        'session_count',
                        'project_count',
                        'last_updated',
                    ]
                )
                updated_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            f'  ✅ Customer aggregates: {created_count} created, {updated_count} updated'
            + (f', {skipped_count} unchanged' if skipped_count else '')
        )

    def populate_deliverable_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Ensure every workspace deliverable has a DeliverableAggregate (zero totals if no sessions)."""
        workspace_users = get_workspace_users(workspace_owner)
        deliverables = Deliverable.objects.filter(project__customer__user__in=workspace_users)
        deliverable_count = deliverables.count()

        deliverable_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        completed_sessions = self._completed_sessions(workspace_users).filter(
            deliverable__isnull=False,
        ).select_related('deliverable')
        for session in completed_sessions.iterator(chunk_size=1000):
            deliverable_id = session.deliverable_id
            deliverable_stats[deliverable_id]['time'] += session.duration_seconds()
            deliverable_stats[deliverable_id]['cost'] += session.cost()
            deliverable_stats[deliverable_id]['count'] += 1

        with_sessions = len(deliverable_stats)
        if dry_run:
            self.stdout.write(
                f'  📦 Would ensure {deliverable_count} deliverable aggregate(s) '
                f'({with_sessions} with sessions, {deliverable_count - with_sessions} zero)'
                + (' [force: recalculate all]' if force else ' [create missing only]')
            )
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0
        for deliverable in deliverables.iterator():
            stats = deliverable_stats.get(deliverable.pk, ZERO_SESSION_STATS)
            aggregate, created = DeliverableAggregate.objects.get_or_create(
                deliverable=deliverable,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count'],
                },
            )
            if created:
                created_count += 1
            elif force:
                aggregate.total_time_seconds = stats['time']
                aggregate.total_cost = stats['cost']
                aggregate.session_count = stats['count']
                aggregate.save(
                    update_fields=[
                        'total_time_seconds',
                        'total_cost',
                        'session_count',
                        'last_updated',
                    ]
                )
                updated_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            f'  ✅ Deliverable aggregates: {created_count} created, {updated_count} updated'
            + (f', {skipped_count} unchanged' if skipped_count else '')
        )

    def populate_user_aggregates(self, workspace_owner, dry_run=False, force=False):
        """Populate user aggregates for each workspace user (team member stats)."""
        workspace_users = get_workspace_users(workspace_owner)
        user_list = list(workspace_users)

        if len(user_list) <= 1:
            if dry_run:
                self.stdout.write('  👥 Skipping user aggregates (single user workspace)')
            return

        user_stats = defaultdict(lambda: {'time': 0, 'cost': 0, 'count': 0})
        completed_sessions = self._completed_sessions(workspace_users).filter(
            created_by__isnull=False,
        ).select_related('created_by')
        for session in completed_sessions.iterator(chunk_size=1000):
            user_stats[session.created_by_id]['time'] += session.duration_seconds()
            user_stats[session.created_by_id]['cost'] += session.cost()
            user_stats[session.created_by_id]['count'] += 1

        with_sessions = len(user_stats)
        if dry_run:
            self.stdout.write(
                f'  👥 Would ensure {len(user_list)} user aggregate(s) '
                f'({with_sessions} with sessions, {len(user_list) - with_sessions} zero)'
                + (' [force: recalculate all]' if force else ' [create missing only]')
            )
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0
        for user in user_list:
            stats = user_stats.get(user.pk, ZERO_SESSION_STATS)
            aggregate, created = UserAggregate.objects.get_or_create(
                user=user,
                workspace_owner=workspace_owner,
                defaults={
                    'total_time_seconds': stats['time'],
                    'total_cost': stats['cost'],
                    'session_count': stats['count'],
                },
            )
            if created:
                created_count += 1
            elif force:
                aggregate.total_time_seconds = stats['time']
                aggregate.total_cost = stats['cost']
                aggregate.session_count = stats['count']
                aggregate.save(
                    update_fields=[
                        'total_time_seconds',
                        'total_cost',
                        'session_count',
                        'last_updated',
                    ]
                )
                updated_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            f'  ✅ User aggregates: {created_count} created, {updated_count} updated'
            + (f', {skipped_count} unchanged' if skipped_count else '')
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        workspace_owner_username = options.get('workspace_owner')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))
        if force and not dry_run:
            self.stdout.write(self.style.WARNING('⚡ FORCE MODE - All existing aggregates will be recalculated\n'))

        if workspace_owner_username:
            try:
                workspace_owner = User.objects.get(username=workspace_owner_username)
                workspace_owners = [workspace_owner]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{workspace_owner_username}" not found.'))
                return
        else:
            from timer.models import TeamMember
            team_member_ids = TeamMember.objects.values_list('member_id', flat=True)
            workspace_owners = User.objects.exclude(id__in=team_member_ids)

        self.stdout.write(f'\n📊 Populating aggregates for {len(workspace_owners)} workspace(s)...\n')

        for workspace_owner in workspace_owners:
            self.stdout.write(f'\n🏢 Workspace: {workspace_owner.username}')

            if dry_run:
                self.populate_workspace_aggregate(workspace_owner, dry_run=True, force=force)
                self.populate_daily_aggregates(workspace_owner, dry_run=True, force=force)
                self.populate_timer_aggregates(workspace_owner, dry_run=True, force=force)
                self.populate_project_aggregates(workspace_owner, dry_run=True, force=force)
                self.populate_customer_aggregates(workspace_owner, dry_run=True, force=force)
                self.populate_deliverable_aggregates(workspace_owner, dry_run=True, force=force)
                self.populate_user_aggregates(workspace_owner, dry_run=True, force=force)
                continue

            with transaction.atomic():
                self.populate_workspace_aggregate(workspace_owner, dry_run=False, force=force)
                self.populate_daily_aggregates(workspace_owner, dry_run=False, force=force)
                self.populate_timer_aggregates(workspace_owner, dry_run=False, force=force)
                self.populate_project_aggregates(workspace_owner, dry_run=False, force=force)
                self.populate_customer_aggregates(workspace_owner, dry_run=False, force=force)
                self.populate_deliverable_aggregates(workspace_owner, dry_run=False, force=force)
                self.populate_user_aggregates(workspace_owner, dry_run=False, force=force)

            self.stdout.write(self.style.SUCCESS(f'  ✅ Completed workspace: {workspace_owner.username}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Population complete!'))
        if dry_run:
            self.stdout.write(self.style.WARNING('\n💡 Run without --dry-run to apply changes'))
            if not force:
                self.stdout.write(
                    self.style.WARNING(
                        '💡 Use --force to recalculate existing rows and reset stale totals to zero'
                    )
                )
