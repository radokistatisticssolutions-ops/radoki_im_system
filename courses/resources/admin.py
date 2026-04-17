from django.contrib import admin
from .models import Resource
from radoki.admin import radoki_admin_site

@radoki_admin_site.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'course')
    list_filter = ('course',)
    search_fields = ('title',)
    actions = None  # Remove the default actions