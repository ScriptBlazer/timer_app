from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
import json
from collections import defaultdict
from datetime import timedelta, datetime

from customers.models import Customer
from projects.models import Project
from timer.models import (
    Timer, TimerSession,
    get_workspace_users
)
from deliverables.models import Deliverable


@login_required
def statistics(request):
    """Statistics and analytics page with charts"""
    workspace_users = get_workspace_users(request.user)
    
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
    most_active_day_name = most_active_day[0] if most_active_day else 'N/A'
    most_active_day_hours = most_active_day[1] / 3600 if most_active_day else 0
    
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
            'color': timer.header_color  # Include the timer's assigned color
        })
    timer_stats.sort(key=lambda x: x['time_seconds'], reverse=True)
    
    # Project statistics
    projects = Project.objects.filter(customer__user__in=workspace_users)
    active_projects = projects.filter(status='active').count()
    completed_projects = projects.filter(status='completed').count()
    
    # Deliverables statistics
    deliverables = Deliverable.objects.filter(project__customer__user__in=workspace_users)
    total_deliverables = deliverables.count()
    deliverables_with_sessions = deliverables.filter(sessions__end_time__isnull=False).distinct().count()
    
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
    
    # Sort by date and create lists for chart
    sorted_dates = sorted(daily_stats.keys())
    # Labels: day and short month name (e.g. '5 Aug')
    daily_labels = [date.strftime('%-d %b') for date in sorted_dates]
    daily_hours = [daily_stats[date] / 3600 for date in sorted_dates]
    daily_costs = [daily_cost_stats[date] for date in sorted_dates]
    
    # Weekly statistics (last 12 weeks)
    weekly_stats = defaultdict(float)
    weekly_cost_stats = defaultdict(float)
    for session in completed_sessions.filter(end_time__gte=now - timedelta(days=84)):
        week_start = session.end_time.date() - timedelta(days=session.end_time.weekday())
        weekly_stats[week_start] += session.duration_seconds()
        weekly_cost_stats[week_start] += session.cost()
    
    sorted_weeks = sorted(weekly_stats.keys())
    # Labels: week start day and short month (e.g. '5 Aug')
    weekly_labels = [week.strftime('%-d %b') for week in sorted_weeks[-12:]]
    weekly_hours = [weekly_stats[week] / 3600 for week in sorted_weeks[-12:]]
    weekly_costs = [weekly_cost_stats[week] for week in sorted_weeks[-12:]]
    
    # Day of week analysis
    day_of_week_stats = defaultdict(float)
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for session in completed_sessions:
        day_name = day_names[session.end_time.weekday()]
        day_of_week_stats[day_name] += session.duration_seconds()
    
    day_of_week_labels = day_names
    day_of_week_hours = [day_of_week_stats[day] / 3600 for day in day_names]
    
    # Hourly distribution (0-23)
    hourly_stats = defaultdict(float)
    for session in completed_sessions:
        hour = session.start_time.hour
        hourly_stats[hour] += session.duration_seconds()
    
    hourly_labels = [f"{h:02d}:00" for h in range(24)]
    hourly_hours = [hourly_stats[h] / 3600 for h in range(24)]
    
    # Monthly comparison (last 6 months)
    monthly_stats = defaultdict(lambda: {'hours': 0, 'cost': 0, 'sessions': 0})
    for session in completed_sessions.filter(end_time__gte=now - timedelta(days=180)):
        month_key = session.end_time.strftime('%Y-%m')
        monthly_stats[month_key]['hours'] += session.duration_seconds() / 3600
        monthly_stats[month_key]['cost'] += session.cost()
        monthly_stats[month_key]['sessions'] += 1
    
    sorted_months = sorted(monthly_stats.keys())
    # Labels: short month and 2‑digit year (e.g. 'Aug 25')
    monthly_labels = [
        datetime.strptime(month, '%Y-%m').strftime('%b %y')
        for month in sorted_months[-6:]
    ]
    monthly_hours = [monthly_stats[month]['hours'] for month in sorted_months[-6:]]
    monthly_costs = [monthly_stats[month]['cost'] for month in sorted_months[-6:]]
    
    # Session duration trends (average session duration over time - last 30 days)
    session_duration_stats = defaultdict(lambda: {'total_duration': 0, 'count': 0})
    for session in completed_sessions.filter(end_time__gte=thirty_days_ago):
        date_key = session.end_time.date()
        session_duration_stats[date_key]['total_duration'] += session.duration_seconds()
        session_duration_stats[date_key]['count'] += 1
    
    # Labels: day and short month (e.g. '5 Aug')
    session_duration_labels = [
        date.strftime('%-d %b') for date in sorted(session_duration_stats.keys())
    ]
    session_duration_avg = [
        (session_duration_stats[date]['total_duration'] / session_duration_stats[date]['count']) / 3600 
        if session_duration_stats[date]['count'] > 0 else 0
        for date in sorted(session_duration_stats.keys())
    ]
    
    # Cost breakdown by timer over time (last 30 days) - for stacked area chart
    timer_cost_over_time = defaultdict(lambda: defaultdict(float))
    timer_names_for_cost = {}
    for session in completed_sessions.filter(end_time__gte=thirty_days_ago):
        timer_name = session.project_timer.timer.task_name
        timer_color = session.project_timer.timer.header_color
        date_key = session.end_time.date()
        timer_cost_over_time[timer_name][date_key] += session.cost()
        timer_names_for_cost[timer_name] = timer_color
    
    # Prepare cost breakdown data
    cost_breakdown_dates = sorted(set(
        date for timer_data in timer_cost_over_time.values() 
        for date in timer_data.keys()
    ))
    # Labels: day and short month (e.g. '5 Aug')
    cost_breakdown_labels = [date.strftime('%-d %b') for date in cost_breakdown_dates]
    cost_breakdown_datasets = []
    for timer_name, timer_color in timer_names_for_cost.items():
        cost_breakdown_datasets.append({
            'label': timer_name,
            'data': [timer_cost_over_time[timer_name].get(date, 0) for date in cost_breakdown_dates],
            'color': timer_color
        })
    
    # Team member statistics (if applicable)
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
    
    # Prepare JSON data for charts
    timer_names = [t['name'] for t in timer_stats[:10]]
    timer_hours = [t['time_seconds'] / 3600 for t in timer_stats[:10]]
    timer_colors = [t['color'] for t in timer_stats[:10]]  # Get timer colors
    
    project_names = [p['name'] for p in project_stats[:10]]
    project_hours = [p['time_seconds'] / 3600 for p in project_stats[:10]]
    
    customer_names = [c['name'] for c in customer_stats[:10]]
    customer_hours = [c['time_seconds'] / 3600 for c in customer_stats[:10]]
    
    team_usernames = [t['username'] for t in team_member_stats]
    team_hours = [t['time_seconds'] / 3600 for t in team_member_stats]
    
    context = {
        'total_sessions': total_sessions,
        'total_time_seconds': total_time_seconds,
        'total_cost': total_cost,
        'this_week_hours': this_week_hours,
        'this_week_cost': this_week_cost,
        'most_active_day_name': most_active_day_name,
        'most_active_day_hours': most_active_day_hours,
        'timer_stats': timer_stats[:10],  # Top 10
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'project_stats': project_stats[:10],  # Top 10
        'customer_stats': customer_stats[:10],  # Top 10
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
        'total_timers': timers.count(),
        'total_customers': customers.count(),
        'total_deliverables': total_deliverables,
        'deliverables_with_sessions': deliverables_with_sessions,
        'deliverable_stats': deliverable_stats[:10],  # Top 10
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
    
    return render(request, 'analytics/analytics.html', context)

