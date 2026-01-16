"""
Management command to benchmark analytics view performance.
Measures database queries, memory usage, and calculation time.

Usage:
    python manage.py benchmark_analytics
    python manage.py benchmark_analytics --username myuser
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection, reset_queries
from django.utils import timezone
from django.conf import settings
import sys
import gc
import time
from datetime import timedelta
from collections import defaultdict
import json
from pathlib import Path

from customers.models import Customer
from projects.models import Project
from timer.models import (
    Timer, TimerSession,
    get_workspace_users
)
from deliverables.models import Deliverable


class Command(BaseCommand):
    help = 'Benchmark analytics view performance (queries and memory)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Username to use for benchmarking (default: first user found)'
        )

    def get_memory_usage(self):
        """Get current memory usage in MB"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            try:
                import tracemalloc
                if not tracemalloc.is_tracing():
                    tracemalloc.start()
                current, peak = tracemalloc.get_traced_memory()
                return current / 1024 / 1024  # Convert to MB
            except:
                return 0

    def run_analytics_calculations(self, user):
        """Replicate the analytics view calculations"""
        workspace_users = get_workspace_users(user)
        
        # Get all completed sessions for the workspace
        completed_sessions = TimerSession.objects.filter(
            project_timer__project__customer__user__in=workspace_users,
            end_time__isnull=False
        ).select_related('project_timer', 'project_timer__timer', 'project_timer__project', 'project_timer__project__customer')
        
        # Overall statistics
        total_sessions = completed_sessions.count()
        total_time_seconds = sum(session.duration_seconds() for session in completed_sessions)
        total_cost = sum(session.cost() for session in completed_sessions)
        
        # This week's statistics
        now = timezone.now()
        week_start = now - timedelta(days=now.weekday())
        this_week_sessions = completed_sessions.filter(end_time__gte=week_start)
        this_week_hours = sum(s.duration_seconds() for s in this_week_sessions) / 3600
        this_week_cost = sum(s.cost() for s in this_week_sessions)
        
        # Most active day
        day_stats = defaultdict(float)
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for session in completed_sessions:
            day_name = day_names[session.end_time.weekday()]
            day_stats[day_name] += session.duration_seconds()
        
        most_active_day = max(day_stats.items(), key=lambda x: x[1]) if day_stats else None
        
        # Timer statistics
        timers = Timer.objects.filter(user__in=workspace_users)
        timer_stats = []
        for timer in timers:
            timer_sessions = completed_sessions.filter(project_timer__timer=timer)
            timer_time = sum(s.duration_seconds() for s in timer_sessions)
            timer_cost = sum(s.cost() for s in timer_sessions)
            timer_stats.append({
                'name': timer.task_name,
                'time_seconds': timer_time,
                'cost': timer_cost,
                'session_count': timer_sessions.count(),
            })
        timer_stats.sort(key=lambda x: x['time_seconds'], reverse=True)
        
        # Project statistics
        projects = Project.objects.filter(customer__user__in=workspace_users)
        active_projects = projects.filter(status='active').count()
        completed_projects = projects.filter(status='completed').count()
        
        # Deliverables statistics
        deliverables = Deliverable.objects.filter(project__customer__user__in=workspace_users)
        total_deliverables = deliverables.count()
        
        deliverable_stats = []
        for deliverable in deliverables:
            deliverable_sessions = completed_sessions.filter(deliverable=deliverable)
            if deliverable_sessions.exists():
                deliverable_time = sum(s.duration_seconds() for s in deliverable_sessions)
                deliverable_cost = sum(s.cost() for s in deliverable_sessions)
                deliverable_stats.append({
                    'name': deliverable.name,
                    'project': deliverable.project.name,
                    'time_seconds': deliverable_time,
                    'cost': deliverable_cost,
                    'session_count': deliverable_sessions.count()
                })
        deliverable_stats.sort(key=lambda x: x['time_seconds'], reverse=True)
        
        project_stats = []
        for project in projects:
            project_sessions = completed_sessions.filter(project_timer__project=project)
            project_time = sum(s.duration_seconds() for s in project_sessions)
            project_cost = sum(s.cost() for s in project_sessions)
            project_stats.append({
                'name': project.name,
                'customer': project.customer.name,
                'status': project.status,
                'time_seconds': project_time,
                'cost': project_cost,
                'session_count': project_sessions.count()
            })
        project_stats.sort(key=lambda x: x['time_seconds'], reverse=True)
        
        # Customer statistics
        customers = Customer.objects.filter(user__in=workspace_users)
        customer_stats = []
        for customer in customers:
            customer_projects = customer.projects.all()
            customer_sessions = completed_sessions.filter(project_timer__project__customer=customer)
            customer_time = sum(s.duration_seconds() for s in customer_sessions)
            customer_cost = sum(s.cost() for s in customer_sessions)
            customer_stats.append({
                'name': customer.name,
                'time_seconds': customer_time,
                'cost': customer_cost,
                'project_count': customer_projects.count(),
                'session_count': customer_sessions.count()
            })
        customer_stats.sort(key=lambda x: x['time_seconds'], reverse=True)
        
        # Time tracking over time (last 30 days)
        thirty_days_ago = now - timedelta(days=30)
        daily_stats = defaultdict(float)
        daily_cost_stats = defaultdict(float)
        
        for session in completed_sessions.filter(end_time__gte=thirty_days_ago):
            date_key = session.end_time.date()
            daily_stats[date_key] += session.duration_seconds()
            daily_cost_stats[date_key] += session.cost()
        
        # Weekly statistics (last 12 weeks)
        weekly_stats = defaultdict(float)
        weekly_cost_stats = defaultdict(float)
        for session in completed_sessions.filter(end_time__gte=now - timedelta(days=84)):
            week_start = session.end_time.date() - timedelta(days=session.end_time.weekday())
            weekly_stats[week_start] += session.duration_seconds()
            weekly_cost_stats[week_start] += session.cost()
        
        # Day of week analysis
        day_of_week_stats = defaultdict(float)
        for session in completed_sessions:
            day_name = day_names[session.end_time.weekday()]
            day_of_week_stats[day_name] += session.duration_seconds()
        
        # Hourly distribution (0-23)
        hourly_stats = defaultdict(float)
        for session in completed_sessions:
            hour = session.start_time.hour
            hourly_stats[hour] += session.duration_seconds()
        
        # Monthly comparison (last 6 months)
        monthly_stats = defaultdict(lambda: {'hours': 0, 'cost': 0, 'sessions': 0})
        for session in completed_sessions.filter(end_time__gte=now - timedelta(days=180)):
            month_key = session.end_time.strftime('%Y-%m')
            monthly_stats[month_key]['hours'] += session.duration_seconds() / 3600
            monthly_stats[month_key]['cost'] += session.cost()
            monthly_stats[month_key]['sessions'] += 1
        
        # Session duration trends
        session_duration_stats = defaultdict(lambda: {'total_duration': 0, 'count': 0})
        for session in completed_sessions.filter(end_time__gte=thirty_days_ago):
            date_key = session.end_time.date()
            session_duration_stats[date_key]['total_duration'] += session.duration_seconds()
            session_duration_stats[date_key]['count'] += 1
        
        # Cost breakdown by timer over time
        timer_cost_over_time = defaultdict(lambda: defaultdict(float))
        for session in completed_sessions.filter(end_time__gte=thirty_days_ago):
            timer_name = session.project_timer.timer.task_name
            date_key = session.end_time.date()
            timer_cost_over_time[timer_name][date_key] += session.cost()
        
        # Team member statistics
        team_member_stats = []
        if len(workspace_users) > 1:
            for user in workspace_users:
                user_sessions = completed_sessions.filter(created_by=user)
                user_time = sum(s.duration_seconds() for s in user_sessions)
                user_cost = sum(s.cost() for s in user_sessions)
                team_member_stats.append({
                    'username': user.username,
                    'time_seconds': user_time,
                    'cost': user_cost,
                    'session_count': user_sessions.count()
                })
            team_member_stats.sort(key=lambda x: x['time_seconds'], reverse=True)
        
        return {
            'total_sessions': total_sessions,
            'all_sessions_count': completed_sessions.count(),
            'total_timers': timers.count(),
            'total_customers': customers.count(),
            'total_deliverables': total_deliverables,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
        }

    def calculate_time_complexity(self, n_sessions, n_timers, n_projects, n_customers):
        """Estimate Big O complexity"""
        # Linear operations: O(n) where n is number of sessions
        linear_ops = n_sessions
        
        # Nested loops in worst case: O(n * m) where m is entities
        nested_ops = n_sessions * (n_timers + n_projects + n_customers)
        
        if nested_ops > linear_ops * 10:
            return "O(n*m)", "Quadratic - nested iterations detected"
        elif n_sessions > 1000:
            return "O(n)", "Linear but large dataset"
        else:
            return "O(n)", "Linear - efficient"

    def handle(self, *args, **options):
        # Get user
        username = options.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{username}" not found.'))
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('No users found in database.'))
                return
        
        self.stdout.write(self.style.SUCCESS(f'Benchmarking analytics for user: {user.username}'))
        
        # Enable query logging
        settings.DEBUG = True
        reset_queries()
        
        # Force garbage collection before measuring
        gc.collect()
        
        # Measure initial memory
        initial_memory = self.get_memory_usage()
        
        # Start timer
        start_time = time.time()
        
        # Run calculations
        try:
            result = self.run_analytics_calculations(user)
            
            # End timer
            calculation_time = time.time() - start_time
            
            # Get query count and details
            queries = connection.queries
            query_count = len(queries)
            
            # Measure final memory
            final_memory = self.get_memory_usage()
            memory_used = final_memory - initial_memory
            
            # Calculate total query time
            total_query_time = sum(float(q.get('time', 0)) for q in queries)
            
            # Calculate complexity
            complexity, complexity_note = self.calculate_time_complexity(
                result['all_sessions_count'],
                result['total_timers'],
                result['active_projects'] + result['completed_projects'],
                result['total_customers']
            )
            
            # Group queries by type
            query_types = defaultdict(int)
            for query in queries:
                sql = query.get('sql', '').upper().strip()
                if sql.startswith('SELECT'):
                    query_types['SELECT'] += 1
                elif sql.startswith('INSERT'):
                    query_types['INSERT'] += 1
                elif sql.startswith('UPDATE'):
                    query_types['UPDATE'] += 1
                elif sql.startswith('DELETE'):
                    query_types['DELETE'] += 1
                else:
                    query_types['OTHER'] += 1
            
            # Save results to JSON file
            benchmark_data = {
                'timestamp': timezone.now().isoformat(),
                'user': user.username,
                'calculation_time_seconds': round(calculation_time, 4),
                'data_statistics': {
                    'all_sessions_count': result['all_sessions_count'],
                    'completed_sessions_count': result['all_sessions_count'],
                    'total_timers': result['total_timers'],
                    'total_customers': result['total_customers'],
                    'total_deliverables': result['total_deliverables'],
                    'active_projects': result['active_projects'],
                    'completed_projects': result['completed_projects'],
                },
                'database_performance': {
                    'total_queries': query_count,
                    'total_query_time_seconds': round(total_query_time, 4),
                    'average_query_time_ms': round((total_query_time/query_count*1000), 2) if query_count > 0 else 0,
                    'query_types': dict(query_types),
                },
                'memory_usage': {
                    'method': 'psutil' if self.get_memory_usage() > 0 else 'tracemalloc',
                    'initial_memory_mb': round(initial_memory, 2),
                    'final_memory_mb': round(final_memory, 2),
                    'memory_used_mb': round(memory_used, 2),
                },
                'time_complexity': {
                    'notation': complexity,
                    'analysis': complexity_note,
                }
            }
            
            # Save to analytics app directory
            current_file = Path(__file__).resolve()
            analytics_dir = current_file.parent.parent.parent  # analytics/
            benchmark_file = analytics_dir / 'benchmark_results.json'
            
            with open(benchmark_file, 'w') as f:
                json.dump(benchmark_data, f, indent=2, default=str)
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Benchmark completed!'))
            self.stdout.write(f'📊 Results saved to: {benchmark_file}')
            self.stdout.write(f'⏱️  Calculation time: {calculation_time:.3f}s')
            self.stdout.write(f'🗄️  Database queries: {query_count}')
            self.stdout.write(f'💾 Memory used: {memory_used:.2f} MB')
            self.stdout.write(f'📈 Time complexity: {complexity}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error during benchmarking: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
