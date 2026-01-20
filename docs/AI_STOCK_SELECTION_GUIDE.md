# 📋 AI 智能选股 GitHub Actions 部署指南

本指南参考原有 `daily_stock_analysis` 的 GitHub Actions 配置，专门为 AI 智能选股功能提供详细的 Step-by-Step 操作说明。

---

## 📑 目录

- [前置准备](#前置准备)
- [Step 1: Fork 仓库](#step-1-fork-仓库)
- [Step 2: 配置 Secrets](#step-2-配置-secrets)
- [Step 3: 启用 Actions](#step-3-启用-actions)
- [Step 4: 手动测试运行](#step-4-手动测试运行)
- [Step 5: 验证运行结果](#step-5-验证运行结果)
- [Step 6: 配置定时任务](#step-6-配置定时任务)
- [常见问题](#常见问题)
- [进阶配置](#进阶配置)

---

## 前置准备

### 1. 需要准备的内容

| 项目 | 说明 | 获取方式 | 必填 |
|------|------|---------|:----:|
| GitHub 账号 | 用于 Fork 仓库 | [github.com](https://github.com) | ✅ |
| Gemini API Key | Google AI 模型 API | [aistudio.google.com](https://aistudio.google.com/) | ✅ |
| 股票池配置 | 选股范围 | `hs300`、`zz500` 等 | ✅ |

**可选配置**（增强功能）：

| 项目 | 说明 | 获取方式 |
|------|------|---------|
| Tavily API Key | 新闻搜索增强 | [tavily.com](https://tavily.com/) |
| Tushare Token | 更多数据维度 | [tushare.pro](https://tushare.pro/) |
| 飞书 Webhook | 接收选股通知 | [飞书开放平台](https://open.feishu.cn/) |

### 2. Gemini API Key 获取步骤

1. 访问 [Google AI Studio](https://aistudio.google.com/)
2. 登录 Google 账号
3. 点击 `Get API Key` → `Create API key`
4. 复制生成的 API Key（格式：`AIza...`）

> 💡 **提示**：Gemini API 有免费额度，每分钟 60 次请求，足够日常使用。

---

## Step 1: Fork 仓库

### 1.1 Fork 到你的账号

1. 访问原仓库（假设为 `https://github.com/YOUR_USERNAME/daily_stock_analysis`）
2. 点击右上角的 **`Fork`** 按钮
3. 选择你的 GitHub 账号
4. 等待 Fork 完成

### 1.2 验证 Fork 成功

- 访问 `https://github.com/YOUR_USERNAME/daily_stock_analysis`
- 确认仓库名称显示为你的用户名
- 确认分支为 `main` 或 `master`

---

## Step 2: 配置 Secrets

### 2.1 进入 Secrets 配置页面

1. 进入你 Fork 的仓库
2. 点击顶部菜单栏的 **`Settings`**
3. 左侧菜单找到 **`Secrets and variables`** → 点击 **`Actions`**
4. 点击绿色按钮 **`New repository secret`**

<div align="center">
  <img src="../sources/secret_config.png" alt="GitHub Secrets 配置示意图" width="700">
</div>

### 2.2 必填 Secrets

#### ✅ GEMINI_API_KEY（必填）

- **Name**: `GEMINI_API_KEY`
- **Value**: 你的 Gemini API Key（如 `AIzaSyABC123...`）
- 点击 **`Add secret`**

#### ✅ STOCK_POOLS（必填 - 二选一）

选择你要选股的股票池：

**方式 1：推荐股票池**（推荐）

- **Name**: `STOCK_POOLS`
- **Value**: `沪深300` 或 `中证500` 或 `沪深300,中证500`（多个用逗号分隔）

**方式 2：自定义股票列表**

- **Name**: `STOCK_LIST`
- **Value**: `600519,000858,002594`（股票代码，逗号分隔）

> 💡 **建议**：新手推荐使用 `STOCK_POOLS=沪深300`，系统会自动从 300 只股票中筛选最优的 10 只。

### 2.3 可选 Secrets（增强功能）

#### Tavily API Key（推荐）

用于获取实时新闻和市场资讯，提升 AI 分析质量。

- **Name**: `TAVILY_API_KEYS`
- **Value**: 你的 Tavily API Key
- 获取方式：访问 [tavily.com](https://tavily.com/) 注册并创建 API Key

#### Tushare Token（可选）

提供更丰富的财务数据和基本面指标。

- **Name**: `TUSHARE_TOKEN`
- **Value**: 你的 Tushare Token
- 获取方式：访问 [tushare.pro](https://tushare.pro/) 注册并获取 Token

#### 飞书通知 Webhook（可选）

接收每日选股结果推送到飞书群。

- **Name**: `FEISHU_WEBHOOK`
- **Value**: 你的飞书群机器人 Webhook URL
- 获取方式：
  1. 飞书群 → 设置 → 群机器人 → 添加机器人 → 自定义机器人
  2. 复制 Webhook URL

### 2.4 检查配置清单

完成后，你的 Secrets 列表应该包含：

- ✅ `GEMINI_API_KEY`
- ✅ `STOCK_POOLS` 或 `STOCK_LIST`
- （可选）`TAVILY_API_KEYS`
- （可选）`TUSHARE_TOKEN`
- （可选）`FEISHU_WEBHOOK`

---

## Step 3: 启用 Actions

### 3.1 启用 GitHub Actions

1. 进入你 Fork 的仓库
2. 点击顶部的 **`Actions`** 标签
3. 如果看到提示 `Workflows aren't being run on this forked repository`
4. 点击绿色按钮 **`I understand my workflows, go ahead and enable them`**

### 3.2 验证 Workflow 文件

1. 点击左侧的 **`AI Smart Stock Selection`** workflow
2. 确认 workflow 文件路径为 `.github/workflows/stock_selection.yml`
3. 确认状态显示为启用（绿色）

---

## Step 4: 手动测试运行

### 4.1 触发手动运行

1. 在 **`Actions`** 页面
2. 左侧点击 **`AI Smart Stock Selection`**
3. 右侧点击 **`Run workflow`** 下拉按钮
4. 选择参数：
   - **股票池选择**: `hs300`（沪深300）
   - **推荐股票数量**: `10`
5. 点击绿色按钮 **`Run workflow`**

<div align="center">

```
┌────────────────────────────────────────┐
│  Run workflow                          │
├────────────────────────────────────────┤
│  Use workflow from: Branch: main       │
│                                        │
│  股票池选择: [hs300 ▼]                 │
│                                        │
│  推荐股票数量: [10 ▼]                  │
│                                        │
│  [Run workflow]                        │
└────────────────────────────────────────┘
```

</div>

### 4.2 观察运行过程

1. 刷新页面，会看到一个新的 workflow run（黄色圆圈 🟡 表示运行中）
2. 点击进入该 run
3. 点击 `智能选股分析` job
4. 展开各个步骤查看日志：
   - ✅ 检出代码
   - ✅ 设置 Python 环境
   - ✅ 安装依赖
   - ✅ 配置环境
   - 🔄 运行智能选股（这步需要 3-5 分钟）

### 4.3 等待完成

- **预计时间**：首次运行 4-5 分钟（沪深 300，10 只推荐）
- **成功标志**：绿色对勾 ✅
- **失败标志**：红色叉号 ❌（参考[常见问题](#常见问题)）

---

## Step 5: 验证运行结果

### 5.1 查看日志输出

1. 展开 `🚀 运行智能选股` 步骤
2. 滚动到日志底部
3. 应该看到类似输出：

```
📊 每日推荐股票 - 2026-01-20
📈 股票池：沪深300
🔍 股票池总数：300 只
✅ 成功获取数据：285 只
❌ 跳过（数据不足）：15 只
⭐ 最终推荐：10 只

==================================================

【1】贵州茅台 (600519)
💰 最新价：1650.00  涨跌幅：+2.35%
🤖 AI评分：85/100  建议：买入
📊 量化评分：8.5/10
💡 AI推荐理由：多头排列强势，量价配合良好，基本面稳健
📈 均线：MA5=1645.00 MA10=1630.00 MA20=1610.00
📦 量比：1.35

【2】...
```

### 5.2 下载结果文件

1. 回到 workflow run 主页
2. 滚动到底部 **`Artifacts`** 区域
3. 点击下载 `stock-selection-results-XXX`
4. 解压后查看：
   - `stock_selection_20260120.json` - JSON 格式结果
   - `*.log` - 详细运行日志

### 5.3 验证统计信息

重点检查日志中的统计信息：

```
🔍 股票池总数：300 只      ← 股票池成分股数量
✅ 成功获取数据：285 只     ← 实际参与评分的股票
❌ 跳过（数据不足）：15 只  ← 因数据问题被跳过的股票
⭐ 最终推荐：10 只          ← AI 精选的推荐股票
```

> ✅ **正常情况**：跳过股票数量 < 10%
> ⚠️ **需要关注**：跳过股票数量 > 20%（可能是数据源问题，参考[常见问题](#常见问题)）

### 5.4 检查飞书通知（如果配置）

如果配置了 `FEISHU_WEBHOOK`，你会在飞书群收到推送消息：

```
📊 AI智能选股完成
时间: 2026-01-20 15:35
推荐股票: 10 只

详情请查看 GitHub Actions 结果
```

---

## Step 6: 配置定时任务

### 6.1 定时任务说明

默认配置为**每个工作日 15:30（北京时间）**自动运行：

```yaml
schedule:
  - cron: '30 7 * * 1-5'  # UTC 7:30 = 北京时间 15:30（周一到周五）
```

### 6.2 修改定时时间（可选）

如果需要修改运行时间：

1. 进入你的仓库
2. 点击 `.github/workflows/stock_selection.yml`
3. 点击 ✏️ 编辑按钮
4. 找到 `cron` 行，修改时间：

**常用时间配置**：

| 北京时间 | Cron 表达式 | 说明 |
|---------|------------|------|
| 15:30 | `30 7 * * 1-5` | 收盘后（默认） |
| 18:00 | `0 10 * * 1-5` | 晚上 6 点 |
| 09:00 | `0 1 * * 1-5` | 开盘前 |
| 12:00 | `0 4 * * 1-5` | 午间休市 |

> 💡 **提示**：GitHub Actions 使用 UTC 时间，需要减去 8 小时。

5. 提交修改

### 6.3 禁用定时任务

如果只想手动运行，不需要自动运行：

1. 编辑 `.github/workflows/stock_selection.yml`
2. 注释掉 `schedule` 部分：

```yaml
# schedule:
#   - cron: '30 7 * * 1-5'
```

3. 提交修改

---

## 常见问题

### ❓ Q1: Workflow 运行失败，显示 "AI 分析器不可用"

**原因**：`GEMINI_API_KEY` 未配置或配置错误

**解决**：
1. 检查 Secrets 中是否有 `GEMINI_API_KEY`
2. 检查 API Key 格式是否正确（应以 `AIza` 开头）
3. 检查 API Key 是否过期或被禁用
4. 重新运行 workflow

### ❓ Q2: 跳过的股票数量过多（>50 只）

**原因**：数据源网络不稳定或限流

**解决**：
1. 等待 10 分钟后重新运行（可能是临时限流）
2. 检查是否配置了 `TUSHARE_TOKEN`（提升数据源稳定性）
3. 参考 [数据源优化文档](./DATA_SOURCE_ANALYSIS.md)

### ❓ Q3: 运行超时（>60 分钟）

**原因**：股票池过大或网络慢

**解决**：
1. 减少推荐数量（如改为 5 只）
2. 使用较小的股票池（如上证50而不是全市场）
3. 增加 `timeout-minutes` 配置

### ❓ Q4: 推荐的股票数量少于预期

**原因**：符合筛选条件的股票不足

**解决**：
1. 查看日志中的 `[选股-阶段1] 评分筛选后剩余 X 只`
2. 如果候选股不足，说明当前市场符合条件的股票较少（正常现象）
3. 可以降低 `MIN_TOTAL_SCORE` 参数（在 `stock_selector.py` 中）

### ❓ Q5: 没有收到飞书通知

**原因**：Webhook 配置错误或消息发送失败

**解决**：
1. 检查 `FEISHU_WEBHOOK` 格式是否正确
2. 在飞书群设置中确认机器人是否启用
3. 查看 workflow 日志中的 `📧 发送结果通知` 步骤

### ❓ Q6: 如何查看更详细的日志？

**解决**：
1. 下载 Artifacts 中的日志文件
2. 或修改代码中的日志级别：

```python
# 在 test_ai_selection.py 中
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG
    ...
)
```

### ❓ Q7: 推荐的股票没有名称，只有代码

**原因**：名称获取失败或数据源未返回名称

**解决**：已在最新版本中优化，会尝试从多个数据源获取股票名称。如果仍然没有，说明该股票可能已退市或代码错误。

---

## 进阶配置

### 🔧 自定义选股参数

编辑 `.github/workflows/stock_selection.yml`，在 `workflow_dispatch` 部分添加更多参数：

```yaml
workflow_dispatch:
  inputs:
    stock_pool:
      description: '股票池选择'
      required: true
      default: 'hs300'
      type: choice
      options:
        - hs300      # 沪深300
        - zz500      # 中证500
        - sz50       # 上证50
        - cyb50      # 创业板50
        - kc50       # 科创50
    
    top_n:
      description: '推荐股票数量'
      required: true
      default: '10'
      type: choice
      options:
        - '5'
        - '10'
        - '15'
        - '20'
```

### 🔧 配置多个股票池

修改 Secrets 中的 `STOCK_POOLS`：

```
沪深300,中证500,创业板50
```

系统会自动合并去重，从所有股票池中选股。

### 🔧 启用数据库缓存

参考 [数据库缓存优化文档](./DATABASE_CACHE_OPTIMIZATION.md)，实施后可将运行时间从 4-5 分钟缩短到 30-60 秒。

### 🔧 配置矩阵策略（多股票池并行）

编辑 `.github/workflows/stock_selection.yml`，添加 `strategy.matrix`：

```yaml
jobs:
  stock-selection:
    strategy:
      matrix:
        pool: [hs300, zz500, cyb50]
    name: 智能选股分析 - ${{ matrix.pool }}
    ...
    
    steps:
      - name: 🚀 运行智能选股
        run: |
          python3 test_ai_selection.py \
            --pool ${{ matrix.pool }} \
            --top-n 10
```

这样会同时为多个股票池生成选股结果。

---

## 🎯 总结检查清单

部署完成后，确保以下项目都已完成：

- [ ] ✅ Fork 仓库到自己的 GitHub 账号
- [ ] ✅ 配置 `GEMINI_API_KEY` Secret
- [ ] ✅ 配置 `STOCK_POOLS` 或 `STOCK_LIST` Secret
- [ ] ✅ 启用 GitHub Actions
- [ ] ✅ 手动运行一次测试成功
- [ ] ✅ 验证日志输出正确，包含统计信息
- [ ] ✅ 下载并查看结果文件
- [ ] ✅ （可选）配置飞书通知并收到推送
- [ ] ✅ （可选）配置定时任务，确认时间正确

**下一步**：
- 每个工作日 15:30 自动运行，获取 AI 智能选股推荐
- 查看 Actions 页面的运行历史
- 根据市场情况调整股票池和参数

---

## 📚 相关文档

1. **[数据源优化分析](./DATA_SOURCE_ANALYSIS.md)** - 了解数据源选择和优化策略
2. **[数据库缓存优化](./DATABASE_CACHE_OPTIMIZATION.md)** - 提升运行速度
3. **[GitHub Actions 配置](./GITHUB_ACTIONS_SETUP.md)** - 高级 Actions 配置
4. **[完整配置指南](./full-guide.md)** - 原有系统的完整配置

---

**准备好了吗？开始你的 AI 智能选股之旅！** 🚀

如有问题，请提交 [Issue](https://github.com/YOUR_USERNAME/daily_stock_analysis/issues) 或查看项目 Wiki。
