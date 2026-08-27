from django.contrib import admin
from .models import CalendarTodo, MeetingAttendee


class MeetingAttendeeInline(admin.TabularInline):
    model = MeetingAttendee
    extra = 1


@admin.register(CalendarTodo)
class CalendarTodoAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "todo_type",
        "user",
        "start",
        "end",
        "priority",
        "assigned_to",
    ]
    list_filter = ["todo_type", "priority"]
    search_fields = ["title", "user__email", "assigned_to__email"]
    inlines = [MeetingAttendeeInline]


@admin.register(MeetingAttendee)
class MeetingAttendeeAdmin(admin.ModelAdmin):
    list_display = ["todo", "user"]
    list_filter = ["user"]
