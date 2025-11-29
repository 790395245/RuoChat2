import logging
from typing import Dict, Optional, TYPE_CHECKING
from datetime import datetime
from django.utils import timezone

from core.models import MessageRecord, ReplyTask, MemoryLibrary, ChatUser
from core.services.ai_service import AIService
from core.services.context_service import ContextService

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MessageHandler:
    """用户消息触发处理流程"""

    def __init__(self):
        self.ai_service = AIService()
        self.context_service = ContextService()

    def handle_user_message(
        self,
        user: ChatUser,
        sender: str,
        content: str,
        msg_type: str = 'text',
        raw_msg: Optional[Dict] = None
    ):
        """
        处理用户消息的完整流程

        阶段2：用户消息处理流程
        1. 接收消息 → 写入消息记录库
        2. 检索并添加上下文（从Vertical Container）
        3. AI判断：回复时间 + 回复内容 → 写入回复任务库
        4. AI判断：是否存在记忆点 → 写入/强化记忆库
        5. 同步修改当日其他自动回复任务

        Args:
            user: 聊天用户对象
            sender: 消息发送者
            content: 消息内容
            msg_type: 消息类型
            raw_msg: 原始消息数据（包含 user_id 等）
        """
        try:
            logger.info(f"开始处理用户 {user} 的消息：{sender} - {content[:50]}")

            # 步骤1：消息已在webhook_service中写入消息记录库

            # 步骤2：检索并添加上下文
            context = self.context_service.get_user_message_context(user, sender)

            # 步骤3：AI判断回复内容和回复时间
            reply_content, scheduled_time = self.ai_service.decide_reply_content_and_timing(
                user=user,
                message_content=content,
                sender=sender,
                context=context
            )

            # 从原始消息中提取 user_id（用于 webhook 回复）
            webhook_user_id = None
            if raw_msg:
                webhook_user_id = raw_msg.get('user_id')

            # 创建回复任务
            reply_task = ReplyTask.objects.create(
                user=user,
                trigger_type='user',
                content=reply_content,
                context={
                    'sender': sender,
                    'user_id': webhook_user_id,  # 保存用户ID用于回复
                    'original_message': content,
                    'msg_type': msg_type,
                },
                scheduled_time=scheduled_time,
                status='pending',
                metadata={
                    'raw_msg': raw_msg or {},
                }
            )

            logger.info(f"创建回复任务 #{reply_task.id}：{reply_content[:50]}... (计划时间: {scheduled_time})")

            # 步骤4：AI判断是否存在记忆点
            memory_info = self.ai_service.detect_memory_points(
                user=user,
                message_content=content,
                sender=sender,
                context=context
            )

            if memory_info:
                # 检查该用户是否存在类似的记忆（标题相同或内容相似）
                existing_memory = MemoryLibrary.objects.filter(
                    user=user,
                    title=memory_info['title']
                ).first()

                if existing_memory:
                    # 强化已有记忆
                    existing_memory.strengthen(delta=1)
                    logger.info(f"强化记忆: {existing_memory.title} (强度: {existing_memory.strength})")
                else:
                    # 创建新记忆
                    new_memory = MemoryLibrary.objects.create(
                        user=user,
                        title=memory_info['title'],
                        content=memory_info['content'],
                        memory_type='user_memory',
                        strength=memory_info['strength'],
                        weight=memory_info['weight'],
                        forget_time=memory_info['forget_time'],
                    )
                    logger.info(f"创建新记忆: {new_memory.title}")

            # 步骤5：同步修改当日其他自动回复任务
            self._sync_autonomous_tasks(user, reply_task)

            logger.info(f"用户 {user} 的消息处理完成: {sender}")

        except Exception as e:
            logger.error(f"处理用户消息失败: {e}", exc_info=True)

    def _sync_autonomous_tasks(self, user: ChatUser, new_reply_task: ReplyTask):
        """
        同步修改当日其他自动回复任务

        当创建新的回复任务时，需要检查是否与现有的自主触发任务冲突，
        避免在相近的时间发送多条消息

        Args:
            user: 聊天用户对象
            new_reply_task: 新创建的回复任务
        """
        try:
            from datetime import timedelta

            # 获取新任务计划时间前后15分钟的时间窗口
            time_window_start = new_reply_task.scheduled_time - timedelta(minutes=15)
            time_window_end = new_reply_task.scheduled_time + timedelta(minutes=15)

            # 查找该用户时间窗口内的其他待执行任务
            conflicting_tasks = ReplyTask.objects.filter(
                user=user,
                trigger_type='autonomous',
                status='pending',
                scheduled_time__gte=time_window_start,
                scheduled_time__lte=time_window_end
            ).exclude(id=new_reply_task.id)

            if conflicting_tasks.exists():
                logger.info(f"发现 {conflicting_tasks.count()} 个可能冲突的自主任务")

                for task in conflicting_tasks:
                    # 延迟冲突的自主任务30分钟
                    new_time = task.scheduled_time + timedelta(minutes=30)
                    task.scheduled_time = new_time
                    task.save(update_fields=['scheduled_time'])

                    logger.info(f"调整自主任务 #{task.id} 时间至 {new_time}")

        except Exception as e:
            logger.error(f"同步自主任务失败: {e}")


# 全局单例
_message_handler_instance = None


def get_message_handler() -> MessageHandler:
    """获取消息处理器单例"""
    global _message_handler_instance
    if _message_handler_instance is None:
        _message_handler_instance = MessageHandler()
    return _message_handler_instance
