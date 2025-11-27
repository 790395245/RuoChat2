from django.core.management.base import BaseCommand
from core.models import PromptLibrary


class Command(BaseCommand):
    help = '初始化RuoChat系统数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新初始化（会清除已有数据）',
        )

    def handle(self, *args, **options):
        force = options['force']

        self.stdout.write(self.style.SUCCESS('开始初始化RuoChat系统...'))

        # 1. 初始化提示词库
        self._init_prompt_library(force)

        # 2. 创建必要的目录
        self._create_directories()

        self.stdout.write(self.style.SUCCESS('\n系统初始化完成！'))
        self.stdout.write('\n接下来的步骤：')
        self.stdout.write('1. 配置 .env 文件（复制 .env.example）')
        self.stdout.write('2. 设置 PostgreSQL 数据库')
        self.stdout.write('3. 运行: python manage.py migrate')
        self.stdout.write('4. 运行: python manage.py createsuperuser')
        self.stdout.write('5. 运行: python manage.py start_wechat')

    def _init_prompt_library(self, force):
        """初始化提示词库"""
        self.stdout.write('\n正在初始化提示词库...')

        # 默认人物设定
        default_character = """我是一个智能助手，具有以下特点：
- 性格：友好、热情、有耐心
- 职业：AI助手
- 爱好：帮助他人、学习新知识
- 沟通风格：简洁明了、富有同理心
"""

        if force:
            PromptLibrary.objects.filter(category='character', key='main_character').delete()

        prompt, created = PromptLibrary.objects.get_or_create(
            category='character',
            key='main_character',
            defaults={
                'content': default_character,
                'is_active': True,
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
                'content': '你需要根据对话内容和上下文，决定何时回复以及如何回复。考虑对话的紧急程度、情感色彩和当前状态。',
            },
            {
                'key': 'memory_detection',
                'content': '分析对话中是否包含值得记忆的信息点，如重要事件、个人偏好、情感时刻等。',
            },
            {
                'key': 'daily_planning',
                'content': '根据历史记忆和昨日任务，为今天生成合理的计划任务列表。',
            },
        ]

        for prompt_data in system_prompts:
            if force:
                PromptLibrary.objects.filter(category='system', key=prompt_data['key']).delete()

            prompt, created = PromptLibrary.objects.get_or_create(
                category='system',
                key=prompt_data['key'],
                defaults={
                    'content': prompt_data['content'],
                    'is_active': True,
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"  ✓ 创建系统提示词: {prompt_data['key']}"))

    def _create_directories(self):
        """创建必要的目录"""
        import os
        from pathlib import Path
        from django.conf import settings

        self.stdout.write('\n正在创建必要的目录...')

        directories = [
            settings.BASE_DIR / 'logs',
            settings.BASE_DIR / 'media',
        ]

        for directory in directories:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f'  ✓ 创建目录: {directory}'))
            else:
                self.stdout.write(self.style.WARNING(f'  - 目录已存在: {directory}'))
