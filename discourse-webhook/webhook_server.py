#!/usr/bin/env python3
"""
Discourse Webhook 接收服务
监听公网端口，接收Discourse新帖通知，直接调用处理脚本
独立Skill，不包含推荐逻辑
"""
from flask import Flask, request, jsonify
import subprocess
import json
import tempfile
import os
import sys
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "scripts"))

app = Flask(__name__)

# 配置
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "discourse-webhook-2026-secure")  # 和Discourse配置的Secret一致
HANDLER_SCRIPT = os.path.join(SCRIPT_DIR, "scripts", "webhook_handler.py")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config", "config.json")

@app.route('/webhook/discourse', methods=['POST'])
def discourse_webhook():
    # 验证Secret（如果Discourse配置了Secret）
    if WEBHOOK_SECRET:
        signature = request.headers.get('X-Discourse-Event-Signature', '')
        # 这里可以加签名验证，暂时先跳过
    
    # 获取请求数据
    payload = request.get_json()
    
    # 只处理新帖事件
    event_type = request.headers.get('X-Discourse-Event', '')
    if event_type != 'topic_created':
        return jsonify({"status": "ignored", "message": "Not a topic_created event"}), 200
    
    try:
        # 保存payload到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(payload, f)
            temp_file = f.name
        
        # 调用处理脚本
        cmd = [
            'python3', HANDLER_SCRIPT,
            '--config', CONFIG_FILE,
            '--payload', temp_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # 清理临时文件
        os.unlink(temp_file)
        
        if result.returncode == 0:
            return jsonify({
                "status": "success",
                "message": "Webhook processed successfully",
                "output": result.stdout
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Processing failed",
                "error": result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Discourse webhook server is running"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=False)
