from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import logging

from .models import (
    PromptLibrary,
    MemoryLibrary,
    PlannedTask,
    ReplyTask,
    MessageRecord
)
from .services.ai_service import AIService

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def system_status(request):
    """获取系统状态"""
    return JsonResponse({
        'status': 'running',
        'prompts_count': PromptLibrary.objects.filter(is_active=True).count(),
        'memories_count': MemoryLibrary.objects.count(),
        'planned_tasks_count': PlannedTask.objects.filter(status='pending').count(),
        'reply_tasks_count': ReplyTask.objects.filter(status='pending').count(),
        'messages_count': MessageRecord.objects.count(),
    })


@csrf_exempt
@require_http_methods(["POST"])
def set_character_config(request):
    """设置人物设定"""
    try:
        data = json.loads(request.body)
        content = data.get('content', '')

        if not content:
            return JsonResponse({'error': '人物设定内容不能为空'}, status=400)

        # 更新或创建人物设定
        prompt, created = PromptLibrary.objects.update_or_create(
            category='character',
            key='main_character',
            defaults={
                'content': content,
                'is_active': True
            }
        )

        action = '创建' if created else '更新'
        logger.info(f"{action}人物设定成功")

        return JsonResponse({
            'success': True,
            'message': f'{action}成功',
            'id': prompt.id
        })
    except Exception as e:
        logger.error(f"设置人物设定失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def add_hotspot(request):
    """添加热点话题"""
    try:
        data = json.loads(request.body)
        title = data.get('title', '')
        content = data.get('content', '')

        if not title or not content:
            return JsonResponse({'error': '标题和内容不能为空'}, status=400)

        # 使用AI判断是否值得记忆
        ai_service = AIService()
        is_memorable = ai_service.judge_hotspot_memorable(title, content)

        if is_memorable:
            memory = MemoryLibrary.objects.create(
                title=title,
                content=content,
                memory_type='hotspot',
                strength=5,  # 初始强度
                weight=1.0,  # 初始权重
            )
            logger.info(f"添加热点记忆: {title}")
            return JsonResponse({
                'success': True,
                'message': '热点已添加到记忆库',
                'id': memory.id,
                'memorable': True
            })
        else:
            logger.info(f"热点不值得记忆: {title}")
            return JsonResponse({
                'success': True,
                'message': '热点不值得记忆',
                'memorable': False
            })
    except Exception as e:
        logger.error(f"添加热点失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def list_planned_tasks(request):
    """获取计划任务列表"""
    status = request.GET.get('status', None)
    queryset = PlannedTask.objects.all()

    if status:
        queryset = queryset.filter(status=status)

    tasks = list(queryset.values(
        'id', 'title', 'description', 'task_type',
        'scheduled_time', 'status', 'created_at'
    ).order_by('-scheduled_time')[:50])

    return JsonResponse({'tasks': tasks})


@require_http_methods(["GET"])
def list_reply_tasks(request):
    """获取回复任务列表"""
    status = request.GET.get('status', None)
    queryset = ReplyTask.objects.all()

    if status:
        queryset = queryset.filter(status=status)

    tasks = list(queryset.values(
        'id', 'trigger_type', 'content', 'scheduled_time',
        'status', 'created_at', 'executed_at'
    ).order_by('-scheduled_time')[:50])

    return JsonResponse({'tasks': tasks})


@require_http_methods(["GET"])
def list_memories(request):
    """获取记忆列表"""
    memory_type = request.GET.get('type', None)
    queryset = MemoryLibrary.objects.all()

    if memory_type:
        queryset = queryset.filter(memory_type=memory_type)

    memories = list(queryset.values(
        'id', 'title', 'content', 'memory_type',
        'strength', 'weight', 'forget_time', 'created_at'
    ).order_by('-created_at')[:50])

    return JsonResponse({'memories': memories})


@require_http_methods(["GET"])
def list_messages(request):
    """获取消息记录列表"""
    message_type = request.GET.get('type', None)
    queryset = MessageRecord.objects.all()

    if message_type:
        queryset = queryset.filter(message_type=message_type)

    messages = list(queryset.values(
        'id', 'message_type', 'sender', 'receiver',
        'content', 'timestamp', 'created_at'
    ).order_by('-timestamp')[:100])

    return JsonResponse({'messages': messages})
