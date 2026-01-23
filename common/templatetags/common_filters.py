from django import template

register = template.Library()


def format_currency_with_commas(value):
    """
    Format a numeric value as currency with comma separators for thousands.
    Returns: £1,000.00 format
    """
    try:
        float_value = float(value)
        # Format with 2 decimal places and comma separators
        formatted = f"{float_value:,.2f}"
        return f"£{formatted}"
    except (ValueError, TypeError):
        return "£0.00"


@register.filter
def truncate_chars(value, arg):
    """
    Truncate a string to a specified number of characters.
    Usage: {{ value|truncate_chars:20 }}
    """
    try:
        length = int(arg)
    except (ValueError, TypeError):
        return value
    
    if value is None:
        return ''
    
    value = str(value)
    if len(value) <= length:
        return value
    
    return value[:length] + '...'

