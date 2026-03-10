---
name: discourse-recommender-service
description: Discourse 论坛高级推荐服务。基于tag的智能推荐系统，支持新帖自动分配tag、交互式推荐、agent智能编写推荐理由、自动更新用户画像，开箱即用。
---

# Discourse Recommender Service

Discourse 论坛高级推荐服务。

---

## 完整技术路线

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         discourse-recommender-service                       │
└─────────────────────────────────────────────────────────────────────────────┘
【冷启动初始化】
  ├─ 加载 tag_dict（每个tag对应其帖子URL列表）
  ├─ 为每个tag创建初始领域配置
  └─ 生成 domains.json 领域定义（基于tag_dict）
       ↓
【定时领域维护（占位符 - 后续实现）】
  ├─ [预留接口供后续领域优化逻辑]
  ├─ [预留领域质量监控]
  └─ [预留领域合并/拆分逻辑]
       ↓
【Webhook 实时更新】
  ├─ 接收新帖通知
  ├─ 自动提取帖子自带tag
  ├─ 检查tag是否存在于现有tag_dict中
  ├─ ✅ 存在 → 自动分配到对应tag领域，更新tag索引
  └─ ❌ 不存在 → 通知agent审核，支持手动分配或创建新tag
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
  ├─ 步骤 2：与用户交互，确认推荐需求（可选）
  ├─ 步骤 3：加载用户画像
  ├─ 步骤 4：获取用户感兴趣tag下的帖子列表（从tag_dict的URL获取）
  ├─ 步骤 5：agent基于帖子内容、用户偏好进行智能筛选和排序
  ├─ 步骤 6：生成推荐列表
  ├─ 步骤 7：agent根据帖子内容编写智能推荐理由（必须手动写！）
  ├─ 步骤 8：返回给用户（飞书 + 站内信）
  └─ 步骤 9：根据此次推荐更新用户画像
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
- **冷启动初始化**：加载tag_dict → 为每个tag创建领域配置 → 生成domains.json
- **定时领域维护**：预留接口，后续实现领域优化、质量监控、合并/拆分逻辑
- **Webhook 实时更新**：新帖通知 → 自动识别tag → 合理tag自动分配 → 不合理tag通知agent审核
- **tag索引系统**：每个tag独立的帖子索引，无需分层缓存，直接从tag获取所有相关帖子

### 交互式推荐
- **用户主动问询**：获取用户信息 → 交互确认需求（可选）
- **从用户感兴趣领域获取帖子**：从用户tag领域获取所有相关帖子
- **Agent 智能筛选排序**：agent基于帖子内容、用户偏好进行智能筛选和排序
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
├── domains/                 # 每个领域一个子目录
│   ├── domain_0/
│   │   ├── l1_hot.json
│   │   └── l3_fresh.json
│   ├── domain_1/
│   │   ├── l1_hot.json
│   │   └── l3_fresh.json
│   └── ...
├── profiles/                # 用户画像存储
│   ├── zekang.chen.json
│   ├── Kayle.json
│   └── ...
├── domains.json            # 领域定义
├── user_domains.json       # 用户-领域映射
└── scripts/
    ├── init_cache.py        # 冷启动初始化（分类为领域）
    ├── build_user_profile.py # 为单个用户构建画像
    ├── cluster_domains.py   # 定时领域聚类 + agent 审核
    ├── webhook_handler.py   # Webhook 接收 + 分发更新
    ├── recommend.py         # 简单版推荐（从用户所属领域推荐）
    ├── utils.py             # 工具函数
    ├── interactive_recommend.py    # 交互式推荐 - 数据准备阶段
    └── update_profile_after_recommend.py  # 推荐完成后更新用户画像
```

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

## Webhook 配置

### 1. OpenClaw 端配置

在 OpenClaw 配置文件 `~/.openclaw/openclaw.json` 中添加 webhook 路由规则：

```json
{
  "webhooks": {
    "/webhook/discourse": {
      "handler": "shell",
      "command": "python3 /root/.openclaw/workspace/skills/discourse-recommender-service/scripts/webhook_handler.py --config /root/.openclaw/workspace/skills/discourse-recommender-service/config/config.json --payload '${payload}'"
    }
  }
}
```

### 3. 公网暴露配置（可选，需要Discourse能访问到）

默认OpenClaw网关仅监听本地127.0.0.1:18789，如果需要Discourse能访问到，有两种方式：

#### 方式1：修改OpenClaw网关绑定地址（推荐）
编辑 `~/.openclaw/openclaw.json`，添加或修改网关配置：
```json
{
  "gateway": {
    "port": 18789,
    "bind": "0.0.0.0"
  }
}
```
重启网关：
```bash
openclaw gateway restart
```
然后在服务器防火墙开放18789端口，Discourse直接访问 `https://your-server-ip:18789/webhook/discourse`

