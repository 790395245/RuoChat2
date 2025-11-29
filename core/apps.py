from django.apps import AppConfig
import logging
import os

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
        # 避免在以下情况重复启动：
        # 1. Django runserver 的 reloader 进程（检查 RUN_MAIN 环境变量）
        # 2. 管理命令（如 migrate）
        if self._should_start_scheduler():
            from core.scheduler import start_scheduler
            try:
                start_scheduler()
                logger.info("定时任务调度器已启动")
            except Exception as e:
                logger.error(f"启动定时任务调度器失败: {e}")

    @staticmethod
    def _should_start_scheduler():
        """判断是否应该启动调度器"""
        import sys

        # 管理命令不启动调度器
        if 'manage.py' in sys.argv[0] and any(
            cmd in sys.argv for cmd in ['migrate', 'makemigrations', 'createsuperuser', 'collectstatic', 'check']
        ):
            return False

        # Django runserver 开发模式下，只在主进程中启动
        # RUN_MAIN 环境变量在 reloader 子进程中被设置为 'true'
        if os.environ.get('RUN_MAIN') != 'true' and 'runserver' in sys.argv:
            return False

        return True
