from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Customer
from .forms import CustomerForm
from timer.models import get_workspace_users, get_workspace_owner, is_workspace_owner


@login_required
def customer_list(request):
    """List all customers for the workspace"""
    workspace_users = get_workspace_users(request.user)
    customers = Customer.objects.filter(user__in=workspace_users).order_by('-created_at')
    return render(request, 'customers/customer_list.html', {'customers': customers})


@login_required
def customer_detail(request, pk):
    """Show customer detail and their projects"""
    workspace_users = get_workspace_users(request.user)
    customer = get_object_or_404(Customer, pk=pk, user__in=workspace_users)
    projects = customer.projects.all()
    return render(request, 'customers/customer_detail.html', {
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
    
    return render(request, 'customers/customer_form.html', {
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
    
    return render(request, 'customers/customer_form.html', {
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
    
    return render(request, 'customers/customer_confirm_delete.html', {
        'customer': customer
    })

