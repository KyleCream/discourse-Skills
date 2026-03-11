#!/usr/bin/env python3
"""
工具函数库
"""
import json
import os
import sys
import requests
from pathlib import Path

def load_config(config_path):
    """加载配置文件"""
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_cache(file_path):
    """加载缓存文件"""
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 加载缓存文件失败 {file_path}: {str(e)}")
        return None

def save_cache(file_path, data):
    """保存缓存文件"""
    # 确保目录存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ 保存缓存文件失败 {file_path}: {str(e)}")
        return False

def send_agent_notification(title, message, level="info"):
    """发送通知给Agent"""
    # 这里可以对接飞书/企业微信等通知渠道
    # 目前先打印到日志
    print(f"\n📢 [{level.upper()}] {title}")
    print(message)
    print("-" * 60)

def get_discourse_client(config):
    """获取Discourse API客户端"""
    class DiscourseClient:
        def __init__(self, url, api_key, api_username):
            self.url = url.rstrip('/')
            self.headers = {
                'Api-Key': api_key,
                'Api-Username': api_username,
                'Content-Type': 'application/json'
            }
        
        def get_topic(self, topic_id):
            """获取帖子详情"""
            try:
                response = requests.get(
                    f"{self.url}/t/{topic_id}.json",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"❌ 获取帖子失败 {topic_id}: {str(e)}")
                return None
    
    return DiscourseClient(
        config['discourse_url'],
        config['api_key'],
        config['api_username']
    )
