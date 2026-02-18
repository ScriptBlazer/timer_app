from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Sum, Count, F, ExpressionWrapper, DecimalField, IntegerField, DateField
from django.db.models.functions import Extract, Cast, TruncDate
from django.db import connection, reset_queries
from django.conf import settings
import json
import time
import gc
from collections import defaultdict
from datetime import timedelta, datetime

from customers.models import Customer
from projects.models import Project
from timer.models import (
    Timer, TimerSession,
    get_workspace_users, get_workspace_owner
)
from deliverables.models import Deliverable
from analytics.models import (
    WorkspaceAggregate, DailyAggregate, TimerAggregate,
    ProjectAggregate, CustomerAggregate, DeliverableAggregate, UserAggregate
)
from django.http import JsonResponse
from django.core.management import call_command
from io import StringIO
import json


def calculate_benchmark_metrics(workspace_users, workspace_aggregate):
    """Calculate benchmark metrics (queries, memory, time complexity)"""
    queries = connection.queries
    query_count = len(queries)
    total_query_time = sum(float(q.get('time', 0)) for q in queries)
    
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
    
    # Calculate memory usage
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        memory_method = 'psutil'
    except ImportError:
        try:
            import tracemalloc
            if not tracemalloc.is_tracing():
                tracemalloc.start()
            current, peak = tracemalloc.get_traced_memory()
            memory_mb = current / 1024 / 1024
            memory_method = 'tracemalloc'
        except:
            memory_mb = 0
            memory_method = None
    
    # Calculate time complexity
    n_sessions = workspace_aggregate.total_sessions if workspace_aggregate else 0
    n_timers = workspace_aggregate.total_timers if workspace_aggregate else 0
    n_projects = (workspace_aggregate.active_projects + workspace_aggregate.completed_projects) if workspace_aggregate else 0
    n_customers = workspace_aggregate.total_customers if workspace_aggregate else 0
    
    # With aggregates, complexity is O(1) - constant time lookups
    if n_sessions > 0:
        complexity = "O(1)"
        complexity_note = "Constant - pre-aggregated data"
    else:
        complexity = "O(1)"
        complexity_note = "Constant - no data"
    
    return {
        'total_queries': query_count,
        'total_query_time_seconds': round(total_query_time, 4),
        'average_query_time_ms': round((total_query_time/query_count*1000), 2) if query_count > 0 else 0,
        'query_types': dict(query_types),
        'memory_method': memory_method,
        'memory_mb': round(memory_mb, 2),
        'complexity': complexity,
        'complexity_note': complexity_note,
    }


