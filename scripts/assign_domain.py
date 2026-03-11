#!/usr/bin/env python3
"""
手动分配帖子到Tag领域
"""
import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from utils import load_config, load_cache, save_cache, DiscourseAPI


def main():
    parser = argparse.ArgumentParser(description="手动分配帖子到Tag领域")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--topic-id", required=True, help="帖子ID")
    parser.add_argument("--tag", required=True, help="目标Tag名称")
    parser.add_argument("--create-tag", action="store_true", help="如果Tag不存在则创建")
    parser.add_argument("--skill-dir", help="Skill 目录路径")
    
    args = parser.parse_args()
    
    if args.skill_dir:
        skill_dir = args.skill_dir
    else:
        skill_dir = Path(SCRIPT_DIR).parent
    
    print("="*70)
    print("🏷️  手动分配帖子到Tag")
    print("="*70)
    
    # 加载配置
    config = load_config(args.config)
    tags_dir = os.path.join(skill_dir, "tags")
    os.makedirs(tags_dir, exist_ok=True)
    
    # 获取帖子详情
    api = DiscourseAPI(config)
    print(f"\n📝 获取帖子详情: #{args.topic_id}")
    topic = api.get_topic(args.topic_id)
    
    if not topic:
        print(f"❌ 无法获取帖子 #{args.topic_id}")
        return
    
    title = topic.get('title', '无标题')
    print(f"   ✅ 帖子标题: {title}")
    
    # 检查Tag是否存在
    tag_file = os.path.join(tags_dir, f"{args.tag}.json")
    tag_exists = os.path.exists(tag_file)
    
    if not tag_exists:
        if args.create_tag:
            print(f"🆕 创建新Tag: {args.tag}")
            tag_data = {"topics": [], "created_at": sys.argv[0], "updated_at": sys.argv[0]}
            save_cache(tag_file, tag_data)
        else:
            print(f"❌ Tag '{args.tag}' 不存在，使用 --create-tag 参数创建")
            return
    
    # 加载Tag数据
    tag_data = load_cache(tag_file) or {"topics": []}
    topics = tag_data.get("topics", [])
    
    # 检查帖子是否已存在
    topic_id = int(args.topic_id)
    if any(t.get("id") == topic_id for t in topics):
        print(f"⚠️  帖子 #{topic_id} 已存在于Tag '{args.tag}' 中")
        return
    
    # 添加帖子到Tag
    topics.insert(0, topic)
    if len(topics) > 500:  # 每个Tag最多保留500帖
        topics = topics[:500]
    
    tag_data["updated_at"] = sys.argv[0]
    tag_data["topics"] = topics
    save_cache(tag_file, tag_data)
    
    print(f"\n✅ 已将帖子 #{topic_id} 分配到Tag '{args.tag}'")
    print(f"   当前Tag '{args.tag}' 共有 {len(topics)} 个帖子")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
