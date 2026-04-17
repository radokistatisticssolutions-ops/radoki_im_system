# radoki/templatetags/admin_filters.py
from django import template
from django.utils.html import format_html
from decimal import Decimal

register = template.Library()


@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return value * Decimal(str(arg))
    except (ValueError, TypeError):
        return 0


@register.filter
def currency(value):
    """Format value as currency (TZS)"""
    try:
        return f"TZS {float(value):,.0f}"
    except (ValueError, TypeError):
        return "TZS 0"


@register.filter
def percentage(value, max_value):
    """Calculate percentage"""
    try:
        if max_value == 0:
            return 0
        return int((float(value) / float(max_value)) * 100)
    except (ValueError, TypeError):
        return 0


@register.filter
def badge(value, color='primary'):
    """Create a badge HTML element"""
    colors = {
        'primary': '#3498db',
        'success': '#27ae60',
        'warning': '#f39c12',
        'danger': '#e74c3c',
        'info': '#9b59b6',
        'secondary': '#95a5a6',
    }
    
    bg_color = colors.get(color, colors['primary'])
    
    return format_html(
        '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 0.85rem;">{}</span>',
        bg_color, value
    )


@register.filter
def status_badge(value):
    """Create a status badge (Active/Inactive)"""
    if value:
        return format_html(
            '<span style="background: #27ae60; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">✓ Active</span>'
        )
    return format_html(
        '<span style="background: #e74c3c; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">✗ Inactive</span>'
    )


@register.filter
def approval_badge(value):
    """Create an approval status badge"""
    if value:
        return format_html(
            '<span style="background: #27ae60; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">✓ Approved</span>'
        )
    return format_html(
        '<span style="background: #f39c12; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">⏳ Pending</span>'
    )


@register.filter
def dict_get(d, key):
    """Look up a key in a dictionary: {{ my_dict|dict_get:key }}"""
    if isinstance(d, dict):
        return d.get(key)
    return None


@register.filter
def truncate_words(value, num_words=5):
    """Truncate text to a number of words"""
    words = str(value).split()
    if len(words) > num_words:
        return ' '.join(words[:num_words]) + '...'
    return value


@register.simple_tag
def multiply_simple(value, arg):
    """Simple tag version of multiply filter"""
    try:
        return value * Decimal(str(arg))
    except (ValueError, TypeError):
        return 0


@register.simple_tag
def get_total_revenue(enrollments_count, price):
    """Calculate total revenue"""
    try:
        return int(int(enrollments_count) * Decimal(str(price)))
    except (ValueError, TypeError):
        return 0
