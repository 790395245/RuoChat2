from django.db import models
from django.utils import timezone


class PromptLibrary(models.Model):
    """提示词库 - 存储人物设定和系统提示词"""

    CATEGORY_CHOICES = [
        ('character', '人物设定'),
        ('system', '系统提示词'),
        ('template', '回复模板'),
    ]

    category = models.CharField('类别', max_length=50, choices=CATEGORY_CHOICES, db_index=True)
    key = models.CharField('唯一标识', max_length=100, unique=True)
    content = models.TextField('提示词内容')
    is_active = models.BooleanField('是否激活', default=True, db_index=True)
    metadata = models.JSONField('元数据', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'prompt_library'
        verbose_name = '提示词库'
        verbose_name_plural = '提示词库'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return f"{self.get_category_display()} - {self.key}"


class MemoryLibrary(models.Model):
    """记忆库 - 存储热点和用户记忆点"""

    MEMORY_TYPE_CHOICES = [
        ('hotspot', '热点话题'),
        ('user_memory', '用户记忆点'),
        ('important_event', '重要事件'),
    ]

    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    memory_type = models.CharField('记忆类型', max_length=50, choices=MEMORY_TYPE_CHOICES, db_index=True)
    strength = models.IntegerField('强度', default=5, help_text='记忆强度 1-10')
    weight = models.FloatField('权重', default=1.0, help_text='记忆权重，影响检索优先级')
    forget_time = models.DateTimeField('遗忘时间', null=True, blank=True, help_text='超过此时间后记忆衰减')
    metadata = models.JSONField('元数据', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'memory_library'
        verbose_name = '记忆库'
        verbose_name_plural = '记忆库'
        ordering = ['-weight', '-strength', '-created_at']
        indexes = [
            models.Index(fields=['memory_type', '-weight']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.get_memory_type_display()} - {self.title}"

    def strengthen(self, delta=1):
        """强化记忆"""
        self.strength = min(10, self.strength + delta)
        self.weight = min(10.0, self.weight + delta * 0.1)
        self.save(update_fields=['strength', 'weight', 'updated_at'])

    def is_forgotten(self):
        """检查是否已遗忘"""
        if self.forget_time is None:
            return False
        return timezone.now() > self.forget_time


class PlannedTask(models.Model):
    """计划任务库 - 存储全天计划任务"""

    TASK_TYPE_CHOICES = [
        ('daily', '日常任务'),
        ('special', '特殊任务'),
        ('reminder', '提醒任务'),
    ]

    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('failed', '执行失败'),
    ]

    title = models.CharField('任务标题', max_length=200)
    description = models.TextField('任务描述', blank=True)
    task_type = models.CharField('任务类型', max_length=50, choices=TASK_TYPE_CHOICES, db_index=True)
    scheduled_time = models.DateTimeField('计划时间', db_index=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    metadata = models.JSONField('元数据', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)

    class Meta:
        db_table = 'planned_task'
        verbose_name = '计划任务'
        verbose_name_plural = '计划任务'
        ordering = ['scheduled_time']
        indexes = [
            models.Index(fields=['status', 'scheduled_time']),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    def mark_completed(self):
        """标记为已完成"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])


class ReplyTask(models.Model):
    """回复任务库 - 存储待回复任务"""

    TRIGGER_TYPE_CHOICES = [
        ('user', '用户触发'),
        ('autonomous', '自主触发'),
    ]

    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('executing', '执行中'),
        ('completed', '已完成'),
        ('failed', '执行失败'),
        ('cancelled', '已取消'),
    ]

    trigger_type = models.CharField('触发类型', max_length=20, choices=TRIGGER_TYPE_CHOICES, db_index=True)
    content = models.TextField('回复内容')
    context = models.JSONField('上下文信息', default=dict, blank=True, help_text='AI决策时的上下文')
    scheduled_time = models.DateTimeField('计划回复时间', db_index=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    retry_count = models.IntegerField('重试次数', default=0)
    error_message = models.TextField('错误信息', blank=True)
    metadata = models.JSONField('元数据', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    executed_at = models.DateTimeField('执行时间', null=True, blank=True)

    class Meta:
        db_table = 'reply_task'
        verbose_name = '回复任务'
        verbose_name_plural = '回复任务'
        ordering = ['scheduled_time']
        indexes = [
            models.Index(fields=['status', 'scheduled_time']),
            models.Index(fields=['trigger_type', 'status']),
        ]

    def __str__(self):
        return f"{self.get_trigger_type_display()} - {self.scheduled_time.strftime('%Y-%m-%d %H:%M')}"

    def mark_executing(self):
        """标记为执行中"""
        self.status = 'executing'
        self.save(update_fields=['status', 'updated_at'])

    def mark_completed(self):
        """标记为已完成"""
        self.status = 'completed'
        self.executed_at = timezone.now()
        self.save(update_fields=['status', 'executed_at', 'updated_at'])

    def mark_failed(self, error_message=''):
        """标记为失败"""
        self.status = 'failed'
        self.error_message = error_message
        self.retry_count += 1
        self.save(update_fields=['status', 'error_message', 'retry_count', 'updated_at'])


class MessageRecord(models.Model):
    """消息记录库 - 存储所有消息交互"""

    MESSAGE_TYPE_CHOICES = [
        ('received', '接收消息'),
        ('sent', '发送消息'),
    ]

    message_type = models.CharField('消息类型', max_length=20, choices=MESSAGE_TYPE_CHOICES, db_index=True)
    sender = models.CharField('发送者', max_length=200, db_index=True)
    receiver = models.CharField('接收者', max_length=200, db_index=True)
    content = models.TextField('消息内容')
    timestamp = models.DateTimeField('消息时间', db_index=True)
    raw_data = models.JSONField('原始数据', default=dict, blank=True, help_text='消息的原始JSON数据')
    reply_task = models.ForeignKey(
        ReplyTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
        verbose_name='关联回复任务'
    )
    metadata = models.JSONField('元数据', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'message_record'
        verbose_name = '消息记录'
        verbose_name_plural = '消息记录'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['message_type', '-timestamp']),
            models.Index(fields=['sender', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.get_message_type_display()} - {self.sender} -> {self.receiver}"
