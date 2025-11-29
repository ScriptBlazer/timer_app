from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Q
import json

from .models import Customer, Project, Timer, ProjectTimer, TimerSession, TeamMember, get_workspace_owner, is_workspace_owner, get_workspace_users
from .forms import RegisterForm, CustomerForm, ProjectForm, TimerForm, SessionNoteForm, SessionEditForm


def check_workspace_permission(request, obj):
    """Check if user has permission to access this object (customer/project/timer)"""
    workspace_users = get_workspace_users(request.user)
    
    if isinstance(obj, Customer):
        return obj.user in workspace_users
    elif isinstance(obj, Project):
        return obj.customer.user in workspace_users
    elif isinstance(obj, (Timer, ProjectTimer)):
        # Timer should belong to workspace
        if hasattr(obj, 'user'):  # Timer
            return obj.user in workspace_users
        else:  # ProjectTimer
            return obj.project.customer.user in workspace_users
    elif isinstance(obj, TimerSession):
        return obj.project_timer.project.customer.user in workspace_users
    
    return False


def home(request):
    """Redirect to customers if logged in, otherwise to login"""
    if request.user.is_authenticated:
        return redirect('customer_list')
    return redirect('login')


def register_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('customer_list')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('customer_list')
    else:
        form = RegisterForm()
    
    return render(request, 'timer_app/register.html', {'form': form})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


# Customer Views
@login_required
def customer_list(request):
    """List all customers for the workspace"""
    workspace_users = get_workspace_users(request.user)
    customers = Customer.objects.filter(user__in=workspace_users).order_by('-created_at')
    return render(request, 'timer_app/customer_list.html', {'customers': customers})


@login_required
def customer_detail(request, pk):
    """Show customer detail and their projects"""
    workspace_users = get_workspace_users(request.user)
    customer = get_object_or_404(Customer, pk=pk, user__in=workspace_users)
    projects = customer.projects.all()
    return render(request, 'timer_app/customer_detail.html', {
        'customer': customer,
        'projects': projects
    })


