import logging
from typing import Dict, Optional, TYPE_CHECKING
from datetime import datetime
from django.utils import timezone

from core.models import MessageRecord, ReplyTask, MemoryLibrary, ChatUser, EmotionRecord
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
        5. AI判断：情绪分析 → 写入情绪记录库
        6. 同步修改当日其他自动回复任务

        Args:
            user: 聊天用户对象
            sender: 消息发送者
            content: 消息内容
            msg_type: 消息类型
            raw_msg: 原始消息数据（包含 user_id 等）
        """
        try:
            logger.info(f"开始处理用户 {user} 的消息：{sender} - {content[:50]}")

            # 检查是否为新用户，如果是则进入引导流程
            if not user.is_initialized:
                self._handle_onboarding(user, sender, content, raw_msg)
                return

            # 步骤1：消息已在webhook_service中写入消息记录库

            # 步骤2：检索并添加上下文
            context = self.context_service.get_user_message_context(user, sender)

            # 获取情绪上下文（用于 AI 决策）
            emotion_context = self.context_service.get_emotion_context(user)
            context['emotion'] = emotion_context

            # 步骤3：AI判断回复内容和回复时间（考虑情绪状态）
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
                    'emotion_at_reply': emotion_context.get('current_emotion'),  # 保存回复时的情绪状态
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

            # 步骤5：AI判断情绪状态
            self._analyze_and_record_emotion(user, content, sender, context, emotion_context)

            # 步骤6：同步修改当日其他自动回复任务
            self._sync_autonomous_tasks(user, reply_task)

            logger.info(f"用户 {user} 的消息处理完成: {sender}")

        except Exception as e:
            logger.error(f"处理用户消息失败: {e}", exc_info=True)

    def _analyze_and_record_emotion(
        self,
        user: ChatUser,
        content: str,
        sender: str,
        context: Dict,
        emotion_context: Dict
    ):
        """
        分析并记录AI助手情绪状态

        Args:
            user: 聊天用户对象
            content: 收到的消息内容
            sender: 消息发送者
            context: 消息上下文
            emotion_context: AI助手情绪上下文
        """
        try:
            # 调用 AI 分析情绪
            emotion_info = self.ai_service.analyze_emotion(
                user=user,
                message_content=content,
                sender=sender,
                context=context,
                current_emotion=emotion_context.get('current_emotion'),
                emotion_trend=emotion_context.get('emotion_trend')
            )

            if emotion_info:
                # 创建情绪记录
                emotion_record = EmotionRecord.objects.create(
                    user=user,
                    emotion_type=emotion_info['emotion_type'],
                    intensity=emotion_info['intensity'],
                    trigger_source='user_message',
                    trigger_content=content[:500],  # 限制长度
                    description=emotion_info.get('description', ''),
                    metadata={
                        'sender': sender,
                        'previous_emotion': emotion_context.get('current_emotion'),
                    }
                )
                logger.info(f"记录AI情绪: {emotion_record.get_emotion_type_display()} ({emotion_record.intensity}/10)")

        except Exception as e:
            logger.error(f"分析AI情绪失败: {e}")

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

    def _handle_onboarding(self, user: ChatUser, sender: str, content: str, raw_msg: Optional[Dict]):
        """
        处理新用户引导流程

        引导流程：
        1. 检测新用户状态
        2. 如果是第一次消息，发送引导消息要求设定character
        3. 接收用户回复，保存为character提示词
        4. 初始化提示词库
        5. 触发生成daily_planning和autonomous_message
        6. 设置is_initialized=True，完成引导

        Args:
            user: 聊天用户对象
            sender: 消息发送者
            content: 消息内容
            raw_msg: 原始消息数据
        """
        try:
            from core.models import PromptLibrary
            from core.services.webhook_service import get_webhook_service

            logger.info(f"用户 {user} 进入引导流程")

            # 获取用户的引导状态
            metadata = user.metadata or {}
            onboarding_step = metadata.get('onboarding_step', 'start')

            webhook_service = get_webhook_service()

            # 从原始消息中提取 user_id（用于 webhook 回复）
            webhook_user_id = None
            if raw_msg:
                webhook_user_id = raw_msg.get('user_id')

            if onboarding_step == 'start':
                # 第一次消息，发送引导消息
                from core.services.user_init_service import get_user_init_service
                user_init_service = get_user_init_service()
                presets = user_init_service.get_character_presets()

                # 构建预设选项列表（排除"自定义"选项）
                preset_list = []
                for preset in presets:
                    if preset['id'] != 'custom':
                        preset_list.append(f"• {preset['name']}: {preset['description']}")

                preset_text = "\n".join(preset_list)

                guide_message = f"""欢迎！👋

