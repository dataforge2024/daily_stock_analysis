# 🧪 测试模式使用指南

## 为什么需要测试模式？

智能选股默认会分析整个股票池（如沪深300的300只股票），这对于测试和调试来说：
- ❌ 耗时太长（4-5分钟）
- ❌ 消耗API配额
- ❌ 不适合频繁测试

**测试模式**可以随机抽取少量股票（如20-30只）进行快速测试，验证workflow配置是否正确。

---

## 📋 测试模式功能

### 1. 本地测试

使用提供的测试脚本，无需推送到GitHub：

```bash
# 设置API Key
export GEMINI_API_KEY='your_api_key_here'

# 运行测试脚本
./test_local_workflow.sh
```

**测试选项**：

| 选项 | 说明 | 耗时 | 适用场景 |
|------|------|------|---------|
| 1 | 智能选股测试（30只） | ~1分钟 | 测试选股功能 |
| 2 | 个股分析测试（3只） | ~30秒 | 测试个股分析 |
| 3 | 全功能测试 | ~2分钟 | 综合测试 |
| 4 | GitHub Actions 完整模拟 | ~2分钟 | 部署前验证 |

### 2. GitHub Actions 测试

在GitHub Actions界面手动触发，选择测试模式：

1. 进入你的仓库
2. 点击 **`Actions`** → **`AI Smart Stock Selection`**
3. 点击 **`Run workflow`**
4. 配置参数：
   - **股票池选择**: `hs300`
   - **推荐股票数量**: `3`
   - **测试模式**: `true` ⬅️ **开启测试模式**
   - **测试样本数量**: `30` ⬅️ **只测试30只股票**
5. 点击 **`Run workflow`**

**预期结果**：
- ⏱️ 运行时间：~1分钟（而不是4-5分钟）
- 📊 测试股票：30只（随机抽取）
- ✅ 验证配置正确性

---

## 🎯 使用场景

### 场景 1：首次部署验证

**问题**：不确定配置是否正确，不想等5分钟才知道结果

**解决**：
```bash
# 本地测试
export GEMINI_API_KEY='your_key'
export TEST_MODE=true
export TEST_SAMPLE_SIZE=20
export STOCK_POOLS="沪深300"

python3 main.py --no-market-review --no-notify
```

或使用快捷脚本：
```bash
./test_local_workflow.sh
# 选择 1 (智能选股测试)
```

### 场景 2：调试代码逻辑

**问题**：修改了代码，想快速验证是否工作

**解决**：
```bash
# 使用测试脚本，选择对应的测试模式
./test_local_workflow.sh

# 或直接运行
export TEST_MODE=true
python3 -c "
from stock_selector import StockSelector, StockPool
from analyzer import GeminiAnalyzer

selector = StockSelector(
    ai_analyzer=GeminiAnalyzer(),
    test_mode=True,
    test_sample_size=20
)
result = selector.select_from_pool(StockPool.HS300)
print(result.format_report())
"
```

### 场景 3：GitHub Actions 快速验证

**问题**：推送代码到GitHub后，想快速验证workflow是否正常

**解决**：
1. Actions → Run workflow
2. 开启 **测试模式 = true**
3. 设置 **测试样本数量 = 20**
4. 运行，1分钟内看到结果

### 场景 4：CI/CD 集成测试

**问题**：想在Pull Request时自动运行测试

**解决**：
在 `.github/workflows/` 中创建测试workflow：

```yaml
name: CI Test

on:
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - run: pip install -r requirements.txt
      
      - name: Test Stock Selection
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          TEST_MODE: 'true'
          TEST_SAMPLE_SIZE: '15'
          STOCK_POOLS: '沪深300'
        run: python3 main.py --no-market-review --no-notify
```

---

## ⚙️ 环境变量说明

### 测试模式相关

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `TEST_MODE` | 是否启用测试模式 | `false` | `true` |
| `TEST_SAMPLE_SIZE` | 测试样本数量 | `30` | `20` |

### 完整环境变量示例

**测试模式（智能选股）**：
```bash
export GEMINI_API_KEY='AIza...'
export TEST_MODE=true
export TEST_SAMPLE_SIZE=25
export STOCK_POOLS='沪深300'
export RECOMMEND_ENABLED=true
```

