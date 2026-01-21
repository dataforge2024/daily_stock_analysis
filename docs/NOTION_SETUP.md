# Notion 集成配置指南

## 功能说明

本系统支持将分析报告自动保存到 Notion 数据库，包括：
- 📊 股票分析报告
- 💼 调仓建议
- 📈 大盘复盘
- ⭐ 推荐股票列表

## 配置步骤

### 1. 创建 Notion Integration

1. 访问 [Notion Integrations](https://www.notion.so/my-integrations)
2. 点击「+ New integration」
3. 填写信息：
   - **Name**: `Stock Analysis Bot`（可自定义）
   - **Associated workspace**: 选择你的工作区
   - **Type**: Internal Integration
4. 点击「Submit」创建
5. 复制「Internal Integration Token」（以`secret_`开头）

### 2. 创建 Notion 数据库

#### 方法一：使用自动化脚本（推荐）

运行以下Python脚本自动创建所有数据库：

```python
python scripts/create_notion_databases.py
```

脚本会：
1. 读取你的 NOTION_TOKEN
2. 创建4个数据库并配置好属性
3. 输出数据库ID供你配置

#### 方法二：手动创建

在 Notion 中创建4个数据库，并配置以下属性：

##### 📊 股票分析数据库

| 属性名称 | 类型 | 说明 |
|---------|------|------|
| 股票名称 | Title | 主标题 |
| 股票代码 | Text | 如 600519 |
| 分析日期 | Date | 分析时间 |
| 评分 | Number | 0-100 |
| 操作建议 | Select | 买入/持有/卖出 |
| 趋势预测 | Text | 趋势描述 |

##### 💼 调仓建议数据库

| 属性名称 | 类型 | 说明 |
|---------|------|------|
| 标题 | Title | 主标题 |
| 日期 | Date | 分析日期 |
| 持仓数量 | Number | 股票数量 |

##### 📈 大盘复盘数据库

| 属性名称 | 类型 | 说明 |
|---------|------|------|
| 标题 | Title | 主标题 |
| 日期 | Date | 复盘日期 |

##### ⭐ 推荐股票数据库

| 属性名称 | 类型 | 说明 |
|---------|------|------|
| 股票名称 | Title | 主标题 |
| 股票代码 | Text | 代码 |
| 推荐日期 | Date | 推荐日期 |
| 股票池 | Select | 沪深300/中证500等 |
| 综合评分 | Number | 评分 |
| 最新价 | Number | 价格 |
| 涨跌幅 | Number | 涨跌幅% |
| AI评分 | Number | AI评分 |
| AI建议 | Select | AI建议 |

### 3. 分享数据库给 Integration

对于每个数据库：
1. 点击数据库右上角「···」
2. 选择「+ Add connections」
3. 搜索并选择你创建的 Integration
4. 点击「Invite」

### 4. 获取数据库ID

两种方法：

**方法1：从URL获取**
- 打开数据库
- 查看浏览器地址栏：`https://www.notion.so/{database_id}?v=...`
- 复制 `{database_id}` 部分（32位字符）

**方法2：使用脚本**
```bash
python scripts/get_notion_database_ids.py
```

### 5. 配置环境变量

在 `.env` 文件中添加：

```bash
# Notion 集成配置
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 数据库 ID（32位字符，不含横杠）
NOTION_STOCK_ANALYSIS_DB=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_PORTFOLIO_DB=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_MARKET_REVIEW_DB=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_STOCK_SELECTION_DB=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 6. 安装依赖

```bash
pip install notion-client
```

或添加到 `requirements.txt`：
```
notion-client>=2.0.0
```

## GitHub Actions 配置

在 GitHub Repository Settings → Secrets and variables → Actions 中添加：

**Secrets:**
- `NOTION_TOKEN`: 你的 Integration Token

**Variables:**
- `NOTION_STOCK_ANALYSIS_DB`
- `NOTION_PORTFOLIO_DB`
- `NOTION_MARKET_REVIEW_DB`
- `NOTION_STOCK_SELECTION_DB`

然后在 workflow 文件中添加环境变量：

```yaml
- name: 执行分析
  env:
    # ... 其他环境变量
    NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
    NOTION_STOCK_ANALYSIS_DB: ${{ vars.NOTION_STOCK_ANALYSIS_DB }}
    NOTION_PORTFOLIO_DB: ${{ vars.NOTION_PORTFOLIO_DB }}
    NOTION_MARKET_REVIEW_DB: ${{ vars.NOTION_MARKET_REVIEW_DB }}
    NOTION_STOCK_SELECTION_DB: ${{ vars.NOTION_STOCK_SELECTION_DB }}
```

## 使用示例

```python
from notion_service import get_notion_service

# 获取服务实例
notion = get_notion_service()

# 保存股票分析
notion.save_stock_analysis(analysis_results)

# 保存调仓建议
notion.save_portfolio_advice(portfolio_advice)

# 保存大盘复盘
notion.save_market_review(review_text, date="2026-01-20")

# 保存推荐股票
notion.save_stock_selection(selection_result)
```

## 自动化脚本

### `scripts/create_notion_databases.py`

自动创建所有必要的 Notion 数据库：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动创建 Notion 数据库
"""
import os
from notion_client import Client

def create_databases():
    token = os.getenv('NOTION_TOKEN')
    if not token:
        print("错误：请先设置 NOTION_TOKEN 环境变量")
        return
    
    client = Client(auth=token)
    
    # 获取默认页面ID（需要手动提供或从用户输入）
    parent_page_id = input("请输入父页面ID（在Notion中打开一个页面，从URL复制）: ").strip()
    
    databases = {}
    
    # 1. 股票分析数据库
    print("创建股票分析数据库...")
    db1 = client.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "📊 股票分析"}}],
        properties={
            "股票名称": {"title": {}},
            "股票代码": {"rich_text": {}},
            "分析日期": {"date": {}},
            "评分": {"number": {"format": "number"}},
            "操作建议": {"select": {"options": [
                {"name": "买入", "color": "green"},
                {"name": "持有", "color": "yellow"},
                {"name": "卖出", "color": "red"},
            ]}},
            "趋势预测": {"rich_text": {}},
        }
    )
    databases['NOTION_STOCK_ANALYSIS_DB'] = db1['id']
    print(f"✅ 股票分析数据库: {db1['id']}")
    
    # 2. 调仓建议数据库
    print("创建调仓建议数据库...")
    db2 = client.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "💼 调仓建议"}}],
        properties={
            "标题": {"title": {}},
            "日期": {"date": {}},
            "持仓数量": {"number": {"format": "number"}},
        }
    )
    databases['NOTION_PORTFOLIO_DB'] = db2['id']
    print(f"✅ 调仓建议数据库: {db2['id']}")
    
    # 3. 大盘复盘数据库
    print("创建大盘复盘数据库...")
    db3 = client.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "📈 大盘复盘"}}],
        properties={
            "标题": {"title": {}},
            "日期": {"date": {}},
        }
    )
    databases['NOTION_MARKET_REVIEW_DB'] = db3['id']
    print(f"✅ 大盘复盘数据库: {db3['id']}")
    
    # 4. 推荐股票数据库
    print("创建推荐股票数据库...")
    db4 = client.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "⭐ 推荐股票"}}],
        properties={
            "股票名称": {"title": {}},
            "股票代码": {"rich_text": {}},
            "推荐日期": {"date": {}},
            "股票池": {"select": {"options": [
                {"name": "沪深300", "color": "blue"},
                {"name": "中证500", "color": "purple"},
                {"name": "创业板50", "color": "pink"},
            ]}},
            "综合评分": {"number": {"format": "number"}},
            "最新价": {"number": {"format": "number"}},
            "涨跌幅": {"number": {"format": "percent"}},
            "AI评分": {"number": {"format": "number"}},
            "AI建议": {"select": {"options": [
                {"name": "买入", "color": "green"},
                {"name": "持有", "color": "yellow"},
                {"name": "卖出", "color": "red"},
            ]}},
        }
    )
    databases['NOTION_STOCK_SELECTION_DB'] = db4['id']
    print(f"✅ 推荐股票数据库: {db4['id']}")
    
    # 输出配置
    print("\n" + "=" * 60)
    print("数据库创建完成！请将以下配置添加到 .env 文件：")
    print("=" * 60)
    for key, value in databases.items():
        print(f"{key}={value}")
    print("=" * 60)

if __name__ == "__main__":
    create_databases()
```

## 故障排查

### 问题1：`Unauthorized` 错误
- 检查 NOTION_TOKEN 是否正确
- 确认 Token 以 `secret_` 开头

### 问题2：`object_not_found` 错误
- 确认数据库ID正确
- 确认已将数据库分享给 Integration

### 问题3：`validation_error` 错误
- 检查数据库属性配置是否匹配
- 确认 Select 选项已创建

## 更多信息

- [Notion API 文档](https://developers.notion.com/)
- [notion-client Python SDK](https://github.com/ramnes/notion-sdk-py)
