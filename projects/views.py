from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Project
from .forms import ProjectForm
from customers.models import Customer
from timer.models import (
    get_workspace_users, get_workspace_owner, 
    TeamMember, is_workspace_owner
)
from timer.views import check_workspace_permission


@login_required
def project_list(request):
    """List all projects across all customers for the current user"""
    projects = Project.objects.filter(customer__user__in=get_workspace_users(request.user)).select_related('customer').order_by('-created_at')
    return render(request, 'projects/project_list.html', {'projects': projects})


@login_required
def project_add(request):
    """Add a new project"""
    customer_id = request.GET.get('customer')
    customer = get_object_or_404(Customer, pk=customer_id, user__in=get_workspace_users(request.user))
    
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
    
    return render(request, 'projects/project_form.html', {
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
    
    return render(request, 'projects/project_detail.html', {
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
    
    return render(request, 'projects/project_form.html', {
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
    
    return render(request, 'projects/project_confirm_delete.html', {
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
    
    return render(request, 'projects/project_confirm_complete.html', {
        'project': project
    })

