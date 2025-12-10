#!/usr/bin/env python
"""
用户初始化功能测试脚本
"""
import os
import django
import sys

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RuoChat2.settings')
django.setup()

from core.models import ChatUser, PromptLibrary
from core.services.user_init_service import get_user_init_service


def test_get_presets():
    """测试获取预设选项"""
    print("\n=== 测试1: 获取预设选项 ===")
    user_init_service = get_user_init_service()
    presets = user_init_service.get_character_presets()

    print(f"✓ 成功获取 {len(presets)} 个预设选项:")
    for preset in presets:
        print(f"  - {preset['id']}: {preset['name']}")

    return True


def test_check_user_status():
    """测试检查用户状态"""
    print("\n=== 测试2: 检查用户状态 ===")

    # 测试不存在的用户
    test_user_id = "test_init_user_001"
    try:
        user = ChatUser.objects.get(user_id=test_user_id)
        print(f"✓ 用户 {test_user_id} 存在, is_initialized={user.is_initialized}")
    except ChatUser.DoesNotExist:
        print(f"✓ 用户 {test_user_id} 不存在 (预期行为)")

    return True


def test_initialize_user():
    """测试初始化用户"""
    print("\n=== 测试3: 初始化用户 ===")

    # 创建测试用户
    test_user_id = "test_init_user_002"

    # 清理可能存在的测试数据
    ChatUser.objects.filter(user_id=test_user_id).delete()

    # 创建新用户
    user = ChatUser.get_or_create_by_webhook(user_id=test_user_id, username="测试用户")
    print(f"✓ 创建用户: {user.user_id}")
    print(f"  初始化状态: {user.is_initialized}")

    # 初始化用户提示词
    user_init_service = get_user_init_service()
    preset = user_init_service.get_preset_by_id('singer_female')

    success = user_init_service.initialize_user_prompts(user, preset['content'])

    if success:
        print(f"✓ 用户初始化成功")

        # 验证提示词是否创建
        user.refresh_from_db()
        print(f"  用户is_initialized状态: {user.is_initialized}")

        prompts = PromptLibrary.objects.filter(user=user)
        print(f"  创建的提示词数量: {prompts.count()}")

        for prompt in prompts:
            print(f"    - {prompt.category}: {prompt.key}")

        # 清理测试数据
        print(f"\n✓ 清理测试数据...")
        prompts.delete()
        user.delete()

        return True
    else:
        print(f"✗ 用户初始化失败")
        return False


def test_duplicate_initialization():
    """测试重复初始化"""
    print("\n=== 测试4: 测试重复初始化保护 ===")

    test_user_id = "test_init_user_003"

    # 清理可能存在的测试数据
    ChatUser.objects.filter(user_id=test_user_id).delete()

    # 创建并初始化用户
    user = ChatUser.get_or_create_by_webhook(user_id=test_user_id, username="测试用户3")
    user_init_service = get_user_init_service()
    preset = user_init_service.get_preset_by_id('programmer_male')

    # 第一次初始化
    success1 = user_init_service.initialize_user_prompts(user, preset['content'])
    print(f"✓ 第一次初始化: {'成功' if success1 else '失败'}")

    # 尝试第二次初始化
    user.refresh_from_db()
    if user.is_initialized:
        print(f"✓ 用户已标记为已初始化，应该拒绝重复初始化")
        print(f"  (在API层面会返回错误，这里仅验证状态)")

    # 清理测试数据
    print(f"\n✓ 清理测试数据...")
    PromptLibrary.objects.filter(user=user).delete()
    user.delete()

    return True


def test_custom_character():
    """测试自定义character"""
    print("\n=== 测试5: 测试自定义character ===")

    test_user_id = "test_init_user_004"

    # 清理可能存在的测试数据
    ChatUser.objects.filter(user_id=test_user_id).delete()

    # 创建用户并使用自定义character
    user = ChatUser.get_or_create_by_webhook(user_id=test_user_id, username="测试用户4")
    custom_content = "你是一位自由职业者，热爱旅行和摄影。"

    user_init_service = get_user_init_service()
    success = user_init_service.initialize_user_prompts(user, custom_content)

    if success:
        print(f"✓ 自定义character初始化成功")

        # 验证character内容
        character_prompt = PromptLibrary.objects.get(
            user=user,
            category='character'
        )

        if character_prompt.content == custom_content:
            print(f"✓ Character内容验证成功")
            print(f"  内容: {character_prompt.content}")
        else:
            print(f"✗ Character内容不匹配")
            return False

        # 清理测试数据
        print(f"\n✓ 清理测试数据...")
        PromptLibrary.objects.filter(user=user).delete()
        user.delete()

        return True
    else:
        print(f"✗ 自定义character初始化失败")
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("用户初始化功能测试")
    print("=" * 60)

    tests = [
        test_get_presets,
        test_check_user_status,
        test_initialize_user,
        test_duplicate_initialization,
        test_custom_character,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False))

    # 输出测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {test_name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
