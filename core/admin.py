from django.contrib import admin
from .models import (
    PromptLibrary,
    MemoryLibrary,
    PlannedTask,
    ReplyTask,
    MessageRecord
)


@admin.register(PromptLibrary)
class PromptLibraryAdmin(admin.ModelAdmin):
    list_display = ('category', 'key', 'is_active', 'created_at', 'updated_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('key', 'content')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MemoryLibrary)
class MemoryLibraryAdmin(admin.ModelAdmin):
    list_display = ('title', 'memory_type', 'strength', 'weight', 'forget_time', 'created_at')
    list_filter = ('memory_type', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(PlannedTask)
class PlannedTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'task_type', 'scheduled_time', 'status', 'created_at')
    list_filter = ('task_type', 'status', 'scheduled_time')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'scheduled_time'


@admin.register(ReplyTask)
class ReplyTaskAdmin(admin.ModelAdmin):
    list_display = ('trigger_type', 'scheduled_time', 'status', 'created_at')
    list_filter = ('trigger_type', 'status', 'scheduled_time')
    search_fields = ('content', 'context')
    readonly_fields = ('created_at', 'updated_at', 'executed_at')
    date_hierarchy = 'scheduled_time'


@admin.register(MessageRecord)
class MessageRecordAdmin(admin.ModelAdmin):
    list_display = ('message_type', 'sender', 'receiver', 'timestamp', 'created_at')
    list_filter = ('message_type', 'timestamp')
    search_fields = ('content', 'sender', 'receiver')
    readonly_fields = ('created_at',)
    date_hierarchy = 'timestamp'
