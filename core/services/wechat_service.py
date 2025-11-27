import logging
import threading
from typing import Optional, Callable
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

# 尝试导入itchat
try:
    import itchat
    from itchat.content import TEXT, PICTURE, RECORDING, ATTACHMENT, VIDEO
    ITCHAT_AVAILABLE = True
except ImportError:
    logger.warning("itchat未安装，微信功能将不可用")
    ITCHAT_AVAILABLE = False


class WeChatService:
    """微信消息服务 - 基于itchat实现"""

    def __init__(self):
        self.enabled = settings.WECHAT_ENABLED and ITCHAT_AVAILABLE
        self.is_logged_in = False
        self.message_callback: Optional[Callable] = None

        if not ITCHAT_AVAILABLE:
            logger.warning("微信服务不可用：itchat未安装")
        elif not self.enabled:
            logger.info("微信服务已禁用")

    def login(self, enable_cmd_qr: bool = True):
        """
        登录微信

        Args:
            enable_cmd_qr: 是否在命令行显示二维码
        """
        if not self.enabled:
            logger.warning("微信服务未启用")
            return False

        try:
            # 登录微信
            itchat.auto_login(
                hotReload=True,  # 热加载，避免频繁扫码
                enableCmdQR=enable_cmd_qr,  # 命令行显示二维码
            )

            self.is_logged_in = True
            logger.info("微信登录成功")

            # 注册消息处理器
            self._register_message_handlers()

            return True

        except Exception as e:
            logger.error(f"微信登录失败: {e}")
            return False

    def logout(self):
        """登出微信"""
        if self.is_logged_in:
            try:
                itchat.logout()
                self.is_logged_in = False
                logger.info("微信已登出")
            except Exception as e:
                logger.error(f"微信登出失败: {e}")

    def start(self):
        """启动微信监听（阻塞模式）"""
        if not self.is_logged_in:
            logger.warning("请先登录微信")
            return

        try:
            logger.info("开始监听微信消息...")
            itchat.run()
        except KeyboardInterrupt:
            logger.info("微信监听已停止")
            self.logout()

    def start_in_background(self):
        """在后台线程启动微信监听（非阻塞模式）"""
        if not self.is_logged_in:
            logger.warning("请先登录微信")
            return

        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        logger.info("微信监听已在后台启动")

    def send_message(self, content: str, to_user: Optional[str] = None) -> bool:
        """
        发送文本消息

        Args:
            content: 消息内容
            to_user: 接收者用户名（None表示文件传输助手）

        Returns:
            bool: 是否发送成功
        """
        if not self.is_logged_in:
            logger.warning("微信未登录，无法发送消息")
            return False

        try:
            if to_user:
                # 发送给指定用户
                itchat.send(content, toUserName=to_user)
            else:
                # 发送给文件传输助手
                itchat.send(content, toUserName='filehelper')

            logger.info(f"消息已发送: {content[:50]}...")

            # 记录到数据库
            self._save_sent_message(content, to_user or 'filehelper')

            return True

        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    def send_message_by_nickname(self, content: str, nickname: str) -> bool:
        """
        根据昵称发送消息

        Args:
            content: 消息内容
            nickname: 接收者昵称

        Returns:
            bool: 是否发送成功
        """
        if not self.is_logged_in:
            logger.warning("微信未登录，无法发送消息")
            return False

        try:
            # 搜索用户
            users = itchat.search_friends(name=nickname)

            if not users:
                logger.warning(f"未找到昵称为 {nickname} 的用户")
                return False

            user = users[0]
            return self.send_message(content, user['UserName'])

        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    def set_message_callback(self, callback: Callable):
        """
        设置消息回调函数

        Args:
            callback: 回调函数，接收参数 (sender, content, msg_type, raw_msg)
        """
        self.message_callback = callback
        logger.info("消息回调函数已设置")

    def _register_message_handlers(self):
        """注册微信消息处理器"""

        @itchat.msg_register([TEXT])
        def text_message_handler(msg):
            """文本消息处理器"""
            self._handle_message(msg, 'text')

        @itchat.msg_register([PICTURE])
        def picture_message_handler(msg):
            """图片消息处理器"""
            self._handle_message(msg, 'picture')

        @itchat.msg_register([RECORDING, VIDEO])
        def media_message_handler(msg):
            """媒体消息处理器"""
            self._handle_message(msg, 'media')

        @itchat.msg_register([ATTACHMENT])
        def file_message_handler(msg):
            """文件消息处理器"""
            self._handle_message(msg, 'file')

        logger.info("微信消息处理器已注册")

    def _handle_message(self, msg: dict, msg_type: str):
        """
        处理接收到的消息

        Args:
            msg: itchat消息对象
            msg_type: 消息类型
        """
        try:
            sender = msg.get('ActualNickName') or msg.get('User', {}).get('NickName', '未知用户')
            content = msg.get('Text', '')

            logger.info(f"收到消息 [{msg_type}] {sender}: {content[:50]}...")

            # 保存到数据库
            self._save_received_message(
                sender=sender,
                content=content,
                msg_type=msg_type,
                raw_data=msg
            )

            # 调用回调函数
            if self.message_callback:
                try:
                    self.message_callback(
                        sender=sender,
                        content=content,
                        msg_type=msg_type,
                        raw_msg=msg
                    )
                except Exception as e:
                    logger.error(f"消息回调函数执行失败: {e}")

        except Exception as e:
            logger.error(f"处理消息失败: {e}")

    def _save_received_message(self, sender: str, content: str, msg_type: str, raw_data: dict):
        """保存接收到的消息到数据库"""
        from core.models import MessageRecord

        try:
            MessageRecord.objects.create(
                message_type='received',
                sender=sender,
                receiver='我',  # 当前用户
                content=content,
                timestamp=datetime.now(),
                raw_data={
                    'msg_type': msg_type,
                    'msg_id': raw_data.get('MsgId', ''),
                },
            )
        except Exception as e:
            logger.error(f"保存接收消息失败: {e}")

    def _save_sent_message(self, content: str, receiver: str):
        """保存发送的消息到数据库"""
        from core.models import MessageRecord

        try:
            MessageRecord.objects.create(
                message_type='sent',
                sender='我',  # 当前用户
                receiver=receiver,
                content=content,
                timestamp=datetime.now(),
                raw_data={},
            )
        except Exception as e:
            logger.error(f"保存发送消息失败: {e}")

    def get_friends_list(self) -> list:
        """获取好友列表"""
        if not self.is_logged_in:
            logger.warning("微信未登录")
            return []

        try:
            friends = itchat.get_friends(update=True)
            return [
                {
                    'username': friend['UserName'],
                    'nickname': friend['NickName'],
                    'remark_name': friend.get('RemarkName', ''),
                }
                for friend in friends
            ]
        except Exception as e:
            logger.error(f"获取好友列表失败: {e}")
            return []


# 全局单例
_wechat_service_instance = None


def get_wechat_service() -> WeChatService:
    """获取微信服务单例"""
    global _wechat_service_instance
    if _wechat_service_instance is None:
        _wechat_service_instance = WeChatService()
    return _wechat_service_instance
