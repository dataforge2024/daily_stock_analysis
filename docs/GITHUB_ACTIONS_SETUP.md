# 🚀 GitHub Actions 配置完整指南

## 📋 前置要求

1. ✅ GitHub 账号
2. ✅ 项目代码已上传到 GitHub
3. ✅ Gemini API Key（必须）
4. ⏳ Tushare Token（可选，推荐）
5. ⏳ 飞书 Webhook（可选）

---

## 🛠️ 配置步骤

### 第一步：创建 GitHub Repository

```bash
# 如果还没有创建仓库
cd /Users/hongzhiyuan/code/own/daily_stock_analysis

# 初始化 Git（如果还没有）
git init

# 添加远程仓库
git remote add origin https://github.com/你的用户名/daily_stock_analysis.git

# 提交代码
git add .
git commit -m "Initial commit: AI智能选股系统"
git push -u origin main
```

### 第二步：配置 Secrets

进入 GitHub 仓库页面：**Settings → Secrets and variables → Actions → New repository secret**

#### 必须配置的 Secrets

| Name | Value | 说明 |
|------|-------|------|
| `GEMINI_API_KEY` | `AIza...` | Gemini API 密钥（必须） |

#### 可选配置的 Secrets

| Name | Value | 说明 |
|------|-------|------|
| `TUSHARE_TOKEN` | `你的token` | Tushare Pro Token（推荐） |
| `TAVILY_API_KEY` | `tvly-...` | Tavily 搜索 API（可选） |
| `FEISHU_WEBHOOK` | `https://...` | 飞书通知 Webhook（可选） |

**配置截图示例**：
```
Name: GEMINI_API_KEY
Value: AIzaSyC_YourActualKeyHere_abcdefg...

点击 "Add secret" 保存
```

### 第三步：启用 GitHub Actions

1. 确保工作流文件已创建
   ```
   .github/workflows/stock_selection.yml  ✅ 已创建
   ```

2. 进入仓库页面：**Actions 标签页**

3. 如果看到提示，点击 **"I understand my workflows, go ahead and enable them"**

4. 你应该能看到 "AI Smart Stock Selection" 工作流

### 第四步：测试运行

#### 方式 1：手动触发（推荐首次测试）

1. 进入 **Actions → AI Smart Stock Selection**
2. 点击右侧 **"Run workflow"** 按钮
3. 选择参数：
   - Branch: `main`
   - 股票池选择: `hs300`（沪深300）
   - 推荐股票数量: `3`
4. 点击 **"Run workflow"** 开始

#### 方式 2：等待定时触发

工作流会在每个工作日（周一到周五）北京时间 15:30 自动运行

**查看运行状态**：
- ✅ 绿色：成功
- 🟡 黄色：运行中
- ❌ 红色：失败（点击查看日志）

---

## 📊 工作流说明

### 运行时间说明

```yaml
# 定时触发 Cron 表达式
'30 7 * * 1-5'

解释:
- 30: UTC 时间 7:30
- 7: UTC 7 点
- * * 1-5: 每周一到周五

转换:
UTC 7:30 = 北京时间 15:30（UTC+8）
```

**为什么选择 15:30？**
- 股市 15:00 收盘
- 等待 30 分钟数据稳定
- 避开收盘高峰期

### 修改运行时间

编辑 `.github/workflows/stock_selection.yml`：

```yaml
schedule:
  # 改成每天 16:00 运行
  - cron: '0 8 * * 1-5'  # UTC 8:00 = 北京时间 16:00
  
  # 改成每天 9:30 运行（开盘后）
  - cron: '30 1 * * 1-5'  # UTC 1:30 = 北京时间 9:30
```

### 手动触发参数说明

| 参数 | 选项 | 说明 |
|------|------|------|
| stock_pool | hs300 / zz500 / all | 股票池选择 |
| top_n | 3 / 5 / 10 | 推荐股票数量 |

---

## 📈 查看运行结果

### 方法 1：查看运行日志

1. **Actions → 选择运行记录**
2. 点击 "智能选股分析" 作业
3. 展开每个步骤查看详细日志

**关键日志示例**：
```
📊 股票池: hs300
🔢 推荐数量: 3

[选股] 开始选股，股票池: 沪深300
[选股] 股票池共 300 只股票
[缓存] 命中 250 只，需要更新 50 只
[更新] 处理批次 1/1
[API] BaostockFetcher 获取成功
[选股] 完成评分，有效股票 298 只
[AI分析] 分析 4 只候选股...
[选股] 最终推荐 3 只股票

✅ 选股完成
```

