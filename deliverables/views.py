from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import IntegrityError
import json

from .models import Deliverable
from projects.models import Project
from timer.views import check_workspace_permission
from timer.models import get_workspace_users
from .forms import DeliverableForm


@login_required
def deliverable_list(request, project_pk):
    """List all deliverables for a project"""
    project = get_object_or_404(Project, pk=project_pk)
    
    # Check permission
    if not check_workspace_permission(request, project):
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('customer_list')
    
    deliverables = project.deliverables.all()
    
    return render(request, 'deliverables/deliverable_list.html', {
        'project': project,
        'deliverables': deliverables
    })


@login_required
def deliverable_add(request, project_pk):
    """Add a new deliverable to a project"""
    project = get_object_or_404(Project, pk=project_pk)
    
    # Check permission
    if not check_workspace_permission(request, project):
        messages.error(request, 'You do not have permission to add deliverables to this project.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        form = DeliverableForm(request.POST, project=project)
        if form.is_valid():
            try:
                deliverable = form.save(commit=False)
                deliverable.project = project
                deliverable.save()
                messages.success(request, f'Deliverable "{deliverable.name}" added successfully!')
                
                # If AJAX request, return JSON
                if request.headers.get('Content-Type') == 'application/json' or request.GET.get('ajax'):
                    return JsonResponse({
                        'success': True,
                        'deliverable': {
                            'id': deliverable.pk,
                            'name': deliverable.name
                        }
                    })
                
                return redirect('deliverables:deliverable_list', project_pk=project.pk)
            except IntegrityError:
                form.add_error('name', 'A deliverable with this name already exists for this project.')
    else:
        form = DeliverableForm(project=project)
    
    return render(request, 'deliverables/deliverable_add.html', {
        'form': form,
        'project': project
    })


@login_required
@require_POST
def deliverable_add_ajax(request, project_pk):
    """AJAX endpoint to add a deliverable inline"""
    project = get_object_or_404(Project, pk=project_pk)
    
    # Check permission
    if not check_workspace_permission(request, project):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required'}, status=400)
        
        # Check for duplicate
        if Deliverable.objects.filter(project=project, name=name).exists():
            return JsonResponse({'success': False, 'error': 'A deliverable with this name already exists for this project.'}, status=400)
        
        try:
            deliverable = Deliverable.objects.create(
                project=project,
                name=name,
                description=data.get('description', '')
            )
        except IntegrityError:
            return JsonResponse({'success': False, 'error': 'A deliverable with this name already exists for this project.'}, status=400)
        
        return JsonResponse({
            'success': True,
            'deliverable': {
                'id': deliverable.pk,
                'name': deliverable.name
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def deliverable_detail(request, pk):
    """Show deliverable detail with linked sessions"""
    deliverable = get_object_or_404(Deliverable, pk=pk)
    
    # Check permission
    if not check_workspace_permission(request, deliverable.project):
        messages.error(request, 'You do not have permission to view this deliverable.')
        return redirect('customer_list')
    
    # Get all sessions linked to this deliverable
    from timer.models import TimerSession
    sessions = TimerSession.objects.filter(
        deliverable=deliverable,
        end_time__isnull=False
    ).select_related('project_timer', 'project_timer__timer', 'project_timer__project').order_by('-start_time')
    
    return render(request, 'deliverables/deliverable_detail.html', {
        'deliverable': deliverable,
        'sessions': sessions
    })


@login_required
def deliverable_edit(request, pk):
    """Edit a deliverable"""
    deliverable = get_object_or_404(Deliverable, pk=pk)
    
    # Check permission
    if not check_workspace_permission(request, deliverable.project):
        messages.error(request, 'You do not have permission to edit this deliverable.')
        return redirect('customer_list')
    
    if request.method == 'POST':
        form = DeliverableForm(request.POST, instance=deliverable, project=deliverable.project)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Deliverable updated successfully!')
                return redirect('deliverables:deliverable_list', project_pk=deliverable.project.pk)
            except IntegrityError:
                form.add_error('name', 'A deliverable with this name already exists for this project.')
    else:
        form = DeliverableForm(instance=deliverable, project=deliverable.project)
    
    return render(request, 'deliverables/deliverable_edit.html', {
        'form': form,
        'deliverable': deliverable
    })


@login_required
@require_POST
def deliverable_delete(request, pk):
    """Delete a deliverable"""
    deliverable = get_object_or_404(Deliverable, pk=pk)
    
    # Check permission
    if not check_workspace_permission(request, deliverable.project):
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        messages.error(request, 'You do not have permission to delete this deliverable.')
        return redirect('customer_list')
    
    project_pk = deliverable.project.pk
    deliverable_name = deliverable.name
    deliverable.delete()
    
    messages.success(request, f'Deliverable "{deliverable_name}" deleted successfully!')
    
    if request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({'success': True})
    
    return redirect('deliverables:deliverable_list', project_pk=project_pk)