我注意到这是你第一次使用本系统。为了更好地为你服务，我需要了解一下你希望我扮演的角色。

你可以选择以下预设角色之一：

{preset_text}

或者，你也可以完全自定义人物设定，例如：
- 性格特点（温柔、活泼、专业等）
- 年龄和性别
- 职业或身份
- 兴趣爱好
- 其他特征

请回复：
1. 预设角色的名称（如"职业歌手(女)"）
2. 或者用一段话描述你希望的人物设定"""

                # 发送引导消息
                if webhook_service.enabled and webhook_user_id:
                    webhook_service.send_message(guide_message, [int(webhook_user_id)])
                    logger.info(f"已向用户 {user} 发送引导消息")

                # 更新用户状态为等待character设定
                metadata['onboarding_step'] = 'waiting_character'
                user.metadata = metadata
                user.save(update_fields=['metadata'])

                logger.info(f"用户 {user} 状态更新为 waiting_character")

            elif onboarding_step == 'waiting_character':
                # 接收用户的character设定
                logger.info(f"用户 {user} 提供了character设定：{content[:100]}")

                # 使用UserInitService初始化所有提示词
                from core.services.user_init_service import get_user_init_service
                user_init_service = get_user_init_service()
                presets = user_init_service.get_character_presets()

                # 检查用户是否选择了预设
                character_content = None
                selected_preset_name = None

                # 尝试匹配预设名称
                for preset in presets:
                    if preset['id'] != 'custom':
                        # 检查用户回复是否包含预设名称
                        if preset['name'] in content or preset['id'] in content:
                            character_content = preset['content']
                            selected_preset_name = preset['name']
                            logger.info(f"用户 {user} 选择了预设: {preset['name']}")
                            break

                # 如果没有匹配到预设，使用用户的自定义描述
                if character_content is None:
                    character_content = content
                    selected_preset_name = "自定义"
                    logger.info(f"用户 {user} 使用自定义character")

                # 初始化所有提示词
                success = user_init_service.initialize_user_prompts(user, character_content)

                if not success:
                    raise Exception("初始化用户提示词失败")

                logger.info(f"用户 {user}: 成功初始化所有提示词")

                # 触发生成daily_planning和autonomous_message
                self._trigger_initial_tasks(user)

                # 清空引导状态
                user.metadata = {}
                user.save(update_fields=['metadata'])

                logger.info(f"用户 {user} 引导流程完成，已设置为已初始化")

                # 发送完成消息
                completion_message = f"""太好了！我已经记住了你的设定。

【{selected_preset_name}】
{character_content}

现在我会根据这个人物设定来与你互动。我已经为你生成了今天的计划任务和一些主动消息，让我们开始吧！😊"""

                if webhook_service.enabled and webhook_user_id:
                    webhook_service.send_message(completion_message, [int(webhook_user_id)])
                    logger.info(f"已向用户 {user} 发送完成消息")

        except Exception as e:
            logger.error(f"处理新用户引导失败: {e}", exc_info=True)
            # 发送错误消息
            try:
                from core.services.webhook_service import get_webhook_service
                webhook_service = get_webhook_service()
                if webhook_service.enabled and raw_msg:
                    webhook_user_id = raw_msg.get('user_id')
                    if webhook_user_id:
                        error_message = "抱歉，引导流程出现了问题。请稍后再试或联系管理员。"
                        webhook_service.send_message(error_message, [int(webhook_user_id)])
            except:
                pass

    def _trigger_initial_tasks(self, user: ChatUser):
        """
        为新用户触发生成初始任务

        生成daily_planning和autonomous_message

        Args:
            user: 聊天用户对象
        """
        try:
            from core.scheduler import generate_daily_planned_tasks, generate_autonomous_messages

            logger.info(f"为用户 {user} 触发生成初始任务")

            # 生成每日计划任务
            try:
                generate_daily_planned_tasks(user)
                logger.info(f"用户 {user}: 成功生成每日计划任务")
            except Exception as e:
                logger.error(f"用户 {user}: 生成每日计划任务失败: {e}")

            # 生成自主触发消息
            try:
                generate_autonomous_messages(user)
                logger.info(f"用户 {user}: 成功生成自主触发消息")
            except Exception as e:
                logger.error(f"用户 {user}: 生成自主触发消息失败: {e}")

            logger.info(f"用户 {user} 初始任务生成完成")

        except Exception as e:
            logger.error(f"触发初始任务失败: {e}", exc_info=True)


# 全局单例
_message_handler_instance = None


def get_message_handler() -> MessageHandler:
    """获取消息处理器单例"""
    global _message_handler_instance
    if _message_handler_instance is None:
        _message_handler_instance = MessageHandler()
    return _message_handler_instance
