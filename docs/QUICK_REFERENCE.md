# 🎯 快速参考卡

## 核心问题速查

### ❓ 有几个 workflow？

**答案**：2个

| Workflow | 功能 | 时间 |
|----------|------|------|
| `stock_selection.yml` | 智能选股 | 15:30 |
| `daily_analysis.yml` | 个股+调仓+大盘 | 18:00 |

---

### ❓ 调仓建议在哪里？

**答案**：在 `daily_analysis.yml` ✅

- ✅ 和个股分析在一起
- ✅ 每天 18:00 运行
- ✅ 需要配置 `STOCK_LIST`

详见：[PORTFOLIO_ADVICE_GUIDE.md](./PORTFOLIO_ADVICE_GUIDE.md)

---

### ❓ STOCK_LIST 为空会报错吗？

**答案**：不会 ✅

```python
# 代码已安全处理
if config.stock_list and config.portfolio_advice_enabled:
    # 只有非空才运行
```

---

### ❓ 如何快速测试？

**答案**：3种方式

#### 1️⃣ 本地测试（最快）
```bash
export GEMINI_API_KEY='your_key'
./test_local_workflow.sh  # 选择测试模式
```

#### 2️⃣ GitHub Actions测试
```
Actions → Run workflow
test_mode: true
test_sample_size: 30
```

#### 3️⃣ Python测试
```bash
export TEST_MODE=true TEST_SAMPLE_SIZE=20
python3 main.py --no-market-review --no-notify
```

---

## 配置速查

### 只要智能选股
```yaml
GEMINI_API_KEY=AIza...
STOCK_POOLS=沪深300
```

### 只要持仓分析
```yaml
GEMINI_API_KEY=AIza...
STOCK_LIST=600519,000858
POSITION_RATIOS=600519:100,000858:80
```

**包含**：个股分析 + 调仓建议

---

### 全功能
```yaml
GEMINI_API_KEY=AIza...
STOCK_POOLS=沪深300
STOCK_LIST=600519,000858
POSITION_RATIOS=600519:100,000858:80
MARKET_REVIEW_ENABLED=true
```

---

## 测试模式速查

### 性能对比
| 模式 | 股票数 | 耗时 | API调用 |
|------|--------|------|---------|
| 测试 | 30只 | 1分钟 | 40次 |
| 正常 | 300只 | 4分钟 | 350次 |

### 环境变量
```bash
TEST_MODE=true          # 开启测试模式
TEST_SAMPLE_SIZE=30     # 样本数量
```

---

## 文档速查

| 调仓建议 | [PORTFOLIO_ADVICE_GUIDE.md](./PORTFOLIO_ADVICE_GUIDE.md) |
| 需求 | 文档 |
|------|------|
| 快速开始 | [QUICK_START.md](./QUICK_START.md) |
| 完整指南 | [AI_STOCK_SELECTION_GUIDE.md](./AI_STOCK_SELECTION_GUIDE.md) |
| 测试模式 | [TEST_MODE_GUIDE.md](./TEST_MODE_GUIDE.md) |
| 架构说明 | [WORKFLOW_ARCHITECTURE.md](./WORKFLOW_ARCHITECTURE.md) |
| 性能优化 | [DATABASE_CACHE_OPTIMIZATION.md](./DATABASE_CACHE_OPTIMIZATION.md) |
| 问题排查 | [WORKFLOW_OPTIMIZATION_SUMMARY.md](./WORKFLOW_OPTIMIZATION_SUMMARY.md) |

---

## 常用命令

```bash
# 本地测试（推荐）
./test_local_workflow.sh

# 智能选股测试
export TEST_MODE=true STOCK_POOLS='沪深300'
python3 main.py --no-market-review --no-notify

# 个股分析测试
export STOCK_LIST='600519,000858'
python3 main.py --no-market-review --no-notify

# 查看日志
tail -f logs/stock_analysis_*.log

# 清理缓存
rm -rf data/*.db logs/*.log
```

---

**记住**：
- 💡 测试模式 = 快速验证
- 📊 生产环境 = 关闭测试模式
- 🧪 本地先测 → GitHub验证 → 生产部署
