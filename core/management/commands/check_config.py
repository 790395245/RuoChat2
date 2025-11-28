from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = '检查RuoChat系统配置'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('RuoChat 系统配置检查'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        all_ok = True

        # 1. 检查Django配置
        all_ok &= self._check_django_config()

        # 2. 检查数据库配置
        all_ok &= self._check_database_config()

        # 3. 检查OpenAI配置
        all_ok &= self._check_openai_config()

        # 4. 检查Webhook配置
        all_ok &= self._check_webhook_config()

        # 5. 检查文件系统
        all_ok &= self._check_filesystem()

        # 6. 检查数据库表
        all_ok &= self._check_database_tables()

        # 7. 检查初始数据
        all_ok &= self._check_initial_data()

        self.stdout.write('\n' + '=' * 60)
        if all_ok:
            self.stdout.write(self.style.SUCCESS('✓ 所有检查通过，系统可以正常启动！'))
        else:
            self.stdout.write(self.style.ERROR('✗ 存在配置问题，请修复后再启动'))
        self.stdout.write('=' * 60 + '\n')

    def _check_django_config(self):
        """检查Django基础配置"""
        self.stdout.write('\n🔧 检查Django配置...')
        all_ok = True

        checks = [
            ('SECRET_KEY', bool(settings.SECRET_KEY)),
            ('DEBUG', hasattr(settings, 'DEBUG')),
            ('ALLOWED_HOSTS', bool(settings.ALLOWED_HOSTS)),
        ]

        for name, status in checks:
            if status:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {name}: 已配置'))
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {name}: 未配置'))
                all_ok = False

        return all_ok

    def _check_database_config(self):
        """检查数据库配置"""
        self.stdout.write('\n💾 检查数据库配置...')
        all_ok = True

        # 检查数据库连接
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
            self.stdout.write(self.style.SUCCESS(f'  ✓ 数据库连接: 成功'))
            self.stdout.write(f'    PostgreSQL版本: {version.split(",")[0]}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ 数据库连接: 失败'))
            self.stdout.write(f'    错误: {str(e)}')
            all_ok = False

        # 检查数据库配置
        db_config = settings.DATABASES['default']
        config_items = [
            ('数据库名称', db_config.get('NAME')),
            ('数据库主机', db_config.get('HOST')),
            ('数据库端口', db_config.get('PORT')),
            ('数据库用户', db_config.get('USER')),
        ]

        for name, value in config_items:
            if value:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {name}: {value}'))
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {name}: 未配置'))
                all_ok = False

        return all_ok

    def _check_openai_config(self):
        """检查OpenAI配置"""
        self.stdout.write('\n🤖 检查OpenAI配置...')
        all_ok = True

        checks = [
            ('OPENAI_API_KEY', bool(getattr(settings, 'OPENAI_API_KEY', None))),
            ('OPENAI_MODEL', bool(getattr(settings, 'OPENAI_MODEL', None))),
            ('OPENAI_API_BASE', bool(getattr(settings, 'OPENAI_API_BASE', None))),
        ]

        for name, status in checks:
            if status:
                value = getattr(settings, name, '')
                # 隐藏API密钥的大部分内容
                if name == 'OPENAI_API_KEY' and value:
                    display_value = value[:8] + '...' + value[-4:]
                else:
                    display_value = value
                self.stdout.write(self.style.SUCCESS(f'  ✓ {name}: {display_value}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ {name}: 未配置'))
                if name == 'OPENAI_API_BASE':
                    self.stdout.write('    (可选配置，留空使用OpenAI官方接口)')
                else:
                    all_ok = False

        return all_ok

    def _check_webhook_config(self):
        """检查Webhook配置"""
        self.stdout.write('\n💬 检查Webhook配置...')

        webhook_url = getattr(settings, 'WEBHOOK_URL', '')
        webhook_user_ids = getattr(settings, 'WEBHOOK_USER_IDS', '')

        if webhook_url:
            self.stdout.write(self.style.SUCCESS('  ✓ WEBHOOK_URL: 已配置'))
            # 只显示 URL 的一部分
            display_url = webhook_url[:50] + '...' if len(webhook_url) > 50 else webhook_url
            self.stdout.write(f'    {display_url}')
        else:
            self.stdout.write(self.style.ERROR('  ✗ WEBHOOK_URL: 未配置'))
            self.stdout.write('    请在.env中设置 WEBHOOK_URL')
            return False

        if webhook_user_ids:
            self.stdout.write(self.style.SUCCESS(f'  ✓ WEBHOOK_USER_IDS: {webhook_user_ids}'))
        else:
            self.stdout.write(self.style.WARNING('  ⚠ WEBHOOK_USER_IDS: 未配置'))
            self.stdout.write('    建议在.env中设置默认接收用户ID')

        return True

    def _check_filesystem(self):
        """检查文件系统"""
        self.stdout.write('\n📁 检查文件系统...')
        all_ok = True

        directories = [
            ('BASE_DIR', settings.BASE_DIR),
            ('MEDIA_ROOT', settings.MEDIA_ROOT),
            ('日志目录', settings.BASE_DIR / 'logs'),
        ]

        for name, path in directories:
            if os.path.exists(path):
                # 检查是否可写
                if os.access(path, os.W_OK):
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {name}: {path} (可写)'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ⚠ {name}: {path} (不可写)'))
                    all_ok = False
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {name}: {path} (不存在)'))
                self.stdout.write('    请运行: python manage.py init_system')
                all_ok = False

        return all_ok

    def _check_database_tables(self):
        """检查数据库表"""
        self.stdout.write('\n📊 检查数据库表...')

        from django.db import connection

        required_tables = [
            'prompt_library',
            'memory_library',
            'planned_task',
            'reply_task',
            'message_record',
        ]

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                """)
                existing_tables = [row[0] for row in cursor.fetchall()]

            all_ok = True
            for table in required_tables:
                if table in existing_tables:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ 表 {table}: 存在'))
                else:
                    self.stdout.write(self.style.ERROR(f'  ✗ 表 {table}: 不存在'))
                    all_ok = False

            if not all_ok:
                self.stdout.write('\n    请运行数据库迁移: python manage.py migrate')

            return all_ok

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ 检查失败: {str(e)}'))
            return False

    def _check_initial_data(self):
        """检查初始数据"""
        self.stdout.write('\n📚 检查初始数据...')

        from core.models import PromptLibrary

        try:
            # 检查人物设定
            character_count = PromptLibrary.objects.filter(
                category='character',
                is_active=True
            ).count()

            if character_count > 0:
                self.stdout.write(self.style.SUCCESS(f'  ✓ 人物设定: {character_count} 个'))
            else:
                self.stdout.write(self.style.ERROR('  ✗ 人物设定: 未配置'))
                self.stdout.write('    请运行: python manage.py init_system')
                return False

            # 检查系统提示词
            system_prompt_count = PromptLibrary.objects.filter(
                category='system',
                is_active=True
            ).count()

            if system_prompt_count > 0:
                self.stdout.write(self.style.SUCCESS(f'  ✓ 系统提示词: {system_prompt_count} 个'))
            else:
                self.stdout.write(self.style.WARNING('  ⚠ 系统提示词: 未配置'))
                self.stdout.write('    建议运行: python manage.py init_system')

            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ 检查失败: {str(e)}'))
            self.stdout.write('    请确保已运行: python manage.py migrate')
            return False
