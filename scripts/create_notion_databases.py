#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动创建 Notion 数据库（使用 requests 直接调用 API）

使用方法：
1. 设置环境变量 NOTION_TOKEN
2. 运行脚本: python scripts/create_notion_databases.py
3. 输入父页面ID（从Notion页面URL复制）
4. 脚本会创建4个数据库并输出配置
"""
import os
import sys
import requests
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"


def create_database(token: str, parent_page_id: str, title: str, properties: dict):
    """创建 Notion 数据库"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": properties,
    }
    
    r = requests.post(f"{BASE_URL}/databases", headers=headers, data=json.dumps(payload))
    if r.status_code >= 300:
        raise RuntimeError(f"Failed to create {title}: {r.status_code} {r.text}")
    return r.json()


def create_databases():
    """创建所有必要的 Notion 数据库"""
    
    # 读取 Token
    token = os.getenv('NOTION_TOKEN')
    if not token:
        print("❌ 错误：请先设置 NOTION_TOKEN 环境变量")
        print("\n在 .env 文件中添加：")
        print("NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        return
    
    # 获取父页面ID
    print("=" * 60)
    print("Notion 数据库自动创建工具")
    print("=" * 60)
    print("\n1. 在 Notion 中打开一个页面（用于存放数据库）")
    print("2. 从浏览器地址栏复制页面ID")
    print("   格式: https://www.notion.so/xxx-{页面ID}?...")
    print("   示例: 如果URL是 https://www.notion.so/My-Page-a1b2c3d4...")
    print("         则ID是: a1b2c3d4e5f6...")
    print()
    
    parent_page_id = input("请输入父页面ID: ").strip()
    
    if not parent_page_id or len(parent_page_id) != 32:
        print("❌ 错误：页面ID格式不正确（应为32位字符）")
        return
    
    databases = {}
    
    try:
        # 1. 股票分析数据库
        print("\n📊 创建股票分析数据库...")
        db1 = create_database(token, parent_page_id, "📊 股票分析", {
            "Name": {"title": {}},
            "Code": {"rich_text": {}},
            "Date": {"date": {}},
            "Score": {"number": {"format": "number"}},
            "Action": {"select": {"options": [
                {"name": "强烈买入", "color": "green"},
                {"name": "买入", "color": "blue"},
                {"name": "持有", "color": "yellow"},
                {"name": "观望", "color": "orange"},
                {"name": "卖出", "color": "red"},
            ]}},
            "Trend": {"rich_text": {}},
        })
        databases['NOTION_STOCK_ANALYSIS_DB'] = db1['id']
        print(f"   ✅ 创建成功: {db1['id']}")
        
        # 2. 调仓建议数据库
        print("\n💼 创建调仓建议数据库...")
        db2 = create_database(token, parent_page_id, "💼 调仓建议", {
            "Title": {"title": {}},
            "Date": {"date": {}},
            "Count": {"number": {"format": "number"}},
        })
        databases['NOTION_PORTFOLIO_DB'] = db2['id']
        print(f"   ✅ 创建成功: {db2['id']}")
        
        # 3. 大盘复盘数据库
        print("\n📈 创建大盘复盘数据库...")
        db3 = create_database(token, parent_page_id, "📈 大盘复盘", {
            "Title": {"title": {}},
            "Date": {"date": {}},
        })
        databases['NOTION_MARKET_REVIEW_DB'] = db3['id']
        print(f"   ✅ 创建成功: {db3['id']}")
        
        # 4. 推荐股票数据库
        print("\n⭐ 创建推荐股票数据库...")
        db4 = create_database(token, parent_page_id, "⭐ 推荐股票", {
            "Name": {"title": {}},
            "Code": {"rich_text": {}},
            "Date": {"date": {}},
            "Pool": {"select": {"options": [
                {"name": "沪深300", "color": "blue"},
                {"name": "中证500", "color": "purple"},
                {"name": "创业板50", "color": "pink"},
                {"name": "科创50", "color": "green"},
                {"name": "上证50", "color": "orange"},
            ]}},
            "TotalScore": {"number": {"format": "number"}},
            "Price": {"number": {"format": "number"}},
            "Change": {"number": {"format": "percent"}},
            "AIScore": {"number": {"format": "number"}},
            "AIAction": {"select": {"options": [
                {"name": "强烈买入", "color": "green"},
                {"name": "买入", "color": "blue"},
                {"name": "持有", "color": "yellow"},
                {"name": "观望", "color": "orange"},
                {"name": "卖出", "color": "red"},
            ]}},
        })
        databases['NOTION_STOCK_SELECTION_DB'] = db4['id']
        print(f"   ✅ 创建成功: {db4['id']}")
        
        # 输出配置
        print("\n" + "=" * 60)
        print("✅ 所有数据库创建完成！")
        print("=" * 60)
        print("\n请将以下配置添加到 .env 文件：\n")
        for key, value in databases.items():
            print(f"{key}={value}")
        print("\n" + "=" * 60)
        print("\n下一步：")
        print("1. 复制上面的配置到 .env 文件")
        print("2. 在 Notion 中找到新创建的数据库")
        print("3. 分享每个数据库给你的 Integration")
        print("   （点击数据库右上角 ··· → Add connections → 选择你的 Integration）")
        print("4. 运行 python test_portfolio_local.py 测试")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        print("\n可能的原因：")
        print("1. NOTION_TOKEN 不正确")
        print("2. 页面ID不正确")
        print("3. Integration 没有权限访问该页面")
        print("\n解决方法：")
        print("1. 检查 NOTION_TOKEN 是否正确")
        print("2. 确认页面已分享给 Integration")
        print("   （打开页面 → 右上角 Share → Add people → 选择你的 Integration）")


if __name__ == "__main__":
    create_databases()
