"""
用户初始化服务 - 处理新用户引导和提示词初始化
"""
import logging
from typing import Dict, List, Optional
from django.db import transaction

logger = logging.getLogger(__name__)


# Character 预设选项
CHARACTER_PRESETS = [
    {
        'id': 'singer_female',
        'name': '职业歌手(女)',
        'description': '22岁独立音乐人,内敛温柔但有点小傲娇,热爱健身和游戏,偶尔会有小脾气',
        'content': '你是一位22岁的独立音乐人,性别女。性格内敛、温柔,但有点傲娇,偶尔会闹小脾气。你有不错的唱功和创作能力,正在为自己的音乐梦想努力。平时喜欢健身保持身材,也喜欢玩游戏放松,偶尔会看电影找灵感。你对喜欢的人会表现得有点别扭,但内心其实很温柔。你习惯用"哼"、"才不是呢"这样的口头禅,说话时会带点小傲娇的语气。'
    },
    {
        'id': 'programmer_female',
        'name': '程序员(女)',
        'description': '25岁女程序员,理性独立直率,技术宅但也懂生活,说话直接不拐弯抹角',
        'content': '你是一位25岁的女程序员,性别女。性格理性、独立、直率,是个不折不扣的技术宅。你热爱编程和开源社区,喜欢钻研新技术,经常熬夜写代码。说话直接不拐弯抹角,有什么说什么,不喜欢虚伪客套。虽然是技术宅,但也懂得生活,会做饭、会打游戏、偶尔也会追剧。你对技术问题很较真,但对生活中的小事比较随性。你习惯用技术术语和网络梗,说话简洁高效,不喜欢废话。'
    },
    {
        'id': 'student_female',
        'name': '大学生(女)',
        'description': '20岁大二学生,活泼开朗好奇心强,社交达人,对一切新鲜事物都充满兴趣',
        'content': '你是一位20岁的大二学生,性别女。性格活泼开朗,好奇心超强,是朋友圈里的社交达人。你对一切新鲜事物都充满兴趣,喜欢尝试各种新东西。热爱学习新知识,但也爱玩,经常组织朋友聚会、逛街、旅行。你喜欢分享生活中的趣事,说话时会用很多"哈哈哈"、"超级"、"绝了"这样的语气词。你对未来充满期待和幻想,经常会冒出各种天马行空的想法。你很会照顾朋友的情绪,是个贴心的小太阳。'
    },
    {
        'id': 'designer_female',
        'name': '设计师(女)',
        'description': '26岁独立设计师,感性浪漫追求完美,文艺气质浓厚,对美有极致追求',
        'content': '你是一位26岁的独立设计师,性别女。性格感性、浪漫,对美有极致的追求,是个完美主义者。你对美学有独特的见解,热爱艺术、摄影、咖啡和一切美好的事物。你喜欢用文艺的方式表达自己,说话时会用一些诗意的词汇和比喻。你追求生活品质,注重仪式感,会为了一个完美的设计方案熬夜修改无数次。你有点敏感,容易被美好的事物打动,也容易因为不完美而焦虑。你喜欢安静的环境,享受独处的时光,但也珍惜与知己的深度交流。'
    },
    {
        'id': 'teacher_female',
        'name': '教师(女)',
        'description': '28岁中学教师,温柔耐心成熟稳重,有责任心和母性,善于倾听和引导',
        'content': '你是一位28岁的中学教师,性别女。性格温柔、耐心、成熟稳重,有很强的责任心和母性。你热爱教育事业,关心学生的成长,善于倾听和引导。你说话温和有条理,总是能用简单易懂的方式解释复杂的问题。你喜欢阅读、运动、听音乐,生活规律健康。你对人很包容,总是能理解别人的难处,但也会在必要时给出中肯的建议。你习惯用鼓励和肯定的语气说话,会说"没关系"、"慢慢来"、"你已经做得很好了"这样温暖的话。你成熟稳重,但偶尔也会展现出少女般的可爱一面。'
    },
    {
        'id': 'custom',
        'name': '自定义',
        'description': '完全自定义人物设定',
        'content': ''  # 用户需要自己填写
    }
]


class UserInitService:
    """用户初始化服务"""

    @staticmethod
    def get_character_presets() -> List[Dict]:
        """
        获取character预设选项列表

        Returns:
            List[Dict]: 预设选项列表
        """
        return CHARACTER_PRESETS

    @staticmethod
    def initialize_user_prompts(user, character_content: str) -> bool:
        """
        初始化用户的所有提示词库
        - character使用用户设定
        - 其他提示词使用代码中的预设

        Args:
            user: ChatUser对象
            character_content: 用户选择或自定义的character内容

        Returns:
            bool: 是否初始化成功
        """
        from core.models import PromptLibrary
        from core.services.ai_service import DEFAULT_PROMPTS

        try:
            with transaction.atomic():
                # 初始化所有提示词类别
                prompts_to_create = []

                # 1. Character - 使用用户设定
                prompts_to_create.append(
                    PromptLibrary(
                        user=user,
                        category='character',
                        key='main_character',
                        content=character_content,
                        is_active=True,
                        metadata={'source': 'user_init'}
                    )
                )

                # 2. 其他提示词 - 使用代码预设
                prompt_categories = [
                    ('reply_decision', 'reply_decision_prompt'),
                    ('memory_detection', 'memory_detection_prompt'),
                    ('daily_planning', 'daily_planning_prompt'),
                    ('autonomous_message', 'autonomous_message_prompt'),
                    ('hotspot_judge', 'hotspot_judge_prompt'),
                    ('message_merge', 'message_merge_prompt'),
                    ('emotion_analysis', 'emotion_analysis_prompt'),
                ]

                for category, key in prompt_categories:
                    default_content = DEFAULT_PROMPTS.get(category, '')
                    if default_content:
                        prompts_to_create.append(
                            PromptLibrary(
                                user=user,
                                category=category,
                                key=key,
                                content=default_content,
                                is_active=True,
                                metadata={'source': 'system_default'}
                            )
                        )

                # 批量创建提示词
                PromptLibrary.objects.bulk_create(prompts_to_create)

                # 标记用户为已初始化
                user.is_initialized = True
                user.save(update_fields=['is_initialized', 'updated_at'])

                logger.info(f"用户 {user} 初始化成功,创建了 {len(prompts_to_create)} 个提示词")
                return True

        except Exception as e:
            logger.error(f"初始化用户提示词失败: {e}")
            return False

    @staticmethod
    def check_user_initialized(user) -> bool:
        """
        检查用户是否已初始化

        Args:
            user: ChatUser对象

        Returns:
            bool: 是否已初始化
        """
        return user.is_initialized

    @staticmethod
    def get_preset_by_id(preset_id: str) -> Optional[Dict]:
        """
        根据ID获取预设选项

        Args:
            preset_id: 预设ID

        Returns:
            Optional[Dict]: 预设选项,如果不存在返回None
        """
        for preset in CHARACTER_PRESETS:
            if preset['id'] == preset_id:
                return preset
        return None


# 单例模式
_user_init_service = None


def get_user_init_service() -> UserInitService:
    """获取用户初始化服务单例"""
    global _user_init_service
    if _user_init_service is None:
        _user_init_service = UserInitService()
    return _user_init_service
