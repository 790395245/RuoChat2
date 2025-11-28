import logging
from typing import Optional
from datetime import datetime
from django.utils import timezone

from core.models import ReplyTask, MessageRecord

logger = logging.getLogger(__name__)


def execute_reply_task(task: ReplyTask) -> bool:
    """
    执行回复任务

    阶段4：回复任务触发与发送
    1. 触发：回复任务计划触发
    2. 执行：发送消息
    3. 记录：发送的消息 → 写入消息记录库
    4. 更新任务状态

    Args:
        task: 回复任务对象

    Returns:
        bool: 是否执行成功
    """
    try:
        logger.info(f"开始执行回复任务 #{task.id}: {task.content[:50]}...")

        # 标记为执行中
        task.mark_executing()

        # 发送消息
        success = _send_message(task)

        if success:
            # 标记为已完成
            task.mark_completed()

            # 记录消息到数据库
            _record_sent_message(task)

            logger.info(f"回复任务 #{task.id} 执行成功")
            return True
        else:
            # 标记为失败
            task.mark_failed("消息发送失败")

            # 如果重试次数未超过限制，重新标记为待执行
            if task.retry_count < 3:
                task.status = 'pending'
                task.save(update_fields=['status'])
                logger.warning(f"回复任务 #{task.id} 发送失败，将重试 (第{task.retry_count}次)")
            else:
                logger.error(f"回复任务 #{task.id} 重试次数已达上限，放弃执行")

            return False

    except Exception as e:
        logger.error(f"执行回复任务 #{task.id} 失败: {e}", exc_info=True)
        task.mark_failed(str(e))
        return False


def _send_message(task: ReplyTask) -> bool:
    """
    发送消息

    Args:
        task: 回复任务对象

    Returns:
        bool: 是否发送成功
    """
    try:
        # 获取 Webhook 服务
        from core.services.webhook_service import get_webhook_service

        webhook = get_webhook_service()

        if not webhook.enabled:
            logger.warning("Webhook 服务未启用，无法发送消息")
            return False

        # 确定接收者（用户ID列表）
        user_ids = _determine_receiver(task)

        # 发送消息
        success = webhook.send_message(task.content, user_ids)

        return success

    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        return False


def _determine_receiver(task: ReplyTask) -> Optional[list]:
    """
    确定消息接收者（用户ID列表）

    Args:
        task: 回复任务对象

    Returns:
        Optional[list]: 接收者用户ID列表，None表示使用默认配置
    """
    try:
        # 从任务上下文中获取接收者信息
        context = task.context or {}

        if task.trigger_type == 'user':
            # 用户触发的任务，尝试获取原发送者的用户ID
            user_id = context.get('user_id')
            if user_id:
                return [int(user_id)] if isinstance(user_id, (str, int)) else None

        # 自主触发的任务或未找到特定用户ID时，使用默认用户ID列表
        # webhook_service 会自动使用 WEBHOOK_USER_IDS 配置
        return None

    except Exception as e:
        logger.error(f"确定接收者失败: {e}")
        return None


def _record_sent_message(task: ReplyTask):
    """
    记录发送的消息到数据库

    Args:
        task: 回复任务对象
    """
    try:
        context = task.context or {}
        receiver = _determine_receiver(task)

        MessageRecord.objects.create(
            user=task.user,  # 关联到任务所属用户
            message_type='sent',
            sender='我',  # 当前用户
            receiver=str(receiver) if receiver else '未知',
            content=task.content,
            timestamp=timezone.now(),
            reply_task=task,
            raw_data={
                'trigger_type': task.trigger_type,
                'task_id': task.id,
            },
        )

        logger.info(f"消息已记录到数据库（用户: {task.user}）：{task.content[:50]}...")

    except Exception as e:
        logger.error(f"记录发送消息失败: {e}")


def execute_batch_reply_tasks(max_tasks: int = 10):
    """
    批量执行待回复任务

    Args:
        max_tasks: 最多执行的任务数量
    """
    try:
        from core.models import ReplyTask

        # 查找到期的待执行任务（只处理活跃用户的任务）
        now = timezone.now()
        pending_tasks = ReplyTask.objects.filter(
            status='pending',
            scheduled_time__lte=now,
            user__is_active=True
        ).select_related('user').order_by('scheduled_time')[:max_tasks]

        if not pending_tasks.exists():
            logger.debug("没有待执行的回复任务")
            return

        logger.info(f"开始批量执行 {pending_tasks.count()} 个回复任务")

        success_count = 0
        failed_count = 0

        for task in pending_tasks:
            try:
                if execute_reply_task(task):
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"执行任务 #{task.id} (用户: {task.user}) 失败: {e}")
                failed_count += 1

        logger.info(f"批量执行完成：成功 {success_count} 个，失败 {failed_count} 个")

    except Exception as e:
        logger.error(f"批量执行回复任务失败: {e}", exc_info=True)
