import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


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

    def _call_openai(self, messages: List[Dict], temperature: float = 0.7) -> str:
        """调用OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            raise

    def judge_hotspot_memorable(self, title: str, content: str) -> bool:
        """
        AI判断：热点是否值得记忆

        Args:
            title: 热点标题
            content: 热点内容

        Returns:
            bool: 是否值得记忆
        """
        from core.models import PromptLibrary

        # 获取人物设定
        character_prompt = PromptLibrary.objects.filter(
            category='character', is_active=True
        ).first()

        character_setting = character_prompt.content if character_prompt else "你是一个智能助手"

        messages = [
            {"role": "system", "content": f"{character_setting}\n\n你需要判断一个热点话题是否值得记忆。"},
            {"role": "user", "content": f"热点标题：{title}\n\n热点内容：{content}\n\n请判断这个热点是否值得记忆（与我的兴趣、经历相关，或对我有重要意义）。只回答'是'或'否'。"}
        ]

        try:
            result = self._call_openai(messages, temperature=0.3)
            return '是' in result or 'yes' in result.lower()
        except Exception as e:
            logger.error(f"判断热点失败: {e}")
            return False

    def decide_reply_content_and_timing(
        self,
        message_content: str,
        sender: str,
        context: Dict
    ) -> Tuple[str, datetime]:
        """
        AI判断：回复内容和回复时间

        Args:
            message_content: 接收到的消息内容
            sender: 发送者
            context: 上下文信息（包含记忆、历史消息等）

        Returns:
            Tuple[str, datetime]: (回复内容, 计划回复时间)
        """
        from core.models import PromptLibrary

        # 获取人物设定和回复模板
        character_prompt = PromptLibrary.objects.filter(
            category='character', is_active=True
        ).first()

        character_setting = character_prompt.content if character_prompt else "你是一个智能助手"

        # 构建上下文信息
        context_str = self._format_context(context)

        messages = [
            {"role": "system", "content": f"{character_setting}\n\n你需要决定如何回复消息，以及何时回复（立即/延迟几分钟）。"},
            {"role": "user", "content": f"发送者：{sender}\n\n接收到的消息：{message_content}\n\n相关上下文：\n{context_str}\n\n请提供：\n1. 回复内容\n2. 回复时间（格式：立即 或 延迟X分钟）\n\n请以JSON格式返回：{{'content': '回复内容', 'delay_minutes': 0}}"}
        ]

        try:
            result = self._call_openai(messages, temperature=0.8)
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
        message_content: str,
        sender: str,
        context: Dict
    ) -> Optional[Dict]:
        """
        AI判断：是否存在记忆点

        Args:
            message_content: 消息内容
            sender: 发送者
            context: 上下文信息

        Returns:
            Optional[Dict]: 记忆点信息（包含title, content, strength, weight, forget_time）
                          如果没有记忆点则返回None
        """
        from core.models import PromptLibrary

        character_prompt = PromptLibrary.objects.filter(
            category='character', is_active=True
        ).first()

        character_setting = character_prompt.content if character_prompt else "你是一个智能助手"

        context_str = self._format_context(context)

        messages = [
            {"role": "system", "content": f"{character_setting}\n\n你需要判断对话中是否存在值得记忆的点（重要信息、情感时刻、特殊事件等）。"},
            {"role": "user", "content": f"发送者：{sender}\n\n消息内容：{message_content}\n\n相关上下文：\n{context_str}\n\n请判断是否存在记忆点，如果存在，请提供：\n1. 记忆标题\n2. 记忆内容\n3. 记忆强度（1-10）\n4. 记忆权重（0.1-10.0）\n5. 遗忘天数（多少天后遗忘，0表示永不遗忘）\n\n请以JSON格式返回：{{'has_memory': true/false, 'title': '标题', 'content': '内容', 'strength': 5, 'weight': 1.0, 'forget_days': 30}}"}
        ]

        try:
            result = self._call_openai(messages, temperature=0.7)
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

    def generate_daily_planned_tasks(self, context: Dict) -> List[Dict]:
        """
        AI判断：生成全天计划任务（每日00:00执行）

        Args:
            context: 上下文信息（记忆库、历史计划等）

        Returns:
            List[Dict]: 计划任务列表
        """
        from core.models import PromptLibrary

        character_prompt = PromptLibrary.objects.filter(
            category='character', is_active=True
        ).first()

        character_setting = character_prompt.content if character_prompt else "你是一个智能助手"

        context_str = self._format_context(context)

        messages = [
            {"role": "system", "content": f"{character_setting}\n\n你需要根据记忆和历史计划，为今天生成计划任务。"},
            {"role": "user", "content": f"今天是{datetime.now().strftime('%Y年%m月%d日 %A')}\n\n相关上下文：\n{context_str}\n\n请生成今天的计划任务列表（3-8个任务），每个任务包含：\n1. 任务标题\n2. 任务描述\n3. 任务类型（daily/special/reminder）\n4. 计划时间（HH:MM格式）\n\n请以JSON格式返回：{{'tasks': [{{'title': '标题', 'description': '描述', 'task_type': 'daily', 'time': '09:00'}}]}}"}
        ]

        try:
            result = self._call_openai(messages, temperature=0.8)
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

    def generate_autonomous_messages(self, context: Dict) -> List[Dict]:
        """
        AI判断：生成全天的主动触发消息（每日00:05执行）

        Args:
            context: 上下文信息（计划任务、记忆、历史消息等）

        Returns:
            List[Dict]: 自动回复任务列表
        """
        from core.models import PromptLibrary

        character_prompt = PromptLibrary.objects.filter(
            category='character', is_active=True
        ).first()

        character_setting = character_prompt.content if character_prompt else "你是一个智能助手"

        context_str = self._format_context(context)

        messages = [
            {"role": "system", "content": f"{character_setting}\n\n你需要根据今天的计划任务和记忆，生成主动发送的消息。"},
            {"role": "user", "content": f"今天是{datetime.now().strftime('%Y年%m月%d日 %A')}\n\n相关上下文：\n{context_str}\n\n请生成今天需要主动发送的消息（1-5条），每条消息包含：\n1. 消息内容\n2. 发送时间（HH:MM格式）\n\n请以JSON格式返回：{{'messages': [{{'content': '消息内容', 'time': '09:00'}}]}}"}
        ]

        try:
            result = self._call_openai(messages, temperature=0.8)
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
                formatted.append(f"- [{msg.get('timestamp', '')}] {msg.get('sender', '')}: {msg.get('content', '')}")

        if 'planned_tasks' in context:
            formatted.append("\n## 今日计划：")
            for task in context['planned_tasks'][:5]:  # 只取前5条
                formatted.append(f"- {task.get('title', '')}: {task.get('description', '')}")

        if 'reply_tasks' in context:
            formatted.append("\n## 待回复任务：")
            for task in context['reply_tasks'][:5]:  # 只取前5条
                formatted.append(f"- [{task.get('scheduled_time', '')}] {task.get('content', '')}")

        return "\n".join(formatted) if formatted else "无相关上下文"

    def _extract_json(self, text: str) -> Dict:
        """从文本中提取JSON"""
        try:
            # 尝试直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取代码块中的JSON
            if '```json' in text:
                start = text.find('```json') + 7
                end = text.find('```', start)
                json_str = text[start:end].strip()
                return json.loads(json_str)
            elif '```' in text:
                start = text.find('```') + 3
                end = text.find('```', start)
                json_str = text[start:end].strip()
                return json.loads(json_str)
            else:
                # 尝试查找JSON对象
                start = text.find('{')
                end = text.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = text[start:end]
                    return json.loads(json_str)

            raise ValueError(f"无法从文本中提取JSON: {text}")
