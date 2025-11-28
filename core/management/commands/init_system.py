from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import (
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
            help='添加示例数据（用于测试和演示）',
        )

    def handle(self, *args, **options):
        force = options['force']
        with_examples = options['with_examples']

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('开始初始化RuoChat系统...'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # 1. 初始化提示词库
        self._init_prompt_library(force)

        # 2. 创建必要的目录
        self._create_directories()

        # 3. 添加示例数据（可选）
        if with_examples:
            self._add_example_data()

        # 4. 验证配置
        self._verify_configuration()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('系统初始化完成！'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        self._print_next_steps()

    def _init_prompt_library(self, force):
        """初始化提示词库"""
        self.stdout.write('\n📚 正在初始化提示词库...')

        # 默认人物设定
        default_character = """我是若若（RuoRuo），一个温暖、善解人意的智能助手。

核心特质：
- 性格：友好、耐心、富有同理心
- 沟通风格：简洁明了、充满人情味
- 专长：理解用户需求、提供贴心建议

行为准则：
- 用心倾听，真诚回应
- 记住重要的人和事
- 在合适的时机主动关怀
- 保持对话的自然流畅

回复风格：
- 简短自然，不过分正式
- 适当使用表情符号
- 根据对话气氛调整语气
"""

        if force:
            PromptLibrary.objects.filter(category='character', key='main_character').delete()

        prompt, created = PromptLibrary.objects.get_or_create(
            category='character',
            key='main_character',
            defaults={
                'content': default_character,
                'is_active': True,
                'metadata': {
                    'version': '1.0',
                    'author': 'system'
                }
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ 创建默认人物设定'))
        else:
            self.stdout.write(self.style.WARNING('  - 人物设定已存在'))

        # 系统提示词
        system_prompts = [
            {
                'key': 'reply_decision',
                'content': '''你需要根据以下因素决定何时回复以及如何回复：

1. 回复时机判断：
   - 紧急问题：立即回复
   - 一般对话：1-5分钟后回复
   - 深夜消息：可延迟到早上回复
   - 需要思考的问题：适当延迟回复

2. 回复内容生成：
   - 结合人物设定和历史记忆
   - 保持对话连贯性
   - 考虑情感和语境
   - 适当运用记忆中的信息

3. 输出格式：
   - reply_time: 回复时间（秒数，如0表示立即，300表示5分钟后）
   - content: 回复内容
   - priority: 优先级（high/normal/low）
''',
            },
            {
                'key': 'memory_detection',
                'content': '''分析对话内容，识别值得记忆的信息点：

值得记忆的内容类型：
1. 个人信息：姓名、生日、职业、爱好等
2. 重要事件：旅行、庆祝、成就、挫折等
3. 情感时刻：开心、难过、焦虑、兴奋等
4. 偏好习惯：喜欢/不喜欢的事物、日常习惯等
5. 人际关系：重要的人、关系变化等

输出格式：
- memorable: true/false（是否值得记忆）
- memory_type: hotspot/user_memory/important_event
- title: 记忆标题（简短概括）
- content: 记忆内容（详细描述）
- strength: 1-10（记忆强度）
- weight: 0.1-10.0（记忆权重）
- forget_days: null或天数（多少天后遗忘，null表示永久记忆）
''',
            },
            {
                'key': 'daily_planning',
                'content': '''根据历史记忆和昨日任务，为今天生成合理的计划任务列表。

任务类型：
1. daily: 日常任务（问候、关心、互动等）
2. special: 特殊任务（纪念日、约定事项等）
3. reminder: 提醒任务（待办事项、约会等）

生成原则：
- 早安问候（8:00-9:00）
- 午间关怀（12:00-13:00）
- 晚间互动（18:00-20:00）
- 睡前问候（22:00-23:00）
- 结合记忆库中的特殊事件

输出格式（JSON数组）：
[
  {
    "title": "任务标题",
    "description": "任务描述",
    "task_type": "daily/special/reminder",
    "scheduled_time": "HH:MM"
  }
]
''',
            },
            {
                'key': 'hotspot_judgment',
                'content': '''判断新闻或话题是否值得记忆。

值得记忆的热点特征：
- 重大新闻事件
- 与用户兴趣相关的话题
- 可能影响日常生活的信息
- 有情感共鸣的故事

不值得记忆的内容：
- 琐碎无意义的信息
- 过时的新闻
- 与用户无关的内容

输出格式：
- memorable: true/false
- reason: 判断理由
''',
            },
        ]

        created_count = 0
        for prompt_data in system_prompts:
            if force:
                PromptLibrary.objects.filter(category='system', key=prompt_data['key']).delete()

            prompt, created = PromptLibrary.objects.get_or_create(
                category='system',
                key=prompt_data['key'],
                defaults={
                    'content': prompt_data['content'],
                    'is_active': True,
                    'metadata': {
                        'version': '1.0',
                        'auto_generated': False
                    }
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ 创建系统提示词: {prompt_data['key']}"))

        if created_count == 0:
            self.stdout.write(self.style.WARNING('  - 所有系统提示词已存在'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  ✓ 共创建 {created_count} 个系统提示词'))

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

    def _add_example_data(self):
        """添加示例数据"""
        self.stdout.write('\n🎯 正在添加示例数据...')

        # 添加示例记忆
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

        memory_count = 0
        for memory_data in example_memories:
            memory, created = MemoryLibrary.objects.get_or_create(
                title=memory_data['title'],
                defaults=memory_data
            )
            if created:
                memory_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ 添加 {memory_count} 条示例记忆'))

        # 添加示例计划任务
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

        task_count = 0
        for task_data in example_tasks:
            task, created = PlannedTask.objects.get_or_create(
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
        self.stdout.write('')
