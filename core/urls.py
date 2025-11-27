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
]
