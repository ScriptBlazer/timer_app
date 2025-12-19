from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import Project
from .forms import ProjectForm
from customers.models import Customer
from timer.models import (
    get_workspace_users, get_workspace_owner, 
    TeamMember, is_workspace_owner, TimerSession
)
from timer.views import check_workspace_permission
from deliverables.models import Deliverable


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


@login_required
def project_summary(request, pk):
    """Show project summary with timers, deliverables, and totals"""
    project = get_object_or_404(Project, pk=pk)
    # Check permission
    if not check_workspace_permission(request, project):
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('customer_list')
    
    # Get all project timers with their totals
    project_timers = project.project_timers.all()
    timer_summaries = []
    for pt in project_timers:
        sessions = pt.sessions.filter(end_time__isnull=False)
        timer_summaries.append({
            'timer': pt.timer,
            'total_time_seconds': pt.total_duration_seconds(),
            'total_cost': pt.total_cost(),
            'session_count': sessions.count(),
        })
    
    # Get all deliverables with their totals
    deliverables = project.deliverables.all()
    deliverable_summaries = []
    for deliverable in deliverables:
        sessions = TimerSession.objects.filter(deliverable=deliverable, end_time__isnull=False)
        deliverable_summaries.append({
            'deliverable': deliverable,
            'total_time_seconds': deliverable.total_duration_seconds(),
            'total_cost': deliverable.total_cost(),
            'session_count': deliverable.session_count(),
        })
    
    # Calculate totals
    total_time_seconds = project.total_duration_seconds()
    total_cost = project.total_cost()
    
    # Calculate deliverable totals
    total_deliverable_time = sum(d['total_time_seconds'] for d in deliverable_summaries)
    total_deliverable_cost = sum(d['total_cost'] for d in deliverable_summaries)
    
    return render(request, 'projects/project_summary.html', {
        'project': project,
        'timer_summaries': timer_summaries,
        'deliverable_summaries': deliverable_summaries,
        'total_time_seconds': total_time_seconds,
        'total_cost': total_cost,
        'total_deliverable_time': total_deliverable_time,
        'total_deliverable_cost': total_deliverable_cost,
    })


@login_required
def project_summary_pdf(request, pk):
    """Generate PDF summary for the project"""
    project = get_object_or_404(Project, pk=pk)
    # Check permission
    if not check_workspace_permission(request, project):
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('customer_list')
    
    # Get all project timers with their totals
    project_timers = project.project_timers.all()
    timer_summaries = []
    for pt in project_timers:
        sessions = pt.sessions.filter(end_time__isnull=False)
        timer_summaries.append({
            'timer': pt.timer,
            'total_time_seconds': pt.total_duration_seconds(),
            'total_cost': pt.total_cost(),
            'session_count': sessions.count(),
        })
    
    # Get all deliverables with their totals
    deliverables = project.deliverables.all()
    deliverable_summaries = []
    for deliverable in deliverables:
        sessions = TimerSession.objects.filter(deliverable=deliverable, end_time__isnull=False)
        deliverable_summaries.append({
            'deliverable': deliverable,
            'total_time_seconds': deliverable.total_duration_seconds(),
            'total_cost': deliverable.total_cost(),
            'session_count': deliverable.session_count(),
        })
    
    # Calculate totals
    total_time_seconds = project.total_duration_seconds()
    total_cost = project.total_cost()
    
    # Calculate deliverable totals
    total_deliverable_time = sum(d['total_time_seconds'] for d in deliverable_summaries)
    total_deliverable_cost = sum(d['total_cost'] for d in deliverable_summaries)
    
    # Render HTML template
    html_string = render_to_string('projects/project_summary_pdf.html', {
        'project': project,
        'timer_summaries': timer_summaries,
        'deliverable_summaries': deliverable_summaries,
        'total_time_seconds': total_time_seconds,
        'total_cost': total_cost,
        'total_deliverable_time': total_deliverable_time,
        'total_deliverable_cost': total_deliverable_cost,
    })
    
    # Generate PDF using weasyprint
    try:
        from weasyprint import HTML
        from django.conf import settings
        import os
        
        # Create HTML object from the rendered template
        html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        
        # Generate PDF
        pdf_file = html.write_pdf()
        
        # Create HTTP response with PDF content
        response = HttpResponse(pdf_file, content_type='application/pdf')
        
        # Set filename and force download
        # Format: "Project summary for {Project Name}, {Customer Name}.pdf"
        customer_name = project.customer.name
        project_name = project.name
        filename = f"Project summary for {project_name}, {customer_name}.pdf"
        # Clean filename of any invalid characters (keep spaces, commas, and periods)
        filename = ''.join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.', ','))
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_file)
        
        return response
        
    except ImportError:
        # If weasyprint is not installed
        messages.error(request, 'PDF generation requires weasyprint. Please install it with: pip install weasyprint')
        return redirect('project_summary', pk=project.pk)
        
    except Exception as e:
        # Log the error and show user-friendly message
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error generating PDF: {str(e)}', exc_info=True)
        messages.error(request, f'Error generating PDF: {str(e)}. Please check the server logs for details.')
        return redirect('project_summary', pk=project.pk)

