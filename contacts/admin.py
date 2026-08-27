from django.contrib import admin
from contacts.models import Contact

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('contact_id', 'name', 'email', 'phone', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('contact_id', 'name', 'email', 'phone')
    readonly_fields = ('contact_id', 'created_at', 'updated_at')