### 方法 2：下载 Artifacts

1. **Actions → 选择运行记录**
2. 滚动到页面底部 "Artifacts" 部分
3. 下载 `stock-selection-results-XXX.zip`
4. 解压查看：
   - `stock_selection_20260120.json`：选股结果
   - `logs/*.log`：详细日志

**结果文件格式**：
```json
{
  "date": "2026-01-20",
  "pool": "hs300",
  "recommendations": [
    {
      "code": "000792",
      "name": "盐湖股份",
      "score": 9.9,
      "reason": "多头排列强势、乖离率健康...",
      "ai_analysis": {
        "sentiment_score": 85,
        "trend_prediction": "强烈看多",
        ...
      }
    },
    ...
  ]
}
```

### 方法 3：飞书通知（如果配置）

配置后会自动发送通知到飞书群：
```
📊 AI智能选股完成
时间: 2026-01-20 15:45
推荐股票: 3 只

详情请查看 GitHub Actions 结果
```

---

## 🔧 常见问题

### 1. 工作流运行失败

**可能原因**：
- ❌ Secrets 未配置或配置错误
- ❌ API Key 额度用尽
- ❌ 网络问题（偶发）

**解决方法**：
1. 检查 Secrets 配置
2. 查看详细日志定位问题
3. 点击 "Re-run failed jobs" 重试

### 2. 运行超时

**现象**：运行超过 60 分钟自动停止

**原因**：
- 股票数量过多（全市场）
- 数据源响应慢

**解决方法**：
- 使用更小的股票池（hs300 而非 all）
- 启用数据库缓存（减少 API 调用）
- 增加 timeout-minutes 限制

### 3. API 限流

**现象**：大量 "RemoteDisconnected" 错误

**原因**：
- 短时间内请求过多
- IP 被限流

**解决方法**：
- ✅ 已优化：使用 BaostockFetcher（不限流）
- ✅ 已优化：增加请求延迟
- ✅ 已优化：启用数据库缓存

---

## 💰 成本分析

### GitHub Actions 免费额度

| 仓库类型 | 免费时长 | 并发作业数 |
|---------|---------|-----------|
| Public | **无限制** | 20 |
| Private | 2000 分钟/月 | 5 |

### 实际消耗

**单次运行**：
```
沪深300选股:
- 运行时长: 5-10 分钟
- 每月运行: 约 20 次（每工作日）
- 总消耗: 100-200 分钟/月

✅ 私有仓库免费额度足够
✅ 公开仓库完全免费
```

**优化后（启用缓存）**：
```
沪深300选股:
- 首次: 5-10 分钟
- 后续: 2-3 分钟
- 月总消耗: 60-80 分钟

✅ 节省 60% 时长
```

---

## 🚀 高级配置

### 多策略并行

```yaml
jobs:
  strategy-matrix:
    strategy:
      matrix:
        pool: [hs300, zz500]
        top_n: [3, 5]
    steps:
      - name: 运行选股
        run: |
          python3 test_ai_selection.py \
            --pool ${{ matrix.pool }} \
            --top-n ${{ matrix.top_n }}
```

### 结果持久化

```yaml
- name: 提交结果到仓库
  run: |
    git config user.name "GitHub Actions"
    git config user.email "actions@github.com"
    git add results/
    git commit -m "📊 更新选股结果 $(date +%Y-%m-%d)"
    git push
```

### 失败重试

```yaml
- name: 运行选股（带重试）
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 30
    max_attempts: 3
    command: python3 test_ai_selection.py
```

---

## 📚 相关文档

- [数据源分析报告](./DATA_SOURCE_ANALYSIS.md)
- [数据库缓存优化](./DATABASE_CACHE_OPTIMIZATION.md)
- [GitHub Actions 官方文档](https://docs.github.com/en/actions)

---

## ✅ 配置检查清单

使用前确认：

- [ ] GitHub 仓库已创建
- [ ] 代码已推送到 main 分支
- [ ] Secrets 已配置（至少 GEMINI_API_KEY）
- [ ] GitHub Actions 已启用
- [ ] 工作流文件 `.github/workflows/stock_selection.yml` 存在
- [ ] 已测试手动触发（建议）
- [ ] 已查看运行日志（确认无误）

**配置完成后，系统将每天自动运行，完全免费！** 🎉
