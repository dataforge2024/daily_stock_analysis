# Notion 集成使用说明

## 快速开始

### 1. 安装依赖

```bash
pip install notion-client
```

### 2. 自动创建数据库

```bash
# 设置环境变量
export NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 运行创建脚本
python scripts/create_notion_databases.py
```

按提示输入父页面ID，脚本会自动创建4个数据库并输出配置。

### 3. 配置环境变量

将脚本输出的配置添加到 `.env` 文件：

```bash
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_STOCK_ANALYSIS_DB=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_PORTFOLIO_DB=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_MARKET_REVIEW_DB=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_STOCK_SELECTION_DB=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. 运行测试

```bash
python main.py
```

查看 Notion 数据库中是否成功创建了记录。

## GitHub Actions 配置

在 Repository → Settings → Secrets and variables → Actions 中添加：

**Secrets:**
- `NOTION_TOKEN`: 你的 Integration Token

**Variables:**  
- `NOTION_STOCK_ANALYSIS_DB`
- `NOTION_PORTFOLIO_DB`
- `NOTION_MARKET_REVIEW_DB`
- `NOTION_STOCK_SELECTION_DB`

更新 workflow 文件添加环境变量：

```yaml
- name: 执行分析
  env:
    # Notion 配置
    NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
    NOTION_STOCK_ANALYSIS_DB: ${{ vars.NOTION_STOCK_ANALYSIS_DB }}
    NOTION_PORTFOLIO_DB: ${{ vars.NOTION_PORTFOLIO_DB }}
    NOTION_MARKET_REVIEW_DB: ${{ vars.NOTION_MARKET_REVIEW_DB }}
    NOTION_STOCK_SELECTION_DB: ${{ vars.NOTION_STOCK_SELECTION_DB }}
```

## 数据库结构

系统会在 Notion 中创建4个数据库：

1. **📊 股票分析** - 保存个股深度分析报告
2. **💼 调仓建议** - 保存持仓调整建议
3. **📈 大盘复盘** - 保存每日市场复盘
4. **⭐ 推荐股票** - 保存智能选股推荐

## 高级功能

### 自定义视图

在 Notion 数据库中可以创建多种视图：

- **表格视图**：查看所有记录
- **看板视图**：按操作建议分组（买入/持有/卖出）
- **日历视图**：按日期查看分析历史
- **画廊视图**：卡片式浏览

### 数据筛选

使用 Notion 的筛选功能：
- 筛选评分 > 70 的股票
- 筛选买入建议
- 按股票池筛选
- 按日期范围筛选

### 数据导出

Notion 支持导出为：
- CSV
- Markdown
- PDF
- HTML

详细配置步骤见 [docs/NOTION_SETUP.md](./NOTION_SETUP.md)
