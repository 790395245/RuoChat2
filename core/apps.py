from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'RuoChat核心模块'

    def ready(self):
        """应用启动时执行"""
        # 导入信号处理器
        try:
            import core.signals  # noqa
        except ImportError:
            pass

        # 启动定时任务调度器
        if not self._is_management_command():
            from core.scheduler import start_scheduler
            try:
                start_scheduler()
                logger.info("定时任务调度器已启动")
            except Exception as e:
                logger.error(f"启动定时任务调度器失败: {e}")

    @staticmethod
    def _is_management_command():
        """检查是否是管理命令（如migrate、makemigrations等）"""
        import sys
        return 'manage.py' in sys.argv[0] and any(
            cmd in sys.argv for cmd in ['migrate', 'makemigrations', 'createsuperuser']
        )
