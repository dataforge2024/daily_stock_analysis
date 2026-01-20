# 🚀 数据库增量更新优化方案

## 📊 核心问题

### 当前状态
```python
每次选股（沪深300）：
- 需要获取 300 只股票 × 30 天历史数据
- API 调用次数：300 次
- 耗时：300 × 0.8秒 = 4 分钟
- 重复拉取历史数据（浪费）
```

### 目标状态
```python
优化后（首次之后）：
- 只更新最新 1-2 天数据
- API 调用次数：10-50 次
- 耗时：30-60 秒
- 节省 85% 的 API 调用
```

---

## 🛠️ 实施方案

### 1. 数据库表结构设计

已有表：`stock_history`（在 `storage.py` 中）

需要添加的字段：
```sql
ALTER TABLE stock_history ADD COLUMN last_updated TIMESTAMP;
CREATE INDEX idx_code_date ON stock_history(code, date);
CREATE INDEX idx_last_updated ON stock_history(last_updated);
```

### 2. 增量更新逻辑

#### 核心代码（在 `storage.py` 中添加）

```python
from datetime import datetime, timedelta
from typing import List, Tuple

class DatabaseManager:
    
    def get_stocks_needing_update(
        self, 
        stock_codes: List[str],
        lookback_days: int = 30
    ) -> List[Tuple[str, str]]:
        """
        获取需要更新的股票列表
        
        Returns:
            List[(code, start_date)]  # 每个股票需要从哪天开始更新
        """
        need_update = []
        today = datetime.now().strftime('%Y-%m-%d')
        lookback_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        with self.Session() as session:
            for code in stock_codes:
                # 查询该股票的最新数据日期
                latest = session.query(func.max(StockHistory.date))\
                    .filter(StockHistory.code == code)\
                    .scalar()
                
                if latest is None:
                    # 没有历史数据，需要全量拉取
                    need_update.append((code, lookback_date))
                else:
                    latest_date = latest.strftime('%Y-%m-%d')
                    # 计算需要更新的起始日期
                    next_day = (latest + timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    if next_day < today:
                        # 有缺失数据，需要更新
                        need_update.append((code, next_day))
        
        return need_update
    
    def bulk_save_stock_data(
        self,
        data_list: List[Tuple[str, pd.DataFrame]]
    ) -> int:
        """
        批量保存股票数据（优化版）
        
        Args:
            data_list: [(code, dataframe), ...]
        
        Returns:
            保存的记录数
        """
        total_saved = 0
        
        with self.Session() as session:
            for code, df in data_list:
                if df is None or df.empty:
                    continue
                
                # 准备数据
                records = []
                for date, row in df.iterrows():
                    records.append({
                        'code': code,
                        'date': date,
                        'open': row['open'],
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close'],
                        'volume': row['volume'],
                        'amount': row.get('amount', 0),
                        'pct_chg': row.get('pct_chg', 0),
                        'last_updated': datetime.now()
                    })
                
                # 批量插入（使用 upsert 避免重复）
                if records:
                    stmt = insert(StockHistory).values(records)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['code', 'date'],
                        set_={
                            'open': stmt.excluded.open,
                            'high': stmt.excluded.high,
                            'low': stmt.excluded.low,
                            'close': stmt.excluded.close,
                            'volume': stmt.excluded.volume,
                            'amount': stmt.excluded.amount,
                            'pct_chg': stmt.excluded.pct_chg,
                            'last_updated': stmt.excluded.last_updated
                        }
                    )
                    session.execute(stmt)
                    total_saved += len(records)
            
            session.commit()
        
        return total_saved
```

### 3. 修改选股逻辑

#### 在 `stock_selector.py` 中优化

```python
class StockSelector:
    
    def select_stocks_with_cache(
        self,
        stock_pool: StockPool,
        top_n: int = 3,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        智能选股（启用缓存）
        """
        logger.info(f"[选股] 开始选股，股票池: {stock_pool.value}")
        
        # 1. 获取股票池
        stock_codes = self._get_stock_pool(stock_pool)
        logger.info(f"[选股] 股票池共 {len(stock_codes)} 只股票")
        
        # 2. 检查缓存，获取需要更新的股票
        if use_cache:
            need_update = self.db.get_stocks_needing_update(
                stock_codes, 
                lookback_days=30
            )
            logger.info(f"[缓存] 需要更新 {len(need_update)} 只股票")
        else:
            # 全量更新
            need_update = [(code, (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')) 
                          for code in stock_codes]
        
        # 3. 分批获取数据（优化）
        batch_size = 50
        for i in range(0, len(need_update), batch_size):
            batch = need_update[i:i+batch_size]
            logger.info(f"[更新] 处理批次 {i//batch_size + 1}/{(len(need_update)+batch_size-1)//batch_size}")
            
            # 批量获取数据
            data_list = []
            for code, start_date in batch:
                try:
                    df = self.data_manager.fetch_stock_data(code, start_date, datetime.now().strftime('%Y-%m-%d'))
                    if df is not None and not df.empty:
                        data_list.append((code, df))
                except Exception as e:
                    logger.error(f"获取 {code} 数据失败: {e}")
            
            # 批量保存
            saved = self.db.bulk_save_stock_data(data_list)
            logger.info(f"[缓存] 保存 {saved} 条记录")
            
            # 批次间延迟（避免限流）
            if i + batch_size < len(need_update):
                time.sleep(5)  # 批次间延迟 5 秒
        
        # 4. 从数据库读取所有股票数据（已有缓存）
        logger.info(f"[缓存] 从数据库读取股票数据...")
        # ... 后续选股逻辑
```

