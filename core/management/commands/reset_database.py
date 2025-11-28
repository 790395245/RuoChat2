"""
数据库重置命令
用于清除所有业务数据并重新创建数据表
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = '重置数据库：清除所有业务数据或完全重建数据表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hard',
            action='store_true',
            help='硬重置：删除所有数据表并重新创建迁移（危险操作）',
        )
        parser.add_argument(
            '--soft',
            action='store_true',
            help='软重置：只清除业务数据，保留表结构',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='只重置指定用户的数据（通过 user_id）',
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help='跳过确认提示',
        )

    def handle(self, *args, **options):
        hard_reset = options['hard']
        soft_reset = options['soft']
        user_id = options.get('user')
        skip_confirm = options['yes']

        if not hard_reset and not soft_reset:
            self.stdout.write(self.style.WARNING(
                '请指定重置类型：\n'
                '  --soft  软重置：只清除业务数据，保留表结构\n'
                '  --hard  硬重置：删除所有数据表并重新创建迁移（危险操作）\n'
                '  --user <user_id>  只重置指定用户的数据'
            ))
            return

        if user_id:
            self._reset_user_data(user_id, skip_confirm)
        elif soft_reset:
            self._soft_reset(skip_confirm)
        elif hard_reset:
            self._hard_reset(skip_confirm)

    def _reset_user_data(self, user_id: str, skip_confirm: bool):
        """重置指定用户的数据"""
        from core.models import (
            ChatUser, PromptLibrary, MemoryLibrary,
            PlannedTask, ReplyTask, MessageRecord
        )

        try:
            user = ChatUser.objects.get(user_id=user_id)
        except ChatUser.DoesNotExist:
            raise CommandError(f'用户 {user_id} 不存在')

        if not skip_confirm:
            self.stdout.write(self.style.WARNING(
                f'\n即将删除用户 "{user}" (ID: {user_id}) 的所有数据：\n'
                f'  - 提示词: {user.prompts.count()} 条\n'
                f'  - 记忆: {user.memories.count()} 条\n'
                f'  - 计划任务: {user.planned_tasks.count()} 条\n'
                f'  - 回复任务: {user.reply_tasks.count()} 条\n'
                f'  - 消息记录: {user.messages.count()} 条\n'
            ))
            confirm = input('确认删除？输入 "yes" 继续: ')
            if confirm != 'yes':
                self.stdout.write(self.style.NOTICE('操作已取消'))
                return

        # 删除用户相关数据
        deleted_counts = {
            '提示词': user.prompts.all().delete()[0],
            '记忆': user.memories.all().delete()[0],
            '计划任务': user.planned_tasks.all().delete()[0],
            '回复任务': user.reply_tasks.all().delete()[0],
            '消息记录': user.messages.all().delete()[0],
        }

        self.stdout.write(self.style.SUCCESS(f'\n用户 "{user}" 的数据已清除：'))
        for name, count in deleted_counts.items():
            self.stdout.write(f'  - {name}: {count} 条')

    def _soft_reset(self, skip_confirm: bool):
        """软重置：只清除业务数据"""
        from core.models import (
            ChatUser, PromptLibrary, MemoryLibrary,
            PlannedTask, ReplyTask, MessageRecord
        )

        # 统计现有数据
        counts = {
            '聊天用户': ChatUser.objects.count(),
            '提示词库': PromptLibrary.objects.count(),
            '记忆库': MemoryLibrary.objects.count(),
            '计划任务': PlannedTask.objects.count(),
            '回复任务': ReplyTask.objects.count(),
            '消息记录': MessageRecord.objects.count(),
        }

        if not skip_confirm:
            self.stdout.write(self.style.WARNING(
                '\n即将清除以下数据：'
            ))
            for name, count in counts.items():
                self.stdout.write(f'  - {name}: {count} 条')

            confirm = input('\n确认清除所有数据？输入 "yes" 继续: ')
            if confirm != 'yes':
                self.stdout.write(self.style.NOTICE('操作已取消'))
                return

        # 按顺序删除数据（注意外键约束）
        MessageRecord.objects.all().delete()
        ReplyTask.objects.all().delete()
        PlannedTask.objects.all().delete()
        MemoryLibrary.objects.all().delete()
        PromptLibrary.objects.all().delete()
        ChatUser.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('\n所有业务数据已清除！'))
        self.stdout.write('数据表结构保持不变，可以直接开始使用。')

    def _hard_reset(self, skip_confirm: bool):
        """硬重置：删除数据表并重新迁移"""
        if not skip_confirm:
            self.stdout.write(self.style.ERROR(
                '\n警告：硬重置将执行以下操作：\n'
                '  1. 删除所有 core 应用的数据表\n'
                '  2. 删除迁移记录\n'
                '  3. 重新执行迁移\n\n'
                '这是一个危险操作，所有数据将永久丢失！'
            ))
            confirm = input('\n确认执行硬重置？输入 "HARD RESET" 继续: ')
            if confirm != 'HARD RESET':
                self.stdout.write(self.style.NOTICE('操作已取消'))
                return

        self.stdout.write('开始硬重置...\n')

        # 获取要删除的表
        tables = [
            'message_record',
            'reply_task',
            'planned_task',
            'memory_library',
            'prompt_library',
            'chat_user',
        ]

        with connection.cursor() as cursor:
            # 删除数据表
            for table in tables:
                try:
                    cursor.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
                    self.stdout.write(f'  已删除表: {table}')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  删除表 {table} 失败: {e}'))

            # 清除迁移记录
            try:
                cursor.execute("DELETE FROM django_migrations WHERE app = 'core'")
                self.stdout.write('  已清除迁移记录')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  清除迁移记录失败: {e}'))

        self.stdout.write(self.style.SUCCESS('\n硬重置完成！'))
        self.stdout.write(self.style.WARNING(
            '\n请执行以下命令重新创建数据表：\n'
            '  python manage.py makemigrations core\n'
            '  python manage.py migrate'
        ))
