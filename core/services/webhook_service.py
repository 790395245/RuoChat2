"""
Webhook 消息服务 - 基于 Synology Chat API 实现
替代 itchat 微信服务，通过 Webhook 方式收发消息
"""
import logging
import requests
import json
from typing import Optional, Callable, Dict, Any, TYPE_CHECKING
from datetime import datetime
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if TYPE_CHECKING:
    from core.models import ChatUser

logger = logging.getLogger(__name__)


class WebhookService:
    """Webhook 消息服务 - 基于 Synology Chat API"""

    def __init__(self):
        self.webhook_url = getattr(settings, 'WEBHOOK_URL', '')
        self.webhook_token = getattr(settings, 'WEBHOOK_TOKEN', '')
        self.enabled = bool(self.webhook_url)
        self.message_callback: Optional[Callable] = None

        # 创建带重试机制的 session
        self.session = self._create_session()

        if not self.enabled:
            logger.warning("Webhook 服务未配置，请在 .env 中设置 WEBHOOK_URL")
        else:
            logger.info("Webhook 服务已启用")

    def _create_session(self) -> requests.Session:
        """创建带重试机制的 requests session"""
        session = requests.Session()

        # 定义重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        # 挂载适配器到会话
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _send_webhook(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """
        发送 Webhook 请求到 Synology Chat

        Args:
            payload: 发送的数据

        Returns:
            发送结果
        """
        try:
            logger.info(f"Sending webhook to {self.webhook_url}")
            logger.info(f"Payload: {payload}")

            # 将 payload 转换为 Synology Chat 需要的格式: payload={JSON}
            payload_str = json.dumps(payload)
            data = f"payload={payload_str}"

            # 设置正确的 headers
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            # 发送请求
            response = self.session.post(
                self.webhook_url,
                data=data,
                headers=headers,
                timeout=(10, 30)  # (连接超时, 读取超时)
            )

            result = {
                "status": "success",
                "status_code": response.status_code,
                "response_text": response.text[:1000]
            }

            logger.info(f"Webhook sent successfully with status code {response.status_code}")
            logger.info(f"Response: {response.text}")

            return result

        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
            logger.error(f"Failed to send webhook: {str(e)}")
            return error_result

    def send_message(self, content: str, user_ids: Optional[list] = None) -> bool:
        """
        发送消息到 Synology Chat

        Args:
            content: 消息内容
            user_ids: 用户ID列表（必须指定）

        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.warning("Webhook 服务未启用，无法发送消息")
            return False

        try:
            # 构建 Synology Chat 消息格式
            payload = {
                "text": content
            }

            if user_ids:
                payload["user_ids"] = user_ids
            else:
                logger.error("未指定目标用户ID，无法发送消息")
                return False

            # 发送请求
            result = self._send_webhook(payload)

            if result.get("status") == "success" and result.get("status_code") == 200:
                # 检查 Synology Chat 的响应
                response_text = result.get("response_text", "")
                if '"success":true' in response_text:
                    logger.info(f"消息已发送: {content[:50]}...")
                    return True
                else:
                    logger.error(f"Synology Chat 返回错误: {response_text}")
                    return False
            else:
                logger.error(f"发送消息失败: {result}")
                return False

        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return False

    def send_message_to_user(self, chat_user: 'ChatUser', content: str) -> bool:
        """
        发送消息给指定的聊天用户

        Args:
            chat_user: ChatUser 对象
            content: 消息内容

        Returns:
            bool: 是否发送成功
        """
        # 从 ChatUser 的 user_id 获取 webhook 用户ID
        try:
            webhook_user_id = int(chat_user.user_id)
            success = self.send_message(content, user_ids=[webhook_user_id])

            if success:
                # 保存发送的消息到数据库
                self._save_sent_message(chat_user, content, str(chat_user.user_id))

            return success
        except (ValueError, TypeError):
            logger.error(f"无效的用户ID: {chat_user.user_id}")
            return False

    def send_file(self, file_url: str, text: Optional[str] = None) -> bool:
        """
        发送文件消息

        Args:
            file_url: 文件URL
            text: 附加文本（可选）

        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.warning("Webhook 服务未启用")
            return False

        try:
            payload = {
                "file_url": file_url
            }
            if text:
                payload["text"] = text

            result = self._send_webhook(payload)
            return result.get("status") == "success" and result.get("status_code") == 200

        except Exception as e:
            logger.error(f"发送文件异常: {e}")
            return False

    def set_message_callback(self, callback: Callable):
        """
        设置消息回调函数

        Args:
            callback: 回调函数，接收参数 (user, sender, content, msg_type, raw_msg)
        """
        self.message_callback = callback
        logger.info("消息回调函数已设置")

    def handle_incoming_message(self, data: dict) -> dict:
        """
        处理接收到的消息（由 Webhook 端点调用）

        Args:
            data: 接收到的消息数据

        Returns:
            dict: 响应数据
        """
        try:
            from core.models import ChatUser

            # 解析 Synology Chat 消息格式
            user_id = data.get('user_id', 'unknown')
            username = data.get('username', '未知用户')
            text = data.get('text', '')
            post_id = data.get('post_id', '')
            timestamp = data.get('timestamp', '')

            logger.info(f"收到消息: [{username}(ID:{user_id})] {text[:50]}...")

            # 获取或创建聊天用户
            chat_user = ChatUser.get_or_create_by_webhook(
                user_id=str(user_id),
                username=username,
                post_id=post_id,
                timestamp=timestamp
            )

            # 保存到数据库
            self._save_received_message(
                user=chat_user,
                sender=username,
                content=text,
                msg_type='text',
                raw_data=data
            )

            # 调用回调函数
            if self.message_callback:
                try:
                    self.message_callback(
                        user=chat_user,
                        sender=username,
                        content=text,
                        msg_type='text',
                        raw_msg=data
                    )
                except Exception as e:
                    logger.error(f"消息回调函数执行失败: {e}")

            return {
                'success': True,
                'message': '消息已接收',
                'user_id': chat_user.id
            }

        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _save_received_message(self, user: 'ChatUser', sender: str, content: str, msg_type: str, raw_data: dict):
        """保存接收到的消息到数据库"""
        from core.models import MessageRecord

        try:
            MessageRecord.objects.create(
                user=user,
                message_type='received',
                sender=sender,
                receiver='我',
                content=content,
                timestamp=datetime.now(),
                raw_data={
                    'msg_type': msg_type,
                    'source': 'webhook',
                    'raw': raw_data
                },
            )
        except Exception as e:
            logger.error(f"保存接收消息失败: {e}")

    def _save_sent_message(self, user: 'ChatUser', content: str, receiver: str):
        """保存发送的消息到数据库"""
        from core.models import MessageRecord

        try:
            MessageRecord.objects.create(
                user=user,
                message_type='sent',
                sender='我',
                receiver=receiver,
                content=content,
                timestamp=datetime.now(),
                raw_data={'source': 'webhook'},
            )
        except Exception as e:
            logger.error(f"保存发送消息失败: {e}")

    def test_connection(self, test_user_id: Optional[int] = None) -> bool:
        """
        测试 Webhook 连接

        Args:
            test_user_id: 测试用的用户ID（必须指定）

        Returns:
            bool: 连接是否成功
        """
        if not self.enabled:
            return False

        if not test_user_id:
            logger.error("测试连接需要指定用户ID")
            return False

        try:
            result = self.send_message("RuoChat Webhook 连接测试", user_ids=[test_user_id])
            return result
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False


# 全局单例
_webhook_service_instance = None


def get_webhook_service() -> WebhookService:
    """获取 Webhook 服务单例"""
    global _webhook_service_instance
    if _webhook_service_instance is None:
        _webhook_service_instance = WebhookService()
    return _webhook_service_instance
