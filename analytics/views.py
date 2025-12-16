from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
import json
from collections import defaultdict
from datetime import timedelta

from timer_app.models import (
    Customer, Project, Timer, TimerSession,
    get_workspace_users
)


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
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    daily_stats = defaultdict(float)
    
    for session in completed_sessions.filter(end_time__gte=thirty_days_ago):
        date_key = session.end_time.date()
        daily_stats[date_key] += session.duration_seconds()
    
    # Sort by date and create lists for chart
    sorted_dates = sorted(daily_stats.keys())
    daily_labels = [date.strftime('%m/%d') for date in sorted_dates]
    daily_hours = [daily_stats[date] / 3600 for date in sorted_dates]
    
    # Weekly statistics (last 12 weeks)
    weekly_stats = defaultdict(float)
    for session in completed_sessions.filter(end_time__gte=now - timedelta(days=84)):
        week_start = session.end_time.date() - timedelta(days=session.end_time.weekday())
        weekly_stats[week_start] += session.duration_seconds()
    
    sorted_weeks = sorted(weekly_stats.keys())
    weekly_labels = [week.strftime('%m/%d') for week in sorted_weeks[-12:]]
    weekly_hours = [weekly_stats[week] / 3600 for week in sorted_weeks[-12:]]
    
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
        'timer_stats': timer_stats[:10],  # Top 10
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'project_stats': project_stats[:10],  # Top 10
        'customer_stats': customer_stats[:10],  # Top 10
        'team_member_stats': team_member_stats,
        'daily_labels': json.dumps(daily_labels),
        'daily_hours': json.dumps(daily_hours),
        'weekly_labels': json.dumps(weekly_labels),
        'weekly_hours': json.dumps(weekly_hours),
        'total_timers': timers.count(),
        'total_customers': customers.count(),
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