#### 方式2：使用Nginx反向代理
配置Nginx反向代理到本地18789端口：
```nginx
server {
    listen 80;
    server_name your-domain.com;
    location /webhook/discourse {
        proxy_pass http://127.0.0.1:18789/webhook/discourse;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
Discourse访问 `https://your-domain.com/webhook/discourse`

### 4. 测试webhook是否正常
本地测试：
```bash
curl -X POST http://127.0.0.1:18789/webhook/discourse \
  -H "Content-Type: application/json" \
  -d @/root/.openclaw/workspace/skills/discourse-recommender-service/real_webhook_payload.json
```

公网测试：
```bash
curl -X POST https://your-public-address/webhook/discourse \
  -H "Content-Type: application/json" \
  -d @/root/.openclaw/workspace/skills/discourse-recommender-service/real_webhook_payload.json
```

### 2. Discourse 端配置

在 Discourse 管理后台设置 webhook：

- **Payload URL**: `https://your-openclaw-server/webhook/discourse`（替换为你的服务器公网地址）
- **Content Type**: `application/json`
- **触发事件**: `topic_created`

---

## 基础设施功能

### 1. 冷启动初始化（两种方式）

#### 方式1：使用仓库自带的预初始化数据（推荐，开箱即用）
```bash
# 直接克隆仓库即可使用，已经包含完整的tag_dict和tag索引
git clone https://github.com/KyleCream/discourse-Skills.git
```

#### 方式2：全新初始化
```bash
# 自动获取Discourse分类作为初始tag
python3 scripts/init_cache.py --config config/config.json

# 或使用自定义tag字典
python3 scripts/init_cache.py --config config/config.json --tag-dict your_tag_dict.json
```

### 2. 脚本列表

| 脚本名称 | 功能说明 |
|----------|---------|
| `init_cache.py` | 冷启动初始化，生成tag领域和domains.json |
| `interactive_recommend.py` | 交互式推荐，数据准备阶段，输出候选帖子 |
| `webhook_handler.py` | Webhook处理，新帖自动分配tag |
| `assign_domain.py` | 手动/自动分配帖子到tag领域，支持自动创建新tag |
| `update_profile_after_recommend.py` | 推荐完成后更新用户画像 |
| `send_pm.py` | 发送Discourse站内信，支持直接发送文本或推荐列表 |
| `utils.py` | 工具函数，包含API客户端、配置加载、站内信发送等 |
| `build_user_profile.py` | 构建/更新单个用户画像 |
| `build_profile.py` | 批量构建用户画像 |

### 3. 接收 Webhook 更新（全自动流程）

新帖子创建
    ↓
Webhook 触发
    ↓
webhook_handler.py 接收新帖信息
    ↓
自动提取帖子自带的tag
    ↓
检查tag是否存在于现有tag_dict中
    ├─ ✅ 存在 → 自动调用assign_domain.py分配到对应tag领域，更新tag索引
    └─ ❌ 不存在 → 保存为待分配，通知agent审核处理

通过 OpenClaw webhook 调用：

```bash
python3 scripts/webhook_handler.py --config config/config.json --payload webhook_payload.json
```

#### 手动分配帖子（当tag不存在时）
```bash
# 分配到现有tag
python3 scripts/assign_domain.py --config config/config.json --topic-id <帖子ID> --tag <现有tag名称>

# 自动创建新tag并分配
python3 scripts/assign_domain.py --config config/config.json --topic-id <帖子ID> --tag <新tag名称>
```

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
步骤 3：运行 interactive_recommend.py（数据准备）
    ├─ 加载领域定义
    ├─ 加载用户画像
    ├─ 如果有关键词，更新用户画像
    ├─ 从用户感兴趣的tag领域加载所有相关帖子
    └─ 根据用户偏好排序
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
