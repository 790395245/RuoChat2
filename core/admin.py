from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count
from .models import (
    ChatUser,
    PromptLibrary,
    MemoryLibrary,
    PlannedTask,
    ReplyTask,
    MessageRecord
)


# 自定义 Admin 站点标题
admin.site.site_header = 'RuoChat2 管理后台'
admin.site.site_title = 'RuoChat2'
admin.site.index_title = '数据管理'


def truncate_text(text, max_length=50):
    """截断长文本"""
    if len(text) > max_length:
        return text[:max_length] + '...'
    return text


@admin.register(ChatUser)
class ChatUserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'username', 'nickname', 'is_active', 'stats_display', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user_id', 'username', 'nickname')
    readonly_fields = ('created_at', 'updated_at', 'stats_detail')
    list_editable = ('is_active',)
    list_per_page = 20

    fieldsets = (
        ('基本信息', {
            'fields': ('user_id', 'username', 'nickname', 'is_active')
        }),
        ('统计信息', {
            'fields': ('stats_detail',),
            'classes': ('collapse',)
        }),
        ('元数据', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def stats_display(self, obj):
        """显示用户数据统计"""
        prompts = obj.prompts.count()
        memories = obj.memories.count()
        messages = obj.messages.count()
        return format_html(
            '<span title="提示词/记忆/消息">📝{} | 🧠{} | 💬{}</span>',
            prompts, memories, messages
        )
    stats_display.short_description = '数据统计'

    def stats_detail(self, obj):
        """详细统计信息"""
        return format_html(
            '<div style="line-height: 2;">'
            '提示词数量: <strong>{}</strong><br/>'
            '记忆数量: <strong>{}</strong><br/>'
            '计划任务数量: <strong>{}</strong><br/>'
            '回复任务数量: <strong>{}</strong><br/>'
            '消息记录数量: <strong>{}</strong>'
            '</div>',
            obj.prompts.count(),
            obj.memories.count(),
            obj.planned_tasks.count(),
            obj.reply_tasks.count(),
            obj.messages.count()
        )
    stats_detail.short_description = '详细统计'

    actions = ['activate_users', 'deactivate_users']

    @admin.action(description='激活选中的用户')
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功激活 {updated} 个用户')

    @admin.action(description='禁用选中的用户')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功禁用 {updated} 个用户')


@admin.register(PromptLibrary)
class PromptLibraryAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'key', 'content_preview', 'is_active', 'updated_at')
    list_filter = ('user', 'category', 'is_active', 'created_at')
    search_fields = ('key', 'content', 'user__username', 'user__nickname')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)
    list_per_page = 20
    raw_id_fields = ('user',)

    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('基本信息', {
            'fields': ('category', 'key', 'is_active')
        }),
        ('提示词内容', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('元数据', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def content_preview(self, obj):
        return truncate_text(obj.content, 80)
    content_preview.short_description = '内容预览'

    actions = ['activate_prompts', 'deactivate_prompts']

    @admin.action(description='激活选中的提示词')
    def activate_prompts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功激活 {updated} 条提示词')

    @admin.action(description='禁用选中的提示词')
    def deactivate_prompts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功禁用 {updated} 条提示词')


@admin.register(MemoryLibrary)
class MemoryLibraryAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'memory_type', 'strength_display', 'weight', 'forget_time', 'created_at')
    list_filter = ('user', 'memory_type', 'strength', 'created_at')
    search_fields = ('title', 'content', 'user__username', 'user__nickname')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('weight',)
    list_per_page = 20
    date_hierarchy = 'created_at'
    raw_id_fields = ('user',)

    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('基本信息', {
            'fields': ('title', 'memory_type')
        }),
        ('记忆内容', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('记忆属性', {
            'fields': ('strength', 'weight', 'forget_time'),
        }),
        ('元数据', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def strength_display(self, obj):
        """可视化显示记忆强度"""
        color = '#4CAF50' if obj.strength >= 7 else '#FFC107' if obj.strength >= 4 else '#f44336'
        bars = '█' * obj.strength + '░' * (10 - obj.strength)
        return format_html(
            '<span style="color: {}; font-family: monospace;">{} ({})</span>',
            color, bars, obj.strength
        )
    strength_display.short_description = '强度'

    actions = ['strengthen_memories', 'clear_expired_memories']

    @admin.action(description='强化选中的记忆 (+1)')
    def strengthen_memories(self, request, queryset):
        for memory in queryset:
            memory.strengthen(delta=1)
        self.message_user(request, f'成功强化 {queryset.count()} 条记忆')

    @admin.action(description='清除已过期的记忆')
    def clear_expired_memories(self, request, queryset):
        from django.utils import timezone
        deleted = queryset.filter(forget_time__lt=timezone.now()).delete()[0]
        self.message_user(request, f'成功删除 {deleted} 条过期记忆')


@admin.register(PlannedTask)
class PlannedTaskAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'task_type', 'scheduled_time', 'status_badge', 'created_at')
    list_filter = ('user', 'task_type', 'status', 'scheduled_time')
    search_fields = ('title', 'description', 'user__username', 'user__nickname')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    list_per_page = 20
    date_hierarchy = 'scheduled_time'
    raw_id_fields = ('user',)

    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('任务信息', {
            'fields': ('title', 'description', 'task_type')
        }),
        ('执行信息', {
            'fields': ('scheduled_time', 'status'),
        }),
        ('元数据', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'pending': '#2196F3',
            'completed': '#4CAF50',
            'cancelled': '#9E9E9E',
            'failed': '#f44336',
        }
        color = colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = '状态'

    actions = ['mark_completed', 'mark_cancelled']

    @admin.action(description='标记为已完成')
    def mark_completed(self, request, queryset):
        for task in queryset.filter(status='pending'):
            task.mark_completed()
        self.message_user(request, f'已标记完成')

    @admin.action(description='标记为已取消')
    def mark_cancelled(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f'已取消 {updated} 个任务')


@admin.register(ReplyTask)
class ReplyTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'trigger_type', 'content_preview', 'scheduled_time', 'status_badge', 'retry_count')
    list_filter = ('user', 'trigger_type', 'status', 'scheduled_time')
    search_fields = ('content', 'user__username', 'user__nickname')
    readonly_fields = ('created_at', 'updated_at', 'executed_at', 'retry_count')
    list_per_page = 20
    date_hierarchy = 'scheduled_time'
    raw_id_fields = ('user',)

    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('任务信息', {
            'fields': ('trigger_type', 'status')
        }),
        ('回复内容', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('上下文', {
            'fields': ('context',),
            'classes': ('collapse',)
        }),
        ('执行信息', {
            'fields': ('scheduled_time', 'retry_count', 'error_message'),
        }),
        ('元数据', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'executed_at'),
            'classes': ('collapse',)
        }),
    )

    def content_preview(self, obj):
        return truncate_text(obj.content, 60)
    content_preview.short_description = '回复内容'

    def status_badge(self, obj):
        colors = {
            'pending': '#2196F3',
            'executing': '#FF9800',
            'completed': '#4CAF50',
            'failed': '#f44336',
            'cancelled': '#9E9E9E',
        }
        color = colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = '状态'

    actions = ['retry_failed_tasks', 'cancel_pending_tasks']

    @admin.action(description='重试失败的任务')
    def retry_failed_tasks(self, request, queryset):
        updated = queryset.filter(status='failed').update(status='pending', retry_count=0)
        self.message_user(request, f'已重置 {updated} 个失败任务')

    @admin.action(description='取消待执行的任务')
    def cancel_pending_tasks(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f'已取消 {updated} 个任务')


