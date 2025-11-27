from django.core.management.base import BaseCommand
from core.services.wechat_service import get_wechat_service
from core.services.message_handler import get_message_handler


class Command(BaseCommand):
    help = '启动微信消息监听服务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-qr',
            action='store_true',
            help='不在命令行显示二维码',
        )

    def handle(self, *args, **options):
        enable_cmd_qr = not options['no_qr']

        self.stdout.write(self.style.SUCCESS('正在启动微信服务...'))

        # 获取微信服务
        wechat = get_wechat_service()

        if not wechat.enabled:
            self.stdout.write(self.style.ERROR('微信服务未启用，请检查配置'))
            return

        # 设置消息回调
        message_handler = get_message_handler()

        def on_message(sender, content, msg_type, raw_msg):
            """消息回调函数"""
            try:
                self.stdout.write(f'收到消息: [{msg_type}] {sender}: {content[:50]}...')
                message_handler.handle_user_message(
                    sender=sender,
                    content=content,
                    msg_type=msg_type,
                    raw_msg=raw_msg
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'处理消息失败: {e}'))

        wechat.set_message_callback(on_message)

        # 登录微信
        self.stdout.write('\n请扫描二维码登录微信...')
        if wechat.login(enable_cmd_qr=enable_cmd_qr):
            self.stdout.write(self.style.SUCCESS('微信登录成功！'))
            self.stdout.write('\n开始监听微信消息...')
            self.stdout.write('按 Ctrl+C 停止服务\n')

            try:
                wechat.start()
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('\n正在停止微信服务...'))
                wechat.logout()
                self.stdout.write(self.style.SUCCESS('微信服务已停止'))
        else:
            self.stdout.write(self.style.ERROR('微信登录失败'))
