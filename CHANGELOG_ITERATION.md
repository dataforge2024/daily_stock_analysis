# 系统迭代总结 - 新增选股推荐与调仓建议功能

## 📋 迭代概述

本次迭代为 A股智能分析系统新增了两大核心功能：

1. **每日推荐股票** - 基于股票池的多因子智能选股
2. **智能调仓建议** - 动态优化持仓结构

同时，STOCK_LIST 不再是必须配置项，系统支持更灵活的使用方式。

---

## 🆕 新增文件

### 1. `stock_selector.py` - 多因子选股服务
**路径**: `/Users/hongzhiyuan/code/own/daily_stock_analysis/stock_selector.py`

**核心功能**:
- 支持从沪深300、中证500、创业板50等股票池获取成分股
- 实现多因子选股模型（技术面 + 基本面）
- 综合评分排序，筛选Top 10-20只股票
- 生成格式化推荐报告

**主要类**:
- `StockPool` - 股票池枚举
- `StockScore` - 股票评分数据类
- `SelectionResult` - 选股结果数据类
- `StockSelector` - 选股服务主类

**选股因子**:
- 趋势强度（25%）：MA5 > MA10 > MA20
- 量能配合（20%）：量价关系
- 波动率（15%）：适度波动
- 乖离率（15%）：不追高
- 市值（10%）
- 换手率（5%）
- 近期表现（10%）

### 2. `portfolio_advisor.py` - 调仓建议模块
**路径**: `/Users/hongzhiyuan/code/own/daily_stock_analysis/portfolio_advisor.py`

**核心功能**:
- 基于持仓和趋势分析生成调仓建议
- 动态调整仓位比例（0～100%）
- 提供加仓、减仓、卖出、持有等操作建议
- 风险提示和理由说明

**主要类**:
- `AdjustAction` - 调仓动作枚举
- `PositionConfig` - 持仓配置数据类
- `AdjustAdvice` - 调仓建议数据类
- `PortfolioAdvice` - 组合建议数据类
- `PortfolioAdvisor` - 调仓顾问主类

**调仓策略**:
- 强烈买入/买入 → 加仓（增至150%，上限100%）
- 观望 → 减仓（减至50%，下限30%）
- 卖出/强烈卖出 → 清仓（0%）
- 持有 → 保持不变

### 3. `docs/new-features-guide.md` - 新功能配置指南
**路径**: `/Users/hongzhiyuan/code/own/daily_stock_analysis/docs/new-features-guide.md`

**内容**:
- 详细的功能说明
- 配置方式示例
- 推送格式展示
- 三种使用场景说明
- 故障排查指南

---

## 🔧 修改文件

### 1. `config.py` - 配置管理
**修改内容**:
- 新增 `stock_pools: List[str]` - 股票池配置
- 新增 `recommend_enabled: bool` - 推荐功能开关
- 新增 `recommend_min_stocks: int` - 最少推荐数
- 新增 `recommend_max_stocks: int` - 最多推荐数
- 新增 `position_ratios: Dict[str, float]` - 仓位比例配置
- 新增 `portfolio_advice_enabled: bool` - 调仓功能开关
- 修改 `_load_from_env()` 方法，解析新配置项
- 修改 `validate()` 方法，适配 STOCK_LIST 可选逻辑

**关键逻辑**:
```python
# STOCK_LIST 不再必须
stock_list = [...]  # 可以为空列表

# 股票池配置
stock_pools = ['沪深300', '中证500', ...]

# 仓位比例配置
position_ratios = {'600519': 100.0, '300750': 80.0, ...}

# 自动启用功能
if stock_pools and not recommend_enabled:
    recommend_enabled = True

if stock_list and not portfolio_advice_enabled:
    portfolio_advice_enabled = True
```

### 2. `notification.py` - 通知服务
**修改内容**:
- 新增延迟导入函数 `_import_stock_modules()`
- 新增 `send_stock_recommendation()` - 发送推荐股票
- 新增 `send_portfolio_advice()` - 发送调仓建议

**新增函数**:
```python
def send_stock_recommendation(selection_result) -> bool:
    """发送每日推荐股票"""
    service = get_notification_service()
    report = selection_result.format_report()
    filename = f"stock_recommendation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    service.save_report_to_file(report, filename=filename)
    return service.send(report)

def send_portfolio_advice(portfolio_advice) -> bool:
    """发送持仓调仓建议"""
    service = get_notification_service()
    report = portfolio_advice.format_report()
    filename = f"portfolio_advice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    service.save_report_to_file(report, filename=filename)
    return service.send(report)
```

### 3. `main.py` - 主程序
**修改内容**:
- 新增导入: `stock_selector`, `portfolio_advisor`
- 完全重写 `run_full_analysis()` 函数，整合新功能流程

