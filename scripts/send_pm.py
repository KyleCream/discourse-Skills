#!/usr/bin/env python3
"""
发送Discourse站内信脚本
"""
import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from utils import load_config, send_discourse_pm, load_cache


def main():
    parser = argparse.ArgumentParser(description="发送Discourse站内信")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--to", required=True, help="目标用户名")
    parser.add_argument("--title", required=True, help="站内信标题")
    parser.add_argument("--content", required=True, help="站内信内容，或包含推荐结果的JSON文件路径")
    parser.add_argument("--top-k", type=int, default=5, help="推荐数量（当content是JSON文件时生效）")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    # 检查content是否是JSON文件
    content = args.content
    if os.path.exists(content) and content.endswith('.json'):
        # 从JSON文件加载推荐结果
        result = load_cache(content)
        recommendations = result.get("recommendations", [])
        
        if not recommendations:
            print("❌ JSON文件中没有推荐结果")
            return
        
        # 生成站内信内容
        pm_content = f"## {args.title}\n\n"
        for i, post in enumerate(recommendations[:args.top_k], 1):
            title = post.get('title', '无标题')
            post_id = post.get('id')
            url = f"{config['discourse_url']}/t/{post.get('slug', 'topic')}/{post_id}"
            posts = post.get('posts_count', 0)
            likes = post.get('like_count', 0)
            
            reasons = []
            if likes > 0:
                reasons.append(f"点赞 {likes}")
            if posts > 0:
                reasons.append(f"回复 {posts}")
            if likes + posts > 5:
                reasons.append("热度不错")
            if not reasons:
                reasons.append("综合推荐")
            
            pm_content += f"{i}. **[{title}]({url})**\n"
            pm_content += f"   - 回复: {posts} | 点赞: {likes}\n"
            pm_content += f"   - 理由: {', '.join(reasons)}\n\n"
        
        pm_content += "\n---\n*由 OpenClaw 自动推荐*"
        content = pm_content
    
    # 发送站内信
    success = send_discourse_pm(
        topics=[],  # 已经生成好content了，不需要再传topics
        base_url=config['discourse_url'],
        api_key=config['api_key'],
        api_username=config['api_username'],
        target_username=args.to,
        top_k=args.top_k
    )
    
    if success:
        print("✅ 站内信发送成功！")
    else:
        print("❌ 站内信发送失败！")


if __name__ == "__main__":
    main()