**正常模式（完整分析）**：
```bash
export GEMINI_API_KEY='AIza...'
export TEST_MODE=false  # 或不设置
export STOCK_POOLS='沪深300,中证500'
export STOCK_LIST='600519,000858'
export POSITION_RATIOS='600519:100,000858:80'
```

---

## 📊 性能对比

| 模式 | 股票池 | 分析数量 | 耗时 | API调用次数 |
|------|--------|---------|------|-----------|
| **测试模式** | 沪深300 | 30只（随机） | ~1分钟 | ~40次 |
| **正常模式** | 沪深300 | 300只（全部） | ~4分钟 | ~350次 |
| **测试模式** | 中证500 | 30只（随机） | ~1分钟 | ~40次 |
| **正常模式** | 中证500 | 500只（全部） | ~7分钟 | ~550次 |

**节省**：
- ⏱️ 时间节省：75%
- 💰 API调用节省：88%

---

## 🔧 高级用法

### 1. 组合测试（本地）

测试智能选股 + 个股分析 + 调仓建议：

```bash
export GEMINI_API_KEY='your_key'
export TEST_MODE=true
export TEST_SAMPLE_SIZE=15
export STOCK_POOLS='沪深300'
export STOCK_LIST='600519,000858'
export POSITION_RATIOS='600519:100,000858:80'
export RECOMMEND_ENABLED=true
export PORTFOLIO_ADVICE_ENABLED=true
export MARKET_REVIEW_ENABLED=false  # 不测试大盘复盘

python3 main.py --no-notify
```

### 2. 自定义样本数量

```bash
# 快速测试（10只）
export TEST_MODE=true TEST_SAMPLE_SIZE=10

# 中等测试（50只）
export TEST_MODE=true TEST_SAMPLE_SIZE=50

# 接近真实（100只）
export TEST_MODE=true TEST_SAMPLE_SIZE=100
```

### 3. 多股票池测试

```bash
export TEST_MODE=true
export TEST_SAMPLE_SIZE=20
export STOCK_POOLS='沪深300,中证500,创业板50'

# 每个池抽取20只，总共60只
python3 main.py --no-market-review --no-notify
```

---

## 🐛 常见问题

### Q: 测试模式和正常模式结果不一样？

**A**: 这是正常的。测试模式是**随机抽样**，每次抽取的股票不同，结果自然会有差异。测试模式主要用于：
- ✅ 验证代码逻辑
- ✅ 验证配置正确
- ✅ 快速调试
- ❌ 不用于实际选股决策

### Q: 如何确保测试覆盖关键股票？

**A**: 测试模式是完全随机的，如果想测试特定股票：

```python
# 方式1：使用个股分析
export STOCK_LIST='600519,000858,002594'
python3 main.py --no-market-review --no-notify

# 方式2：修改代码临时固定随机种子
import random
random.seed(42)  # 固定随机结果
```

### Q: GitHub Actions 测试模式如何保存结果？

**A**: 测试模式和正常模式一样，都会：
- ✅ 上传 Artifacts
- ✅ 生成完整报告
- ✅ 显示日志

区别只是分析的股票数量不同。

### Q: 测试模式能否用于生产环境？

**A**: ❌ **不建议**。测试模式用于开发和调试，生产环境应该：
- 使用完整股票池
- 关闭测试模式（`TEST_MODE=false`）
- 确保数据完整性

---

## ✅ 最佳实践

### 开发流程

```
1. 本地开发
   ↓
2. 本地测试（test_local_workflow.sh）
   ↓
3. 推送到GitHub
   ↓
4. GitHub Actions 测试模式验证
   ↓
5. 确认无误后，关闭测试模式
   ↓
6. 正式运行（定时任务或手动触发）
```

### 推荐配置

**开发阶段**：
```bash
TEST_MODE=true
TEST_SAMPLE_SIZE=20
```

**预发布验证**：
```bash
TEST_MODE=true
TEST_SAMPLE_SIZE=50
```

**生产环境**：
```bash
TEST_MODE=false  # 或不设置
```

---

## 📚 相关文档

- **[本地测试脚本](../test_local_workflow.sh)** - 快速本地测试
- **[GitHub Actions 配置](./AI_STOCK_SELECTION_GUIDE.md)** - 完整部署指南
- **[Workflow 架构](./WORKFLOW_ARCHITECTURE.md)** - 多功能说明

---

**记住**：测试模式让你更快验证，但不要忘了最终切换回正常模式！🚀
