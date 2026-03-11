---
name: discourse-webhook
description: Discourse Webhook 接收处理服务。独立运行，接收新帖通知，自动更新tag索引，无需耦合推荐逻辑。
---

# Discourse Webhook Service

Discourse Webhook 独立接收处理服务，负责实时更新tag索引。

## 功能

- ✅ 独立运行，与推荐Skill解耦
- ✅ 监听新帖事件，自动提取帖子tag
- ✅ 自动更新对应tag的索引文件
- ✅ 未知tag自动通知Agent审核
- ✅ 支持OpenClaw内置webhook或独立服务运行

## 目录结构

```
discourse-webhook/
├── SKILL.md
├── webhook_server.py    # 独立HTTP服务（可选）
├── config/
│   ├── config.json.example
│   └── config.json      # 用户创建，不提交
└── scripts/
    ├── webhook_handler.py  # Webhook处理逻辑
    └── utils.py            # 工具函数
```

## 配置方式

### 方式1：使用OpenClaw内置Webhook（推荐）

在 `~/.openclaw/openclaw.json` 中添加：

```json
{
  "webhooks": {
    "/webhook/discourse": {
      "handler": "shell",
      "command": "python3 /root/.openclaw/workspace/skills/discourse-webhook/scripts/webhook_handler.py --config /root/.openclaw/workspace/skills/discourse-webhook/config/config.json --payload '${payload}'"
    }
  }
}
```

重启网关：
```bash
openclaw gateway restart
```

### 方式2：独立运行HTTP服务

```bash
# 安装依赖
pip install flask requests

# 启动服务
python3 webhook_server.py
```

## Discourse 端配置

在 Discourse 管理后台设置 Webhook：
- **Payload URL**: `https://your-server-address/webhook/discourse`
- **Content Type**: `application/json`
- **触发事件**: `topic_created`

## 配置文件

复制 `config/config.json.example` 为 `config/config.json` 并填写：

```json
{
  "discourse_url": "https://your-discourse.example.com",
  "api_key": "your-discourse-api-key",
  "api_username": "system-username-for-api",
  "tag_root": "/root/.openclaw/workspace/skills/discourse-recommender-service/tags"
}
```

## 工作流程

```
新帖子创建 → Webhook触发 → 提取帖子tag → 检查tag是否存在
    ├─ ✅ 存在 → 更新对应tag的索引文件
    └─ ❌ 不存在 → 通知Agent审核处理
```
