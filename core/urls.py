from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # 系统状态
    path('status/', views.system_status, name='system_status'),

    # 配置管理
    path('config/character/', views.set_character_config, name='set_character'),
    path('config/hotspot/', views.add_hotspot, name='add_hotspot'),

    # 任务管理
    path('tasks/planned/', views.list_planned_tasks, name='list_planned_tasks'),
    path('tasks/reply/', views.list_reply_tasks, name='list_reply_tasks'),

    # 记忆管理
    path('memories/', views.list_memories, name='list_memories'),

    # 消息记录
    path('messages/', views.list_messages, name='list_messages'),

    # 情绪管理
    path('emotions/', views.list_emotions, name='list_emotions'),
    path('emotions/status/', views.get_emotion_status, name='get_emotion_status'),
    path('emotions/record/', views.manual_emotion_record, name='manual_emotion_record'),

    # 用户初始化
    path('user/init/presets/', views.get_character_presets, name='get_character_presets'),
    path('user/init/status/', views.check_user_init_status, name='check_user_init_status'),
    path('user/init/complete/', views.complete_user_initialization, name='complete_user_initialization'),

    # Webhook API
    path('webhook/incoming/', views.webhook_incoming, name='webhook_incoming'),
    path('webhook/send/', views.webhook_send, name='webhook_send'),
    path('webhook/status/', views.webhook_status, name='webhook_status'),
    path('webhook/test/', views.webhook_test, name='webhook_test'),
]
