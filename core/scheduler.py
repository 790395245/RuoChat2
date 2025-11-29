import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# 全局调度器实例
_scheduler = None


def start_scheduler():
    """启动APScheduler定时任务调度器"""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("调度器已在运行")
        return _scheduler

    try:
        # 创建后台调度器
        _scheduler = BackgroundScheduler(timezone='Asia/Shanghai')

        # 添加定时任务
        _add_scheduled_jobs(_scheduler)

        # 启动调度器
        _scheduler.start()

        logger.info("定时任务调度器启动成功")
        return _scheduler

    except Exception as e:
        logger.error(f"启动调度器失败: {e}")
        raise


def _add_scheduled_jobs(scheduler: BackgroundScheduler):
    """添加所有定时任务"""

    # 任务1：每日00:00 - 为所有用户生成全天计划任务
    scheduler.add_job(
        func=generate_daily_planned_tasks_for_all_users,
        trigger=CronTrigger(hour=0, minute=0),
        id='daily_planning_00_00',
        name='每日00:00生成全天计划任务',
        replace_existing=True,
    )
    logger.info("已添加任务：每日00:00生成全天计划任务")

    # 任务2：每日00:05 - 为所有用户生成全天自动触发消息
    scheduler.add_job(
        func=generate_autonomous_messages_for_all_users,
        trigger=CronTrigger(hour=0, minute=5),
        id='autonomous_messages_00_05',
        name='每日00:05生成全天自动触发消息',
        replace_existing=True,
    )
    logger.info("已添加任务：每日00:05生成全天自动触发消息")

    # 任务3：每分钟检查并执行回复任务
    scheduler.add_job(
        func=execute_pending_reply_tasks,
        trigger=IntervalTrigger(minutes=1),
        id='execute_reply_tasks',
        name='每分钟执行待回复任务',
        replace_existing=True,
    )
    logger.info("已添加任务：每分钟执行待回复任务")


def generate_daily_planned_tasks_for_all_users():
    """
    每日00:00执行：为所有活跃用户生成全天计划任务
    """
    try:
        logger.info("开始为所有用户生成每日计划任务...")

        from core.models import ChatUser

        # 获取所有活跃用户
        active_users = ChatUser.objects.filter(is_active=True)
        total_users = active_users.count()

        if total_users == 0:
            logger.info("没有活跃用户，跳过生成计划任务")
            return

        logger.info(f"发现 {total_users} 个活跃用户")

        for user in active_users:
            try:
                generate_daily_planned_tasks(user)
            except Exception as e:
                logger.error(f"为用户 {user} 生成计划任务失败: {e}")

        logger.info(f"完成为 {total_users} 个用户生成每日计划任务")

    except Exception as e:
        logger.error(f"生成每日计划任务失败: {e}", exc_info=True)


def generate_daily_planned_tasks(user):
    """
    为指定用户生成全天计划任务

    阶段3：自主触发与定时任务
    1. 触发：自主触发 → 启动每日00:00任务
    2. 上下文补充：从Vertical Container检索记忆库、计划任务库
    3. AI决策：生成全天计划任务
    4. 数据存储：计划任务 → 写入计划任务库
    """
    try:
        logger.info(f"为用户 {user} 生成计划任务...")

        from core.models import PlannedTask
        from core.services.ai_service import AIService
        from core.services.context_service import ContextService

        # 获取该用户的上下文
        context_service = ContextService()
        context = context_service.get_daily_planning_context(user)

        # AI生成计划任务
        ai_service = AIService()
        tasks = ai_service.generate_daily_planned_tasks(user, context)

        # 批量创建任务
        created_count = 0
        for task_data in tasks:
            PlannedTask.objects.create(
                user=user,
                title=task_data['title'],
                description=task_data['description'],
                task_type=task_data['task_type'],
                scheduled_time=task_data['scheduled_time'],
                status='pending',
            )
            created_count += 1

        logger.info(f"为用户 {user} 成功生成 {created_count} 个计划任务")

    except Exception as e:
        logger.error(f"为用户 {user} 生成计划任务失败: {e}", exc_info=True)


