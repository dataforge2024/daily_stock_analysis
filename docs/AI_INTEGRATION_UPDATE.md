# 🤖 AI 智能分析集成更新

## 📅 更新日期：2026-01-20

## 🎯 更新概述

将原先纯规则的选股和调仓功能升级为 **两阶段智能分析**：
1. **第一阶段：规则筛选** - 快速过滤，缩小范围
2. **第二阶段：AI 深度分析** - 精准判断，生成理由

## ✨ 主要更新

### 1️⃣ 智能选股功能升级

#### 原来的实现
- ✅ 多因子量化模型（7个维度）
- ✅ 综合评分排序
- ❌ **纯规则，无智能理由**
- ❌ 无法深度分析技术面和行情

#### 现在的实现
- ✅ 保留多因子模型（规则筛选）
- ✅ **新增 AI 深度分析阶段**
- ✅ **AI 评分 + 规则评分综合排序**
- ✅ **生成详细理由、关键指标、风险提示**

#### 工作流程

```
股票池（300-1000只）
    ↓
【第一阶段：规则筛选】
    ├─ 多因子评分（趋势、量能、波动等）
    ├─ 筛选 Top 候选股（50只，2.5倍推荐数）
    ↓
【第二阶段：AI 深度分析】
    ├─ 获取完整技术面数据
    ├─ 调用 Gemini AI 分析
    ├─ 筛选 AI 评分 ≥ 60
    ├─ 综合排序（AI 70% + 规则 30%）
    ↓
最终推荐（10-20只）
    ├─ AI 评分
    ├─ AI 建议（强烈买入、买入等）
    ├─ AI 理由（详细分析）
    ├─ 关键指标
    └─ 风险提示
```

### 2️⃣ 调仓建议功能升级

#### 原来的实现
- ✅ 基于趋势分析信号
- ✅ 动态仓位调整
- ❌ **纯规则判断**
- ❌ 无 AI 辅助决策

#### 现在的实现
- ✅ 保留规则分析逻辑
- ✅ **新增 AI 深度分析**
- ✅ **AI 评分修正规则建议**
- ✅ **生成智能调仓理由**

#### AI 修正逻辑

| 场景 | 规则建议 | AI 评分 | 最终建议 | 说明 |
|------|---------|---------|---------|------|
| 场景1 | 减仓/卖出 | ≥ 75 | 持有 | AI 发现趋势良好，修正为持有 |
| 场景2 | 持有/加仓 | ≤ 40 | 减仓 | AI 发现风险加大，修正为减仓 |
| 场景3 | 持有 | 60-75 | 持有 | AI 与规则一致 |

## 🔧 技术实现

### 修改的文件

#### 1. `stock_selector.py`

**新增代码**：
```python
# 导入 AI 分析器和搜索服务
from analyzer import GeminiAnalyzer, AnalysisResult
from search_service import SearchService

# StockScore 新增 AI 分析字段
ai_analysis: Optional[AnalysisResult] = None
ai_sentiment_score: Optional[int] = None
ai_advice: Optional[str] = None
ai_core_reason: Optional[str] = None

# 新增 AI 分析参数
CANDIDATE_MULTIPLIER = 2.5  # 候选股倍数
AI_MIN_SCORE = 60           # AI 最低评分
USE_AI_ANALYSIS = True      # 是否启用

# 新增 _ai_deep_analysis() 方法
def _ai_deep_analysis(self, candidates: List[StockScore]) -> List[StockScore]:
    """AI 深度分析候选股"""
    # 为每只候选股调用 AI 分析
    # 筛选 AI 评分 >= AI_MIN_SCORE
    # 综合排序返回
```

**修改方法**：
- `__init__()`: 增加 `ai_analyzer` 和 `search_service` 参数
- `_filter_and_rank()`: 改为两阶段筛选
- `format_report()`: 优先显示 AI 分析结果

#### 2. `portfolio_advisor.py`

**新增代码**：
```python
# 导入 AI 分析器
from analyzer import GeminiAnalyzer, AnalysisResult

# AdjustAdvice 新增 AI 字段
ai_analysis: Optional[AnalysisResult] = None
ai_sentiment_score: Optional[int] = None
ai_advice: Optional[str] = None
ai_reason: Optional[str] = None

# 新增 AI 分析配置
USE_AI_ANALYSIS = True

# 新增方法
def _apply_ai_analysis(self, advice: AdjustAdvice, pos: PositionConfig, df: pd.DataFrame):
    """应用 AI 深度分析"""
    # 调用 AI 分析器
    # 根据 AI 评分修正建议
```