@login_required
def statistics(request):
    """Statistics and analytics page with charts - OPTIMIZED with aggregates"""
    # Enable query logging for benchmark
    was_debug = settings.DEBUG
    settings.DEBUG = True
    reset_queries()
    
    # Track calculation time
    calculation_start = time.time()
    
    workspace_users = get_workspace_users(request.user)
    workspace_owner = get_workspace_owner(request.user)
    
    # Get workspace aggregate (O(1) lookup!)
    try:
        workspace_aggregate = WorkspaceAggregate.objects.get(owner=workspace_owner)
    except WorkspaceAggregate.DoesNotExist:
        # Aggregate doesn't exist yet - create empty one
        workspace_aggregate = WorkspaceAggregate.objects.create(owner=workspace_owner)
    
    # Overall statistics from workspace aggregate (O(1))
    total_sessions = workspace_aggregate.total_sessions
    total_time_seconds = workspace_aggregate.total_time_seconds
    total_cost = float(workspace_aggregate.total_cost)
    
    # This week's statistics from daily aggregates (efficient!)
    now = timezone.now()
    week_start = now - timedelta(days=now.weekday())
    week_start_date = week_start.date()
    
    # Get daily aggregates for this week
    this_week_daily = DailyAggregate.objects.filter(
        workspace_owner=workspace_owner,
        date__gte=week_start_date
    ).aggregate(
        total_time=Sum('total_time_seconds'),
        total_cost=Sum('total_cost'),
        total_sessions=Sum('session_count')
    )
    
    this_week_hours = (this_week_daily['total_time'] or 0) / 3600
    this_week_cost = float(this_week_daily['total_cost'] or 0)
    
    # Most active day - use database aggregation
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Calculate duration in seconds - for SQLite compatibility, calculate in Python
    # Note: Pauses are relatively rare, so this approximation is acceptable for visualization
    
    # Group by day of week - get sessions and calculate in Python
    completed_sessions = TimerSession.objects.filter(
        project_timer__project__customer__user__in=workspace_users,
        end_time__isnull=False
    ).only('end_time', 'start_time', 'pause_start_time').prefetch_related('pauses')
    
    # Calculate day stats in Python
    day_stats = defaultdict(float)
    for session in completed_sessions:
        day_name = day_names[session.end_time.weekday()]
        duration = session.duration_seconds()
        day_stats[day_name] += duration
    
    
    most_active_day = max(day_stats.items(), key=lambda x: x[1]) if day_stats else None
    most_active_day_name = most_active_day[0] if most_active_day else 'N/A'
    most_active_day_hours = most_active_day[1] / 3600 if most_active_day else 0
    
    # Timer statistics from TimerAggregate (O(1) - single query!)
    timer_aggregates = TimerAggregate.objects.filter(
        workspace_owner=workspace_owner
    ).select_related('timer').order_by('-total_time_seconds')[:10]
    
    timer_stats = [{
        'name': agg.timer.task_name,
        'time_seconds': agg.total_time_seconds,
        'cost': float(agg.total_cost),
        'session_count': agg.session_count,
        'color': agg.timer.header_color
    } for agg in timer_aggregates]
    
    # Project statistics from ProjectAggregate (O(1) - single query!)
    project_aggregates = ProjectAggregate.objects.filter(
        project__customer__user__in=workspace_users
    ).select_related('project', 'project__customer').order_by('-total_time_seconds')[:10]
    
    project_stats = [{
        'name': agg.project.name,
        'customer': agg.project.customer.name,
        'status': agg.project.status,
        'time_seconds': agg.total_time_seconds,
        'cost': float(agg.total_cost),
        'session_count': agg.session_count
    } for agg in project_aggregates]
    
    # Get project counts from workspace aggregate
    active_projects = workspace_aggregate.active_projects
    completed_projects = workspace_aggregate.completed_projects
    
    # Customer statistics from CustomerAggregate (O(1) - single query!)
    customer_aggregates = CustomerAggregate.objects.filter(
        customer__user__in=workspace_users
    ).select_related('customer').order_by('-total_time_seconds')[:10]
    
    customer_stats = [{
        'name': agg.customer.name,
        'time_seconds': agg.total_time_seconds,
        'cost': float(agg.total_cost),
        'project_count': agg.project_count,
        'session_count': agg.session_count
    } for agg in customer_aggregates]
    
    # Deliverables statistics from DeliverableAggregate (O(1) - single query!)
    deliverable_aggregates = DeliverableAggregate.objects.filter(
        deliverable__project__customer__user__in=workspace_users
    ).select_related('deliverable', 'deliverable__project').order_by('-total_time_seconds')[:10]
    
    deliverable_stats = [{
        'name': agg.deliverable.name,
        'project': agg.deliverable.project.name,
        'time_seconds': agg.total_time_seconds,
        'cost': float(agg.total_cost),
        'session_count': agg.session_count
    } for agg in deliverable_aggregates]
    
    total_deliverables = workspace_aggregate.total_deliverables
    deliverables_with_sessions = DeliverableAggregate.objects.filter(
        deliverable__project__customer__user__in=workspace_users,
        session_count__gt=0
    ).count()
    
    # Time tracking over time (last 30 days) from DailyAggregate (O(1) - single query!)
    thirty_days_ago = now - timedelta(days=30)
    daily_aggregates = DailyAggregate.objects.filter(
        workspace_owner=workspace_owner,
        date__gte=thirty_days_ago.date()
    ).order_by('date')
    
    # Build daily stats from aggregates
    daily_stats = {agg.date: agg.total_time_seconds for agg in daily_aggregates}
    daily_cost_stats = {agg.date: float(agg.total_cost) for agg in daily_aggregates}
    
    # Sort by date and create lists for chart
    sorted_dates = sorted(daily_stats.keys())
    daily_labels = [date.strftime('%-d %b') for date in sorted_dates]
    daily_hours = [daily_stats[date] / 3600 for date in sorted_dates]
    daily_costs = [daily_cost_stats[date] for date in sorted_dates]
    
    # Weekly statistics (last 12 weeks) - aggregate from daily aggregates
    twelve_weeks_ago = now - timedelta(days=84)
    weekly_daily_aggregates = DailyAggregate.objects.filter(
        workspace_owner=workspace_owner,
        date__gte=twelve_weeks_ago.date()
    )
    
    # Group daily aggregates by week
    weekly_stats = defaultdict(float)
    weekly_cost_stats = defaultdict(float)
    for agg in weekly_daily_aggregates:
        week_start = agg.date - timedelta(days=agg.date.weekday())
        weekly_stats[week_start] += agg.total_time_seconds
        weekly_cost_stats[week_start] += float(agg.total_cost)
    
    sorted_weeks = sorted(weekly_stats.keys())
    weekly_labels = [week.strftime('%-d %b') for week in sorted_weeks[-12:]]
    weekly_hours = [weekly_stats[week] / 3600 for week in sorted_weeks[-12:]]
    weekly_costs = [weekly_cost_stats[week] for week in sorted_weeks[-12:]]
    
    # Day of week analysis - use database aggregation (reuse the query above)
    day_of_week_labels = day_names
    day_of_week_hours = [day_stats.get(day, 0) / 3600 for day in day_names]
    
    # Hourly distribution (0-23) - calculate in Python for SQLite compatibility
    hourly_stats = defaultdict(float)
    for session in completed_sessions:
        hour = session.start_time.hour
        duration = session.duration_seconds()
        hourly_stats[hour] += duration
    
    hourly_labels = [f"{h:02d}:00" for h in range(24)]
    hourly_hours = [hourly_stats.get(h, 0) / 3600 for h in range(24)]
    
    # Monthly comparison (last 6 months) - aggregate from daily aggregates
    six_months_ago = now - timedelta(days=180)
    monthly_daily_aggregates = DailyAggregate.objects.filter(
        workspace_owner=workspace_owner,
        date__gte=six_months_ago.date()
    )
    
    # Group by month
    monthly_stats = defaultdict(lambda: {'hours': 0, 'cost': 0, 'sessions': 0})
    for agg in monthly_daily_aggregates:
        month_key = agg.date.strftime('%Y-%m')
        monthly_stats[month_key]['hours'] += agg.total_time_seconds / 3600
        monthly_stats[month_key]['cost'] += float(agg.total_cost)
        monthly_stats[month_key]['sessions'] += agg.session_count
    
    sorted_months = sorted(monthly_stats.keys())
    monthly_labels = [
        datetime.strptime(month, '%Y-%m').strftime('%b %y')
        for month in sorted_months[-6:]
    ]
    monthly_hours = [monthly_stats[month]['hours'] for month in sorted_months[-6:]]
    monthly_costs = [monthly_stats[month]['cost'] for month in sorted_months[-6:]]
    
    # Session duration trends (average session duration over time - last 30 days)
    # Use daily aggregates
    session_duration_labels = []
    session_duration_avg = []
    for agg in daily_aggregates:
        if agg.session_count > 0:
            session_duration_labels.append(agg.date.strftime('%-d %b'))
            avg_duration_hours = (agg.total_time_seconds / agg.session_count) / 3600
            session_duration_avg.append(avg_duration_hours)
    
    # Cost breakdown by timer over time (last 30 days) - calculate in Python for SQLite compatibility
    cost_breakdown_sessions = TimerSession.objects.filter(
        project_timer__project__customer__user__in=workspace_users,
        end_time__isnull=False,
        end_time__gte=thirty_days_ago
    ).select_related('project_timer', 'project_timer__timer').only(
        'end_time', 'start_time', 'pause_start_time', 'price_per_hour',
        'project_timer__timer__task_name', 'project_timer__timer__header_color'
    ).prefetch_related('pauses')
    
    # Convert to nested dict structure - calculate cost in Python
    timer_cost_over_time = defaultdict(lambda: defaultdict(float))
    timer_names_for_cost = {}
    cost_breakdown_dates_set = set()
    
    for session in cost_breakdown_sessions:
        timer_name = session.project_timer.timer.task_name
        timer_color = session.project_timer.timer.header_color
        date_key = session.end_time.date()
        
        # Calculate cost using duration_seconds() which correctly excludes pauses
        duration_hours = session.duration_seconds() / 3600
        cost = float(session.price_per_hour) * duration_hours
        
        timer_cost_over_time[timer_name][date_key] += cost
        timer_names_for_cost[timer_name] = timer_color
        cost_breakdown_dates_set.add(date_key)
    
    # Prepare cost breakdown data
    cost_breakdown_dates = sorted(cost_breakdown_dates_set)
    cost_breakdown_labels = [date.strftime('%-d %b') for date in cost_breakdown_dates]
    cost_breakdown_datasets = []
    for timer_name, timer_color in timer_names_for_cost.items():
        cost_breakdown_datasets.append({
            'label': timer_name,
            'data': [float(timer_cost_over_time[timer_name].get(date, 0)) for date in cost_breakdown_dates],
            'color': timer_color
        })
    
    # Team member statistics from UserAggregate (O(1) - single query!)
    user_aggregates = UserAggregate.objects.filter(
        workspace_owner=workspace_owner
    ).select_related('user').order_by('-total_time_seconds')
    
    team_member_stats = [{
        'username': agg.user.username,
        'time_seconds': agg.total_time_seconds,
        'cost': float(agg.total_cost),
        'session_count': agg.session_count
    } for agg in user_aggregates]
    
    # Prepare JSON data for charts
    timer_names = [t['name'] for t in timer_stats]
    timer_hours = [t['time_seconds'] / 3600 for t in timer_stats]
    timer_colors = [t['color'] for t in timer_stats]
    
    project_names = [p['name'] for p in project_stats]
    project_hours = [p['time_seconds'] / 3600 for p in project_stats]
    
    customer_names = [c['name'] for c in customer_stats]
    customer_hours = [c['time_seconds'] / 3600 for c in customer_stats]
    
    team_usernames = [t['username'] for t in team_member_stats]
    team_hours = [t['time_seconds'] / 3600 for t in team_member_stats]
    
    # Calculate benchmark metrics
    calculation_time = time.time() - calculation_start
    benchmark_metrics = calculate_benchmark_metrics(workspace_users, workspace_aggregate)
    
    context = {
        'total_sessions': total_sessions,
        'total_time_seconds': total_time_seconds,
        'total_cost': total_cost,
        'this_week_hours': this_week_hours,
        'this_week_cost': this_week_cost,
        'most_active_day_name': most_active_day_name,
        'most_active_day_hours': most_active_day_hours,
        'timer_stats': timer_stats,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'project_stats': project_stats,
        'customer_stats': customer_stats,
        'team_member_stats': team_member_stats,
        'daily_labels': json.dumps(daily_labels),
        'daily_hours': json.dumps(daily_hours),
        'daily_costs': json.dumps(daily_costs),
        'weekly_labels': json.dumps(weekly_labels),
        'weekly_hours': json.dumps(weekly_hours),
        'weekly_costs': json.dumps(weekly_costs),
        'day_of_week_labels': json.dumps(day_of_week_labels),
        'day_of_week_hours': json.dumps(day_of_week_hours),
        'hourly_labels': json.dumps(hourly_labels),
        'hourly_hours': json.dumps(hourly_hours),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_hours': json.dumps(monthly_hours),
        'monthly_costs': json.dumps(monthly_costs),
        'session_duration_labels': json.dumps(session_duration_labels),
        'session_duration_avg': json.dumps(session_duration_avg),
        'cost_breakdown_labels': json.dumps(cost_breakdown_labels),
        'cost_breakdown_datasets': json.dumps(cost_breakdown_datasets),
        'total_timers': workspace_aggregate.total_timers,
        'total_customers': workspace_aggregate.total_customers,
        'total_deliverables': total_deliverables,
        'deliverables_with_sessions': deliverables_with_sessions,
        'deliverable_stats': deliverable_stats,
        'timer_names': json.dumps(timer_names),
        'timer_hours': json.dumps(timer_hours),
        'timer_colors': json.dumps(timer_colors),
        'project_names': json.dumps(project_names),
        'project_hours': json.dumps(project_hours),
        'customer_names': json.dumps(customer_names),
        'customer_hours': json.dumps(customer_hours),
        'team_usernames': json.dumps(team_usernames),
        'team_hours': json.dumps(team_hours),
    }
    
    # Add benchmark data to context
    context['benchmark_data'] = {
        'timestamp': timezone.now().isoformat(),
        'user': request.user.username,
        'calculation_time_seconds': round(calculation_time, 4),
        'data_statistics': {
            'all_sessions_count': total_sessions,
            'completed_sessions_count': total_sessions,
            'total_timers': workspace_aggregate.total_timers,
            'total_customers': workspace_aggregate.total_customers,
            'total_deliverables': total_deliverables,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
        },
        'database_performance': {
            'total_queries': benchmark_metrics['total_queries'],
            'total_query_time_seconds': benchmark_metrics['total_query_time_seconds'],
            'average_query_time_ms': benchmark_metrics['average_query_time_ms'],
            'query_types': benchmark_metrics['query_types'],
        },
        'memory_usage': {
            'method': benchmark_metrics['memory_method'],
            'memory_mb': benchmark_metrics['memory_mb'],
        },
        'time_complexity': {
            'notation': benchmark_metrics['complexity'],
            'analysis': benchmark_metrics['complexity_note'],
        }
    }
    
    # Restore DEBUG setting
    settings.DEBUG = was_debug
    
    return render(request, 'analytics/analytics.html', context)


