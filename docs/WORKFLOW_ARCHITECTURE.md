# GitHub Actions Workflow 架构说明

## 📋 当前 Workflow 架构

### 现有 Workflows

| Workflow 文件 | 名称 | 功能 | 触发方式 |
|--------------|------|------|---------|
| `daily_analysis.yml` | 每日股票分析 | **全功能**：个股分析 + 大盘复盘 | 定时 + 手动 |
| `stock_selection.yml` | AI 智能选股 | **仅智能选股**：从股票池推荐股票 | 定时 + 手动 |

### 功能对应关系

| 功能 | 在 `daily_analysis.yml` | 在 `stock_selection.yml` | main.py 入口 |
|------|----------------------|------------------------|-------------|
| **智能选股** | ✅ 支持（需配置 STOCK_POOLS） | ✅ 专用 | `select_stocks()` |
| **个股深度分析** | ✅ 支持（需配置 STOCK_LIST） | ❌ 不支持 | `StockAnalysisPipeline.run()` |
| **调仓建议** | ✅ 支持（需配置 STOCK_LIST） | ❌ 不支持 | `analyze_portfolio()` |
| **大盘复盘** | ✅ 支持（可选） | ❌ 不支持 | `MarketAnalyzer` |

---

## 🎯 统一 Workflow 方案

### 方案 1：扩展现有 `daily_analysis.yml`（推荐）

**优点**：
- ✅ 一个 workflow 完成所有功能
- ✅ 配置统一，便于管理
- ✅ 可以根据环境变量自动判断运行哪些功能

**缺点**：
- ⚠️ 所有功能都运行可能耗时较长

**实现方式**：
1. 保留 `daily_analysis.yml` 作为主 workflow
2. 删除或禁用 `stock_selection.yml`
3. 通过环境变量控制功能开关

### 方案 2：保持独立 Workflows（当前方案）

**优点**：
- ✅ 职责清晰，选股独立运行
- ✅ 互不影响，失败隔离

**缺点**：
- ⚠️ 配置分散，需要维护两个 workflow
- ⚠️ 功能重叠时可能重复运行

---

## 💡 推荐架构

### 统一 Workflow 配置

合并到 `daily_analysis.yml`，通过环境变量控制：

```yaml
env:
  # === 功能开关 ===
  RECOMMEND_ENABLED: 'true'           # 启用智能选股
  PORTFOLIO_ADVICE_ENABLED: 'true'   # 启用调仓建议
  MARKET_REVIEW_ENABLED: 'true'      # 启用大盘复盘
  
  # === 数据配置 ===
  STOCK_POOLS: ${{ secrets.STOCK_POOLS }}       # 智能选股的股票池
  STOCK_LIST: ${{ secrets.STOCK_LIST }}         # 个股分析和调仓的股票列表
  POSITION_RATIOS: ${{ secrets.POSITION_RATIOS }} # 持仓比例
```

### 运行逻辑（main.py 已实现）

```python
# 1. 智能选股：如果配置了 STOCK_POOLS
if config.stock_pools and config.recommend_enabled:
    selection_result = select_stocks(config.stock_pools)
    send_stock_recommendation(selection_result)

# 2. 个股分析：如果配置了 STOCK_LIST
if config.stock_list:
    results = pipeline.run(stock_codes=config.stock_list)

# 3. 调仓建议：如果配置了 STOCK_LIST（且 stock_list 不为空）
if config.stock_list and config.portfolio_advice_enabled:
    portfolio_advice = analyze_portfolio(
        stock_list=config.stock_list,
        position_ratios=config.position_ratios
    )
    send_portfolio_advice(portfolio_advice)

# 4. 大盘复盘：如果启用
if config.market_review_enabled:
    market_report = market_analyzer.generate_report()
```

---

## 🔧 如何配置

### 场景 1：只要智能选股

**Secrets 配置**：
```
GEMINI_API_KEY=AIza...
STOCK_POOLS=沪深300
RECOMMEND_ENABLED=true
```

**结果**：只运行智能选股，不运行个股分析和调仓

---

### 场景 2：只要个股分析 + 调仓建议

**Secrets 配置**：
```
GEMINI_API_KEY=AIza...
STOCK_LIST=600519,000858,002594
POSITION_RATIOS=600519:100,000858:80,002594:50
```

**结果**：
- ✅ 个股深度分析
- ✅ 调仓建议
- ❌ 不运行智能选股（因为没有 STOCK_POOLS）

---

### 场景 3：全功能（智能选股 + 个股分析 + 调仓 + 大盘）

**Secrets 配置**：
```
GEMINI_API_KEY=AIza...
STOCK_POOLS=沪深300
STOCK_LIST=600519,000858,002594
POSITION_RATIOS=600519:100,000858:80,002594:50
MARKET_REVIEW_ENABLED=true
```

**结果**：运行所有功能

---

### 场景 4：智能选股 + 大盘复盘（无持仓）

**Secrets 配置**：
```
GEMINI_API_KEY=AIza...
STOCK_POOLS=沪深300
MARKET_REVIEW_ENABLED=true
```

**结果**：
- ✅ 智能选股
- ✅ 大盘复盘
- ❌ 不运行个股分析和调仓（因为 STOCK_LIST 为空）

---

## 🚨 关键问题：STOCK_LIST 为空时不报错

### 当前代码逻辑（已正确处理）

```python
# main.py line 866
if config.stock_list and config.portfolio_advice_enabled:
    # 只有 stock_list 不为空才运行
    portfolio_advice = analyze_portfolio(...)
```

✅ **已经处理**：如果 `STOCK_LIST` 为空，不会运行调仓建议，不会报错。

### 确保安全

在 `config.py` 中，`stock_list` 为空字符串时会被处理为空列表：

```python
stock_list_str = os.getenv('STOCK_LIST', '')
stock_list = [s.strip() for s in stock_list_str.split(',') if s.strip()]
```

所以：
- `STOCK_LIST=""` → `config.stock_list = []` → 不运行个股分析和调仓
- `STOCK_LIST` 未配置 → `config.stock_list = []` → 不运行个股分析和调仓

✅ **无需额外修改**，已安全处理。

---

## 📊 建议的最终架构

### 保留两个 Workflows，明确职责

| Workflow | 用途 | Secrets 配置 |
|----------|------|-------------|
| `daily_analysis.yml` | **完整分析**（个股+大盘+调仓） | `STOCK_LIST`、`POSITION_RATIOS` |
| `stock_selection.yml` | **轻量选股**（仅智能选股） | `STOCK_POOLS` |

**定时任务**：
- `daily_analysis.yml`：每天 18:00（收盘后分析持仓）
- `stock_selection.yml`：每天 15:30（收盘时推荐新股）

**优点**：
- ✅ 职责清晰：选股和分析分开
- ✅ 互不干扰：选股失败不影响持仓分析
- ✅ 灵活性高：可以单独触发某个功能

---

## 🎯 总结

### 现状
- ✅ 已有两个 workflows
- ✅ `main.py` 已正确处理所有功能开关
- ✅ `STOCK_LIST` 为空不会报错

### 建议
1. **保留两个 workflows**，职责分明
2. **用户根据需求选择配置**：
   - 只想选股 → 配置 `STOCK_POOLS`，运行 `stock_selection.yml`
   - 只想分析持仓 → 配置 `STOCK_LIST`，运行 `daily_analysis.yml`
   - 两者都要 → 两个都配置，两个 workflows 都运行

### 下一步
需要我帮你：
1. ✅ 修改 workflows 使其更清晰
2. ✅ 添加测试模式（少量股票）
3. ✅ 提供本地测试方法
