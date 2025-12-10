import logging
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone

if TYPE_CHECKING:
    from core.models import ChatUser

logger = logging.getLogger(__name__)


class ContextService:
    """上下文检索和聚合服务 - Vertical Container实现"""

    def get_user_message_context(self, user: 'ChatUser', sender: str, limit: int = 10) -> Dict:
        """
        获取用户消息处理所需的上下文

        Args:
            user: 聊天用户对象
            sender: 消息发送者
            limit: 每类数据的限制数量

        Returns:
            Dict: 聚合的上下文信息
        """
        from core.models import MemoryLibrary, MessageRecord, PlannedTask, ReplyTask

        context = {}

        # 1. 检索该用户相关的记忆（根据权重和时间排序，过滤已遗忘的记忆）
        memories = MemoryLibrary.objects.filter(
            user=user
        ).filter(
            Q(forget_time__isnull=True) | Q(forget_time__gt=timezone.now())
        ).order_by('-weight', '-strength')[:limit]

        context['memories'] = [
            {
                'id': m.id,
                'title': m.title,
                'content': m.content,
                'type': m.memory_type,
                'strength': m.strength,
                'weight': m.weight,
            }
            for m in memories
        ]

        # 2. 检索该用户的历史消息（包含发送和接收的所有消息）
        recent_messages = MessageRecord.objects.filter(
            user=user
        ).order_by('-timestamp')[:limit]

        context['recent_messages'] = [
            {
                'id': m.id,
                'type': m.message_type,
                'sender': m.sender,
                'receiver': m.receiver,
                'content': m.content,
                'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for m in recent_messages
        ]

        # 3. 检索该用户今日计划任务
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        planned_tasks = PlannedTask.objects.filter(
            user=user,
            scheduled_time__gte=today_start,
            scheduled_time__lt=today_end,
            status='pending'
        ).order_by('scheduled_time')[:limit]

        context['planned_tasks'] = [
            {
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'task_type': t.task_type,
                'scheduled_time': timezone.localtime(t.scheduled_time).strftime('%Y-%m-%d %H:%M:%S'),
            }
            for t in planned_tasks
        ]

        # 4. 检索该用户待回复任务
        reply_tasks = ReplyTask.objects.filter(
            user=user,
            status='pending',
            scheduled_time__gte=timezone.now()
        ).order_by('scheduled_time')[:limit]

        context['reply_tasks'] = [
            {
                'id': t.id,
                'trigger_type': t.trigger_type,
                'content': t.content,
                'scheduled_time': timezone.localtime(t.scheduled_time).strftime('%Y-%m-%d %H:%M:%S'),
            }
            for t in reply_tasks
        ]

        logger.info(f"为用户 {user} 聚合了上下文：{len(context['memories'])}条记忆，{len(context['recent_messages'])}条消息")
        return context

    def get_daily_planning_context(self, user: 'ChatUser', limit: int = 20) -> Dict:
        """
        获取生成每日计划所需的上下文（00:00任务使用）

        Args:
            user: 聊天用户对象
            limit: 每类数据的限制数量

        Returns:
            Dict: 聚合的上下文信息
        """
        from core.models import MemoryLibrary, PlannedTask

        context = {}

        # 1. 检索该用户高权重记忆
        memories = MemoryLibrary.objects.filter(
            user=user
        ).filter(
            Q(forget_time__isnull=True) | Q(forget_time__gt=timezone.now())
        ).filter(weight__gte=5.0).order_by('-weight', '-strength')[:limit]

        context['memories'] = [
            {
                'id': m.id,
                'title': m.title,
                'content': m.content,
                'type': m.memory_type,
                'strength': m.strength,
                'weight': m.weight,
            }
            for m in memories
        ]

        # 2. 检索该用户昨天的计划任务（作为参考）
        yesterday_start = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = yesterday_start + timedelta(days=1)

        yesterday_tasks = PlannedTask.objects.filter(
            user=user,
            scheduled_time__gte=yesterday_start,
            scheduled_time__lt=yesterday_end
        ).order_by('scheduled_time')[:limit]

        context['yesterday_tasks'] = [
            {
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'task_type': t.task_type,
                'status': t.status,
            }
            for t in yesterday_tasks
        ]

        logger.info(f"为用户 {user} 聚合每日计划上下文：{len(context['memories'])}条记忆，{len(context['yesterday_tasks'])}条昨日任务")
        return context

    def get_autonomous_message_context(self, user: 'ChatUser', limit: int = 20) -> Dict:
        """
        获取生成自主消息所需的上下文（00:05任务使用）

        Args:
            user: 聊天用户对象
            limit: 每类数据的限制数量

        Returns:
            Dict: 聚合的上下文信息
        """
        from core.models import MemoryLibrary, MessageRecord, PlannedTask, ReplyTask

        context = {}

        # 1. 检索该用户重要记忆
        memories = MemoryLibrary.objects.filter(
            user=user
        ).filter(
            Q(forget_time__isnull=True) | Q(forget_time__gt=timezone.now())
        ).filter(weight__gte=3.0).order_by('-weight', '-strength')[:limit]

        context['memories'] = [
            {
                'id': m.id,
                'title': m.title,
                'content': m.content,
                'type': m.memory_type,
                'strength': m.strength,
                'weight': m.weight,
            }
            for m in memories
        ]

        # 2. 检索该用户今日计划任务
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        planned_tasks = PlannedTask.objects.filter(
            user=user,
            scheduled_time__gte=today_start,
            scheduled_time__lt=today_end,
            status='pending'
        ).order_by('scheduled_time')[:limit]

        context['planned_tasks'] = [
            {
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'task_type': t.task_type,
                'scheduled_time': timezone.localtime(t.scheduled_time).strftime('%Y-%m-%d %H:%M:%S'),
            }
            for t in planned_tasks
        ]

        # 3. 检索该用户近期消息记录
        recent_messages = MessageRecord.objects.filter(
            user=user,
            timestamp__gte=datetime.now() - timedelta(days=3)
        ).order_by('-timestamp')[:limit]

        context['recent_messages'] = [
            {
                'id': m.id,
                'type': m.message_type,
                'sender': m.sender,
                'receiver': m.receiver,
                'content': m.content,
                'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for m in recent_messages
        ]

        # 4. 检索该用户已存在的待回复任务（避免重复）
        existing_reply_tasks = ReplyTask.objects.filter(
            user=user,
            status='pending',
            scheduled_time__gte=today_start,
            scheduled_time__lt=today_end
        ).order_by('scheduled_time')[:limit]

        context['existing_reply_tasks'] = [
            {
                'id': t.id,
                'content': t.content,
                'scheduled_time': timezone.localtime(t.scheduled_time).strftime('%Y-%m-%d %H:%M:%S'),
            }
            for t in existing_reply_tasks
        ]

        logger.info(f"为用户 {user} 聚合自主消息上下文：{len(context['memories'])}条记忆，{len(context['planned_tasks'])}条计划")
        return context

    def get_reply_execution_context(self, task_id: int) -> Dict:
        """
        获取回复任务执行所需的上下文

        Args:
            task_id: 回复任务ID

        Returns:
            Dict: 聚合的上下文信息
        """
        from core.models import ReplyTask, MessageRecord

        context = {}

        try:
            task = ReplyTask.objects.get(id=task_id)
            user = task.user

            # 包含任务自身的上下文
            context['task_context'] = task.context

            # 检索该用户相关历史消息
            if task.trigger_type == 'user':
                # 如果是用户触发，检索与用户的对话历史
                recent_messages = MessageRecord.objects.filter(
                    user=user
                ).order_by('-timestamp')[:10]

                context['recent_messages'] = [
                    {
                        'type': m.message_type,
                        'sender': m.sender,
                        'receiver': m.receiver,
                        'content': m.content,
                        'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    }
                    for m in recent_messages
                ]

            logger.info(f"为回复任务 {task_id} (用户: {user}) 聚合了上下文")

        except ReplyTask.DoesNotExist:
            logger.error(f"回复任务 {task_id} 不存在")

        return context

    def search_memories_by_keyword(self, user: 'ChatUser', keyword: str, limit: int = 10) -> List[Dict]:
        """
        根据关键词搜索记忆

        Args:
            user: 聊天用户对象
            keyword: 搜索关键词
            limit: 结果数量限制

        Returns:
            List[Dict]: 匹配的记忆列表
        """
        from core.models import MemoryLibrary

        memories = MemoryLibrary.objects.filter(
            user=user
        ).filter(
            Q(title__icontains=keyword) | Q(content__icontains=keyword)
        ).filter(
            Q(forget_time__isnull=True) | Q(forget_time__gt=timezone.now())
        ).order_by('-weight', '-strength')[:limit]

        return [
            {
                'id': m.id,
                'title': m.title,
                'content': m.content,
                'type': m.memory_type,
                'strength': m.strength,
                'weight': m.weight,
            }
            for m in memories
        ]

    def get_emotion_context(self, user: 'ChatUser', hours: int = 24) -> Dict:
        """
        获取AI助手情绪相关上下文

        Args:
            user: 聊天用户对象
            hours: 查询多少小时内的情绪记录

        Returns:
            Dict: 情绪上下文信息
                - current_emotion: AI助手当前情绪状态
                - emotion_trend: AI助手近期情绪趋势
                - emotion_stats: 情绪统计
        """
        from core.models import EmotionRecord
        from datetime import timedelta
        from django.db.models import Avg, Count

        context = {}
        cutoff = timezone.now() - timedelta(hours=hours)

        # 1. 获取当前情绪状态（最新一条记录）
        current_emotion = EmotionRecord.objects.filter(user=user).first()
        if current_emotion:
            context['current_emotion'] = {
                'emotion_type': current_emotion.emotion_type,
                'emotion_type_display': current_emotion.get_emotion_type_display(),
                'intensity': current_emotion.intensity,
                'description': current_emotion.description,
                'trigger_source': current_emotion.trigger_source,
                'created_at': current_emotion.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        else:
            context['current_emotion'] = None

        # 2. 获取近期情绪趋势
        emotion_records = EmotionRecord.objects.filter(
            user=user,
            created_at__gte=cutoff
        ).order_by('created_at')[:20]

        context['emotion_trend'] = [
            {
                'emotion_type': e.emotion_type,
                'intensity': e.intensity,
                'trigger_source': e.trigger_source,
                'created_at': e.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for e in emotion_records
        ]

        # 3. 情绪统计
        emotion_stats = EmotionRecord.objects.filter(
            user=user,
            created_at__gte=cutoff
        ).values('emotion_type').annotate(
            count=Count('id'),
            avg_intensity=Avg('intensity')
        ).order_by('-count')

        context['emotion_stats'] = list(emotion_stats)

        # 4. 计算主导情绪
        if context['emotion_stats']:
            dominant = context['emotion_stats'][0]
            context['dominant_emotion'] = {
                'emotion_type': dominant['emotion_type'],
                'count': dominant['count'],
                'avg_intensity': round(dominant['avg_intensity'], 1) if dominant['avg_intensity'] else 0,
            }
        else:
            context['dominant_emotion'] = None

        logger.info(f"为用户 {user} 聚合AI情绪上下文：{len(context['emotion_trend'])}条记录")
        return context

    def get_message_merge_context(self, user: 'ChatUser') -> Dict:
        """
        获取消息合并所需的上下文（计划任务和情绪状态）

        Args:
            user: 聊天用户对象

        Returns:
            Dict: 聚合的上下文信息
        """
        from core.models import PlannedTask

        context = {}

        # 1. 检索该用户今日计划任务
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        planned_tasks = PlannedTask.objects.filter(
            user=user,
            scheduled_time__gte=today_start,
            scheduled_time__lt=today_end
        ).order_by('scheduled_time')

        context['planned_tasks'] = [
            {
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'task_type': t.task_type,
                'status': t.status,
                'scheduled_time': timezone.localtime(t.scheduled_time).strftime('%Y-%m-%d %H:%M:%S'),
            }
            for t in planned_tasks
        ]

        # 2. 获取情绪上下文
        emotion_context = self.get_emotion_context(user, hours=24)
        context['emotion'] = emotion_context

        logger.info(f"为用户 {user} 聚合消息合并上下文：{len(context['planned_tasks'])}条计划任务")
        return context