@admin.register(MessageRecord)
class MessageRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'message_type_badge', 'sender', 'receiver', 'content_preview', 'timestamp')
    list_filter = ('user', 'message_type', 'timestamp', 'sender')
    search_fields = ('content', 'sender', 'receiver', 'user__username', 'user__nickname')
    readonly_fields = ('created_at', 'reply_task')
    list_per_page = 30
    date_hierarchy = 'timestamp'
    raw_id_fields = ('user',)

    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('消息信息', {
            'fields': ('message_type', 'sender', 'receiver', 'timestamp')
        }),
        ('消息内容', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('关联信息', {
            'fields': ('reply_task',),
            'classes': ('collapse',)
        }),
        ('原始数据', {
            'fields': ('raw_data', 'metadata'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def content_preview(self, obj):
        return truncate_text(obj.content, 80)
    content_preview.short_description = '消息内容'

    def message_type_badge(self, obj):
        colors = {
            'received': '#2196F3',
            'sent': '#4CAF50',
        }
        icons = {
            'received': '📥',
            'sent': '📤',
        }
        color = colors.get(obj.message_type, '#9E9E9E')
        icon = icons.get(obj.message_type, '')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icon, obj.get_message_type_display()
        )
    message_type_badge.short_description = '类型'

    actions = ['export_messages']

    @admin.action(description='导出选中的消息')
    def export_messages(self, request, queryset):
        # 简单提示，实际可以实现 CSV 导出
        self.message_user(request, f'选中了 {queryset.count()} 条消息')