**新流程**:
```python
def run_full_analysis():
    # 1. 每日推荐股票（如果配置了股票池）
    if config.stock_pools and config.recommend_enabled:
        selection_result = select_stocks(config.stock_pools)
        send_stock_recommendation(selection_result)
    
    # 2. 个股深度分析（如果配置了自选股）
    if config.stock_list:
        results = pipeline.run(...)
    
    # 3. 调仓建议（如果配置了自选股）
    if config.stock_list and config.portfolio_advice_enabled:
        portfolio_advice = analyze_portfolio(...)
        send_portfolio_advice(portfolio_advice)
    
    # 4. 大盘复盘（如果启用）
    if config.market_review_enabled:
        market_report = run_market_review(...)
    
    # 5. 生成飞书云文档（如果配置）
    if feishu_doc.is_configured():
        doc_url = feishu_doc.create_daily_doc(...)
```

### 4. `README.md` - 项目说明
**修改内容**:
- 核心功能板块新增两项功能说明
- 配置表格新增 `STOCK_POOLS` 和 `POSITION_RATIOS`
- 添加配置说明：至少配置 STOCK_LIST 或 STOCK_POOLS 之一
- 引导用户查看新功能配置指南

### 5. `docs/full-guide.md` - 完整配置指南
**修改内容**:
- 其他配置表格新增新配置项
- 环境变量完整列表新增新配置项
- 添加新功能说明和引导链接

### 6. `.env.example` - 配置模板
**修改内容**:
- 新增股票池配置示例
- 新增仓位比例配置示例
- 新增推荐股票数量配置
- 添加详细注释说明

---

## 🎯 功能实现细节

### 多因子选股流程

1. **获取股票池成分股**
   - 调用 akshare API 获取指数成分股
   - 支持多个股票池合并去重

2. **批量获取数据**
   - 获取最近30天日线数据
   - 每10只股票休眠2秒（防止API限流）

3. **计算技术指标**
   - 均线（MA5, MA10, MA20）
   - 量比
   - 波动率
   - 乖离率

4. **多因子评分**
   - 趋势强度：0-1分
   - 量能配合：0-1分
   - 波动率：0-1分
   - 乖离率：0-1分
   - 换手率：0-1分
   - 近期表现：0-1分
   - 加权综合：0-10分

5. **筛选排序**
   - 过滤：综合评分 >= 6.0
   - 排序：按评分降序
   - 截取：Top 10-20

### 调仓建议流程

1. **获取持仓数据**
   - 读取 STOCK_LIST 和 POSITION_RATIOS
   - 构建持仓配置对象

2. **趋势分析**
   - 调用 StockTrendAnalyzer 分析每只股票
   - 获取买入/卖出信号

3. **生成建议**
   - 根据信号和当前仓位计算建议仓位
   - 确定调仓动作（加仓/减仓/卖出/持有）
   - 生成操作理由

4. **风险检查**
   - 乖离率预警
   - 放量下跌预警
   - 跌破支撑预警

5. **格式化输出**
   - 按动作分组
   - 生成详细报告

---

## 📊 配置场景

### 场景1：仅推荐（无自选股）
```bash
STOCK_POOLS=沪深300,中证500
```
- ✅ 每日推荐10-20只股票
- ❌ 不进行个股分析
- ❌ 不生成调仓建议

### 场景2：仅分析（无推荐）
```bash
STOCK_LIST=600519,300750,002594
POSITION_RATIOS=600519:100,300750:80,002594:50
```
- ❌ 不生成推荐
- ✅ 个股深度分析
- ✅ 调仓建议

### 场景3：完整功能
```bash
STOCK_POOLS=沪深300,中证500
STOCK_LIST=600519,300750,002594
POSITION_RATIOS=600519:100,300750:80,002594:50
```
- ✅ 推荐股票
- ✅ 个股分析
- ✅ 调仓建议

---

## 🔄 向后兼容性

### 现有用户（已配置 STOCK_LIST）
- ✅ 不需要任何修改
- ✅ 原有功能完全保留
- ✅ 自动启用调仓建议（可选关闭）

### 新用户
- ✅ 可以只配置 STOCK_POOLS 使用推荐功能
- ✅ 可以只配置 STOCK_LIST 使用分析功能
- ✅ 可以同时配置使用完整功能

---

## 📝 待办事项

- [ ] 测试选股功能在不同股票池的表现
- [ ] 测试调仓建议在实际交易中的效果
- [ ] 优化选股因子权重配置
- [ ] 添加选股结果的历史回测功能
- [ ] 支持自定义选股因子和权重
- [ ] 添加更多股票池（如科创板、北交所等）

---

## ✅ 测试建议

### 单元测试
```bash
# 测试选股功能
python stock_selector.py

# 测试调仓建议
python portfolio_advisor.py
```

### 集成测试
```bash
# 仅推荐
STOCK_POOLS=沪深300 python main.py

# 仅分析
STOCK_LIST=600519,300750 python main.py

# 完整功能
STOCK_POOLS=沪深300 STOCK_LIST=600519,300750 python main.py
```

---

## 📖 文档清单

1. ✅ `README.md` - 更新核心功能和配置说明
2. ✅ `docs/new-features-guide.md` - 新功能详细配置指南（新建）
3. ✅ `docs/full-guide.md` - 更新环境变量列表
4. ✅ `.env.example` - 更新配置模板
5. ✅ 本文档 - 迭代总结

---

> 🎉 所有功能已完成实现，文档已同步更新！
