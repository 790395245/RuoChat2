from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import (
    ChatUser,
    PromptLibrary,
    MemoryLibrary,
    PlannedTask,
    ReplyTask,
    MessageRecord
)


class Command(BaseCommand):
    help = '初始化RuoChat系统数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新初始化（会清除已有数据）',
        )
        parser.add_argument(
            '--with-examples',
            action='store_true',
            help='添加示例数据（用于测试和演示，需要指定 --user-id）',
        )
        parser.add_argument(
            '--user-id',
            type=str,
            help='指定用户ID（用于创建示例数据）',
        )

    def handle(self, *args, **options):
        force = options['force']
        with_examples = options['with_examples']
        user_id = options.get('user_id')

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('开始初始化RuoChat系统...'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # 1. 创建必要的目录
        self._create_directories()

        # 2. 创建管理员账号
        self._create_admin_user()

        # 3. 添加示例数据（可选，需要指定用户）
        if with_examples:
            if not user_id:
                self.stdout.write(self.style.ERROR(
                    '\n⚠ 添加示例数据需要指定 --user-id 参数'
                ))
            else:
                self._add_example_data(user_id, force)

        # 4. 验证配置
        self._verify_configuration()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('系统初始化完成！'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        self._print_next_steps()

    def _create_directories(self):
        """创建必要的目录"""
        import os
        from pathlib import Path
        from django.conf import settings

        self.stdout.write('\n📁 正在创建必要的目录...')

        directories = [
            settings.BASE_DIR / 'logs',
            settings.BASE_DIR / 'media',
            settings.BASE_DIR / 'staticfiles',
        ]

        created_count = 0
        for directory in directories:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ 创建目录: {directory.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  - 目录已存在: {directory.name}'))

        if created_count == 0:
            self.stdout.write(self.style.WARNING('  - 所有目录已存在'))

    def _create_admin_user(self):
        """创建管理员账号"""
        import os
        from django.contrib.auth.models import User

        self.stdout.write('\n👤 正在检查管理员账号...')

        # 从环境变量读取管理员配置
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')

        # 检查管理员是否已存在
        if User.objects.filter(username=admin_username).exists():
            self.stdout.write(self.style.WARNING(f'  - 管理员账号已存在: {admin_username}'))
            self.stdout.write(f'    如需重置密码，请使用: python manage.py changepassword {admin_username}')
        else:
            # 创建管理员账号
            User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password
            )
            self.stdout.write(self.style.SUCCESS(f'  ✓ 管理员账号创建成功'))
            self.stdout.write(f'    用户名: {admin_username}')
            self.stdout.write(f'    密码: {admin_password}')
            self.stdout.write(self.style.WARNING('    ⚠ 请及时修改默认密码！'))

    def _add_example_data(self, user_id: str, force: bool):
        """添加示例数据"""
        self.stdout.write(f'\n🎯 正在为用户 {user_id} 添加示例数据...')

        # 获取或创建用户
        chat_user = ChatUser.get_or_create_by_webhook(
            user_id=user_id,
            username=f'示例用户_{user_id}'
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ 用户: {chat_user}'))

        # 初始化该用户的提示词库
        self._init_user_prompts(chat_user, force)

        # 添加示例记忆
        self._add_example_memories(chat_user, force)

        # 添加示例计划任务
        self._add_example_tasks(chat_user, force)

    def _init_user_prompts(self, user: ChatUser, force: bool):
        """为用户初始化提示词库"""
        from core.services.ai_service import DEFAULT_PROMPTS

        self.stdout.write('\n📚 正在初始化提示词库...')

        # 类别与 key 的映射
        category_keys = {
            'character': 'default_character',
            'reply_decision': 'reply_decision_prompt',
            'memory_detection': 'memory_detection_prompt',
            'daily_planning': 'daily_planning_prompt',
            'autonomous_message': 'autonomous_message_prompt',
            'hotspot_judge': 'hotspot_judge_prompt',
        }

        # 类别描述
        category_descriptions = {
            'character': '人物设定',
            'reply_decision': '回复决策',
            'memory_detection': '记忆检测',
            'daily_planning': '每日计划',
            'autonomous_message': '自主消息',
            'hotspot_judge': '热点判断',
        }

        if force:
            # 删除用户所有提示词
            deleted_count = PromptLibrary.objects.filter(user=user).delete()[0]
            if deleted_count:
                self.stdout.write(self.style.WARNING(f'  - 已删除 {deleted_count} 条旧提示词'))

        created_count = 0
        for category, content in DEFAULT_PROMPTS.items():
            key = category_keys.get(category, f'{category}_default')
            description = category_descriptions.get(category, category)

            prompt, created = PromptLibrary.objects.get_or_create(
                user=user,
                category=category,
                defaults={
                    'key': key,
                    'content': content,
                    'is_active': True,
                    'metadata': {
                        'version': '1.0',
                        'auto_generated': True,
                        'description': description
                    }
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ 创建提示词: {description}'))
            else:
                self.stdout.write(self.style.WARNING(f'  - 提示词已存在: {description}'))

        self.stdout.write(self.style.SUCCESS(f'  ✓ 共创建 {created_count} 个提示词'))

    def _add_example_memories(self, user: ChatUser, force: bool):
        """添加示例记忆"""
        example_memories = [
            {
                'title': '用户喜欢喝咖啡',
                'content': '用户提到每天早上都会喝一杯美式咖啡，这是他的日常习惯。',
                'memory_type': 'user_memory',
                'strength': 7,
                'weight': 1.5,
            },
            {
                'title': '2024年重要科技新闻',
                'content': 'AI技术取得重大突破，多个大语言模型发布。',
                'memory_type': 'hotspot',
                'strength': 6,
                'weight': 1.0,
                'forget_time': timezone.now() + timedelta(days=30),
            },
        ]

        if force:
            MemoryLibrary.objects.filter(user=user).delete()

        memory_count = 0
        for memory_data in example_memories:
            memory, created = MemoryLibrary.objects.get_or_create(
                user=user,
                title=memory_data['title'],
                defaults=memory_data
            )
            if created:
                memory_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ 添加 {memory_count} 条示例记忆'))

    def _add_example_tasks(self, user: ChatUser, force: bool):
        """添加示例计划任务"""
        tomorrow = timezone.now() + timedelta(days=1)
        example_tasks = [
            {
                'title': '早安问候',
                'description': '向用户发送早安问候',
                'task_type': 'daily',
                'scheduled_time': tomorrow.replace(hour=8, minute=30, second=0, microsecond=0),
            },
            {
                'title': '晚间互动',
                'description': '询问用户今天过得如何',
                'task_type': 'daily',
                'scheduled_time': tomorrow.replace(hour=19, minute=0, second=0, microsecond=0),
            },
        ]

        if force:
            PlannedTask.objects.filter(user=user).delete()

        task_count = 0
        for task_data in example_tasks:
            task, created = PlannedTask.objects.get_or_create(
                user=user,
                title=task_data['title'],
                scheduled_time=task_data['scheduled_time'],
                defaults=task_data
            )
            if created:
                task_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ 添加 {task_count} 个示例计划任务'))

    def _verify_configuration(self):
        """验证系统配置"""
        self.stdout.write('\n🔍 正在验证系统配置...')

        from django.conf import settings

        # 检查必要的配置项
        checks = [
            ('OPENAI_API_KEY', hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY),
            ('OPENAI_MODEL', hasattr(settings, 'OPENAI_MODEL') and settings.OPENAI_MODEL),
            ('WEBHOOK_URL', hasattr(settings, 'WEBHOOK_URL') and settings.WEBHOOK_URL),
            ('数据库连接', self._test_database_connection()),
        ]

        all_ok = True
        for name, status in checks:
            if status:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {name}: 已配置'))
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {name}: 未配置'))
                all_ok = False

        if all_ok:
            self.stdout.write(self.style.SUCCESS('  ✓ 所有配置项检查通过'))
        else:
            self.stdout.write(self.style.WARNING('  ⚠ 部分配置项需要检查'))

    def _test_database_connection(self):
        """测试数据库连接"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _print_next_steps(self):
        """打印后续步骤"""
        self.stdout.write('\n📋 后续步骤：')
        self.stdout.write('\n1. 检查配置文件:')
        self.stdout.write('   python manage.py check_config')
        self.stdout.write('\n2. 启动Web服务:')
        self.stdout.write('   python manage.py runserver')
        self.stdout.write('   或使用Docker: docker-compose up -d web')
        self.stdout.write('\n3. 测试Webhook连接:')
        self.stdout.write('   curl -X POST http://localhost:8000/api/webhook/test/')
        self.stdout.write('\n4. 查看Webhook状态:')
        self.stdout.write('   curl http://localhost:8000/api/webhook/status/')
        self.stdout.write('\n5. 查看系统状态:')
        self.stdout.write('   curl http://localhost:8000/api/status/')
        self.stdout.write('\n6. 为用户初始化示例数据:')
        self.stdout.write('   python manage.py init_system --with-examples --user-id <用户ID>')
        self.stdout.write('')