**修改方法**：
- `__init__()`: 增加 `ai_analyzer` 参数
- `_generate_advice()`: 改为两阶段分析
- `format_report()`: 优先显示 AI 结果

#### 3. 便捷函数更新

**`select_stocks()` 函数**：
```python
# 自动创建 AI 分析器和搜索服务
ai_analyzer = GeminiAnalyzer()
search_service = SearchService()

# 传递给 StockSelector
selector = StockSelector(
    ai_analyzer=ai_analyzer,
    search_service=search_service
)
```

### 新增文件

#### `test_ai_selection.py` - 测试脚本

提供两个测试功能：
1. `test_ai_stock_selection()` - 测试 AI 选股
2. `test_ai_portfolio_advice()` - 测试 AI 调仓

## 📊 性能影响

### API 调用量

| 功能 | 调用次数 | 说明 |
|------|---------|------|
| 选股（20只推荐） | 约 50 次 | 分析候选股（2.5倍） |
| 调仓（10只持仓） | 约 10 次 | 每只持仓1次 |

### 限流策略

- 每分析 3 只股票休眠 3 秒
- 避免触发 API 限流
- 单次运行时间：约 5-10 分钟（取决于股票数量）

## 🎨 推送格式变化

### 原推送格式

```
【1】贵州茅台 (600519)
💰 最新价：1850.50  涨跌幅：+1.23%
📊 综合评分：8.5/10
💡 理由：多头排列、量价配合
```

### 新推送格式

```
【1】贵州茅台 (600519)
💰 最新价：1850.50  涨跌幅：+1.23%
📊 综合评分：8.5/10 (AI评分: 85/100)
🤖 AI建议：强烈买入
💡 AI理由：主力持续流入，技术面强势突破，预期短期持续上涨
📈 关键指标：均线多头排列、量价配合优秀、MACD金叉
⚠️ 风险提示：估值略高，注意回调风险
```

## 📖 文档更新

### 更新的文档

1. **README.md**
   - 更新功能特性说明
   - 标注 "规则筛选 + AI 深度分析"

2. **docs/new-features-guide.md**
   - 详细说明两阶段分析流程
   - 新增 AI 修正逻辑说明
   - 新增测试指南
   - 更新故障排查（AI 相关）

## 🚀 使用建议

### 1. 关注 AI 评分

- **AI 评分 ≥ 75**：强烈关注，深度分析价值大
- **AI 评分 60-75**：值得关注，结合规则判断
- **AI 评分 < 60**：已被过滤

### 2. 重点阅读 AI 理由

AI 会综合分析：
- 技术面：趋势、均线、MACD、KDJ等
- 资金面：主力资金流向、成交量变化
- 情绪面：市场拥挤度、板块热度

### 3. AI 与规则冲突时

- 优先考虑 **AI 建议**
- AI 有更完整的上下文信息
- 但仍需结合自己的判断

### 4. 注意风险提示

AI 会提示：
- 估值风险
- 回调风险
- 趋势反转风险
- 资金流出风险

## ⚠️ 注意事项

1. **API 配额管理**
   - Gemini 免费额度有限
   - 建议每天运行 1-2 次
   - 测试时限制股票数量

2. **分析时间**
   - AI 分析耗时较长
   - 建议非交易时段运行
   - GitHub Actions 默认 18:00

3. **结果参考性**
   - AI 分析仅供参考
   - 不构成投资建议
   - 需结合基本面判断

## 🔄 后续优化方向

1. **性能优化**
   - 批量并发分析
   - 缓存 AI 分析结果
   - 增量更新机制

2. **功能增强**
   - 集成新闻搜索到选股
   - 多模型对比分析
   - 历史推荐效果追踪

3. **用户体验**
   - 推送格式优化
   - 可视化分析结果
   - 交互式调仓建议

---

## 📝 总结

本次更新将纯规则的选股和调仓功能升级为 **智能两阶段分析**，大幅提升了推荐的准确性和可解释性。用户不仅能看到推荐结果，还能了解 **为什么推荐**、**有哪些风险**，从而做出更明智的投资决策。

**核心优势**：
- ✅ 保留规则筛选的高效性
- ✅ 增加 AI 分析的智能性
- ✅ 提供详细的投资理由
- ✅ 生成准确的风险提示
- ✅ 支持 AI 修正规则建议

欢迎测试并反馈！🎉
