from django import template
from timer_app.models import is_workspace_owner as check_is_workspace_owner

register = template.Library()

@register.filter
def is_workspace_owner(user):
    """Template filter to check if user is workspace owner"""
    return check_is_workspace_owner(user)

