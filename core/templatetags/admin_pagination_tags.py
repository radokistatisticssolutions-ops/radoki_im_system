from django import template
from django.contrib.admin.views.main import PAGE_VAR

register = template.Library()


@register.simple_tag
def prev_page_url(cl):
    return cl.get_query_string({PAGE_VAR: cl.page_num - 1})


@register.simple_tag
def next_page_url(cl):
    return cl.get_query_string({PAGE_VAR: cl.page_num + 1})