def generate_autonomous_messages_for_all_users():
    """
    每日00:05执行：为所有活跃用户生成全天自动触发消息
    """
    try:
        logger.info("开始为所有用户生成自主触发消息...")

        from core.models import ChatUser

        # 获取所有活跃用户
        active_users = ChatUser.objects.filter(is_active=True)
        total_users = active_users.count()

        if total_users == 0:
            logger.info("没有活跃用户，跳过生成自主消息")
            return

        logger.info(f"发现 {total_users} 个活跃用户")

        for user in active_users:
            try:
                generate_autonomous_messages(user)
            except Exception as e:
                logger.error(f"为用户 {user} 生成自主消息失败: {e}")

        logger.info(f"完成为 {total_users} 个用户生成自主触发消息")

    except Exception as e:
        logger.error(f"生成自主触发消息失败: {e}", exc_info=True)


def generate_autonomous_messages(user):
    """
    为指定用户生成全天自动触发消息

    阶段3：自主触发与定时任务
    1. 触发：自主触发 → 启动每日00:05任务
    2. 上下文补充：从Vertical Container检索计划任务库、记忆库、回复任务库
    3. AI决策：生成全天的主动触发消息
    4. 数据存储：自动回复任务 → 写入回复任务库
    """
    try:
        logger.info(f"为用户 {user} 生成自主触发消息...")

        from core.models import ReplyTask
        from core.services.ai_service import AIService
        from core.services.context_service import ContextService

        # 获取该用户的上下文
        context_service = ContextService()
        context = context_service.get_autonomous_message_context(user)

        # AI生成自主消息
        ai_service = AIService()
        messages = ai_service.generate_autonomous_messages(user, context)

        # 批量创建回复任务
        created_count = 0
        for msg_data in messages:
            ReplyTask.objects.create(
                user=user,
                trigger_type='autonomous',
                content=msg_data['content'],
                scheduled_time=msg_data['scheduled_time'],
                status='pending',
                context={
                    'generated_at': datetime.now().isoformat(),
                    'task_context': 'autonomous_daily',
                }
            )
            created_count += 1

        logger.info(f"为用户 {user} 成功生成 {created_count} 条自主触发消息")

    except Exception as e:
        logger.error(f"为用户 {user} 生成自主触发消息失败: {e}", exc_info=True)


def execute_pending_reply_tasks():
    """
    每分钟执行：检查并执行待回复任务

    阶段4：回复任务触发与发送
    1. 触发：回复任务计划触发
    2. 执行：发送消息（从回复任务库）
    3. 记录：发送的消息 → 写入消息记录库
    """
    try:
        from core.models import ReplyTask
        from django.utils import timezone

        # 查找到期的待执行任务（所有用户）
        now = timezone.now()
        pending_tasks = ReplyTask.objects.filter(
            status='pending',
            scheduled_time__lte=now,
            user__is_active=True  # 只处理活跃用户的任务
        ).select_related('user').order_by('scheduled_time')[:10]  # 每次最多执行10个任务

        if not pending_tasks.exists():
            return

        logger.info(f"发现 {pending_tasks.count()} 个待执行的回复任务")

        # 导入执行服务
        from core.services.task_executor import execute_reply_task

        for task in pending_tasks:
            try:
                execute_reply_task(task)
            except Exception as e:
                logger.error(f"执行回复任务 #{task.id} (用户: {task.user}) 失败: {e}")

    except Exception as e:
        logger.error(f"执行待回复任务失败: {e}", exc_info=True)


def stop_scheduler():
    """停止调度器"""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown()
        logger.info("调度器已停止")
        _scheduler = None


def get_scheduler():
    """获取调度器实例"""
    return _scheduler
