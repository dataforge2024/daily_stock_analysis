# 🎯 快速开始 - 三步完成 AI 智能选股部署

本指南是 [AI_STOCK_SELECTION_GUIDE.md](./AI_STOCK_SELECTION_GUIDE.md) 的精简版，适合快速上手。

---

## 📋 准备工作（2 分钟）

### 必需项

1. **GitHub 账号** - [注册](https://github.com/signup)
2. **Gemini API Key** - [获取](https://aistudio.google.com/)（免费）

### 获取 Gemini API Key

1. 访问 https://aistudio.google.com/
2. 登录 Google 账号
3. 点击 `Get API Key` → `Create API key`
4. 复制 API Key（格式：`AIzaSy...`）

---

## 🚀 三步部署

### Step 1: Fork 仓库（1 分钟）

1. 点击右上角 **`Fork`** 按钮
2. 选择你的 GitHub 账号
3. 等待 Fork 完成

### Step 2: 配置 Secrets（3 分钟）

1. 进入你 Fork 的仓库
2. **`Settings`** → **`Secrets and variables`** → **`Actions`**
3. 点击 **`New repository secret`**，添加以下配置：

#### 必填配置

| Name | Value | 说明 |
|------|-------|------|
| `GEMINI_API_KEY` | `AIzaSy...` | 你的 Gemini API Key |
| `STOCK_POOLS` | `沪深300` | 股票池（可选：`中证500`、`创业板50`） |

#### 可选配置（增强功能）

| Name | Value | 说明 |
|------|-------|------|
| `TAVILY_API_KEYS` | `tvly-...` | [Tavily](https://tavily.com/) 新闻搜索（推荐） |
| `FEISHU_WEBHOOK` | `https://...` | 飞书通知 Webhook |

### Step 3: 启用并测试（2 分钟）

1. 点击顶部 **`Actions`** 标签
2. 点击 **`I understand my workflows, go ahead and enable them`**
3. 左侧选择 **`AI Smart Stock Selection`**
4. 右侧点击 **`Run workflow`** → 选择参数：
   - 股票池：`hs300`
   - 推荐数量：`10`
5. 点击 **`Run workflow`** 开始运行

---

## ✅ 验证结果（3-5 分钟）

### 1. 查看运行状态

- 黄色圆圈 🟡 = 运行中
- 绿色对勾 ✅ = 成功
- 红色叉号 ❌ = 失败（查看[常见问题](./AI_STOCK_SELECTION_GUIDE.md#常见问题)）

### 2. 查看日志

点击运行记录 → `智能选股分析` → 展开 `🚀 运行智能选股`

**应该看到**：

```
📊 每日推荐股票 - 2026-01-20
📈 股票池：沪深300
🔍 股票池总数：300 只
✅ 成功获取数据：285 只
❌ 跳过（数据不足）：15 只
⭐ 最终推荐：10 只

【1】贵州茅台 (600519)
💰 最新价：1650.00  涨跌幅：+2.35%
...
```

### 3. 下载结果

滚动到底部 → **`Artifacts`** → 下载 `stock-selection-results-XXX`

---

## 🤔 常见问题（快速解答）

### Q: 运行失败显示 "AI 分析器不可用"

**A**: 检查 `GEMINI_API_KEY` 是否正确配置，格式应为 `AIzaSy...`

### Q: 跳过的股票太多（>50 只）

**A**: 
1. 等待 10 分钟后重新运行
2. 配置 `TUSHARE_TOKEN` 提升稳定性

### Q: 没有股票名称，只有代码

**A**: 已在最新版本修复，如果仍有问题：
1. 确保拉取了最新代码
2. 查看日志中的 `[选股] 获取股票名称失败` 错误

### 更多问题？

查看完整文档：[AI_STOCK_SELECTION_GUIDE.md](./AI_STOCK_SELECTION_GUIDE.md#常见问题)

---

## 📅 自动运行配置

默认配置：**每个工作日 15:30（北京时间）自动运行**

### 修改运行时间

编辑 `.github/workflows/stock_selection.yml`，找到：

```yaml
schedule:
  - cron: '30 7 * * 1-5'  # 当前：15:30
```

修改为：

```yaml
  - cron: '0 10 * * 1-5'  # 18:00
  - cron: '0 1 * * 1-5'   # 09:00
```

---

## 🎯 下一步

### 基础使用

- ✅ 每天 15:30 自动运行
- ✅ 查看 Actions 页面获取结果
- ✅ 下载 Artifacts 查看详细报告

### 进阶配置

- [ ] 配置 [飞书通知](./AI_STOCK_SELECTION_GUIDE.md#飞书通知-webhook可选) 自动推送
- [ ] 启用 [数据库缓存](./DATABASE_CACHE_OPTIMIZATION.md) 提速 4-8 倍
- [ ] 配置 [多股票池并行](./AI_STOCK_SELECTION_GUIDE.md#配置矩阵策略多股票池并行)

---

## 📚 完整文档

- **[AI 智能选股部署指南](./AI_STOCK_SELECTION_GUIDE.md)** - 详细步骤（推荐）
- **[优化完成总结](./OPTIMIZATION_COMPLETED.md)** - 本次优化详情
- **[数据源分析](./DATA_SOURCE_ANALYSIS.md)** - 大规模选股方案
- **[数据库缓存优化](./DATABASE_CACHE_OPTIMIZATION.md)** - 提速指南

---

**总用时：10 分钟 | 难度：⭐ | 成本：免费**

开始你的 AI 智能选股之旅吧！🚀
