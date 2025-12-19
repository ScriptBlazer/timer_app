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

from .models import Timer, ProjectTimer, TimerSession, TeamMember, PendingRegistration, CustomColor, get_workspace_owner, is_workspace_owner, get_workspace_users
from customers.models import Customer
from projects.models import Project
from .telegram_utils import send_telegram_approval_request, send_telegram_notification
from .forms import RegisterForm, TimerForm, SessionNoteForm, SessionEditForm


def check_workspace_permission(request, obj):
    """Check if user has permission to access this object (customer/project/timer/deliverable)"""
    workspace_users = get_workspace_users(request.user)
    
    # Import here to avoid circular imports
    from customers.models import Customer
    from projects.models import Project
    
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
    else:
        # Check if it's a Deliverable (import here to avoid circular imports)
        try:
            from deliverables.models import Deliverable
            if isinstance(obj, Deliverable):
                return obj.project.customer.user in workspace_users
        except ImportError:
            pass
    
    return False


def home(request):
    """Redirect to customers if logged in, otherwise to login"""
    if request.user.is_authenticated:
        return redirect('customer_list')
    return redirect('login')


def register_view(request):
    """User registration - requires admin approval via Telegram"""
    if request.user.is_authenticated:
        return redirect('customer_list')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Don't create user yet - create pending registration
            username = form.cleaned_data['username']
            email = form.cleaned_data.get('email', '')
            password = form.cleaned_data['password1']
            
            # Check if username already exists as a user
            if User.objects.filter(username=username).exists():
                messages.error(request, 'A user with this username already exists.')
                return render(request, 'timer/register.html', {'form': form})
            
            # Check if already pending
            pending = PendingRegistration.objects.filter(username=username).first()
            if pending:
                messages.error(request, f'A registration for "{username}" is already pending approval.')
                return render(request, 'timer/register.html', {
                    'form': form,
                    'pending_registration': pending
                })
            
            # Create pending registration with hashed password
            from django.contrib.auth.hashers import make_password
            pending = PendingRegistration.objects.create(
                username=username,
                email=email,
                password_hash=make_password(password)
            )
            
            # Send Telegram notification
            success, error_msg = send_telegram_approval_request(pending, request)
            if not success and error_msg:
                print(f"Warning: {error_msg}")
            
            # Show success message
            return render(request, 'timer/registration_pending.html', {
                'username': username
            })
        else:
            # Form validation failed - show errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RegisterForm()
    
    return render(request, 'timer/register.html', {'form': form})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


def approve_registration(request, token):
    """Approve a pending registration"""
    pending = get_object_or_404(PendingRegistration, approval_token=token)
    
    # Create the user
    user = User.objects.create(
        username=pending.username,
        email=pending.email,
        password=pending.password_hash  # Already hashed
    )
    
    # Send confirmation
    send_telegram_notification(
        f"✅ Registration approved!\n\n"
        f"Username: {user.username}\n"
        f"Email: {user.email}\n\n"
        f"User can now log in."
    )
    
    # Delete pending registration
    pending.delete()
    
    return render(request, 'timer/registration_approved.html', {
        'username': user.username
    })


def deny_registration(request, token):
    """Deny a pending registration"""
    pending = get_object_or_404(PendingRegistration, approval_token=token)
    
    username = pending.username
    email = pending.email
    
    # Send notification
    send_telegram_notification(
        f"❌ Registration denied\n\n"
        f"Username: {username}\n"
        f"Email: {email}"
    )
    
    # Delete pending registration
    pending.delete()
    
    return render(request, 'timer/registration_denied.html', {
        'username': username
    })


def resend_approval_notification(request, token):
    """Resend Telegram approval notification for a pending registration"""
    pending = get_object_or_404(PendingRegistration, approval_token=token)
    
    # Resend Telegram notification
    success, error_msg = send_telegram_approval_request(pending, request)
    
    # Check if this is coming from admin panel (user is authenticated) or registration page
    if request.user.is_authenticated:
        # Coming from admin panel
        if success:
            messages.success(request, f'Approval notification for "{pending.username}" has been resent to Telegram!')
        else:
            # Show specific error message
            error_display = error_msg if error_msg else 'Failed to send Telegram notification. Please check the server logs.'
            messages.error(request, error_display)
        return redirect('admin_panel')
    else:
        # Coming from registration page
        if success:
            return render(request, 'timer/register.html', {
                'form': RegisterForm(),
                'notification_resent': True,
                'pending_username': pending.username
            })
        else:
            # Show specific error message
            error_display = error_msg if error_msg else 'Failed to send Telegram notification. Please try again later.'
            messages.error(request, error_display)
            return render(request, 'timer/register.html', {
                'form': RegisterForm(),
                'pending_registration': pending,
                'telegram_error': True
            })


