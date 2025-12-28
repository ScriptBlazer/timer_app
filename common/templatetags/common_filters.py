from django import template

register = template.Library()


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

