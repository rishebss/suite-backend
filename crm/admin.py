from django.contrib import admin
from crm.models import CRM

@admin.register(CRM)
class CRMAdmin(admin.ModelAdmin):
    list_display = ('contact', 'stage', 'value', 'priority', 'created_at')
    list_filter = ('stage', 'priority')
    search_fields = ('contact__name', 'contact__email')
