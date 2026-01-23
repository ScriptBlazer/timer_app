from django import template
from common.templatetags.common_filters import format_currency_with_commas

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
    """Format value as currency with comma separators"""
    return format_currency_with_commas(value)

