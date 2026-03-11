---
name: discourse-recommender-service
description: Discourse 论坛高级推荐服务。基于tag的智能推荐系统，支持交互式推荐、agent智能编写推荐理由、自动更新用户画像，开箱即用。
---

# Discourse Recommender Service

Discourse 论坛高级推荐服务。

---

## 完整技术路线

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         discourse-recommender-service                       │
└─────────────────────────────────────────────────────────────────────────────┘
       ↓
【用户画像】
  ├─ 记录用户感兴趣的tag领域（tag_ids）
  ├─ 记录用户兴趣关键词（keywords）
  ├─ 记录最近浏览的帖子（recent_topics）
  ├─ 记录推荐历史（recommendation_history）
  └─ 用户偏好权重（新鲜度/热度/个性化）
       ↓
【用户主动问询 → 交互式推荐】
  ├─ 步骤 1：获取用户ID/用户名
  ├─ 步骤 2：与用户交互，确认推荐需求（可选，提取关键词）
  ├─ 步骤 3：加载用户画像（包含用户感兴趣的tag、关键词、历史偏好）
  ├─ 步骤 4：【算法匹配】根据用户画像的tag和关键词，从对应tag索引中获取候选帖子列表
  ├─ 步骤 5：【Agent智能筛选】agent基于帖子内容、用户偏好进行二次筛选和排序
  ├─ 步骤 6：生成推荐列表
  ├─ 步骤 7：agent根据帖子内容编写智能推荐理由（必须手动写！）
  ├─ 步骤 8：返回给用户（飞书 + 站内信）
  └─ 步骤 9：根据此次推荐更新用户画像（新增推荐的tag到用户兴趣）
       ↓
【更新用户画像】
  ├─ 提取推荐帖子的tag，加入用户感兴趣的tag领域
  ├─ 提取推荐帖子的关键词，加入用户兴趣
  ├─ 记录推荐历史
  ├─ 更新最近浏览的帖子列表
  └─ 清理临时文件
```

---

## 核心架构

### 基础设施
- **tag索引系统**：每个tag独立的帖子索引，无需分层缓存，直接从tag获取所有相关帖子

### 交互式推荐
- **用户主动问询**：获取用户信息 → 交互确认需求（可选，提取关键词）
- **算法自动匹配tag**：根据用户画像中的兴趣tag和当前问询的关键词，自动匹配对应的tag索引
- **从匹配的tag领域获取候选帖子**：从匹配的tag索引中加载所有相关帖子，按时间/热度初步排序
- **Agent 智能筛选排序**：agent基于帖子内容、用户偏好进行二次筛选和个性化排序
- **Agent 智能推荐理由**：必须由 agent 手动编写，禁止代码自动生成
- **自动更新用户画像**：记录用户感兴趣的tag领域、关键词、推荐历史

---

## tag索引系统设计

每个tag对应独立的索引文件，无需分层缓存：

| 项目 | 说明 | 存储位置 |
|------|------|---------|
| tag_dict | 所有tag对应的帖子URL列表 | domains.json |
| tag索引 | 每个tag下所有帖子的详细信息（标题、链接、作者、关键词等） | tags/{tag名称}.json |
| 领域定义 | tag与领域ID的映射关系 | domains.json |

---

## 用户画像结构

```json
{
  "username": "用户名",
  "created_at": "创建时间",
  "updated_at": "更新时间",
  "interests": {
    "keywords": ["AI", "编程", "GitHub"],           // 用户兴趣关键词
    "domain_ids": ["4", "2"],                        // 用户感兴趣的领域ID
    "recent_topics": [1, 2, 3]                       // 最近浏览的帖子
  },
  "preferences": {
    "freshness_weight": 0.3,
    "popularity_weight": 0.4,
    "personalization_weight": 0.3
  },
  "interaction_history": [],
  "recommendation_history": [
    {
      "timestamp": "时间",
      "recommended_post_ids": [1, 2, 3],
      "feedback": "用户反馈（可选）"
    }
  ]
}
```

---

## 目录结构

```
discourse-recommender-service/
├── SKILL.md
├── config/
│   ├── config.json.example
│   └── config.json          # (用户创建，不提交)
├── tags/                    # Tag索引目录（由discourse-init和discourse-webhook更新）
│   ├── 游戏.json
│   ├── nba.json
│   ├── 体育.json
│   └── ...
├── profiles/                # 用户画像存储
│   ├── zekang.chen.json
│   ├── Kayle.json
│   └── ...
├── domains.json            # 领域定义（由discourse-init生成）
└── scripts/
    ├── build_user_profile.py # 为单个用户构建画像
    ├── cluster_domains.py   # 定时领域聚类 + agent 审核
    ├── recommend.py         # 简单版推荐（从用户所属领域推荐）
    ├── utils.py             # 工具函数
    ├── interactive_recommend.py    # 交互式推荐 - 数据准备阶段
    ├── update_profile_after_recommend.py  # 推荐完成后更新用户画像
    ├── assign_domain.py     # 手动/自动分配帖子到tag领域
    ├── build_profile.py     # 批量构建用户画像
    └── send_pm.py           # 发送Discourse站内信