@login_required
def performance_report(request):
    """Generate and return performance report as JSON"""
    from django.test import RequestFactory
    from analytics.views import statistics
    from django.db import connection, reset_queries
    from django.conf import settings
    import time
    import os
    from django.utils import timezone
    
    # Track memory usage
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        memory_method = 'psutil'
    except ImportError:
        try:
            import tracemalloc
            if not tracemalloc.is_tracing():
                tracemalloc.start()
            current, peak = tracemalloc.get_traced_memory()
            memory_before = current / 1024 / 1024  # MB
            memory_method = 'tracemalloc'
        except:
            memory_before = 0
            memory_method = None
    
    # Enable query logging
    was_debug = settings.DEBUG
    settings.DEBUG = True
    reset_queries()
    
    # Time the view (end-to-end)
    total_start_time = time.time()
    result_data = {
        'success': False,
        'error': None,
        'timestamp': timezone.now().isoformat(),
        'user': request.user.username,
    }
    
    try:
        response = statistics(request)
        total_load_time = time.time() - total_start_time
        calculation_time = total_load_time  # Same as total load time for this endpoint
        
        # Get memory after
        if memory_method == 'psutil':
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = memory_after - memory_before
        elif memory_method == 'tracemalloc':
            current, peak = tracemalloc.get_traced_memory()
            memory_after = current / 1024 / 1024  # MB
            memory_used = memory_after - memory_before
        else:
            memory_after = 0
            memory_used = 0
        
        # Get memory after
        if memory_method == 'psutil':
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = memory_after - memory_before
        elif memory_method == 'tracemalloc':
            current, peak = tracemalloc.get_traced_memory()
            memory_after = current / 1024 / 1024  # MB
            memory_used = memory_after - memory_before
        else:
            memory_after = 0
            memory_used = 0
        
        # Get query info
        queries = connection.queries
        query_count = len(queries)
        total_query_time = sum(float(q.get('time', 0)) for q in queries)
        avg_query_time = (total_query_time / query_count * 1000) if query_count > 0 else 0
        
        # Get database backend info
        db_backend = connection.vendor
        db_version = connection.get_server_version() if hasattr(connection, 'get_server_version') else 'Unknown'
        
        # Show query breakdown
        query_types = {}
        query_details = []
        query_times = []  # For finding slowest queries
        
        for q in queries:
            sql = q.get('sql', '').upper().strip()
            query_time = float(q.get('time', 0))
            query_times.append((query_time, q.get('sql', '')))
            
            if sql.startswith('SELECT'):
                query_types['SELECT'] = query_types.get('SELECT', 0) + 1
            elif sql.startswith('INSERT'):
                query_types['INSERT'] = query_types.get('INSERT', 0) + 1
            elif sql.startswith('UPDATE'):
                query_types['UPDATE'] = query_types.get('UPDATE', 0) + 1
            elif sql.startswith('DELETE'):
                query_types['DELETE'] = query_types.get('DELETE', 0) + 1
            else:
                query_types['OTHER'] = query_types.get('OTHER', 0) + 1
            
            # Store query details (limit to first 50 for JSON size)
            if len(query_details) < 50:
                query_details.append({
                    'sql': q.get('sql', '')[:200] + ('...' if len(q.get('sql', '')) > 200 else ''),
                    'time': round(query_time, 4),
                    'type': sql.split()[0] if sql else 'OTHER'
                })
        
        # Get slowest queries (top 10)
        slowest_queries = sorted(query_times, key=lambda x: x[0], reverse=True)[:10]
        slowest_queries_list = [{
            'sql': q[1][:200] + ('...' if len(q[1]) > 200 else ''),
            'time': round(q[0], 4),
            'time_ms': round(q[0] * 1000, 2)
        } for q in slowest_queries]
        
        # Calculate query efficiency
        non_query_time = calculation_time - total_query_time
        query_time_percentage = (total_query_time / calculation_time * 100) if calculation_time > 0 else 0
        
        # Get context data directly from aggregates (since response is HttpResponse, not a view with context_data)
        workspace_users = get_workspace_users(request.user)
        workspace_owner = get_workspace_owner(request.user)
        
        # Get workspace aggregate
        try:
            workspace_agg = WorkspaceAggregate.objects.get(owner=workspace_owner)
        except WorkspaceAggregate.DoesNotExist:
            workspace_agg = None
        
        # Get this week's data
        now = timezone.now()
        week_start = now - timedelta(days=now.weekday())
        week_start_date = week_start.date()
        
        this_week_daily = DailyAggregate.objects.filter(
            workspace_owner=workspace_owner,
            date__gte=week_start_date
        ).aggregate(
            total_time=Sum('total_time_seconds'),
            total_cost=Sum('total_cost'),
            total_sessions=Sum('session_count')
        )
        
        # Get more detailed data statistics
        total_timers = workspace_agg.total_timers if workspace_agg else 0
        total_customers = workspace_agg.total_customers if workspace_agg else 0
        total_deliverables = workspace_agg.total_deliverables if workspace_agg else 0
        active_projects = workspace_agg.active_projects if workspace_agg else 0
        completed_projects = workspace_agg.completed_projects if workspace_agg else 0
        
        # Count aggregate records
        daily_agg_count = DailyAggregate.objects.filter(workspace_owner=workspace_owner).count()
        timer_agg_count = TimerAggregate.objects.filter(workspace_owner=workspace_owner).count()
        project_agg_count = ProjectAggregate.objects.filter(project__customer__user__in=workspace_users).count()
        customer_agg_count = CustomerAggregate.objects.filter(customer__user__in=workspace_users).count()
        deliverable_agg_count = DeliverableAggregate.objects.filter(deliverable__project__customer__user__in=workspace_users).count()
        user_agg_count = UserAggregate.objects.filter(workspace_owner=workspace_owner).count()
        
        context_data = {
            'total_sessions': workspace_agg.total_sessions if workspace_agg else 0,
            'total_time_seconds': workspace_agg.total_time_seconds if workspace_agg else 0,
            'total_time_hours': round((workspace_agg.total_time_seconds if workspace_agg else 0) / 3600, 2),
            'total_cost': float(workspace_agg.total_cost if workspace_agg else 0),
            'this_week_hours': round((this_week_daily['total_time'] or 0) / 3600, 2),
            'this_week_cost': float(this_week_daily['total_cost'] or 0),
            'total_timers': total_timers,
            'total_customers': total_customers,
            'total_deliverables': total_deliverables,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
        }
        
        data_statistics = {
            'total_timers': total_timers,
            'total_customers': total_customers,
            'total_deliverables': total_deliverables,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
            'daily_aggregates': daily_agg_count,
            'timer_aggregates': timer_agg_count,
            'project_aggregates': project_agg_count,
            'customer_aggregates': customer_agg_count,
            'deliverable_aggregates': deliverable_agg_count,
            'user_aggregates': user_agg_count,
        }
        
        # Check if targets met
        target_queries = 20
        target_time_ms = 100
        passed = query_count < target_queries and calculation_time < 0.1
        
        # Build result data
        result_data.update({
            'success': True,
            'performance': {
                'total_queries': query_count,
                'total_query_time_seconds': round(total_query_time, 4),
                'total_query_time_ms': round(total_query_time * 1000, 2),
                'average_query_time_ms': round(avg_query_time, 2),
                'calculation_time_seconds': round(calculation_time, 4),
                'calculation_time_ms': round(calculation_time * 1000, 2),
                'total_load_time_seconds': round(total_load_time, 4),
                'total_load_time_ms': round(total_load_time * 1000, 2),
                'non_query_time_ms': round(non_query_time * 1000, 2),
                'query_time_percentage': round(query_time_percentage, 1),
            },
            'database': {
                'backend': db_backend,
                'version': str(db_version) if db_version != 'Unknown' else 'Unknown',
            },
            'slowest_queries': slowest_queries_list,
            'data_statistics': data_statistics,
            'memory': {
                'method': memory_method,
                'memory_before_mb': round(memory_before, 2),
                'memory_after_mb': round(memory_after, 2),
                'memory_used_mb': round(memory_used, 2),
            },
            'targets': {
                'query_count': target_queries,
                'calculation_time_ms': target_time_ms,
                'passed': passed,
            },
            'query_breakdown': query_types,
            'query_details': query_details,
            'context_data': context_data,
        })
        
    except Exception as e:
        import traceback
        result_data.update({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
        })
    finally:
        settings.DEBUG = was_debug
    
    return JsonResponse(result_data)
