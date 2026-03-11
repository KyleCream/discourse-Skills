#!/usr/bin/env python3
"""
冷启动初始化脚本
全量拉取Discourse历史帖子，构建tag索引
独立Skill，不包含推荐逻辑
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from utils import load_config, load_cache, save_cache, get_discourse_client

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = Path(SCRIPT_DIR).parent

def main():
    parser = argparse.ArgumentParser(description="Discourse 冷启动初始化，构建tag索引")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--tag-dict", help="自定义tag字典文件路径")
    parser.add_argument("--days", type=int, help="只拉取最近N天的帖子")
    parser.add_argument("--limit", type=int, default=0, help="最大拉取帖子数量，0表示不限制")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    client = get_discourse_client(config)
    
    print("="*60)
    print("Discourse 冷启动初始化")
    print("="*60)
    
    # 加载自定义tag字典（如果提供）
    allowed_tags = None
    if args.tag_dict:
        with open(args.tag_dict, 'r', encoding='utf-8') as f:
            tag_dict = json.load(f)
            allowed_tags = list(tag_dict.keys())
        print(f"\n加载自定义tag字典，共 {len(allowed_tags)} 个tag")
    
    # 计算时间范围
    start_time = None
    if args.days:
        start_time = time.time() - args.days * 86400
        print(f"只拉取最近 {args.days} 天的帖子")
    
    # 拉取帖子
    print("\n开始拉取帖子...")
    page = 0
    total_posts = 0
    tag_counts = {}
    
    while True:
        try:
            # 拉取帖子列表
            response = client._session.get(
                f"{client.url}/latest.json",
                headers=client.headers,
                params={"page": page}
            )
            response.raise_for_status()
            data = response.json()
            
            topics = data.get('topic_list', {}).get('topics', [])
            if not topics:
                break
            
            for topic in topics:
                # 检查时间范围
                if start_time:
                    created_at = time.mktime(time.strptime(topic['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ"))
                    if created_at < start_time:
                        print(f"\n已到达时间范围，停止拉取")
                        break
                
                topic_id = topic['id']
                topic_tags = topic.get('tags', [])
                
                # 过滤不在白名单的tag
                if allowed_tags:
                    topic_tags = [t for t in topic_tags if t in allowed_tags]
                
                if not topic_tags:
                    continue
                
                # 获取完整帖子详情
                full_topic = client.get_topic(topic_id)
                if not full_topic:
                    continue
                
                # 更新每个tag的索引
                for tag in topic_tags:
                    tag_file = os.path.join(config['tag_root'], f"{tag}.json")
                    tag_data = load_cache(tag_file) or {"topics": []}
                    tag_topics = tag_data.get("topics", [])
                    
                    if not any(t.get("id") == topic_id for t in tag_topics):
                        tag_topics.insert(0, full_topic)
                        if len(tag_topics) > 500:  # 每个tag最多保留500帖
                            tag_topics = tag_topics[:500]
                        
                        tag_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                        tag_data["topics"] = tag_topics
                        save_cache(tag_file, tag_data)
                        
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
                total_posts += 1
                if args.limit and total_posts >= args.limit:
                    print(f"\n已达到最大拉取数量 {args.limit}，停止拉取")
                    break
                
                # 速率限制
                time.sleep(0.1)
                
                if total_posts % 10 == 0:
                    print(f"已处理 {total_posts} 帖...")
            
            if args.limit and total_posts >= args.limit:
                break
            
            page += 1
            print(f"处理完第 {page} 页，共 {total_posts} 帖")
            
        except Exception as e:
            print(f"❌ 拉取失败: {str(e)}")
            break
    
    print("\n" + "="*60)
    print(f"冷启动完成！")
    print(f"总处理帖子数: {total_posts}")
    print(f"更新的tag数量: {len(tag_counts)}")
    for tag, count in tag_counts.items():
        print(f"  - {tag}: {count} 帖")
    print("="*60)


if __name__ == "__main__":
    main()
