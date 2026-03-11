#!/usr/bin/env python3
"""
Discourse Webhook 处理脚本
接收新帖信息，更新对应tag领域的索引
独立Skill，不包含推荐逻辑
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from utils import load_config, load_cache, save_cache, send_agent_notification

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = Path(SCRIPT_DIR).parent

def main():
    parser = argparse.ArgumentParser(description="Webhook 更新对应领域 L3")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--payload", required=True, help="Webhook payload")
    parser.add_argument("--tag-root", default="/root/.openclaw/workspace/skills/discourse-recommender-service/tags", help="Tag索引存储根目录")
    
    args = parser.parse_args()
    
    print("="*60)
    print("处理 Webhook（多领域）")
    print("="*60)
    
    with open(args.payload, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    
    topic = payload.get("topic", {})
    if not topic.get("id"):
        print("⚠️ 无效话题，跳过")
        return
    
    topic_tags = topic.get('tags', [])
    topic_id = topic.get("id")
    topic_title = topic.get("title")
    
    print(f"\n新帖子: {topic_title}")
    print(f"帖子ID: {topic_id}")
    print(f"自带Tags: {topic_tags}")
    
    updated_count = 0
    unknown_tags = []
    
    for tag in topic_tags:
        tag_file = os.path.join(args.tag_root, f"{tag}.json")
        if os.path.exists(tag_file):
            # 更新已有tag的索引
            tag_data = load_cache(tag_file) or {"topics": []}
            topics = tag_data.get("topics", [])
            
            if not any(t.get("id") == topic_id for t in topics):
                topics.insert(0, topic)
                if len(topics) > 200:  # 每个tag保留最近200帖
                    topics = topics[:200]
                
                tag_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                tag_data["topics"] = topics
                save_cache(tag_file, tag_data)
                print(f"✅ 已更新Tag '{tag}' 的索引（当前 {len(topics)} 帖）")
                updated_count += 1
        else:
            unknown_tags.append(tag)
            print(f"⚠️ 未知Tag '{tag}'，待Agent审核")
    
    if unknown_tags:
        # 发送通知给Agent处理未知Tag
        send_agent_notification(
            title="新帖包含未知Tag",
            message=f"帖子：{topic_title}\nID：{topic_id}\n未知Tags：{', '.join(unknown_tags)}",
            level="info"
        )
    
    print(f"\n处理完成：更新了 {updated_count} 个Tag索引，{len(unknown_tags)} 个未知Tag待处理")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
