#!/usr/bin/env python3
"""
交互式推荐脚本 - 与用户交互后生成推荐（有机结合新旧版）
"""
import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from utils import load_config, save_cache, load_cache, DiscourseAPI


def get_user_profile(skill_dir, username):
    """获取用户画像，如果不存在则创建新的"""
    profiles_dir = os.path.join(skill_dir, "profiles")
    profile_file = os.path.join(profiles_dir, f"{username}.json")
    
    if os.path.exists(profile_file):
        return load_cache(profile_file)
    
    # 创建新用户画像
    new_profile = {
        "username": username,
        "created_at": datetime.now().isoformat(),
        "interests": {
            "keywords": [],
            "domain_ids": [],  # 用户感兴趣的领域ID列表
            "recent_topics": []
        },
        "preferences": {
            "freshness_weight": 0.3,
            "popularity_weight": 0.4,
            "personalization_weight": 0.3
        },
        "interaction_history": [],
        "recommendation_history": []
    }
    
    return new_profile


def save_user_profile(skill_dir, username, profile):
    """保存用户画像"""
    profiles_dir = os.path.join(skill_dir, "profiles")
    os.makedirs(profiles_dir, exist_ok=True)
    profile_file = os.path.join(profiles_dir, f"{username}.json")
    profile["updated_at"] = datetime.now().isoformat()
    save_cache(profile_file, profile)


def get_tags_from_keywords(keywords, skill_dir):
    """根据关键词匹配对应的tag（直接匹配，不依赖domain文件）"""
    tags = set()
    tags_dir = os.path.join(skill_dir, "tags")
    
    if not os.path.exists(tags_dir):
        return list(tags)
    
    # 获取所有存在的tag
    existing_tags = [os.path.splitext(f)[0] for f in os.listdir(tags_dir) if f.endswith('.json')]
    
    # 关键词匹配tag名称（包含匹配）
    for kw in keywords:
        kw_lower = kw.lower()
        for tag in existing_tags:
            if kw_lower in tag.lower() or tag.lower() in kw_lower:
                tags.add(tag)
    
    return list(tags)


def load_posts_from_tags(skill_dir, tags):
    """从指定tag加载帖子（从tags目录下的JSON文件读取）"""
    tags_dir = os.path.join(skill_dir, "tags")
    all_posts = []
    
    if not os.path.exists(tags_dir):
        return all_posts
    
    for tag in tags:
        tag_file = os.path.join(tags_dir, f"{tag}.json")
        if not os.path.exists(tag_file):
            continue
        
        # 加载tag对应的帖子
        data = load_cache(tag_file)
        posts = data.get("topics", [])
        # 标记来源
        for post in posts:
            post["_tag"] = tag
            post["_pool"] = "tag"
        all_posts.extend(posts)
    
    return all_posts


def score_posts_by_preferences(posts, profile):
    """根据用户偏好给帖子打分（有机结合新旧版）"""
    preferences = profile.get("preferences", {})
    freshness_weight = preferences.get("freshness_weight", 0.3)
    popularity_weight = preferences.get("popularity_weight", 0.4)
    personalization_weight = preferences.get("personalization_weight", 0.3)
    
    interests = profile.get("interests", {})
    user_keywords = [k.lower() for k in interests.get("keywords", [])]
    recent_topic_ids = set(interests.get("recent_topics", []))
    
    scored = []
    for post in posts:
        score = 0.0
        post_id = post.get("id")
        title = post.get("title", "").lower()
        
        # 1. 热门度（来自旧版）
        popularity_score = (post.get("like_count", 0) * 2) + post.get("posts_count", 0)
        score += popularity_score * popularity_weight
        
        # 2. 新颖性（不推荐最近看过的）
        if post_id in recent_topic_ids:
            score -= 50
        
        # 3. 个性化匹配（关键词匹配）
        keyword_match = sum(1 for kw in user_keywords if kw in title)
        score += keyword_match * 10 * personalization_weight
        
        # 4. L1 池优先（热门池）
        if post.get("_pool") == "L1":
            score += 5
        
        scored.append((post, score))
    
    # 按分数排序
    scored.sort(key=lambda x: x[1], reverse=True)
    return [post for post, score in scored if score > -100]


def update_profile_with_keywords(profile, keywords):
    """根据用户输入的关键词更新用户画像"""
    interests = profile.setdefault("interests", {})
    profile_keywords = interests.setdefault("keywords", [])
    
    # 添加新关键词
    for keyword in keywords:
        keyword = keyword.strip()
        if keyword and keyword not in profile_keywords:
            profile_keywords.append(keyword)
    
    # 只保留最近 30 个关键词
    if len(profile_keywords) > 30:
        profile_keywords = profile_keywords[-30:]
    
    return profile