def test_telegram(request):
    """Test endpoint to verify Telegram connection"""
    from django.contrib.auth.decorators import login_required
    from .telegram_utils import send_telegram_notification
    import os
    from dotenv import load_dotenv
    
    if not request.user.is_authenticated or not is_workspace_owner(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    load_dotenv()
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_ADMIN_CHAT_ID')
    
    info = {
        'bot_token_exists': bool(bot_token),
        'bot_token_preview': bot_token[:10] + '...' if bot_token else None,
        'chat_id': chat_id,
        'chat_id_exists': bool(chat_id),
    }
    
    if request.method == 'POST':
        # Try sending a test message
        test_message = "🧪 Test message from Timer App!\n\nIf you received this, Telegram is working correctly! ✅"
        success = send_telegram_notification(test_message)
        info['test_sent'] = True
        info['test_success'] = success
    
    from django.http import JsonResponse
    return JsonResponse(info)


# User Account Management
# Timer Views
@login_required
def timer_list(request):
    """List all global timers for the current user"""
    timers = Timer.objects.filter(user__in=get_workspace_users(request.user))
    return render(request, 'timer/timer_list.html', {'timers': timers})


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
    
    # Get custom colors saved by workspace owner
    workspace_owner = get_workspace_owner(request.user)
    custom_colors = CustomColor.objects.filter(owner=workspace_owner).order_by('-created_at')
    custom_colors_list = [cc.color.upper() for cc in custom_colors]
    
    return render(request, 'timer/timer_create.html', {
        'form': form,
        'title': 'Create Timer',
        'custom_colors': custom_colors_list
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
    
    # Get custom colors saved by workspace owner
    workspace_owner = get_workspace_owner(request.user)
    custom_colors = CustomColor.objects.filter(owner=workspace_owner).order_by('-created_at')
    custom_colors_list = [cc.color.upper() for cc in custom_colors]
    
    return render(request, 'timer/timer_create.html', {
        'form': form,
        'title': 'Edit Timer',
        'timer': timer,
        'custom_colors': custom_colors_list
    })


@login_required
@require_POST
def add_custom_color(request):
    """Add a custom color to the workspace"""
    try:
        data = json.loads(request.body)
        color = data.get('color', '').strip().upper()
        
        # Validate hex color
        if not color or not color.startswith('#') or len(color) != 7:
            return JsonResponse({'success': False, 'error': 'Invalid color format'})
        
        # Validate hex characters
        if not all(c in '0123456789ABCDEF' for c in color[1:]):
            return JsonResponse({'success': False, 'error': 'Invalid hex color'})
        
        workspace_owner = get_workspace_owner(request.user)
        
        # Check if color already exists
        if CustomColor.objects.filter(owner=workspace_owner, color=color).exists():
            return JsonResponse({'success': False, 'error': 'Color already exists'})
        
        # Create custom color
        custom_color = CustomColor.objects.create(owner=workspace_owner, color=color)
        
        return JsonResponse({
            'success': True,
            'color': custom_color.color,
            'message': 'Custom color added successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def timer_delete_global(request, pk):
    """Delete a global timer"""
    timer = get_object_or_404(Timer, pk=pk, user__in=get_workspace_users(request.user))
    
    if request.method == 'POST':
        timer_name = timer.task_name
        timer.delete()
        messages.success(request, f'Timer "{timer_name}" deleted successfully!')
        return redirect('admin_panel')
    
    return render(request, 'timer/timer_global_confirm_delete.html', {
        'timer': timer
    })


@login_required
def running_timers(request):
    """Show all running timers across all projects"""
    active_sessions = TimerSession.objects.filter(
        project_timer__project__customer__user__in=get_workspace_users(request.user),
        end_time__isnull=True
    ).select_related('project_timer', 'project_timer__timer', 'project_timer__project', 'project_timer__project__customer').order_by('-start_time')
    
    return render(request, 'timer/running_timers.html', {
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
        timer = get_object_or_404(Timer, pk=timer_id, user__in=get_workspace_users(request.user))
        
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
    
    return render(request, 'projects/timer_assign.html', {
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
    
    return render(request, 'projects/project_timer_confirm_remove.html', {
        'project_timer': project_timer
    })




# Note: timer_delete was removed - use timer_delete_global instead
# This function was incorrectly trying to access timer.project which doesn't exist


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
    """Update a session's note and deliverable (AJAX endpoint)"""
    session = get_object_or_404(TimerSession, pk=pk)
    
    # Check permission
    if not check_workspace_permission(request, session):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        note = data.get('note')
        deliverable_id = data.get('deliverable')
        
        # Only update note if it's provided in the request
        if note is not None:
            session.note = note
        
        # Update deliverable if provided
        if deliverable_id is not None:
            from deliverables.models import Deliverable
            if deliverable_id:
                try:
                    deliverable = Deliverable.objects.get(pk=deliverable_id, project=session.project_timer.project)
                    session.deliverable = deliverable
                except Deliverable.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Invalid deliverable'}, status=400)
            else:
                session.deliverable = None
        
        session.save()
        
        # Include deliverable info in response if it exists
        deliverable_info = None
        if session.deliverable:
            deliverable_info = {
                'id': session.deliverable.pk,
                'name': session.deliverable.name
            }
        
        response_data = {
            'success': True,
            'note': session.note,
        }
        if deliverable_info:
            response_data['deliverable'] = deliverable_info
        
        return JsonResponse(response_data)
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
    
    return render(request, 'timer/session_edit.html', {
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
    
    return render(request, 'timer/session_confirm_delete.html', {
        'session': session
    })