@login_required
def customer_add(request):
    """Add a new customer"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.user = get_workspace_owner(request.user)
            customer.save()
            messages.success(request, f'Customer "{customer.name}" created successfully!')
            return redirect('customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    
    return render(request, 'timer_app/customer_form.html', {
        'form': form,
        'title': 'Add Customer'
    })


@login_required
def customer_edit(request, pk):
    """Edit a customer"""
    customer = get_object_or_404(Customer, pk=pk, user__in=get_workspace_users(request.user))
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Customer "{customer.name}" updated successfully!')
            return redirect('customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'timer_app/customer_form.html', {
        'form': form,
        'title': 'Edit Customer',
        'customer': customer
    })


@login_required
def customer_delete(request, pk):
    """Delete a customer (admin only)"""
    workspace_users = get_workspace_users(request.user)
    customer = get_object_or_404(Customer, pk=pk, user__in=workspace_users)
    
    # Only workspace owner can delete
    if not is_workspace_owner(request.user):
        messages.error(request, 'Only the workspace owner can delete customers.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        customer_name = customer.name
        customer.delete()
        messages.success(request, f'Customer "{customer_name}" deleted successfully!')
        return redirect('customer_list')
    
    return render(request, 'timer_app/customer_confirm_delete.html', {
        'customer': customer
    })


# Project Views
@login_required
def project_list(request):
    """List all projects across all customers for the current user"""
    projects = Project.objects.filter(customer__user__in=get_workspace_users(request.user)).select_related('customer').order_by('-created_at')
    return render(request, 'timer_app/project_list.html', {'projects': projects})


@login_required
def project_add(request):
    """Add a new project"""
    customer_id = request.GET.get('customer')
    customer = get_object_or_404(Customer, pk=customer_id, user=request.user)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.customer = customer
            project.save()
            messages.success(request, f'Project "{project.name}" created successfully!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    
    return render(request, 'timer_app/project_form.html', {
        'form': form,
        'title': 'Add Project',
        'customer': customer
    })


@login_required
def project_detail(request, pk):
    """Show project detail and its timers"""
    project = get_object_or_404(Project, pk=pk)
    # Check permission
    if not check_workspace_permission(request, project):
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('customer_list')
    
    project_timers = project.project_timers.all()
    
    # Check if there are team members in workspace (to show "Started by" tags)
    workspace_owner = get_workspace_owner(request.user)
    has_team_members = TeamMember.objects.filter(owner=workspace_owner).exists()
    is_owner = is_workspace_owner(request.user)
    
    return render(request, 'timer_app/project_detail.html', {
        'project': project,
        'project_timers': project_timers,
        'has_team_members': has_team_members,
        'is_owner': is_owner
    })


@login_required
def project_edit(request, pk):
    """Edit a project"""
    project = get_object_or_404(Project, pk=pk)
    # Check permission
    if not check_workspace_permission(request, project):
        messages.error(request, 'You do not have permission to edit this project.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Project "{project.name}" updated successfully!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    
    return render(request, 'timer_app/project_form.html', {
        'form': form,
        'title': 'Edit Project',
        'project': project,
        'customer': project.customer
    })


@login_required
def project_delete(request, pk):
    """Delete a project"""
    project = get_object_or_404(Project, pk=pk)
    # Check permission
    if not check_workspace_permission(request, project):
        messages.error(request, 'You do not have permission to delete this project.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        project_name = project.name
        customer = project.customer
        project.delete()
        messages.success(request, f'Project "{project_name}" deleted successfully!')
        return redirect('customer_detail', pk=customer.pk)
    
    return render(request, 'timer_app/project_confirm_delete.html', {
        'project': project
    })


@login_required
def project_complete(request, pk):
    """Mark a project as completed"""
    project = get_object_or_404(Project, pk=pk)
    # Check permission
    if not check_workspace_permission(request, project):
        messages.error(request, 'You do not have permission to modify this project.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        project.status = 'completed'
        project.save()
        messages.success(request, f'Project "{project.name}" marked as completed!')
        return redirect('project_detail', pk=project.pk)
    
    return render(request, 'timer_app/project_confirm_complete.html', {
        'project': project
    })


# User Account Management
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
    
    return render(request, 'timer_app/edit_own_account.html', {
        'user': request.user
    })


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
    
    return render(request, 'timer_app/edit_team_member.html', {
        'team_member': team_member,
        'member_user': member_user
    })


# Team Management Views
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
    
    return render(request, 'timer_app/team_member_confirm_remove.html', {
        'team_member': team_member
    })


# Admin Panel
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
    if is_owner:
        team_memberships = TeamMember.objects.filter(owner=request.user).select_related('member')
        for tm in team_memberships:
            team_members.append({
                'membership': tm,
                'user': tm.member
            })
    
    return render(request, 'timer_app/admin_panel.html', {
        'timer_stats': timer_stats,
        'customer_stats': customer_stats,
        'project_stats': project_stats,
        'team_members': team_members,
        'is_owner': is_owner,
        'workspace_owner': workspace_owner
    })


# Timer Views
@login_required
def timer_list(request):
    """List all global timers for the current user"""
    timers = Timer.objects.filter(user__in=get_workspace_users(request.user))
    return render(request, 'timer_app/timer_list.html', {'timers': timers})


@login_required
def timer_create(request):
    """Create a new global timer"""
    if request.method == 'POST':
        form = TimerForm(request.POST)
        if form.is_valid():
            timer = form.save(commit=False)
            timer.user = request.user
            timer.save()
            messages.success(request, f'Timer "{timer.task_name}" created successfully!')
            return redirect('admin_panel')
    else:
        form = TimerForm()
    
    return render(request, 'timer_app/timer_create.html', {
        'form': form,
        'title': 'Create Timer'
    })


@login_required
def timer_edit_global(request, pk):
    """Edit a global timer"""
    timer = get_object_or_404(Timer, pk=pk, user__in=get_workspace_users(request.user))
    
    if request.method == 'POST':
        form = TimerForm(request.POST, instance=timer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Timer "{timer.task_name}" updated successfully!')
            return redirect('admin_panel')
    else:
        form = TimerForm(instance=timer)
    
    return render(request, 'timer_app/timer_create.html', {
        'form': form,
        'title': 'Edit Timer',
        'timer': timer
    })


@login_required
def timer_delete_global(request, pk):
    """Delete a global timer"""
    timer = get_object_or_404(Timer, pk=pk, user__in=get_workspace_users(request.user))
    
    if request.method == 'POST':
        timer_name = timer.task_name
        timer.delete()
        messages.success(request, f'Timer "{timer_name}" deleted successfully!')
        return redirect('admin_panel')
    
    return render(request, 'timer_app/timer_global_confirm_delete.html', {
        'timer': timer
    })


@login_required
def running_timers(request):
    """Show all running timers across all projects"""
    active_sessions = TimerSession.objects.filter(
        project_timer__project__customer__user__in=get_workspace_users(request.user),
        end_time__isnull=True
    ).select_related('project_timer', 'project_timer__timer', 'project_timer__project', 'project_timer__project__customer').order_by('-start_time')
    
    return render(request, 'timer_app/running_timers.html', {
        'active_sessions': active_sessions
    })


@login_required
def timer_assign_to_project(request):
    """Assign an existing timer to a project"""
    project_id = request.GET.get('project')
    project = get_object_or_404(Project, pk=project_id)
    
    # Check permission
    if not check_workspace_permission(request, project):
        messages.error(request, 'You do not have permission to add timers to this project.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        timer_id = request.POST.get('timer')
        timer = get_object_or_404(Timer, pk=timer_id, user=request.user)
        
        # Check if already assigned
        if ProjectTimer.objects.filter(project=project, timer=timer).exists():
            messages.error(request, f'Timer "{timer.task_name}" is already assigned to this project.')
        else:
            ProjectTimer.objects.create(project=project, timer=timer)
            messages.success(request, f'Timer "{timer.task_name}" assigned to project!')
        
        return redirect('project_detail', pk=project.pk)
    
    # Get user's timers
    timers = Timer.objects.filter(user__in=get_workspace_users(request.user))
    # Get already assigned timer IDs
    assigned_timer_ids = project.project_timers.values_list('timer_id', flat=True)
    
    return render(request, 'timer_app/timer_assign.html', {
        'project': project,
        'timers': timers,
        'assigned_timer_ids': list(assigned_timer_ids)
    })


@login_required
def project_timer_remove(request, pk):
    """Remove a timer from a project"""
    project_timer = get_object_or_404(ProjectTimer, pk=pk)
    
    # Check permission
    if not check_workspace_permission(request, project_timer):
        messages.error(request, 'You do not have permission to remove this timer.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        timer_name = project_timer.timer.task_name
        project = project_timer.project
        project_timer.delete()
        messages.success(request, f'Timer "{timer_name}" removed from project!')
        return redirect('project_detail', pk=project.pk)
    
    return render(request, 'timer_app/project_timer_confirm_remove.html', {
        'project_timer': project_timer
    })




@login_required
def timer_delete(request, pk):
    """Delete a timer"""
    timer = get_object_or_404(Timer, pk=pk)
    # Check permission
    if timer.project.customer.user != request.user:
        messages.error(request, 'You do not have permission to delete this timer.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        timer_name = timer.task_name
        project = timer.project
        timer.delete()
        messages.success(request, f'Timer "{timer_name}" deleted successfully!')
        return redirect('project_detail', pk=project.pk)
    
    return render(request, 'timer_app/timer_confirm_delete.html', {
        'timer': timer
    })


@login_required
@require_POST
def timer_start(request, pk):
    """Start a timer (AJAX endpoint)"""
    project_timer = get_object_or_404(ProjectTimer, pk=pk)
    
    # Check permission
    if not check_workspace_permission(request, project_timer):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # Check if project is completed
    if project_timer.project.status == 'completed':
        return JsonResponse({
            'success': False,
            'error': 'Cannot start timer on a completed project'
        }, status=400)
    
    # Check if timer is already running
    if project_timer.is_running():
        return JsonResponse({
            'success': False,
            'error': 'Timer is already running'
        }, status=400)
    
    # Create new session with price snapshot and creator
    session = TimerSession.objects.create(
        project_timer=project_timer,
        start_time=timezone.now(),
        price_per_hour=project_timer.timer.price_per_hour,  # Snapshot the current price
        created_by=request.user  # Track who started this session
    )
    
    return JsonResponse({
        'success': True,
        'session_id': session.pk,
        'start_time': session.start_time.isoformat()
    })


@login_required
@require_POST
def timer_stop(request, pk):
    """Stop a timer (AJAX endpoint)"""
    project_timer = get_object_or_404(ProjectTimer, pk=pk)
    
    # Check permission
    if not check_workspace_permission(request, project_timer):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # Check if timer is running
    if not project_timer.is_running():
        return JsonResponse({
            'success': False,
            'error': 'Timer is not running'
        }, status=400)
    
    # Get active session and stop it
    session = project_timer.active_session()
    session.end_time = timezone.now()
    session.save()
    
    return JsonResponse({
        'success': True,
        'session_id': session.pk,
        'end_time': session.end_time.isoformat()
    })


@login_required
@require_POST
def session_update_note(request, pk):
    """Update a session's note (AJAX endpoint)"""
    session = get_object_or_404(TimerSession, pk=pk)
    
    # Check permission
    if not check_workspace_permission(request, session):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        note = data.get('note', '')
        session.note = note
        session.save()
        
        return JsonResponse({
            'success': True,
            'note': session.note
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)


@login_required
def session_edit(request, pk):
    """Edit a session's times and note"""
    session = get_object_or_404(TimerSession, pk=pk)
    
    # Check permission
    if not check_workspace_permission(request, session):
        messages.error(request, 'You do not have permission to edit this session.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        form = SessionEditForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, 'Session updated successfully!')
            return redirect('project_detail', pk=session.project_timer.project.pk)
    else:
        form = SessionEditForm(instance=session)
    
    return render(request, 'timer_app/session_edit.html', {
        'form': form,
        'session': session
    })


@login_required
def session_delete(request, pk):
    """Delete a session"""
    session = get_object_or_404(TimerSession, pk=pk)
    
    # Check permission
    if not check_workspace_permission(request, session):
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        messages.error(request, 'You do not have permission to delete this session.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        # Handle AJAX request
        if request.headers.get('Content-Type') == 'application/json':
            session.delete()
            return JsonResponse({'success': True})
        
        # Handle regular form submission
        project_timer = session.project_timer
        session.delete()
        messages.success(request, 'Session deleted successfully!')
        return redirect('project_detail', pk=project_timer.project.pk)
    
    return render(request, 'timer_app/session_confirm_delete.html', {
        'session': session
    })
