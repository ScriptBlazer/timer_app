from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Q
import json

from .models import Customer, Project, Timer, TimerSession
from .forms import RegisterForm, CustomerForm, ProjectForm, TimerForm, SessionNoteForm


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
    """List all customers for the current user"""
    customers = Customer.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'timer_app/customer_list.html', {'customers': customers})


@login_required
def customer_detail(request, pk):
    """Show customer detail and their projects"""
    customer = get_object_or_404(Customer, pk=pk, user=request.user)
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
            customer.user = request.user
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
    customer = get_object_or_404(Customer, pk=pk, user=request.user)
    
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
    """Delete a customer"""
    customer = get_object_or_404(Customer, pk=pk, user=request.user)
    
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
    projects = Project.objects.filter(customer__user=request.user).select_related('customer').order_by('-created_at')
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
    if project.customer.user != request.user:
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('customer_list')
    
    timers = project.timers.all()
    return render(request, 'timer_app/project_detail.html', {
        'project': project,
        'timers': timers
    })


@login_required
def project_edit(request, pk):
    """Edit a project"""
    project = get_object_or_404(Project, pk=pk)
    # Check permission
    if project.customer.user != request.user:
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
    if project.customer.user != request.user:
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
    if project.customer.user != request.user:
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


# Timer Views
@login_required
def running_timers(request):
    """Show all running timers across all projects"""
    active_sessions = TimerSession.objects.filter(
        timer__project__customer__user=request.user,
        end_time__isnull=True
    ).select_related('timer', 'timer__project', 'timer__project__customer').order_by('-start_time')
    
    return render(request, 'timer_app/running_timers.html', {
        'active_sessions': active_sessions
    })


@login_required
def timer_add(request):
    """Add a new timer"""
    project_id = request.GET.get('project')
    project = get_object_or_404(Project, pk=project_id)
    # Check permission
    if project.customer.user != request.user:
        messages.error(request, 'You do not have permission to add timers to this project.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        form = TimerForm(request.POST)
        if form.is_valid():
            timer = form.save(commit=False)
            timer.project = project
            timer.save()
            messages.success(request, f'Timer "{timer.task_name}" created successfully!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = TimerForm()
    
    return render(request, 'timer_app/timer_form.html', {
        'form': form,
        'title': 'Add Timer',
        'project': project
    })


@login_required
def timer_detail(request, pk):
    """Show timer detail and its sessions"""
    timer = get_object_or_404(Timer, pk=pk)
    # Check permission
    if timer.project.customer.user != request.user:
        messages.error(request, 'You do not have permission to view this timer.')
        return redirect('customer_list')
    
    sessions = timer.sessions.all()
    return render(request, 'timer_app/timer_detail.html', {
        'timer': timer,
        'sessions': sessions
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
    timer = get_object_or_404(Timer, pk=pk)
    
    # Check permission
    if timer.project.customer.user != request.user:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # Check if project is completed
    if timer.project.status == 'completed':
        return JsonResponse({
            'success': False,
            'error': 'Cannot start timer on a completed project'
        }, status=400)
    
    # Check if timer is already running
    if timer.is_running():
        return JsonResponse({
            'success': False,
            'error': 'Timer is already running'
        }, status=400)
    
    # Create new session
    session = TimerSession.objects.create(
        timer=timer,
        start_time=timezone.now()
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
    timer = get_object_or_404(Timer, pk=pk)
    
    # Check permission
    if timer.project.customer.user != request.user:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # Check if timer is running
    if not timer.is_running():
        return JsonResponse({
            'success': False,
            'error': 'Timer is not running'
        }, status=400)
    
    # Get active session and stop it
    session = timer.active_session()
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
    if session.timer.project.customer.user != request.user:
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
def session_delete(request, pk):
    """Delete a session"""
    session = get_object_or_404(TimerSession, pk=pk)
    
    # Check permission
    if session.timer.project.customer.user != request.user:
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
        timer = session.timer
        session.delete()
        messages.success(request, 'Session deleted successfully!')
        return redirect('timer_detail', pk=timer.pk)
    
    return render(request, 'timer_app/session_confirm_delete.html', {
        'session': session
    })
