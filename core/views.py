from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import logging

from .models import (
    ChatUser,
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
        'users_count': ChatUser.objects.filter(is_active=True).count(),
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
        user_id = data.get('user_id', '')

        if not content:
            return JsonResponse({'error': '人物设定内容不能为空'}, status=400)

        if not user_id:
            return JsonResponse({'error': '用户ID不能为空'}, status=400)

        # 获取或创建用户
        chat_user = ChatUser.get_or_create_by_webhook(user_id=str(user_id))

        # 更新或创建该用户的人物设定
        prompt, created = PromptLibrary.objects.update_or_create(
            user=chat_user,
            category='character',
            key='main_character',
            defaults={
                'content': content,
                'is_active': True
            }
        )

        action = '创建' if created else '更新'
        logger.info(f"用户 {chat_user}: {action}人物设定成功")

        return JsonResponse({
            'success': True,
            'message': f'{action}成功',
            'id': prompt.id,
            'user_id': chat_user.id
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
        user_id = data.get('user_id', '')

        if not title or not content:
            return JsonResponse({'error': '标题和内容不能为空'}, status=400)

        if not user_id:
            return JsonResponse({'error': '用户ID不能为空'}, status=400)

        # 获取或创建用户
        chat_user = ChatUser.get_or_create_by_webhook(user_id=str(user_id))

        # 使用AI判断是否值得记忆
        ai_service = AIService()
        is_memorable = ai_service.judge_hotspot_memorable(title, content)

        if is_memorable:
            memory = MemoryLibrary.objects.create(
                user=chat_user,
                title=title,
                content=content,
                memory_type='hotspot',
                strength=5,  # 初始强度
                weight=1.0,  # 初始权重
            )
            logger.info(f"用户 {chat_user}: 添加热点记忆: {title}")
            return JsonResponse({
                'success': True,
                'message': '热点已添加到记忆库',
                'id': memory.id,
                'user_id': chat_user.id,
                'memorable': True
            })
        else:
            logger.info(f"用户 {chat_user}: 热点不值得记忆: {title}")
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
    user_id = request.GET.get('user_id', None)
    queryset = PlannedTask.objects.all()

    if user_id:
        queryset = queryset.filter(user__user_id=user_id)

    if status:
        queryset = queryset.filter(status=status)

    tasks = list(queryset.values(
        'id', 'user__user_id', 'title', 'description', 'task_type',
        'scheduled_time', 'status', 'created_at'
    ).order_by('-scheduled_time')[:50])

    return JsonResponse({'tasks': tasks})


@require_http_methods(["GET"])
def list_reply_tasks(request):
    """获取回复任务列表"""
    status = request.GET.get('status', None)
    user_id = request.GET.get('user_id', None)
    queryset = ReplyTask.objects.all()

    if user_id:
        queryset = queryset.filter(user__user_id=user_id)

    if status:
        queryset = queryset.filter(status=status)

    tasks = list(queryset.values(
        'id', 'user__user_id', 'trigger_type', 'content', 'scheduled_time',
        'status', 'created_at', 'executed_at'
    ).order_by('-scheduled_time')[:50])

    return JsonResponse({'tasks': tasks})


@require_http_methods(["GET"])
def list_memories(request):
    """获取记忆列表"""
    memory_type = request.GET.get('type', None)
    user_id = request.GET.get('user_id', None)
    queryset = MemoryLibrary.objects.all()

    if user_id:
        queryset = queryset.filter(user__user_id=user_id)

    if memory_type:
        queryset = queryset.filter(memory_type=memory_type)

    memories = list(queryset.values(
        'id', 'user__user_id', 'title', 'content', 'memory_type',
        'strength', 'weight', 'forget_time', 'created_at'
    ).order_by('-created_at')[:50])

    return JsonResponse({'memories': memories})


@require_http_methods(["GET"])
def list_messages(request):
    """获取消息记录列表"""
    message_type = request.GET.get('type', None)
    user_id = request.GET.get('user_id', None)
    queryset = MessageRecord.objects.all()

    if user_id:
        queryset = queryset.filter(user__user_id=user_id)

    if message_type:
        queryset = queryset.filter(message_type=message_type)

    messages = list(queryset.values(
        'id', 'user__user_id', 'message_type', 'sender', 'receiver',
        'content', 'timestamp', 'created_at'
    ).order_by('-timestamp')[:100])

    return JsonResponse({'messages': messages})


# ==================== Webhook API ====================

@csrf_exempt
@require_http_methods(["POST", "GET"])
def webhook_incoming(request):
    """
    Webhook 消息接收端点
    接收来自 Synology Chat 或其他服务的消息

    Synology Chat 发送的数据字段：
    - token: bot token
    - user_id: 用户ID
    - username: 用户名
    - post_id: 消息ID
    - timestamp: 时间戳
    - text: 消息内容
    """
    from .services.webhook_service import get_webhook_service
    from .services.message_handler import get_message_handler

    try:
        # 记录请求详情用于调试
        logger.info(f"Webhook 收到请求:")
        logger.info(f"  Content-Type: {request.content_type}")
        logger.info(f"  Body: {request.body[:500] if request.body else 'empty'}")

        # GET 请求用于验证 webhook
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'message': 'Webhook endpoint is active',
                'service': 'RuoChat2'
            })

        logger.info(f"  POST data: {dict(request.POST)}")

        # POST 请求处理消息
        # Synology Chat 使用 application/x-www-form-urlencoded 格式
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
        else:
            # Synology Chat 使用表单数据
            data = {
                'user_id': request.POST.get('user_id', ''),
                'username': request.POST.get('username', '未知用户'),
                'text': request.POST.get('text', ''),
                'post_id': request.POST.get('post_id', ''),
                'timestamp': request.POST.get('timestamp', ''),
                'token': request.POST.get('token', ''),
            }

        logger.info(f"Webhook 解析数据: {data}")

        # 验证 token（可选）
        webhook_token = getattr(settings, 'WEBHOOK_TOKEN', '')
        if webhook_token and data.get('token') != webhook_token:
            logger.warning("Webhook token 验证失败")
            # 不强制验证，继续处理

        # 获取消息内容
        text = data.get('text', '')
        username = data.get('username', '未知用户')
        user_id = data.get('user_id', '')

        logger.info(f"收到消息: [{username}(ID:{user_id})] {text}")

        if not text:
            return JsonResponse({
                'success': True,
                'message': 'No text content'
            })

        # 获取 webhook 服务
        webhook_service = get_webhook_service()

        # 设置消息处理器回调
        message_handler = get_message_handler()

        def on_message(user, sender, content, msg_type, raw_msg):
            """消息回调函数"""
            try:
                message_handler.handle_user_message(
                    user=user,
                    sender=sender,
                    content=content,
                    msg_type=msg_type,
                    raw_msg=raw_msg
                )
            except Exception as e:
                logger.error(f'处理消息失败: {e}')

        webhook_service.set_message_callback(on_message)

        # 处理消息
        result = webhook_service.handle_incoming_message(data)

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Webhook 处理异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_send(request):
    """
    通过 Webhook 发送消息
    POST 参数: content (消息内容), user_id (可选，用户ID)
    """
    from .services.webhook_service import get_webhook_service

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        content = data.get('content', '')
        user_id = data.get('user_id')

        if not content:
            return JsonResponse({
                'success': False,
                'error': '消息内容不能为空'
            }, status=400)

        webhook_service = get_webhook_service()
        result = webhook_service.send_message(content, user_id)

        return JsonResponse({
            'success': result,
            'message': '消息已发送' if result else '发送失败'
        })

    except Exception as e:
        logger.error(f"发送消息异常: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def webhook_status(request):
    """获取 Webhook 服务状态"""
    from .services.webhook_service import get_webhook_service

    webhook_service = get_webhook_service()

    return JsonResponse({
        'enabled': webhook_service.enabled,
        'webhook_url_configured': bool(webhook_service.webhook_url),
        'message': 'Webhook 服务运行中' if webhook_service.enabled else 'Webhook 服务未配置'
    })


@csrf_exempt
@require_http_methods(["POST"])
def webhook_test(request):
    """测试 Webhook 连接"""
    from .services.webhook_service import get_webhook_service

    webhook_service = get_webhook_service()

    if not webhook_service.enabled:
        return JsonResponse({
            'success': False,
            'error': 'Webhook 服务未配置'
        }, status=400)

    result = webhook_service.test_connection()

    return JsonResponse({
        'success': result,
        'message': '连接测试成功' if result else '连接测试失败'
    })


