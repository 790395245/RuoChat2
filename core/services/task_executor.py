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
        # 获取微信服务
        from core.services.wechat_service import get_wechat_service

        wechat = get_wechat_service()

        if not wechat.is_logged_in:
            logger.warning("微信未登录，无法发送消息")
            return False

        # 确定接收者
        receiver = _determine_receiver(task)

        if not receiver:
            logger.error(f"无法确定回复任务 #{task.id} 的接收者")
            return False

        # 发送消息
        success = wechat.send_message(task.content, receiver)

        return success

    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        return False


def _determine_receiver(task: ReplyTask) -> Optional[str]:
    """
    确定消息接收者

    Args:
        task: 回复任务对象

    Returns:
        Optional[str]: 接收者用户名，None表示无法确定
    """
    try:
        # 从任务上下文中获取接收者信息
        context = task.context or {}

        if task.trigger_type == 'user':
            # 用户触发的任务，回复给原发送者
            sender = context.get('sender')
            if sender:
                # 这里需要将发送者昵称转换为微信用户名
                # 实际使用时需要维护一个昵称到用户名的映射
                return sender

        elif task.trigger_type == 'autonomous':
            # 自主触发的任务，发送给默认接收者（文件传输助手或指定用户）
            # 这里可以从配置中读取默认接收者
            return 'filehelper'

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
            message_type='sent',
            sender='我',  # 当前用户
            receiver=receiver or '未知',
            content=task.content,
            timestamp=timezone.now(),
            reply_task=task,
            raw_data={
                'trigger_type': task.trigger_type,
                'task_id': task.id,
            },
        )

        logger.info(f"消息已记录到数据库：{task.content[:50]}...")

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

        # 查找到期的待执行任务
        now = timezone.now()
        pending_tasks = ReplyTask.objects.filter(
            status='pending',
            scheduled_time__lte=now
        ).order_by('scheduled_time')[:max_tasks]

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
                logger.error(f"执行任务 #{task.id} 失败: {e}")
                failed_count += 1

        logger.info(f"批量执行完成：成功 {success_count} 个，失败 {failed_count} 个")

    except Exception as e:
        logger.error(f"批量执行回复任务失败: {e}", exc_info=True)