---

## 📊 预期效果

### 首次运行（全量）
```
沪深300选股:
- 300 只股票 × 30 天
- API 调用: 300 次
- 耗时: 4-5 分钟
- 数据库写入: 9000 条记录
```

### 后续运行（增量）
```
沪深300选股:
- 仅更新最新 1-2 天数据
- API 调用: 10-50 次（大部分股票有缓存）
- 耗时: 30-60 秒
- 数据库写入: 300-600 条记录

提升:
- ⚡ 速度提升 4-8 倍
- 💰 API 调用减少 85%
- 🛡️ 稳定性提升（减少 API 压力）
```

---

## 🎯 实施步骤

### 第一阶段：基础优化（今天完成）

1. ✅ 优化数据源（已完成）
   - BaostockFetcher 优先级最高
   - EfinanceFetcher 增加延迟和重试

2. ⏳ 添加数据库索引
   ```python
   # 在 storage.py 中的表定义添加：
   Index('idx_code_date', 'code', 'date', unique=True)
   Index('idx_last_updated', 'last_updated')
   ```

3. ⏳ 实现增量更新逻辑
   - 添加 `get_stocks_needing_update()` 方法
   - 添加 `bulk_save_stock_data()` 方法

### 第二阶段：集成优化（明天完成）

1. ⏳ 修改 `stock_selector.py`
   - 集成缓存检查
   - 实现分批处理

2. ⏳ 添加配置选项
   ```python
   # config.py
   USE_DATABASE_CACHE = True  # 是否启用缓存
   CACHE_LOOKBACK_DAYS = 30   # 缓存历史天数
   BATCH_SIZE = 50            # 批处理大小
   ```

### 第三阶段：GitHub Actions（后天完成）

1. ⏳ 配置 Secrets
   - GEMINI_API_KEY
   - TUSHARE_TOKEN（可选）

2. ⏳ 测试工作流
   - 手动触发测试
   - 验证定时任务

---

## 🛡️ 注意事项

### 数据一致性

1. **并发控制**
   - GitHub Actions 只能顺序执行，无并发问题
   - 本地运行时注意不要同时启动多个实例

2. **数据校验**
   - 每次读取缓存时检查数据完整性
   - 发现异常自动触发全量更新

3. **失效策略**
   - 超过 7 天未更新的数据视为失效
   - 自动触发重新拉取

### 性能优化

1. **批量操作**
   - 使用 SQLAlchemy 的 bulk_insert_mappings
   - 减少数据库事务次数

2. **索引优化**
   - (code, date) 复合索引
   - last_updated 索引

3. **连接池**
   - 使用 SQLAlchemy 连接池
   - 避免频繁建立连接

---

## 🚀 快速开始

### 立即启用缓存

在 `.env` 文件中添加：

```bash
# 数据库缓存配置
USE_DATABASE_CACHE=true
CACHE_LOOKBACK_DAYS=30
BATCH_SIZE=50
BATCH_DELAY=5  # 批次间延迟（秒）
```

### 运行测试

```bash
# 首次运行（全量）
python3 test_ai_selection.py --pool hs300 --top-n 3

# 后续运行（增量）
python3 test_ai_selection.py --pool hs300 --top-n 3 --use-cache
```

---

## 📈 监控指标

### 关键指标

```python
{
    "total_stocks": 300,          # 总股票数
    "cached_stocks": 250,         # 缓存命中数
    "updated_stocks": 50,         # 需要更新数
    "api_calls": 50,             # API 调用次数
    "duration": 45.3,            # 耗时（秒）
    "cache_hit_rate": 0.83       # 缓存命中率
}
```

### 日志示例

```
[选股] 开始选股，股票池: 沪深300
[选股] 股票池共 300 只股票
[缓存] 检查缓存状态...
[缓存] 命中 250 只，需要更新 50 只
[更新] 处理批次 1/1
[API] 调用 BaostockFetcher 获取 50 只股票数据
[缓存] 保存 1500 条新记录
[选股] 完成评分，有效股票 298 只
[选股] 耗时 45.3 秒，API调用 50 次，缓存命中率 83%
```

---

**准备好了吗？我可以现在就开始实施增量更新逻辑！**
