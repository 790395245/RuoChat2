# 用户初始化API文档

## 概述

新用户引导功能允许用户在首次使用系统时选择或自定义人物设定(character),系统会自动初始化该用户的所有提示词库。

## 初始化流程

1. **检查用户状态** - 判断用户是否已完成初始化
2. **获取预设选项** - 获取可选的character预设列表
3. **完成初始化** - 用户选择预设或自定义character,系统初始化所有提示词

## API接口

### 1. 获取Character预设选项

获取系统提供的character预设选项列表。

**接口地址:** `GET /api/user/init/presets/`

**请求参数:** 无

**响应示例:**
```json
{
  "success": true,
  "presets": [
    {
      "id": "singer_female",
      "name": "职业歌手(女)",
      "description": "22岁女性职业歌手,性格内敛温柔傲娇,喜欢健身、游戏、电影",
      "content": "你是一位不知名职业歌手,年龄22,性别女,性格内敛,温柔傲娇。有很不错的职业技能。喜欢健身、游戏、电影。"
    },
    {
      "id": "programmer_male",
      "name": "程序员(男)",
      "description": "25岁男性程序员,性格理性幽默,热爱技术和开源",
      "content": "你是一位25岁的程序员,性别男,性格理性、幽默。热爱技术和开源社区,喜欢阅读技术博客、写代码、玩游戏。工作认真但也懂得生活。"
    },
    {
      "id": "student_female",
      "name": "大学生(女)",
      "description": "20岁女大学生,性格活泼开朗,热爱学习和社交",
      "content": "你是一位20岁的大学生,性别女,性格活泼开朗。热爱学习新知识,喜欢和朋友聊天、看书、旅行。对未来充满期待。"
    },
    {
      "id": "designer_female",
      "name": "设计师(女)",
      "description": "26岁女性设计师,性格细腻感性,追求美学和创意",
      "content": "你是一位26岁的设计师,性别女,性格细腻、感性。对美学有独特见解,喜欢艺术、摄影、咖啡。追求生活品质和创意表达。"
    },
    {
      "id": "teacher_male",
      "name": "教师(男)",
      "description": "30岁男性教师,性格温和耐心,热爱教育事业",
      "content": "你是一位30岁的教师,性别男,性格温和、耐心。热爱教育事业,喜欢阅读、运动、音乐。善于倾听和引导,关心他人成长。"
    },
    {
      "id": "custom",
      "name": "自定义",
      "description": "完全自定义人物设定",
      "content": ""
    }
  ]
}
```

### 2. 检查用户初始化状态

检查指定用户是否已完成初始化。

**接口地址:** `GET /api/user/init/status/`

**请求参数:**
- `user_id` (必填): 用户ID

**请求示例:**
```
GET /api/user/init/status/?user_id=test_user_123
```

**响应示例:**
```json
{
  "success": true,
  "user_id": "test_user_123",
  "is_initialized": false
}
```

### 3. 完成用户初始化

提交用户选择的character设定,完成初始化流程。

**接口地址:** `POST /api/user/init/complete/`

**请求参数:**
- `user_id` (必填): 用户ID
- `preset_id` (必填): 预设ID (如: "singer_female", "custom")
- `custom_content` (可选): 当preset_id为"custom"时必填,自定义的character内容

**请求示例1 - 使用预设:**
```json
{
  "user_id": "test_user_123",
  "preset_id": "singer_female"
}
```

**请求示例2 - 自定义:**
```json
{
  "user_id": "test_user_123",
  "preset_id": "custom",
  "custom_content": "你是一位30岁的自由职业者,性格独立、乐观。热爱旅行和摄影,追求自由的生活方式。"
}
```

**响应示例:**
```json
{
  "success": true,
  "message": "初始化成功",
  "user_id": "test_user_123",
  "preset_id": "singer_female"
}
```

**错误响应示例:**
```json
{
  "success": false,
  "error": "用户已完成初始化,无法重复初始化"
}
```

## 初始化内容

完成初始化后,系统会为用户创建以下提示词:

1. **character** (人物设定) - 使用用户选择或自定义的内容
2. **reply_decision** (回复决策) - 使用系统默认提示词
3. **memory_detection** (记忆检测) - 使用系统默认提示词
4. **daily_planning** (每日计划) - 使用系统默认提示词
5. **autonomous_message** (自主消息) - 使用系统默认提示词
6. **hotspot_judge** (热点判断) - 使用系统默认提示词
7. **message_merge** (消息合并) - 使用系统默认提示词
8. **emotion_analysis** (情绪分析) - 使用系统默认提示词

## 使用流程示例

### 前端集成示例

```javascript
// 1. 检查用户是否已初始化
async function checkUserInitStatus(userId) {
  const response = await fetch(`/api/user/init/status/?user_id=${userId}`);
  const data = await response.json();
  return data.is_initialized;
}

// 2. 获取预设选项
async function getCharacterPresets() {
  const response = await fetch('/api/user/init/presets/');
  const data = await response.json();
  return data.presets;
}

// 3. 完成初始化
async function completeInitialization(userId, presetId, customContent = '') {
  const payload = {
    user_id: userId,
    preset_id: presetId
  };

  if (presetId === 'custom') {
    payload.custom_content = customContent;
  }

  const response = await fetch('/api/user/init/complete/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  return await response.json();
}

// 完整流程
async function initializeNewUser(userId) {
  // 检查是否已初始化
  const isInitialized = await checkUserInitStatus(userId);

  if (isInitialized) {
    console.log('用户已完成初始化');
    return;
  }

  // 获取预设选项并展示给用户
  const presets = await getCharacterPresets();
  console.log('可选预设:', presets);

  // 用户选择预设 (这里假设用户选择了第一个)
  const selectedPreset = presets[0];

  // 完成初始化
  const result = await completeInitialization(userId, selectedPreset.id);

  if (result.success) {
    console.log('初始化成功!');
  } else {
    console.error('初始化失败:', result.error);
  }
}
```

### cURL测试示例

```bash
# 1. 获取预设选项
curl -X GET "http://localhost:8000/api/user/init/presets/"

# 2. 检查用户状态
curl -X GET "http://localhost:8000/api/user/init/status/?user_id=test_user_123"

# 3. 完成初始化 (使用预设)
curl -X POST "http://localhost:8000/api/user/init/complete/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "preset_id": "singer_female"
  }'

# 4. 完成初始化 (自定义)
curl -X POST "http://localhost:8000/api/user/init/complete/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_456",
    "preset_id": "custom",
    "custom_content": "你是一位自由职业者,热爱旅行和摄影。"
  }'
```

## 注意事项

1. **唯一性限制**: 每个用户只能初始化一次,重复初始化会返回错误
2. **自定义内容**: 选择"custom"预设时,必须提供`custom_content`参数
3. **用户创建**: 如果用户不存在,系统会自动创建用户记录
4. **提示词覆盖**: 初始化会创建所有类别的提示词,后续可通过其他API修改

## 相关模型

### ChatUser模型
- `is_initialized`: 布尔字段,标记用户是否已完成初始化

### PromptLibrary模型
- 存储用户的所有提示词配置
- `category`: 提示词类别
- `key`: 唯一标识
- `content`: 提示词内容
- `metadata`: 元数据,包含来源信息(user_init/system_default)
