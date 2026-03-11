---
name: discourse-coldstart
description: Discourse 推荐系统冷启动工具。手动执行，全量拉取历史帖子，构建tag索引和领域数据，无需耦合推荐逻辑。
---

# Discourse Coldstart Tool

Discourse 推荐系统冷启动初始化工具，手动执行，全量构建数据。

## 功能

- ✅ 独立运行，与推荐Skill解耦
- ✅ 全量拉取Discourse历史帖子
- ✅ 自动按tag分类构建索引
- ✅ 生成领域定义文件
- ✅ 支持自定义tag字典
- ✅ 手动执行，不自动运行

## 目录结构

```
discourse-coldstart/
├── SKILL.md
├── config/
│   ├── config.json.example
│   └── config.json      # 用户创建，不提交
└── scripts/
    ├── init_cache.py       # 冷启动主脚本
    ├── build_domains.py    # 构建领域定义
    └── utils.py            # 工具函数
```

## 使用方法

### 1. 配置文件

复制 `config/config.json.example` 为 `config/config.json` 并填写：

```json
{
  "discourse_url": "https://your-discourse.example.com",
  "api_key": "your-discourse-api-key",
  "api_username": "system-username-for-api",
  "tag_root": "/root/.openclaw/workspace/skills/discourse-recommender-service/tags",
  "domains_file": "/root/.openclaw/workspace/skills/discourse-recommender-service/domains.json"
}
```

### 2. 执行冷启动

```bash
# 全量拉取所有帖子，按tag构建索引
python3 scripts/init_cache.py --config config/config.json

# 使用自定义tag字典
python3 scripts/init_cache.py --config config/config.json --tag-dict your_tag_dict.json

# 只拉取最近N天的帖子
python3 scripts/init_cache.py --config config/config.json --days 30
```

### 3. 构建领域定义（可选）

```bash
python3 scripts/build_domains.py --config config/config.json
```

## 输出

- `tags/` 目录下每个tag对应一个JSON文件，包含该tag下所有帖子
- `domains.json` 领域定义文件，包含tag与领域的映射关系

## 注意事项

- ⚠️ 手动执行，不要配置为自动运行
- ⚠️ 全量拉取可能需要较长时间，建议在低峰期执行
- ✅ 数据直接写入推荐Skill的tag目录，无需额外同步
