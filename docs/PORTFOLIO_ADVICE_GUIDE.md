# 📍 调仓建议功能位置和使用说明

## 🎯 调仓建议在哪里？

**答案：调仓建议和个股深度分析在一起，运行在 `daily_analysis.yml` workflow 中。**

---

## 📊 功能分布

### Workflow 1: `stock_selection.yml`（智能选股）
**功能**：仅智能选股
- ✅ 智能选股（从股票池推荐10只股票）
- ❌ 个股深度分析
- ❌ 调仓建议
- ❌ 大盘复盘

**运行时间**：每天 15:30（收盘时）

---

### Workflow 2: `daily_analysis.yml`（完整分析）⭐
**功能**：个股分析 + 调仓建议 + 大盘复盘
- ✅ 个股深度分析（如果配置了 STOCK_LIST）
- ✅ **调仓建议**（如果配置了 STOCK_LIST + POSITION_RATIOS）⬅️ **在这里**
- ✅ 大盘复盘（可选）
- ✅ 智能选股（如果配置了 STOCK_POOLS）

**运行时间**：每天 18:00（收盘后）

---

## 🔧 如何运行调仓建议？

### 前置条件

调仓建议需要两个配置：

| 配置项 | 说明 | 示例 | 必填 |
|--------|------|------|:----:|
| `STOCK_LIST` | 持仓股票代码列表 | `600519,000858,002594` | ✅ |
| `POSITION_RATIOS` | 各股票仓位比例 | `600519:100,000858:80,002594:50` | 可选 |

> 💡 如果不配置 `POSITION_RATIOS`，系统会假设所有持仓都是100%仓位。

---

## 🚀 运行方式

### 方式 1: GitHub Actions 自动运行（推荐）

#### 步骤 1：配置 Secrets

进入仓库 → Settings → Secrets and variables → Actions

添加以下 Secrets：

```yaml
# 必填
GEMINI_API_KEY: AIzaSy...

# 持仓配置（调仓建议需要）
STOCK_LIST: 600519,000858,002594
POSITION_RATIOS: 600519:100,000858:80,002594:50
```

#### 步骤 2：等待自动运行

- ⏰ 每天 18:00 自动运行 `daily_analysis.yml`
- 🔄 自动执行：个股分析 → **调仓建议** → 大盘复盘
- 📧 通知推送（如果配置了通知渠道）

#### 步骤 3：查看结果

1. Actions → 最新的 "每日股票分析" run
2. 查看日志输出（包含调仓建议）
3. 下载 Artifacts（包含详细报告）

---

### 方式 2: 手动触发

1. 进入 Actions → "每日股票分析"
2. 点击 "Run workflow"
3. 选择运行模式：
   - **full**：完整分析（包含调仓建议）✅
   - **stocks-only**：仅股票分析（包含调仓建议）✅
   - **market-only**：仅大盘复盘（不含调仓）❌
4. 运行

---

### 方式 3: 本地运行

#### 设置环境变量

```bash
export GEMINI_API_KEY='your_api_key'
export STOCK_LIST='600519,000858,002594'
export POSITION_RATIOS='600519:100,000858:80,002594:50'
```

#### 运行完整分析（包含调仓建议）

```bash
python3 main.py
```

#### 仅运行个股分析和调仓（不含大盘复盘）

```bash
python3 main.py --no-market-review
```

---

## 📋 运行逻辑

### main.py 执行顺序

```python
# 1. 智能选股（如果配置了 STOCK_POOLS）
if config.stock_pools and config.recommend_enabled:
    selection_result = select_stocks(config.stock_pools)

# 2. 个股深度分析（如果配置了 STOCK_LIST）
if config.stock_list:
    results = pipeline.run(stock_codes=config.stock_list)

# 3. 调仓建议（如果配置了 STOCK_LIST）⬅️ 这里
if config.stock_list and config.portfolio_advice_enabled:
    portfolio_advice = analyze_portfolio(
        stock_list=config.stock_list,
        position_ratios=config.position_ratios
    )
    send_portfolio_advice(portfolio_advice)  # 发送通知

# 4. 大盘复盘（如果启用）
if config.market_review_enabled:
    market_report = market_analyzer.generate_report()
```

### 触发条件

调仓建议会在以下条件**同时满足**时运行：

1. ✅ 配置了 `STOCK_LIST`（持仓列表不为空）
2. ✅ `portfolio_advice_enabled = true`（默认会自动启用）

> 💡 **重要**：如果 `STOCK_LIST` 为空，调仓建议不会运行，也不会报错。

---

## 🎯 使用场景

### 场景 1：只要调仓建议（无智能选股）

**配置**：
```yaml
GEMINI_API_KEY: AIza...
STOCK_LIST: 600519,000858
POSITION_RATIOS: 600519:100,000858:80
```

**运行**：
- `daily_analysis.yml` 每天 18:00 自动运行
- 或手动触发

