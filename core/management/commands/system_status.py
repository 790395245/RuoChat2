from django.core.management.base import BaseCommand
from core.models import ReplyTask, PlannedTask, MemoryLibrary, MessageRecord


class Command(BaseCommand):
    help = '显示系统状态统计信息'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== RuoChat系统状态 ===\n'))

        # 回复任务统计
        pending_tasks = ReplyTask.objects.filter(status='pending').count()
        completed_tasks = ReplyTask.objects.filter(status='completed').count()
        failed_tasks = ReplyTask.objects.filter(status='failed').count()

        self.stdout.write('回复任务：')
        self.stdout.write(f'  待执行: {pending_tasks}')
        self.stdout.write(f'  已完成: {completed_tasks}')
        self.stdout.write(f'  失败: {failed_tasks}')

        # 计划任务统计
        planned_pending = PlannedTask.objects.filter(status='pending').count()
        planned_completed = PlannedTask.objects.filter(status='completed').count()

        self.stdout.write('\n计划任务：')
        self.stdout.write(f'  待执行: {planned_pending}')
        self.stdout.write(f'  已完成: {planned_completed}')

        # 记忆库统计
        total_memories = MemoryLibrary.objects.count()
        hotspot_memories = MemoryLibrary.objects.filter(memory_type='hotspot').count()
        user_memories = MemoryLibrary.objects.filter(memory_type='user_memory').count()

        self.stdout.write('\n记忆库：')
        self.stdout.write(f'  总记忆数: {total_memories}')
        self.stdout.write(f'  热点记忆: {hotspot_memories}')
        self.stdout.write(f'  用户记忆: {user_memories}')

        # 消息记录统计
        total_messages = MessageRecord.objects.count()
        received_messages = MessageRecord.objects.filter(message_type='received').count()
        sent_messages = MessageRecord.objects.filter(message_type='sent').count()

        self.stdout.write('\n消息记录：')
        self.stdout.write(f'  总消息数: {total_messages}')
        self.stdout.write(f'  接收消息: {received_messages}')
        self.stdout.write(f'  发送消息: {sent_messages}')

        self.stdout.write('\n')