```

**注意**：冷启动和Webhook功能已拆分为独立Skill：
- 冷启动初始化：使用 [discourse-init](https://github.com/KyleCream/discourse-init) Skill
- Webhook实时更新：使用 [discourse-webhooks](https://github.com/KyleCream/discourse-webhooks) Skill

---

## 配置
判断config文件夹下是否有config.json文件，有则之前已经创建过，无则为首次使用
首次使用前，复制 `config/config.json.example` 为 `config/config.json` 并填写：

```json
{
  "discourse_url": "https://your-discourse.example.com",
  "api_key": "your-discourse-api-key",
  "api_username": "system-username-for-api"
}
```

---



---

## 脚本列表

| 脚本名称 | 功能说明 |
|----------|---------|
| `interactive_recommend.py` | 交互式推荐，数据准备阶段，输出候选帖子 |
| `assign_domain.py` | 手动/自动分配帖子到tag领域，支持自动创建新tag |
| `update_profile_after_recommend.py` | 推荐完成后更新用户画像 |
| `send_pm.py` | 发送Discourse站内信，支持直接发送文本或推荐列表 |
| `utils.py` | 工具函数，包含API客户端、配置加载、站内信发送等 |
| `build_user_profile.py` | 构建/更新单个用户画像 |
| `build_profile.py` | 批量构建用户画像 |

### 4. 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/KyleCream/discourse-Skills.git ~/.openclaw/workspace/skills/discourse-recommender-service

# 2. 创建配置文件
cd ~/.openclaw/workspace/skills/discourse-recommender-service
cp config/config.json.example config/config.json
# 编辑config.json，填写你的Discourse API信息

# 3. 测试推荐
python3 scripts/interactive_recommend.py --config config/config.json --username 你的用户名 --keywords "AI,开发" --top 3
```

---

## 交互式推荐功能

### 完整流程

```
用户主动问询
    ↓
步骤 1：获取用户ID/用户名
    ↓
步骤 2：与用户交互，确认推荐需求（可选）
    ↓
步骤 3：运行 interactive_recommend.py（数据准备 - 算法自动匹配）
    ├─ 加载领域定义和tag映射
    ├─ 加载用户画像（提取用户已有的兴趣tag）
    ├─ 分析用户当前问询的关键词，匹配对应的tag
    ├─ 合并用户历史兴趣tag和当前关键词匹配的tag
    ├─ 从所有匹配的tag索引中加载相关帖子
    └─ 按时间/热度/相关性初步排序，生成候选列表
    ↓
步骤 4：Agent 查看输出，编写智能推荐理由
    └─ 【重要】必须手动编写！禁止代码自动生成！
    ↓
步骤 5：发送给用户（飞书 + 站内信）
    ↓
步骤 6：运行 update_profile_after_recommend.py（更新画像）
    ├─ 提取推荐帖子的领域，加入用户感兴趣的领域
    ├─ 提取推荐帖子的关键词，加入用户兴趣
    ├─ 记录推荐历史
    ├─ 更新最近浏览的帖子列表
    └─ 清理临时文件
```

---

### 步骤 1：用户主动问询，获取用户信息

用户说："给我推荐一些帖子"

Agent 应该：
1. 获取用户名（从消息上下文或询问用户）
2. 询问用户想要什么类型的推荐（可选）

示例交互：
> Agent: "好的，你想要什么类型的帖子？比如：AI 相关、GitHub 项目、技术分享等"

---

### 步骤 2：运行交互式推荐脚本（数据准备阶段）

获取用户和关键词后，运行：

```bash
cd /path/to/discourse-recommender-service

# 交互式推荐 - 数据准备
python3 scripts/interactive_recommend.py \
  --config config/config.json \
  --username zekang.chen \
  --keywords "GitHub,AI,编程" \
  --top 5
```