def main():
    parser = argparse.ArgumentParser(description="交互式推荐 - 数据准备阶段（基于Tag索引）")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--username", required=True, help="用户名")
    parser.add_argument("--keywords", help="推荐关键词（逗号分隔，用于匹配tag和更新用户画像）")
    parser.add_argument("--tags", help="指定tag（逗号分隔，可选，直接从指定tag获取帖子）")
    parser.add_argument("--skill-dir", help="Skill 目录路径")
    parser.add_argument("--top", type=int, default=5, help="推荐数量")
    parser.add_argument("--output", help="输出推荐结果到 JSON 文件")
    
    args = parser.parse_args()
    
    if args.skill_dir:
        skill_dir = args.skill_dir
    else:
        skill_dir = Path(SCRIPT_DIR).parent
    
    print("="*70)
    print("🤖 Discourse 交互式推荐 - 数据准备阶段（基于Tag索引）")
    print("="*70)
    
    # ========== 步骤 1：加载现有Tag列表 ==========
    print(f"\n🏷️  加载现有Tag列表...")
    tags_dir = os.path.join(skill_dir, "tags")
    existing_tags = []
    if os.path.exists(tags_dir):
        existing_tags = [os.path.splitext(f)[0] for f in os.listdir(tags_dir) if f.endswith('.json')]
    print(f"   ✅ 已加载 {len(existing_tags)} 个Tag")
    if existing_tags:
        print(f"   现有Tag: {', '.join(existing_tags[:10])}{'...' if len(existing_tags) > 10 else ''}")
    
    # ========== 步骤 2：加载/创建用户画像 ==========
    print(f"\n👤 加载用户画像: {args.username}")
    profile = get_user_profile(skill_dir, args.username)
    print(f"   ✅ 用户画像已加载（创建时间: {profile.get('created_at', '新用户')}）")
    
    # ========== 步骤 3：处理输入关键词（更新用户画像 + 匹配tag） ==========
    input_keywords = []
    if args.keywords:
        input_keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
        print(f"\n🔍 输入关键词: {', '.join(input_keywords)}")
        # 更新用户画像，加入这些关键词
        profile = update_profile_with_keywords(profile, input_keywords)
        save_user_profile(skill_dir, args.username, profile)
        print(f"   ✅ 用户画像已更新（关键词已加入）")
    
    # ========== 步骤 4：确定要从哪些tag获取帖子 ==========
    target_tags = []
    if args.tags:
        # 用户指定了tag
        target_tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        print(f"\n🎯 使用指定tag: {', '.join(target_tags)}")
    else:
        # 从用户画像获取兴趣关键词 + 当前输入关键词 → 匹配tag
        interests = profile.get("interests", {})
        user_keywords = interests.get("keywords", [])
        all_keywords = user_keywords + input_keywords
        
        if all_keywords:
            target_tags = get_tags_from_keywords(all_keywords, skill_dir)
            print(f"\n🎯 从关键词匹配tag: {', '.join(target_tags)}")
        else:
            # 新用户，加载所有tag
            tags_dir = os.path.join(skill_dir, "tags")
            if os.path.exists(tags_dir):
                target_tags = [os.path.splitext(f)[0] for f in os.listdir(tags_dir) if f.endswith('.json')]
                print(f"\n🎯 新用户，从所有tag获取: {', '.join(target_tags[:10])}{'...' if len(target_tags) > 10 else ''}")
    
    # ========== 步骤 5：从目标tag加载候选帖子 ==========
    print(f"\n📦 从tag加载候选帖子...")
    candidate_posts = load_posts_from_tags(skill_dir, target_tags)
    print(f"   ✅ 加载了 {len(candidate_posts)} 个候选帖子")
    
    # 去重
    seen_ids = set()
    unique_posts = []
    for post in candidate_posts:
        post_id = post.get("id")
        if post_id and post_id not in seen_ids:
            seen_ids.add(post_id)
            unique_posts.append(post)
    
    print(f"   🧹 去重后: {len(unique_posts)} 个帖子")
    
    # ========== 步骤 6：根据用户偏好排序（有机结合新旧版） ==========
    print(f"\n📊 根据用户偏好排序...")
    ranked_posts = score_posts_by_preferences(unique_posts, profile)
    final_posts = ranked_posts[:args.top]
    print(f"   ✅ 精选 Top {len(final_posts)} 个帖子")
    
    # ========== 步骤 7：输出结果 ==========
    result = {
        "username": args.username,
        "input_keywords": input_keywords,
        "target_tags": target_tags,
        "recommendations": final_posts,
        "generated_at": datetime.now().isoformat()
    }
    
    if args.output:
        save_cache(args.output, result)
        print(f"\n💾 推荐结果已保存到: {args.output}")
    
    # 显示推荐列表（供 agent 使用）
    print("\n" + "="*70)
    print("📋 推荐列表（供 agent 编写推荐理由）")
    print("="*70)
    
    config = load_config(args.config)
    for i, post in enumerate(final_posts, 1):
        post_id = post.get("id")
        title = post.get("title")
        slug = post.get("slug", "topic")
        url = f"{config['discourse_url']}/t/{slug}/{post_id}"
        tag = post.get("_tag", "?")
        pool = post.get("_pool", "?")
        
        print(f"\n{i}. {title}")
        print(f"   🔗 {url}")
        print(f"   🏷️ 标签: {tag}")
        print(f"   数据: id={post_id}, likes={post.get('like_count', 0)}, replies={post.get('posts_count', 0)}")
    
    print("\n" + "="*70)
    print("✅ 数据准备完成！请 agent 编写推荐理由并发送给用户")
    print("="*70)
    
    # 保存临时数据供后续更新画像使用
    temp_file = os.path.join(skill_dir, f"temp_{args.username}_recommendation.json")
    save_cache(temp_file, {
        "recommended_posts": final_posts,
        "input_keywords": input_keywords,
        "target_tags": target_tags
    })
    print(f"\n📝 临时数据已保存，用于后续更新用户画像")


if __name__ == "__main__":
    main()
