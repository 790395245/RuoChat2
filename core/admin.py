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
    list_display = ('user_id', 'username', 'nickname', 'is_active', 'prompts_status', 'stats_display', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user_id', 'username', 'nickname')
    readonly_fields = ('created_at', 'updated_at', 'stats_detail', 'prompts_detail')
    list_editable = ('is_active', 'username', 'nickname')
    list_per_page = 20

    fieldsets = (
        ('基本信息', {
            'fields': ('user_id', 'username', 'nickname', 'is_active')
        }),
        ('提示词配置', {
            'fields': ('prompts_detail',),
            'description': '使用下方"初始化默认提示词"操作为用户创建所有提示词'
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

    def prompts_status(self, obj):
        """显示提示词配置状态"""
        from core.services.ai_service import DEFAULT_PROMPTS
        total_categories = len(DEFAULT_PROMPTS)
        configured = obj.prompts.filter(is_active=True).values('category').distinct().count()

        if configured >= total_categories:
            return format_html('<span style="color: green;">✓ 已配置 ({}/{})</span>', configured, total_categories)
        elif configured > 0:
            return format_html('<span style="color: orange;">⚠ 部分配置 ({}/{})</span>', configured, total_categories)
        else:
            return format_html('<span style="color: red;">✗ 未配置</span>')
    prompts_status.short_description = '提示词状态'

    def prompts_detail(self, obj):
        """显示提示词详细配置情况"""
        from core.services.ai_service import DEFAULT_PROMPTS

        category_names = {
            'character': '人物设定',
            'reply_decision': '回复决策',
            'memory_detection': '记忆检测',
            'daily_planning': '每日计划',
            'autonomous_message': '自主消息',
            'hotspot_judge': '热点判断',
        }

        html_parts = ['<table style="width: 100%; border-collapse: collapse;">']
        html_parts.append('<tr style="background: #f5f5f5;"><th style="padding: 8px; text-align: left;">类别</th><th style="padding: 8px; text-align: left;">状态</th><th style="padding: 8px; text-align: left;">操作</th></tr>')

        for category in DEFAULT_PROMPTS.keys():
            name = category_names.get(category, category)
            prompt = obj.prompts.filter(category=category, is_active=True).first()

            if prompt:
                status = '<span style="color: green;">✓ 已配置</span>'
                from django.urls import reverse
                edit_url = reverse('admin:core_promptlibrary_change', args=[prompt.pk])
                action = f'<a href="{edit_url}">编辑</a>'
            else:
                status = '<span style="color: red;">✗ 未配置</span>'
                action = '-'

            html_parts.append(f'<tr><td style="padding: 8px;">{name}</td><td style="padding: 8px;">{status}</td><td style="padding: 8px;">{action}</td></tr>')

        html_parts.append('</table>')
        html_parts.append('<p style="margin-top: 10px; color: #666;">提示：在列表页选中用户后，使用"初始化默认提示词"操作可一键创建所有提示词</p>')

        return mark_safe(''.join(html_parts))
    prompts_detail.short_description = '提示词配置详情'

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

    actions = [
        'activate_users', 'deactivate_users',
        'init_default_prompts', 'reset_prompts',
        'generate_daily_tasks', 'generate_autonomous_msgs'
    ]

    @admin.action(description='激活选中的用户')
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功激活 {updated} 个用户')

    @admin.action(description='禁用选中的用户')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功禁用 {updated} 个用户')

    @admin.action(description='初始化默认提示词（跳过已有）')
    def init_default_prompts(self, request, queryset):
        """为选中的用户初始化默认提示词"""
        from core.services.ai_service import DEFAULT_PROMPTS

        category_keys = {
            'character': 'default_character',
            'reply_decision': 'reply_decision_prompt',
            'memory_detection': 'memory_detection_prompt',
            'daily_planning': 'daily_planning_prompt',
            'autonomous_message': 'autonomous_message_prompt',
            'hotspot_judge': 'hotspot_judge_prompt',
        }

        total_created = 0
        users_updated = 0

        for user in queryset:
            user_created = 0
            for category, content in DEFAULT_PROMPTS.items():
                # 检查该用户是否已有该类别的提示词
                if not PromptLibrary.objects.filter(user=user, category=category).exists():
                    key = category_keys.get(category, f'{category}_default')
                    PromptLibrary.objects.create(
                        user=user,
                        category=category,
                        key=key,
                        content=content,
                        is_active=True,
                        metadata={'auto_generated': True}
                    )
                    user_created += 1
                    total_created += 1

            if user_created > 0:
                users_updated += 1

        self.message_user(
            request,
            f'成功为 {users_updated} 个用户创建了 {total_created} 条默认提示词'
        )

    @admin.action(description='重置提示词为默认值（覆盖已有）')
    def reset_prompts(self, request, queryset):
        """重置选中用户的提示词为默认值"""
        from core.services.ai_service import DEFAULT_PROMPTS

        category_keys = {
            'character': 'default_character',
            'reply_decision': 'reply_decision_prompt',
            'memory_detection': 'memory_detection_prompt',
            'daily_planning': 'daily_planning_prompt',
            'autonomous_message': 'autonomous_message_prompt',
            'hotspot_judge': 'hotspot_judge_prompt',
        }

        total_updated = 0

        for user in queryset:
            # 删除用户现有的提示词
            deleted = PromptLibrary.objects.filter(user=user).delete()[0]

            # 创建新的默认提示词
            for category, content in DEFAULT_PROMPTS.items():
                key = category_keys.get(category, f'{category}_default')
                PromptLibrary.objects.create(
                    user=user,
                    category=category,
                    key=key,
                    content=content,
                    is_active=True,
                    metadata={'auto_generated': True, 'reset': True}
                )
                total_updated += 1

        self.message_user(
            request,
            f'成功为 {queryset.count()} 个用户重置了提示词（共 {total_updated} 条）'
        )

    @admin.action(description='生成今日计划任务（AI）')
    def generate_daily_tasks(self, request, queryset):
        """为选中的用户生成今日计划任务"""
        from core.scheduler import generate_daily_planned_tasks

        success_count = 0
        error_users = []

        for user in queryset:
            try:
                generate_daily_planned_tasks(user)
                success_count += 1
            except Exception as e:
                error_users.append(f'{user.nickname or user.username}({e})')

        if error_users:
            self.message_user(
                request,
                f'成功为 {success_count} 个用户生成计划任务，{len(error_users)} 个失败: {", ".join(error_users)}',
                level='warning'
            )
        else:
            self.message_user(
                request,
                f'成功为 {success_count} 个用户生成今日计划任务'
            )

    @admin.action(description='生成今日自主消息（AI）')
    def generate_autonomous_msgs(self, request, queryset):
        """为选中的用户生成今日自主触发消息"""
        from core.scheduler import generate_autonomous_messages

        success_count = 0
        error_users = []

        for user in queryset:
            try:
                generate_autonomous_messages(user)
                success_count += 1
            except Exception as e:
                error_users.append(f'{user.nickname or user.username}({e})')

        if error_users:
            self.message_user(
                request,
                f'成功为 {success_count} 个用户生成自主消息，{len(error_users)} 个失败: {", ".join(error_users)}',
                level='warning'
            )
        else:
            self.message_user(
                request,
                f'成功为 {success_count} 个用户生成今日自主消息'
            )


@admin.register(PromptLibrary)
class PromptLibraryAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'key', 'content', 'variables_display', 'is_active', 'updated_at')
    list_filter = ('user', 'category', 'is_active', 'created_at')
    search_fields = ('key', 'content', 'user__username', 'user__nickname')
    readonly_fields = ('created_at', 'updated_at', 'variables_help', 'all_variables_reference')
    list_editable = ('is_active', 'category', 'key', 'content')
    list_per_page = 20
    raw_id_fields = ('user',)

    # 自定义列表页的字段显示样式
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'content':
            from django import forms
            kwargs['widget'] = forms.Textarea(attrs={
                'rows': 4,
                'cols': 60,
                'style': 'font-family: monospace; font-size: 12px;'
            })
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    # 所有变量的详细说明
    VARIABLE_DESCRIPTIONS = {
        '{sender}': '消息发送者的名称',
        '{message}': '用户发送的消息内容',
        '{context}': '相关上下文信息，包含：\n- 相关记忆\n- 最近消息\n- 今日计划\n- 待回复任务',
        '{current_time}': '当前时间，格式如：2024年01月15日 14:30:00 星期一',
        '{date}': '当前日期，格式如：2024年01月15日 星期一',
        '{title}': '热点话题的标题',
        '{content}': '热点话题的内容',
    }

    # 各类别提示词的可用变量说明
    CATEGORY_VARIABLES = {
        'character': [],
        'reply_decision': ['{current_time}', '{sender}', '{message}', '{context}'],
        'memory_detection': ['{sender}', '{message}', '{context}'],
        'daily_planning': ['{date}', '{context}'],
        'autonomous_message': ['{date}', '{context}'],
        'hotspot_judge': ['{title}', '{content}'],
        'message_merge': ['{current_time}', '{messages}'],
        'system': [],
        'template': [],
    }

    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('基本信息', {
            'fields': ('category', 'key', 'is_active'),
        }),
        ('变量参考', {
            'fields': ('all_variables_reference',),
            'classes': ('collapse',),
            'description': '展开查看所有可用变量的详细说明'
        }),
        ('提示词内容', {
            'fields': ('content', 'variables_help'),
            'classes': ('wide',),
        }),
        ('元数据', {
            'fields': ('metadata',),
            'classes': ('collapse',),
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def variables_display(self, obj):
        """显示该类别可用的变量"""
        variables = self.CATEGORY_VARIABLES.get(obj.category, [])
        if not variables:
            return format_html('<span style="color: #999;">无变量</span>')
        return format_html('<code style="font-size: 11px;">{}</code>', ', '.join(variables))
    variables_display.short_description = '可用变量'

    def all_variables_reference(self, obj):
        """显示所有变量的完整参考表"""
        html = '''
<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
<h4 style="margin-top: 0; color: #495057;">所有可用变量参考表</h4>
<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
<thead>
<tr style="background: #e9ecef;">
<th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; width: 120px;">变量</th>
<th style="padding: 10px; text-align: left; border: 1px solid #dee2e6;">说明</th>
<th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; width: 200px;">适用类别</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 10px; border: 1px solid #dee2e6;"><code style="background: #e2e3ff; padding: 2px 6px; border-radius: 3px;">{current_time}</code></td>
<td style="padding: 10px; border: 1px solid #dee2e6;">当前时间<br/><span style="font-size: 12px; color: #666;">格式：2024年01月15日 14:30:00 星期一</span></td>
<td style="padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">回复决策</td>
</tr>
<tr style="background: #fff;">
<td style="padding: 10px; border: 1px solid #dee2e6;"><code style="background: #fff3cd; padding: 2px 6px; border-radius: 3px;">{sender}</code></td>
<td style="padding: 10px; border: 1px solid #dee2e6;">消息发送者的名称</td>
<td style="padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">回复决策、记忆检测</td>
</tr>
<tr>
<td style="padding: 10px; border: 1px solid #dee2e6;"><code style="background: #fff3cd; padding: 2px 6px; border-radius: 3px;">{message}</code></td>
<td style="padding: 10px; border: 1px solid #dee2e6;">用户发送的消息内容</td>
<td style="padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">回复决策、记忆检测</td>
</tr>
<tr style="background: #fff;">
<td style="padding: 10px; border: 1px solid #dee2e6;"><code style="background: #d4edda; padding: 2px 6px; border-radius: 3px;">{context}</code></td>
<td style="padding: 10px; border: 1px solid #dee2e6;">
<strong>上下文信息</strong>，自动填充以下内容：<br/>
<ul style="margin: 5px 0 0 0; padding-left: 20px; font-size: 12px;">
<li>相关记忆（最近5条）</li>
<li>最近消息（最近10条）</li>
<li>今日计划任务</li>
<li>待回复任务</li>
</ul>
</td>
<td style="padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">回复决策、记忆检测、每日计划、自主消息</td>
</tr>
<tr>
<td style="padding: 10px; border: 1px solid #dee2e6;"><code style="background: #cce5ff; padding: 2px 6px; border-radius: 3px;">{date}</code></td>
<td style="padding: 10px; border: 1px solid #dee2e6;">当前日期<br/><span style="font-size: 12px; color: #666;">格式：2024年01月15日 星期一</span></td>
<td style="padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">每日计划、自主消息</td>
</tr>
<tr style="background: #fff;">
<td style="padding: 10px; border: 1px solid #dee2e6;"><code style="background: #f8d7da; padding: 2px 6px; border-radius: 3px;">{title}</code></td>
<td style="padding: 10px; border: 1px solid #dee2e6;">热点话题的标题</td>
<td style="padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">热点判断</td>
</tr>
<tr>
<td style="padding: 10px; border: 1px solid #dee2e6;"><code style="background: #f8d7da; padding: 2px 6px; border-radius: 3px;">{content}</code></td>
<td style="padding: 10px; border: 1px solid #dee2e6;">热点话题的详细内容</td>
<td style="padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">热点判断</td>
</tr>
</tbody>
</table>
<p style="margin-top: 15px; font-size: 12px; color: #6c757d;">
<strong>使用方法：</strong>在提示词内容中直接写入变量（如 <code>{sender}</code>），系统会在运行时自动替换为实际值。
</p>
</div>
'''
        return mark_safe(html)
    all_variables_reference.short_description = '变量参考表'

    def variables_help(self, obj):
        """根据类别显示具体的变量帮助"""
        category = obj.category if obj.pk else None

        # 类别说明和返回格式
        category_info = {
            'character': {
                'name': '人物设定',
                'desc': '描述 AI 的性格、身份、说话风格等。这个设定会作为所有 AI 决策的基础。',
                'variables': [],
                'return_format': '无需返回特定格式，直接描述人物即可',
                'example': '''你是一个温暖体贴的朋友，名叫小若。
你说话风格亲切自然，善于倾听，喜欢用简短的话语表达关心。
你记性很好，会记住和朋友聊过的重要事情。'''
            },
            'reply_decision': {
                'name': '回复决策',
                'desc': '决定如何回复用户消息，以及何时回复。',
                'variables': [
                    ('{current_time}', '当前时间（含日期、时分秒、星期）'),
                    ('{sender}', '消息发送者'),
                    ('{message}', '接收到的消息内容'),
                    ('{context}', '相关上下文（记忆、历史消息等）'),
                ],
                'return_format': 'JSON: {"content": "回复内容", "delay_minutes": 0}',
                'example': '''当前时间：{current_time}

根据消息决定回复：
- 发送者：{sender}
- 消息：{message}
- 上下文：{context}

请返回JSON格式的回复决策。'''
            },
            'memory_detection': {
                'name': '记忆检测',
                'desc': '判断对话中是否存在值得记忆的点。',
                'variables': [
                    ('{sender}', '消息发送者'),
                    ('{message}', '消息内容'),
                    ('{context}', '相关上下文'),
                ],
                'return_format': 'JSON: {"has_memory": true/false, "title": "标题", "content": "内容", "strength": 5, "weight": 1.0, "forget_days": 30}',
                'example': '''分析这条消息是否包含值得记忆的信息：
发送者：{sender}
消息：{message}'''
            },
            'daily_planning': {
                'name': '每日计划',
                'desc': '每日00:00执行，为用户生成全天计划任务。',
                'variables': [
                    ('{date}', '今天的日期'),
                    ('{context}', '上下文（记忆、历史计划等）'),
                ],
                'return_format': 'JSON: {"tasks": [{"title": "标题", "description": "描述", "task_type": "daily", "time": "09:00"}]}',
                'example': '''今天是{date}，请根据以下上下文生成今日计划：
{context}'''
            },
            'autonomous_message': {
                'name': '自主消息',
                'desc': '每日00:05执行，生成需要主动发送的关怀消息。',
                'variables': [
                    ('{date}', '今天的日期'),
                    ('{context}', '上下文（计划任务、记忆等）'),
                ],
                'return_format': 'JSON: {"messages": [{"content": "消息内容", "time": "09:00"}]}',
                'example': '''今天是{date}，请生成今日的主动关怀消息：
{context}'''
            },
            'hotspot_judge': {
                'name': '热点判断',
                'desc': '判断热点话题是否值得记忆。',
                'variables': [
                    ('{title}', '热点标题'),
                    ('{content}', '热点内容'),
                ],
                'return_format': '直接回答"是"或"否"',
                'example': '''判断以下热点是否值得记忆：
标题：{title}
内容：{content}'''
            },
        }

        info = category_info.get(category, None)

        if not info:
            return mark_safe('''
<div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
<p style="margin: 0;"><strong>提示：</strong>请先选择类别，然后保存后刷新页面查看该类别的变量说明。</p>
</div>
''')

        # 构建变量表格
        var_rows = ''
        if info['variables']:
            for var, desc in info['variables']:
                var_rows += f'''
<tr>
<td style="padding: 8px; border: 1px solid #dee2e6;"><code style="background: #e7f3ff; padding: 2px 8px; border-radius: 3px; font-weight: bold;">{var}</code></td>
<td style="padding: 8px; border: 1px solid #dee2e6;">{desc}</td>
</tr>'''
            var_table = f'''
<h5 style="margin: 15px 0 10px 0;">可用变量：</h5>
<table style="width: 100%; border-collapse: collapse;">
<thead><tr style="background: #f8f9fa;"><th style="padding: 8px; text-align: left; border: 1px solid #dee2e6;">变量</th><th style="padding: 8px; text-align: left; border: 1px solid #dee2e6;">说明</th></tr></thead>
<tbody>{var_rows}</tbody>
</table>'''
        else:
            var_table = '<p style="color: #666; margin: 10px 0;"><em>此类别无需使用变量</em></p>'

        html = f'''
<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6; margin-top: 10px;">
<h4 style="margin: 0 0 10px 0; color: #495057; border-bottom: 2px solid #007bff; padding-bottom: 8px;">
{info['name']}
</h4>
<p style="margin: 10px 0; color: #666;">{info['desc']}</p>

{var_table}

<h5 style="margin: 15px 0 10px 0;">返回格式：</h5>
<code style="background: #e9ecef; padding: 8px 12px; border-radius: 4px; display: block; font-size: 12px;">{info['return_format']}</code>

<h5 style="margin: 15px 0 10px 0;">示例模板：</h5>
<pre style="background: #2d2d2d; color: #f8f8f2; padding: 12px; border-radius: 4px; font-size: 12px; overflow-x: auto; white-space: pre-wrap;">{info['example']}</pre>
</div>
'''
        return mark_safe(html)
    variables_help.short_description = '当前类别变量说明'

    actions = ['activate_prompts', 'deactivate_prompts', 'duplicate_prompts', 'create_default_prompts']

    @admin.action(description='激活选中的提示词')
    def activate_prompts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功激活 {updated} 条提示词')

    @admin.action(description='禁用选中的提示词')
    def deactivate_prompts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功禁用 {updated} 条提示词')

    @admin.action(description='复制选中的提示词')
    def duplicate_prompts(self, request, queryset):
        for prompt in queryset:
            prompt.pk = None
            prompt.key = f"{prompt.key}_copy"
            prompt.save()
        self.message_user(request, f'成功复制 {queryset.count()} 条提示词')

    @admin.action(description='为选中用户创建默认提示词')
    def create_default_prompts(self, request, queryset):
        from core.services.ai_service import DEFAULT_PROMPTS

        created_count = 0
        for prompt in queryset:
            user = prompt.user
            for category, content in DEFAULT_PROMPTS.items():
                key = PromptLibrary.PROMPT_KEYS.get(category, f'{category}_default')
                if not PromptLibrary.objects.filter(user=user, category=category).exists():
                    PromptLibrary.objects.create(
                        user=user,
                        category=category,
                        key=key,
                        content=content,
                        is_active=True
                    )
                    created_count += 1
        self.message_user(request, f'成功创建 {created_count} 条默认提示词')


@admin.register(MemoryLibrary)
class MemoryLibraryAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'memory_type', 'strength_display', 'weight', 'forget_time', 'created_at')
    list_filter = ('user', 'memory_type', 'strength', 'created_at')
    search_fields = ('title', 'content', 'user__username', 'user__nickname')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('weight', 'memory_type', 'forget_time')
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
    list_display = ('user', 'title', 'task_type', 'scheduled_time', 'status_badge', 'status', 'created_at')
    list_filter = ('user', 'task_type', 'status', 'scheduled_time')
    search_fields = ('title', 'description', 'user__username', 'user__nickname')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    list_editable = ('status', 'task_type', 'scheduled_time')
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
    list_display = ('id', 'user', 'trigger_type', 'content_preview', 'scheduled_time', 'status_badge', 'status', 'retry_count')
    list_filter = ('user', 'trigger_type', 'status', 'scheduled_time')
    search_fields = ('content', 'user__username', 'user__nickname')
    readonly_fields = ('created_at', 'updated_at', 'executed_at', 'retry_count')
    list_editable = ('status', 'trigger_type', 'scheduled_time')
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
