import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


# 默认提示词模板（当数据库中没有配置时使用）
DEFAULT_PROMPTS = {
    'character': '你是一位不知名职业歌手，年龄22，性别女，性格内敛，温柔傲娇。有很不错的职业技能。喜欢健身、游戏、电影。',

    'reply_decision': '''当前时间：{current_time}

你需要结合上下文决定如何回复消息，以及何时回复。回复内容尽量言简意赅，不要出现疑问、重复。
也不要重复之前的双方对话中出现过的话语。不用刻意提起与当前接受到的消息无关的上下文。
如果用户有很多消息没有回复，可以质疑。

请根据以下信息决定回复：
- 发送者：{sender}
- 接收到的消息：{message}
- 相关上下文：
{context}

请提供：
1. 回复内容（符合人物设定和上下文语境的自然回复）
2. 回复时间（立即回复设为0，延迟回复设为分钟数，如5表示5分钟后回复）（需根据当前时段的日程判断,如果延迟回复，需要在回复内容中说明延迟原因）

请以JSON格式返回：{{"content": "回复内容", "delay_minutes": 0}}''',

    'memory_detection': '''你需要判断对话中是否存在值得记忆的点（重要信息、情感时刻、特殊事件等）。
你只需要记忆非常重要的信息，日常琐事不用记忆。

对话信息：
- 发送者：{sender}
- 消息内容：{message}
- 相关上下文：
{context}

请判断是否存在记忆点，如果存在，请提供：
1. 记忆标题（简短概括）
2. 记忆内容（详细描述）
3. 记忆强度（1-10，10最重要）
4. 记忆权重（0.1-10.0，影响检索优先级）
5. 遗忘天数（多少天后遗忘，0表示永不遗忘）

请以JSON格式返回：
- 如果没有记忆点：{{"has_memory": false}}
- 如果有记忆点：{{"has_memory": true, "title": "标题", "content": "内容", "strength": 5, "weight": 1.0, "forget_days": 30}}''',

    'daily_planning': '''今天是{date}

请根据以下上下文，为今天生成计划任务列表（覆盖当天的所有时段），尽量消息的描述任务的详细内容、耗时：
{context}

每个任务包含：
1. 任务标题
2. 任务描述
3. 任务类型（daily=日常任务/special=特殊任务/reminder=提醒任务）
4. 计划时间（HH:MM格式）

请以JSON格式返回：{{"tasks": [{{"title": "标题", "description": "描述", "task_type": "daily", "time": "09:00"}}]}}''',

    'autonomous_message': '''今天是{date}

请根据以下上下文，生成今天需要主动发送的关怀消息：
{context}

每条消息包含：
1. 消息内容（自然、温暖的问候或关心）
2. 发送时间（HH:MM格式，根据上下文中的今日计划任务，抽空发送，分布在全天合适的时间段）

请以JSON格式返回：{{"messages": [{{"content": "消息内容", "time": "09:00"}}]}}''',

    'hotspot_judge': '''请判断以下热点话题是否值得记忆（与用户的兴趣、经历相关，或对用户有重要意义）。

热点标题：{title}
热点内容：{content}

只回答"是"或"否"。''',

    'message_merge': '''当前时间：{current_time}

你有多条待发送的消息需要整合成一条自然的消息。请根据当前的计划和情绪状态，将以下消息内容融合，保持整体语气一致、流畅自然。注意消息内容和当前时间的逻辑漏洞。

待整合的消息：
{messages}

当前上下文：
{context}

要求：
1. 保留所有消息的核心信息和情感
2. 根据当前情绪状态调整语气和措辞
3. 参考今日计划安排，使消息内容更贴合当前时段的状态
4. 语气要自然连贯，像是一个人一次说完的话
5. 可以适当调整顺序和措辞，但不要丢失重要内容
6. 不要太长，控制在合理长度内
7. 可以删减原文中不必要的内容

请直接返回整合后的消息内容，不需要JSON格式。''',

    'emotion_analysis': '''你需要分析并模拟作为AI助手的你自己在收到这条消息后的情绪状态。

当前时间：{current_time}
发送者：{sender}
收到的消息：{message}

你当前的情绪状态：
{current_emotion}

你近期的情绪趋势：
{emotion_trend}

相关上下文：
{context}

请根据你的人物设定和当前情境，分析你作为AI助手收到这条消息后的情绪反应：
1. 情绪类型：happy（开心）、sad（悲伤）、angry（愤怒）、anxious（焦虑）、calm（平静）、excited（兴奋）、tired（疲倦）、neutral（中性）、worried（担忧）、grateful（感激）
2. 情绪强度：1-10，10表示最强烈
3. 情绪描述：简短描述你当前的情绪状态和产生这种情绪的原因

请以JSON格式返回：
{{"emotion_type": "happy", "intensity": 7, "description": "收到用户的问候让我感到开心"}}''',
}