**结果**：
- ✅ 个股深度分析
- ✅ 调仓建议
- ❌ 不运行智能选股（STOCK_POOLS未配置）

---

### 场景 2：智能选股 + 调仓建议

**配置**：
```yaml
GEMINI_API_KEY: AIza...
STOCK_POOLS: 沪深300              # 智能选股
STOCK_LIST: 600519,000858         # 调仓建议
POSITION_RATIOS: 600519:100,000858:80
```

**运行**：
- `stock_selection.yml` 15:30 运行智能选股
- `daily_analysis.yml` 18:00 运行调仓建议

**结果**：
- ✅ 15:30 推荐10只新股票
- ✅ 18:00 分析持仓并给出调仓建议

---

### 场景 3：只要个股分析，不要调仓建议

**配置**：
```yaml
GEMINI_API_KEY: AIza...
STOCK_LIST: 600519,000858
PORTFOLIO_ADVICE_ENABLED: false  # 禁用调仓建议
```

**结果**：
- ✅ 个股深度分析
- ❌ 不生成调仓建议

---

## 🧪 测试调仓建议

### 本地测试

```bash
# 1. 设置环境变量
export GEMINI_API_KEY='your_key'
export STOCK_LIST='600519,000858'
export POSITION_RATIOS='600519:100,000858:80'

# 2. 运行（不发送通知）
python3 main.py --no-market-review --no-notify

# 3. 查看输出
# 应该看到：
# ===== 开始执行：持仓调仓建议 =====
# ...调仓建议详情...
```

### 测试脚本

```bash
./test_local_workflow.sh
# 选择 2) 个股分析测试
# 会包含调仓建议
```

---

## 📊 调仓建议输出示例

```
===== 开始执行：持仓调仓建议 =====

📊 持仓调仓建议 - 2026-01-21
持仓数量：2 只

【1】贵州茅台 (600519)
💰 最新价：1650.00  涨跌幅：+2.35%
📊 当前仓位：100%
💡 建议：持有
📈 理由：多头排列强势，量价配合良好，建议继续持有
🎯 目标仓位：100% → 100%（维持）

【2】五粮液 (000858)
💰 最新价：180.00  涨跌幅：-1.20%
📊 当前仓位：80%
💡 建议：减仓
📈 理由：短期回调，建议减至60%仓位
🎯 目标仓位：80% → 60%（减仓20%）

===== 调仓建议完成 =====
```

---

## 🔍 常见问题

### Q: 为什么没有生成调仓建议？

**检查清单**：
1. ✅ `STOCK_LIST` 是否配置且不为空？
2. ✅ 运行的是 `daily_analysis.yml` 而不是 `stock_selection.yml`？
3. ✅ 日志中是否有 "开始执行：持仓调仓建议" 提示？

### Q: 必须配置 POSITION_RATIOS 吗？

**答案**：不是必须的
- 不配置：默认所有股票都是 100% 仓位
- 配置：根据实际仓位给出精准的调仓建议

### Q: 调仓建议和个股分析有什么区别？

**区别**：

| 功能 | 个股深度分析 | 调仓建议 |
|------|-------------|---------|
| **分析模式** | 深度分析（技术+基本面+舆情） | 仓位管理（调仓建议） |
| **AI Prompt** | `SYSTEM_PROMPT`（详细） | `SYSTEM_PROMPT_PORTFOLIO_ADJUSTMENT`（仓位管理） |
| **输出重点** | 买入/卖出建议、点位分析 | 加仓/减仓/持有、目标仓位 |
| **适用场景** | 深度研究个股 | 已持仓的仓位管理 |

### Q: 能否只运行调仓建议，不运行个股分析？

**答案**：不能
- 调仓建议依赖个股分析的数据
- 两者会依次运行：先个股分析 → 再调仓建议

---

## 📚 相关文档

- [WORKFLOW_ARCHITECTURE.md](./WORKFLOW_ARCHITECTURE.md) - Workflow 架构说明
- [AI_STOCK_SELECTION_GUIDE.md](./AI_STOCK_SELECTION_GUIDE.md) - GitHub Actions 部署指南
- [TEST_MODE_GUIDE.md](./TEST_MODE_GUIDE.md) - 测试模式指南
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - 快速参考

---

## 🎯 总结

**调仓建议在哪？**
- ✅ 在 `daily_analysis.yml` workflow
- ✅ 和个股分析在一起
- ✅ 每天 18:00 自动运行

**怎么跑？**
1. 配置 `STOCK_LIST` + `POSITION_RATIOS`
2. 等待每天 18:00 自动运行
3. 或手动触发 `daily_analysis.yml`
4. 或本地运行 `python3 main.py`

**立即测试**：
```bash
export GEMINI_API_KEY='your_key'
export STOCK_LIST='600519,000858'
python3 main.py --no-market-review --no-notify
```
