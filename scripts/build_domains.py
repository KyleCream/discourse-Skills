#!/usr/bin/env python3
"""
构建领域定义文件
"""
import argparse
import json
import os
import sys
from pathlib import Path
from utils import load_config, save_cache

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = Path(SCRIPT_DIR).parent

def main():
    parser = argparse.ArgumentParser(description="构建领域定义文件")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--tag-group", help="tag分组配置文件，将多个tag合并为一个领域")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    tag_root = config['tag_root']
    
    print("="*60)
    print("构建领域定义")
    print("="*60)
    
    # 获取所有tag文件
    tag_files = [f for f in os.listdir(tag_root) if f.endswith('.json')]
    tags = [os.path.splitext(f)[0] for f in tag_files]
    
    print(f"\n发现 {len(tags)} 个tag:")
    for tag in tags:
        print(f"  - {tag}")
    
    # 加载tag分组（如果提供）
    tag_groups = {}
    if args.tag_group:
        with open(args.tag_group, 'r', encoding='utf-8') as f:
            tag_groups = json.load(f)
        print(f"\n加载tag分组配置，共 {len(tag_groups)} 个分组")
    
    # 构建领域定义
    domains = {}
    domain_id = 0
    
    # 处理分组
    for group_name, group_tags in tag_groups.items():
        domains[str(domain_id)] = {
            "name": group_name,
            "tags": group_tags,
            "description": f"包含tag: {', '.join(group_tags)}"
        }
        domain_id += 1
        # 从tags列表中移除已分组的tag
        for tag in group_tags:
            if tag in tags:
                tags.remove(tag)
    
    # 剩余tag每个单独作为一个领域
    for tag in tags:
        domains[str(domain_id)] = {
            "name": tag,
            "tags": [tag],
            "description": f"单独tag领域: {tag}"
        }
        domain_id += 1
    
    # 保存领域定义
    domains_data = {
        "domains": domains,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_domains": len(domains)
    }
    
    save_cache(config['domains_file'], domains_data)
    
    print(f"\n构建完成！共生成 {len(domains)} 个领域")
    print(f"领域定义已保存到: {config['domains_file']}")
    print("="*60)


if __name__ == "__main__":
    main()
