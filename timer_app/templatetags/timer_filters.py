from django import template

register = template.Library()


@register.filter
def format_duration(seconds):
    """Format seconds as HH:MM:SS"""
    if seconds is None:
        return "00:00:00"
    
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@register.filter
def format_currency(value):
    """Format value as currency"""
    try:
        return f"${float(value):.2f}"
    except (ValueError, TypeError):
        return "$0.00"

