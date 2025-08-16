from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def div(value, arg):
    """Divide value by arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def percentage(value, total):
    """Calculate percentage of value in total"""
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, ZeroDivisionError):
        return 0