class AIService:
    """AI决策服务 - 集成OpenAI API实现各种AI判断节点"""

    def __init__(self):
        # 初始化 OpenAI 客户端
        client_kwargs = {
            'api_key': settings.OPENAI_API_KEY
        }

        # 如果配置了自定义 API Base URL，则使用它
        if settings.OPENAI_API_BASE:
            client_kwargs['base_url'] = settings.OPENAI_API_BASE
            logger.info(f"使用自定义 API Base URL: {settings.OPENAI_API_BASE}")

        self.client = OpenAI(**client_kwargs)
        self.model = settings.OPENAI_MODEL

    def _get_prompt(self, user, category: str) -> str:
        """
        获取提示词，优先从数据库读取，否则使用默认值

        Args:
            user: ChatUser 对象
            category: 提示词类别

        Returns:
            str: 提示词内容
        """
        from core.models import PromptLibrary

        # 优先获取用户专属的提示词
        prompt = PromptLibrary.objects.filter(
            user=user,
            category=category,
            is_active=True
        ).first()

        if prompt:
            return prompt.content

        # 返回默认提示词
        return DEFAULT_PROMPTS.get(category, '')

    def _get_character_prompt(self, user) -> str:
        """获取人物设定"""
        return self._get_prompt(user, 'character')

    def _call_openai(self, messages: List[Dict], temperature: float = 0.7, caller: str = 'unknown') -> str:
        """调用OpenAI API"""
        try:
            # 记录请求日志
            self._log_request(messages, temperature, caller)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            result = response.choices[0].message.content.strip()

            # 记录响应日志
            self._log_response(result, caller)

            return result
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            raise

    def _log_request(self, messages: List[Dict], temperature: float, caller: str):
        """记录 AI 请求日志"""
        separator = "=" * 60
        logger.info(f"\n{separator}")
        logger.info(f"[AI 请求] 调用方: {caller} | 模型: {self.model} | temperature: {temperature}")
        logger.info(separator)

        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown').upper()
            content = msg.get('content', '')

            # 对于长内容，进行适当截断显示
            if len(content) > 1500:
                display_content = content[:1500] + f"\n... (内容过长，已截断，原始长度: {len(content)} 字符)"
            else:
                display_content = content

            logger.info(f"\n[{role}]\n{display_content}")

        logger.info(separator)

    def _log_response(self, result: str, caller: str):
        """记录 AI 响应日志"""
        separator = "-" * 60
        logger.info(f"\n{separator}")
        logger.info(f"[AI 响应] 调用方: {caller}")
        logger.info(separator)

        # 对于长响应，进行适当截断显示
        if len(result) > 2000:
            display_result = result[:2000] + f"\n... (响应过长，已截断，原始长度: {len(result)} 字符)"
        else:
            display_result = result

        logger.info(f"\n{display_result}")
        logger.info(f"\n{'=' * 60}\n")

    def judge_hotspot_memorable(self, user, title: str, content: str) -> bool:
        """
        AI判断：热点是否值得记忆

        Args:
            user: ChatUser 对象
            title: 热点标题
            content: 热点内容

        Returns:
            bool: 是否值得记忆
        """
        character_setting = self._get_character_prompt(user)
        hotspot_prompt = self._get_prompt(user, 'hotspot_judge')

        # 替换变量
        user_prompt = hotspot_prompt.format(title=title, content=content)

        messages = [
            {"role": "system", "content": f"{character_setting}\n\n你需要判断一个热点话题是否值得记忆。"},
            {"role": "user", "content": user_prompt}
        ]

        try:
            result = self._call_openai(messages, temperature=0.3, caller='热点判断')
            return '是' in result or 'yes' in result.lower()
        except Exception as e:
            logger.error(f"判断热点失败: {e}")
            return False

    def decide_reply_content_and_timing(
        self,
        user,
        message_content: str,
        sender: str,
        context: Dict
    ) -> Tuple[str, datetime]:
        """
        AI判断：回复内容和回复时间

        Args:
            user: ChatUser 对象
            message_content: 接收到的消息内容
            sender: 发送者
            context: 上下文信息（包含记忆、历史消息等）

        Returns:
            Tuple[str, datetime]: (回复内容, 计划回复时间)
        """
        character_setting = self._get_character_prompt(user)
        reply_prompt = self._get_prompt(user, 'reply_decision')

        # 构建上下文信息
        context_str = self._format_context(context)
        current_time = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S %A')

        # 替换变量
        user_prompt = reply_prompt.format(
            sender=sender,
            message=message_content,
            context=context_str,
            current_time=current_time
        )

        messages = [
            {"role": "system", "content": f"{character_setting}\n\n{self._get_prompt(user, 'system') or '你需要决定如何回复消息。'}"},
            {"role": "user", "content": user_prompt}
        ]

        try:
            result = self._call_openai(messages, temperature=0.8, caller='回复决策')
            # 解析JSON响应
            result_json = self._extract_json(result)

            reply_content = result_json.get('content', '收到')
            delay_minutes = int(result_json.get('delay_minutes', 0))

            scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)

            logger.info(f"AI决策：回复'{reply_content}'，延迟{delay_minutes}分钟")
            return reply_content, scheduled_time

        except Exception as e:
            logger.error(f"决策回复失败: {e}")
            # 默认回复
            return "收到", datetime.now()

    def detect_memory_points(
        self,
        user,
        message_content: str,
        sender: str,
        context: Dict
    ) -> Optional[Dict]:
        """
        AI判断：是否存在记忆点

        Args:
            user: ChatUser 对象
            message_content: 消息内容
            sender: 发送者
            context: 上下文信息

        Returns:
            Optional[Dict]: 记忆点信息（包含title, content, strength, weight, forget_time）
                          如果没有记忆点则返回None
        """
        character_setting = self._get_character_prompt(user)
        memory_prompt = self._get_prompt(user, 'memory_detection')

        context_str = self._format_context(context)

        # 替换变量
        user_prompt = memory_prompt.format(
            sender=sender,
            message=message_content,
            context=context_str
        )

        messages = [
            {"role": "system", "content": f"{character_setting}\n\n你需要判断对话中是否存在值得记忆的点。"},
            {"role": "user", "content": user_prompt}
        ]

        try:
            result = self._call_openai(messages, temperature=0.7, caller='记忆检测')
            result_json = self._extract_json(result)

            if not result_json.get('has_memory', False):
                return None

            forget_days = result_json.get('forget_days', 30)
            forget_time = None if forget_days == 0 else datetime.now() + timedelta(days=forget_days)

            memory_info = {
                'title': result_json.get('title', '未命名记忆'),
                'content': result_json.get('content', message_content),
                'strength': min(10, max(1, result_json.get('strength', 5))),
                'weight': min(10.0, max(0.1, result_json.get('weight', 1.0))),
                'forget_time': forget_time,
            }

            logger.info(f"检测到记忆点: {memory_info['title']}")
            return memory_info

        except Exception as e:
            logger.error(f"检测记忆点失败: {e}")
            return None

    def generate_daily_planned_tasks(self, user, context: Dict) -> List[Dict]:
        """
        AI判断：生成全天计划任务（每日00:00执行）

        Args:
            user: ChatUser 对象
            context: 上下文信息（记忆库、历史计划等）

        Returns:
            List[Dict]: 计划任务列表
        """
        character_setting = self._get_character_prompt(user)
        planning_prompt = self._get_prompt(user, 'daily_planning')

        context_str = self._format_context(context)
        date_str = datetime.now().strftime('%Y年%m月%d日 %A')

        # 替换变量
        user_prompt = planning_prompt.format(
            date=date_str,
            context=context_str
        )

        messages = [
            {"role": "system", "content": f"{character_setting}\n\n你需要根据你的记忆和你的历史计划，为今天生成你的计划任务。"},
            {"role": "user", "content": user_prompt}
        ]

        try:
            result = self._call_openai(messages, temperature=0.8, caller='每日计划')
            result_json = self._extract_json(result)

            tasks = []
            today = datetime.now().date()

            for task_data in result_json.get('tasks', []):
                try:
                    time_str = task_data.get('time', '12:00')
                    hour, minute = map(int, time_str.split(':'))
                    scheduled_time = datetime.combine(today, datetime.min.time()).replace(hour=hour, minute=minute)

                    tasks.append({
                        'title': task_data.get('title', '未命名任务'),
                        'description': task_data.get('description', ''),
                        'task_type': task_data.get('task_type', 'daily'),
                        'scheduled_time': scheduled_time,
                    })
                except Exception as e:
                    logger.error(f"解析任务时间失败: {e}")
                    continue

            logger.info(f"生成了{len(tasks)}个计划任务")
            return tasks

        except Exception as e:
            logger.error(f"生成计划任务失败: {e}")
            return []

    def generate_autonomous_messages(self, user, context: Dict) -> List[Dict]:
        """
        AI判断：生成全天的主动触发消息（每日00:05执行）

        Args:
            user: ChatUser 对象
            context: 上下文信息（计划任务、记忆、历史消息等）

        Returns:
            List[Dict]: 自动回复任务列表
        """
        character_setting = self._get_character_prompt(user)
        autonomous_prompt = self._get_prompt(user, 'autonomous_message')

        context_str = self._format_context(context)
        date_str = datetime.now().strftime('%Y年%m月%d日 %A')

        # 替换变量
        user_prompt = autonomous_prompt.format(
            date=date_str,
            context=context_str
        )

        messages = [
            {"role": "system", "content": f"{character_setting}\n\n你需要根据你自己今天的计划任务和记忆，生成主动发送给用户的关怀消息。"},
            {"role": "user", "content": user_prompt}
        ]

        try:
            result = self._call_openai(messages, temperature=0.8, caller='自主消息')
            result_json = self._extract_json(result)

            messages_list = []
            today = datetime.now().date()

            for msg_data in result_json.get('messages', []):
                try:
                    time_str = msg_data.get('time', '12:00')
                    hour, minute = map(int, time_str.split(':'))
                    scheduled_time = datetime.combine(today, datetime.min.time()).replace(hour=hour, minute=minute)

                    messages_list.append({
                        'content': msg_data.get('content', ''),
                        'scheduled_time': scheduled_time,
                    })
                except Exception as e:
                    logger.error(f"解析消息时间失败: {e}")
                    continue

            logger.info(f"生成了{len(messages_list)}条自动消息")
            return messages_list

        except Exception as e:
            logger.error(f"生成自动消息失败: {e}")
            return []

    def merge_messages(self, user, messages: List[str], context: Optional[Dict] = None) -> str:
        """
        AI整合多条消息为一条自然的消息

        Args:
            user: ChatUser 对象
            messages: 待整合的消息内容列表
            context: 上下文信息（包含计划任务、情绪状态等）

        Returns:
            str: 整合后的消息内容
        """
        if not messages:
            return ""

        if len(messages) == 1:
            return messages[0]

        character_setting = self._get_character_prompt(user)
        merge_prompt = self._get_prompt(user, 'message_merge')

        current_time = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S %A')

        # 格式化消息列表
        messages_text = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(messages)])

        # 格式化上下文信息
        context_str = self._format_context(context) if context else "无相关上下文"

        # 替换变量
        user_prompt = merge_prompt.format(
            current_time=current_time,
            messages=messages_text,
            context=context_str
        )

        ai_messages = [
            {"role": "system", "content": f"{character_setting}\n\n你需要将多条消息整合成一条自然流畅的消息。"},
            {"role": "user", "content": user_prompt}
        ]

        try:
            result = self._call_openai(ai_messages, temperature=0.7, caller='消息整合')
            merged_content = result.strip()

            logger.info(f"成功整合 {len(messages)} 条消息")
            return merged_content

        except Exception as e:
            logger.error(f"整合消息失败: {e}")
            # 失败时简单拼接
            return " ".join(messages)

    def analyze_emotion(
        self,
        user,
        message_content: str,
        sender: str,
        context: Dict,
        current_emotion: Optional[Dict] = None,
        emotion_trend: Optional[List[Dict]] = None
    ) -> Optional[Dict]:
        """
        AI判断：分析AI助手自己收到消息后的情绪状态

        Args:
            user: ChatUser 对象
            message_content: 收到的消息内容
            sender: 消息发送者
            context: 上下文信息
            current_emotion: AI助手当前情绪状态
            emotion_trend: AI助手近期情绪趋势

        Returns:
            Optional[Dict]: 情绪分析结果
                - emotion_type: 情绪类型
                - intensity: 情绪强度 (1-10)
                - description: 情绪描述
        """
        character_setting = self._get_character_prompt(user)
        emotion_prompt = self._get_prompt(user, 'emotion_analysis')

        context_str = self._format_context(context)
        current_time = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S %A')

        # 格式化当前情绪状态
        current_emotion_str = "无记录"
        if current_emotion:
            current_emotion_str = f"{current_emotion.get('emotion_type', '未知')} (强度: {current_emotion.get('intensity', 0)}/10)"

        # 格式化情绪趋势
        emotion_trend_str = "无历史记录"
        if emotion_trend:
            trend_items = []
            for item in emotion_trend[-5:]:  # 只取最近5条
                trend_items.append(
                    f"- {item.get('created_at', '')} : {item.get('emotion_type', '')} ({item.get('intensity', 0)}/10)"
                )
            if trend_items:
                emotion_trend_str = "\n".join(trend_items)

        # 替换变量
        user_prompt = emotion_prompt.format(
            current_time=current_time,
            sender=sender,
            message=message_content,
            current_emotion=current_emotion_str,
            emotion_trend=emotion_trend_str,
            context=context_str
        )

        messages = [
            {"role": "system", "content": f"{character_setting}\n\n你需要根据人物设定，分析并模拟自己收到消息后的情绪状态。"},
            {"role": "user", "content": user_prompt}
        ]

        try:
            result = self._call_openai(messages, temperature=0.5, caller='情绪分析')
            result_json = self._extract_json(result)

            # 验证情绪类型
            valid_emotions = ['happy', 'sad', 'angry', 'anxious', 'calm', 'excited', 'tired', 'neutral', 'worried', 'grateful']
            emotion_type = result_json.get('emotion_type', 'neutral')
            if emotion_type not in valid_emotions:
                emotion_type = 'neutral'

            emotion_info = {
                'emotion_type': emotion_type,
                'intensity': min(10, max(1, int(result_json.get('intensity', 5)))),
                'description': result_json.get('description', ''),
            }

            logger.info(f"AI情绪分析结果: {emotion_info['emotion_type']} ({emotion_info['intensity']}/10)")
            return emotion_info

        except Exception as e:
            logger.error(f"情绪分析失败: {e}")
            return None

    def _format_context(self, context: Dict) -> str:
        """格式化上下文信息为字符串"""
        formatted = []

        if 'memories' in context:
            formatted.append("## 相关记忆：")
            for memory in context['memories'][:5]:  # 只取前5条
                formatted.append(f"- {memory.get('title', '')}: {memory.get('content', '')}")

        if 'recent_messages' in context:
            formatted.append("\n## 最近消息：")
            for msg in context['recent_messages'][:10]:  # 只取前10条
                sender = msg.get('sender', '')
                receiver = msg.get('receiver', '')
                content = msg.get('content', '')
                timestamp = msg.get('timestamp', '')
                formatted.append(f"- [{timestamp}] {sender} → {receiver}: {content}")

        if 'planned_tasks' in context:
            formatted.append("\n## 今日计划：")
            for task in context['planned_tasks']:  # 传递全部计划任务
                scheduled_time = task.get('scheduled_time', '')
                # 处理不同格式的时间
                if hasattr(scheduled_time, 'strftime'):
                    # datetime 对象
                    time_str = scheduled_time.strftime('%H:%M')
                elif isinstance(scheduled_time, str) and len(scheduled_time) >= 16:
                    # 字符串格式 'YYYY-MM-DD HH:MM:SS'，提取 HH:MM
                    time_str = scheduled_time[11:16]
                else:
                    time_str = str(scheduled_time)
                formatted.append(f"- [{time_str}] {task.get('title', '')}: {task.get('description', '')}")

        if 'reply_tasks' in context:
            formatted.append("\n## 待回复任务：")
            for task in context['reply_tasks'][:5]:  # 只取前5条
                formatted.append(f"- [{task.get('scheduled_time', '')}] {task.get('content', '')}")

        if 'emotion' in context:
            emotion = context['emotion']
            formatted.append("\n## AI情绪状态：")
            if emotion.get('current_emotion'):
                current = emotion['current_emotion']
                formatted.append(f"- 当前情绪：{current.get('emotion_type_display', current.get('emotion_type', '未知'))} (强度: {current.get('intensity', 0)}/10)")
                if current.get('description'):
                    formatted.append(f"  描述：{current['description']}")
            if emotion.get('dominant_emotion'):
                dominant = emotion['dominant_emotion']
                formatted.append(f"- 主导情绪：{dominant.get('emotion_type', '未知')} (出现{dominant.get('count', 0)}次，平均强度: {dominant.get('avg_intensity', 0)})")

        return "\n".join(formatted) if formatted else "无相关上下文"

    def _extract_json(self, text: str) -> Dict:
        """从文本中提取JSON"""
        import re
        import ast

        # 首先移除 Qwen3 等模型的 thinking 标签
        # 支持 <think>...</think> 格式
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = text.strip()

        def try_parse(json_str: str) -> Dict:
            """尝试解析 JSON，支持单引号格式（Python 字典风格）"""
            json_str = json_str.strip()
            try:
                # 首先尝试标准 JSON 解析
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 如果失败，尝试用 ast.literal_eval 解析 Python 字典格式
                try:
                    result = ast.literal_eval(json_str)
                    if isinstance(result, dict):
                        return result
                except (ValueError, SyntaxError):
                    pass
                raise

        try:
            # 尝试直接解析
            return try_parse(text)
        except (json.JSONDecodeError, ValueError, SyntaxError):
            # 尝试提取代码块中的JSON
            if '```json' in text:
                start = text.find('```json') + 7
                end = text.find('```', start)
                json_str = text[start:end].strip()
                return try_parse(json_str)
            elif '```' in text:
                start = text.find('```') + 3
                end = text.find('```', start)
                json_str = text[start:end].strip()
                return try_parse(json_str)
            else:
                # 尝试查找JSON对象
                start = text.find('{')
                end = text.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = text[start:end]
                    return try_parse(json_str)

            raise ValueError(f"无法从文本中提取JSON: {text}")