**参数说明：**
- `--config`: 配置文件路径
- `--username`: 用户名
- `--keywords`: 推荐关键词，逗号分隔（可选，用于更新用户画像）
- `--domain-ids`: 指定领域ID，逗号分隔（可选，默认从用户画像获取）
- `--top`: 推荐数量（默认 5）
- `--output`: 输出推荐结果到 JSON 文件（可选）
- `--skill-dir`: Skill 目录路径（可选）

**脚本会输出：**
1. 领域定义加载情况
2. 用户画像加载情况
3. 目标领域确认
4. 从目标tag领域加载所有相关帖子
5. 根据用户偏好排序后的推荐列表（供 agent 编写推荐理由）

---

### 步骤 3：Agent 编写智能推荐理由

**⚠️ 重要：推荐理由必须由 Agent 手动编写，不能用代码自动生成！**

Agent 应该：
1. 查看脚本输出的推荐列表
2. 逐个查看帖子内容（通过 API 获取或点击链接）
3. 为每个帖子写个性化的推荐理由
4. 格式：标题 + 链接 + 推荐理由

**推荐理由示例：**
```
### 1. ai-code-reviewer - 基于大语言模型的自动化代码审查工具
🔗 链接：https://zyt.discourse.diy/t/topic/54

**推荐理由**：这是一个基于大语言模型的自动化代码审查工具。对于开发者来说非常实用，可以自动审查代码质量、发现潜在问题、提供改进建议，大幅提升代码审查效率。
```

---

### 步骤 4：发送给用户

通过飞书和站内信发送推荐：
- **飞书**：直接在对话中发送
- **站内信**：使用 `send_pm.py` 脚本发送

#### 站内信发送示例：
```bash
# 直接发送文本内容
python3 scripts/send_pm.py --config config/config.json --to zekang.chen --title "🤖 为你推荐的帖子" --content "这里是推荐内容"

# 从推荐结果JSON文件发送
python3 scripts/send_pm.py --config config/config.json --to zekang.chen --title "🤖 为你推荐的帖子" --content temp_recommendation.json
```

---

### 步骤 5：更新用户画像

推荐完成后，运行更新脚本：

```bash
python3 scripts/update_profile_after_recommend.py \
  --config config/config.json \
  --username zekang.chen \
  --feedback "用户反馈（可选）"
```

**参数说明：**
- `--config`: 配置文件路径
- `--username`: 用户名
- `--feedback`: 用户反馈（可选）
- `--temp-file`: 临时推荐数据文件路径（可选，默认自动查找）
- `--skill-dir`: Skill 目录路径（可选）

**脚本会自动：**
1. 加载用户画像
2. 从临时文件加载推荐数据
3. 提取推荐帖子的领域，加入用户感兴趣的领域
4. 提取推荐帖子的关键词，加入用户兴趣
5. 记录推荐历史
6. 更新最近浏览的帖子列表
7. 保存用户画像
8. 清理临时文件

---

## 完整使用示例

### 场景：用户要 AI-coding 相关推荐

**1. 用户询问**
> 用户："给我推荐一些 AI-coding 相关的帖子"

**2. Agent 交互（可选，如果需要更明确的需求）**
> Agent："好的，你是想要 AI 编程工具、代码审查、还是其他特定类型？"
> 用户："AI 编程工具就行"

**3. 运行数据准备脚本**
```bash
python3 scripts/interactive_recommend.py \
  --config config/config.json \
  --username zekang.chen \
  --keywords "AI,coding,编程,代码" \
  --top 3
```

**4. Agent 查看输出，编写推荐理由**
（查看脚本输出的推荐列表，逐个写理由）

**5. 发送给用户**
（飞书 + 站内信）

**6. 更新用户画像**
```bash
python3 scripts/update_profile_after_recommend.py \
  --config config/config.json \
  --username zekang.chen
```

---

## 注意事项

- ✅ **开箱即用**：仓库已包含预初始化的tag_dict和tag索引，无需重新初始化即可使用
- ⚠️ **推荐理由必须由 Agent 手动编写**，禁止使用代码自动生成的模板理由
- 🎯 **智能筛选**：agent基于帖子内容、用户偏好进行智能筛选和排序，不是简单关键词匹配
- 🔒 配置文件 `config/config.json` 包含敏感信息，请勿提交到版本控制
- 📂 tag索引位于 `tags/` 目录，每个tag对应一个JSON文件
- 👤 用户画像位于 `profiles/` 目录，记录用户兴趣和推荐历史
- 🔑 API Key 需要有足够权限（读取帖子、用户信息、发送站内信）
- 🧹 临时文件会在更新画像后自动清理
- 🌐 多OpenClaw实例支持：所有数据都在仓库中，其他实例克隆后即可使用
