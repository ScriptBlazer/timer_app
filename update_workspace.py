#!/usr/bin/env python
"""Update views.py to use workspace filtering"""
import re

views_file = 'timer_app/views.py'

with open(views_file, 'r') as f:
    content = f.read()

# Patterns to replace
replacements = [
    # Customer filters
    (r'Customer\.objects\.filter\(user=request\.user\)', 'Customer.objects.filter(user__in=get_workspace_users(request.user))'),
    (r'get_object_or_404\(Customer, pk=pk, user=request\.user\)', 'get_object_or_404(Customer, pk=pk, user__in=get_workspace_users(request.user))'),
    
    # Project filters
    (r'Project\.objects\.filter\(customer__user=request\.user\)', 'Project.objects.filter(customer__user__in=get_workspace_users(request.user))'),
    
    # Timer filters
    (r'Timer\.objects\.filter\(user=request\.user\)', 'Timer.objects.filter(user__in=get_workspace_users(request.user))'),
    (r'get_object_or_404\(Timer, pk=pk, user=request\.user\)', 'get_object_or_404(Timer, pk=pk, user__in=get_workspace_users(request.user))'),
    
    # Permission checks
    (r'if project\.customer\.user != request\.user:', 'if not check_workspace_permission(request, project):'),
    (r'if project_timer\.project\.customer\.user != request\.user:', 'if not check_workspace_permission(request, project_timer):'),
    (r'if session\.project_timer\.project\.customer\.user != request\.user:', 'if not check_workspace_permission(request, session):'),
    
    # Running timers
    (r'project_timer__project__customer__user=request\.user', 'project_timer__project__customer__user__in=get_workspace_users(request.user)'),
    
    # New customer assignment
    (r'customer\.user = request\.user', 'customer.user = get_workspace_owner(request.user)'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

with open(views_file, 'w') as f:
    f.write(content)

print("✅ Updated views.py with workspace filtering!")

