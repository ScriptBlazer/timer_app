from .models import TimerSession, get_workspace_users


def running_timer_count(request):
    """Context processor to get the count of running timers for the workspace"""
    if request.user.is_authenticated:
        running_count = TimerSession.objects.filter(
            project_timer__project__customer__user__in=get_workspace_users(request.user),
            end_time__isnull=True
        ).count()
        return {'running_timer_count': running_count}
    return {'running_timer_count': 0}
