from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

from customers.models import Customer
from projects.models import Project
from timer.models import (
    Timer, ProjectTimer, TimerSession,
    TeamMember, PendingRegistration, CustomColor,
    get_workspace_owner, is_workspace_owner, get_workspace_users
)
from timer.forms import TimerForm
from timer.views import check_workspace_permission


@login_required
def admin_panel(request):
    """Custom admin panel for managing timers, customers, and projects (Owner Only)"""
    # Only workspace owners can access admin panel
    if not is_workspace_owner(request.user):
        messages.error(request, 'Only workspace owners can access the admin panel.')
        return redirect('customer_list')
    
    workspace_owner = get_workspace_owner(request.user)
    is_owner = is_workspace_owner(request.user)
    workspace_users = get_workspace_users(request.user)
    
    # Timer stats
    timers = Timer.objects.filter(user__in=workspace_users).order_by('task_name')
    timer_stats = []
    for timer in timers:
        project_count = timer.project_timers.count()
        total_sessions = TimerSession.objects.filter(project_timer__timer=timer).count()
        timer_stats.append({
            'timer': timer,
            'project_count': project_count,
            'session_count': total_sessions
        })
    
    # Customer stats
    customers = Customer.objects.filter(user__in=workspace_users).order_by('name')
    customer_stats = []
    for customer in customers:
        project_count = customer.projects.count()
        customer_stats.append({
            'customer': customer,
            'project_count': project_count
        })
    
    # Project stats
    projects = Project.objects.filter(customer__user__in=workspace_users).order_by('-created_at')
    project_stats = []
    for project in projects:
        timer_count = project.project_timers.count()
        session_count = TimerSession.objects.filter(project_timer__project=project).count()
        project_stats.append({
            'project': project,
            'timer_count': timer_count,
            'session_count': session_count
        })
    
    # Team member stats (only for owner)
    team_members = []
    pending_registrations = []
    if is_owner:
        team_memberships = TeamMember.objects.filter(owner=request.user).select_related('member')
        for tm in team_memberships:
            team_members.append({
                'membership': tm,
                'user': tm.member
            })
        
        # Get pending registrations (show to all owners, not workspace-specific)
        pending_registrations = PendingRegistration.objects.all()
    
    return render(request, 'workspace_admin/admin_panel.html', {
        'timer_stats': timer_stats,
        'customer_stats': customer_stats,
        'project_stats': project_stats,
        'team_members': team_members,
        'pending_registrations': pending_registrations,
        'is_owner': is_owner,
        'workspace_owner': workspace_owner
    })


@login_required
def edit_own_account(request):
    """Owner edits their own account"""
    if not is_workspace_owner(request.user):
        messages.error(request, 'Only workspace owners can access this page.')
        return redirect('admin_panel')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        current_password = request.POST.get('current_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        # Update username
        if username and username != request.user.username:
            if User.objects.filter(username=username).exists():
                messages.error(request, f'Username "{username}" is already taken.')
                return redirect('edit_own_account')
            request.user.username = username
        
        # Update email
        if email != request.user.email:
            if email and User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                messages.error(request, f'Email "{email}" is already in use.')
                return redirect('edit_own_account')
            request.user.email = email
        
        # Update password if provided
        if new_password:
            if not current_password:
                messages.error(request, 'Please enter your current password to change it.')
                return redirect('edit_own_account')
            
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return redirect('edit_own_account')
            
            if new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
                return redirect('edit_own_account')
            
            if len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
                return redirect('edit_own_account')
            
            request.user.set_password(new_password)
        
        request.user.save()
        messages.success(request, 'Your account has been updated successfully!')
        return redirect('admin_panel')
    
    return render(request, 'workspace_admin/edit_own_account.html', {
        'user': request.user
    })


@login_required
def team_add_member(request):
    """Create a new team member user (owner only)"""
    if not is_workspace_owner(request.user):
        messages.error(request, 'Only the workspace owner can add team members.')
        return redirect('admin_panel')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '').strip()
        
        # Validation
        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return redirect('admin_panel')
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" is already taken.')
            return redirect('admin_panel')
        
        # Check if email already exists (if provided)
        if email and User.objects.filter(email=email).exists():
            messages.error(request, f'Email "{email}" is already in use.')
            return redirect('admin_panel')
        
        # Create new user
        new_user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )
        
        # Automatically add as team member
        TeamMember.objects.create(
            owner=request.user,
            member=new_user,
            role='member'
        )
        
        messages.success(request, f'User "{username}" created and added to your workspace!')
    
    return redirect('admin_panel')


@login_required
def edit_team_member(request, pk):
    """Owner edits a team member's account"""
    if not is_workspace_owner(request.user):
        messages.error(request, 'Only workspace owners can manage team members.')
        return redirect('admin_panel')
    
    team_member = get_object_or_404(TeamMember, pk=pk, owner=request.user)
    member_user = team_member.member
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        
        # Update username
        if username and username != member_user.username:
            if User.objects.filter(username=username).exists():
                messages.error(request, f'Username "{username}" is already taken.')
                return redirect('edit_team_member', pk=pk)
            member_user.username = username
        
        # Update email
        if email != member_user.email:
            if email and User.objects.filter(email=email).exclude(pk=member_user.pk).exists():
                messages.error(request, f'Email "{email}" is already in use.')
                return redirect('edit_team_member', pk=pk)
            member_user.email = email
        
        # Update password if provided
        if new_password:
            if len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
                return redirect('edit_team_member', pk=pk)
            
            member_user.set_password(new_password)
        
        member_user.save()
        messages.success(request, f'Account for {member_user.username} has been updated!')
        return redirect('admin_panel')
    
    return render(request, 'workspace_admin/edit_team_member.html', {
        'team_member': team_member,
        'member_user': member_user
    })


@login_required
def team_remove_member(request, pk):
    """Remove a team member (owner only)"""
    if not is_workspace_owner(request.user):
        messages.error(request, 'Only the workspace owner can remove team members.')
        return redirect('admin_panel')
    
    team_member = get_object_or_404(TeamMember, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        username = team_member.member.username
        team_member.delete()
        messages.success(request, f'{username} removed from your workspace.')
        return redirect('admin_panel')
    
    return render(request, 'workspace_admin/team_member_confirm_remove.html', {
        'team_member': team_member
    })

