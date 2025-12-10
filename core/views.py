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
    MessageRecord,
    EmotionRecord
)
from .services.ai_service import AIService
from .services.context_service import ContextService

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
        'emotions_count': EmotionRecord.objects.count(),
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
        is_memorable = ai_service.judge_hotspot_memorable(chat_user, title, content)

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


# ==================== Emotion API ====================

@require_http_methods(["GET"])
def list_emotions(request):
    """获取情绪记录列表"""
    user_id = request.GET.get('user_id', None)
    emotion_type = request.GET.get('emotion_type', None)
    hours = request.GET.get('hours', 24)

    try:
        hours = int(hours)
    except ValueError:
        hours = 24

    from datetime import timedelta
    from django.utils import timezone as tz

    queryset = EmotionRecord.objects.all()

    if user_id:
        queryset = queryset.filter(user__user_id=user_id)

    if emotion_type:
        queryset = queryset.filter(emotion_type=emotion_type)

    # 按时间过滤
    cutoff = tz.now() - timedelta(hours=hours)
    queryset = queryset.filter(created_at__gte=cutoff)

    emotions = list(queryset.values(
        'id', 'user__user_id', 'emotion_type', 'intensity',
        'trigger_source', 'trigger_content', 'description', 'created_at'
    ).order_by('-created_at')[:100])

    return JsonResponse({'emotions': emotions})


@require_http_methods(["GET"])
def get_emotion_status(request):
    """获取用户当前情绪状态和趋势"""
    user_id = request.GET.get('user_id', None)
    hours = request.GET.get('hours', 24)

    try:
        hours = int(hours)
    except ValueError:
        hours = 24

    if not user_id:
        return JsonResponse({
            'success': False,
            'error': '用户ID不能为空'
        }, status=400)

    try:
        chat_user = ChatUser.objects.get(user_id=user_id)
    except ChatUser.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '用户不存在'
        }, status=404)

    # 使用 ContextService 获取情绪上下文
    context_service = ContextService()
    emotion_context = context_service.get_emotion_context(chat_user, hours=hours)

    return JsonResponse({
        'success': True,
        'user_id': user_id,
        'current_emotion': emotion_context.get('current_emotion'),
        'emotion_trend': emotion_context.get('emotion_trend'),
        'emotion_stats': emotion_context.get('emotion_stats'),
        'dominant_emotion': emotion_context.get('dominant_emotion'),
    })


@csrf_exempt
@require_http_methods(["POST"])
def manual_emotion_record(request):
    """手动记录情绪状态（用于测试或手动设置）"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id', '')
        emotion_type = data.get('emotion_type', 'neutral')
        intensity = data.get('intensity', 5)
        description = data.get('description', '')

        if not user_id:
            return JsonResponse({
                'success': False,
                'error': '用户ID不能为空'
            }, status=400)

        # 验证情绪类型
        valid_emotions = ['happy', 'sad', 'angry', 'anxious', 'calm', 'excited', 'tired', 'neutral', 'worried', 'grateful']
        if emotion_type not in valid_emotions:
            return JsonResponse({
                'success': False,
                'error': f'无效的情绪类型，有效类型: {valid_emotions}'
            }, status=400)

        # 验证强度
        try:
            intensity = int(intensity)
            intensity = max(1, min(10, intensity))
        except ValueError:
            intensity = 5

        # 获取或创建用户
        chat_user = ChatUser.get_or_create_by_webhook(user_id=str(user_id))

        # 创建情绪记录
        emotion_record = EmotionRecord.objects.create(
            user=chat_user,
            emotion_type=emotion_type,
            intensity=intensity,
            trigger_source='system',
            trigger_content='手动记录',
            description=description,
        )

        logger.info(f"用户 {chat_user}: 手动记录情绪 {emotion_type} ({intensity}/10)")

        return JsonResponse({
            'success': True,
            'message': '情绪记录成功',
            'id': emotion_record.id,
            'emotion_type': emotion_record.emotion_type,
            'intensity': emotion_record.intensity,
        })

    except Exception as e:
        logger.error(f"手动记录情绪失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ==================== User Initialization API ====================

@require_http_methods(["GET"])
def get_character_presets(request):
    """获取character预设选项列表"""
    from .services.user_init_service import get_user_init_service

    try:
        user_init_service = get_user_init_service()
        presets = user_init_service.get_character_presets()

        return JsonResponse({
            'success': True,
            'presets': presets
        })
    except Exception as e:
        logger.error(f"获取预设选项失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def check_user_init_status(request):
    """检查用户是否已初始化"""
    user_id = request.GET.get('user_id', None)

    if not user_id:
        return JsonResponse({
            'success': False,
            'error': '用户ID不能为空'
        }, status=400)

    try:
        # 尝试获取用户
        try:
            chat_user = ChatUser.objects.get(user_id=user_id)
            is_initialized = chat_user.is_initialized
        except ChatUser.DoesNotExist:
            # 用户不存在，视为未初始化
            is_initialized = False

        return JsonResponse({
            'success': True,
            'user_id': user_id,
            'is_initialized': is_initialized
        })
    except Exception as e:
        logger.error(f"检查用户初始化状态失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def complete_user_initialization(request):
    """完成用户初始化（提交character选择）"""
    from .services.user_init_service import get_user_init_service

    try:
        data = json.loads(request.body)
        user_id = data.get('user_id', '')
        preset_id = data.get('preset_id', '')
        custom_content = data.get('custom_content', '')

        if not user_id:
            return JsonResponse({
                'success': False,
                'error': '用户ID不能为空'
            }, status=400)

        user_init_service = get_user_init_service()

        # 确定character内容
        character_content = ''

        if preset_id == 'custom':
            # 自定义内容
            if not custom_content:
                return JsonResponse({
                    'success': False,
                    'error': '自定义内容不能为空'
                }, status=400)
            character_content = custom_content
        else:
            # 使用预设
            preset = user_init_service.get_preset_by_id(preset_id)
            if not preset:
                return JsonResponse({
                    'success': False,
                    'error': f'无效的预设ID: {preset_id}'
                }, status=400)
            character_content = preset['content']

        # 获取或创建用户
        chat_user = ChatUser.get_or_create_by_webhook(user_id=str(user_id))

        # 检查是否已初始化
        if chat_user.is_initialized:
            return JsonResponse({
                'success': False,
                'error': '用户已完成初始化，无法重复初始化'
            }, status=400)

        # 初始化用户提示词
        success = user_init_service.initialize_user_prompts(chat_user, character_content)

        if success:
            logger.info(f"用户 {chat_user} 完成初始化，使用预设: {preset_id}")
            return JsonResponse({
                'success': True,
                'message': '初始化成功',
                'user_id': chat_user.user_id,
                'preset_id': preset_id
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '初始化失败，请稍后重试'
            }, status=500)

    except Exception as e:
        logger.error(f"完成用户初始化失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)