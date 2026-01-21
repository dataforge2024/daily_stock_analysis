# -*- coding: utf-8 -*-
"""
===================================
多因子选股服务模块
===================================

职责：
1. 基于配置的股票池（沪深300、中证500、创业板50等）获取成分股
2. 实现多因子选股策略（价值回归、成长趋势、主题轮动等）
3. 综合分析价格、量能、趋势、波动、市场拥挤度等维度
4. 生成每日推荐股票列表（10～20只）

选股策略：
- 技术面：趋势强度、量能配合、波动率、乖离率
- 基本面：市值、换手率、涨跌幅
- 市场面：板块热度、资金流向、市场情绪
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

import pandas as pd
import numpy as np

from data_provider import DataFetcherManager
from analyzer import GeminiAnalyzer, AnalysisResult
from search_service import SearchService

logger = logging.getLogger(__name__)


class StockPool(Enum):
    """股票池枚举"""
    HS300 = "沪深300"           # 上证000300
    ZZ500 = "中证500"           # 中证000905
    CYB50 = "创业板50"          # 创业板399673
    KC50 = "科创50"             # 科创000688
    SZ50 = "上证50"             # 上证000016
    ZZ1000 = "中证1000"         # 中证000852


# 股票池对应的指数代码
POOL_INDEX_MAP = {
    StockPool.HS300: "000300",
    StockPool.ZZ500: "000905",
    StockPool.CYB50: "399673",
    StockPool.KC50: "000688",
    StockPool.SZ50: "000016",
    StockPool.ZZ1000: "000852",
}


@dataclass
class StockScore:
    """股票评分"""
    code: str
    name: str = ""
    
    # 技术面评分
    trend_score: float = 0.0        # 趋势强度评分 (0-10)
    volume_score: float = 0.0       # 量能评分 (0-10)
    volatility_score: float = 0.0   # 波动率评分 (0-10)
    bias_score: float = 0.0         # 乖离率评分 (0-10)
    
    # 基本面评分
    market_cap_score: float = 0.0   # 市值评分 (0-10)
    turnover_score: float = 0.0     # 换手率评分 (0-10)
    performance_score: float = 0.0  # 近期表现评分 (0-10)
    
    # 综合评分
    total_score: float = 0.0
    
    # 推荐理由
    reason: str = ""
    
    # 关键数据
    latest_price: float = 0.0
    pct_chg: float = 0.0
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    volume_ratio: float = 0.0       # 量比
    
    # 🆕 AI 深度分析结果
    ai_analysis: Optional[AnalysisResult] = None
    ai_sentiment_score: int = 0     # AI 评分 (0-100)
    ai_advice: str = ""             # AI 建议
    ai_core_reason: str = ""        # AI 核心理由


@dataclass
class SelectionResult:
    """选股结果"""
    date: str
    pool_name: str
    total_stocks: int
    selected_stocks: List[StockScore] = field(default_factory=list)
    selection_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # 🆕 跳过股票统计
    skipped_stocks: int = 0  # 跳过的股票数量
    skipped_codes: List[str] = field(default_factory=list)  # 跳过的股票代码
    effective_stocks: int = 0  # 实际参与评分的股票数量
    
    def format_report(self) -> str:
        """格式化选股报告"""
        lines = [
            f"📊 每日推荐股票 - {self.date}",
            f"📈 股票池：{self.pool_name}",
            f"🔍 股票池总数：{self.total_stocks} 只",
            f"✅ 成功获取数据：{self.effective_stocks} 只",
            f"❌ 跳过（数据不足）：{self.skipped_stocks} 只",
            f"⭐ 最终推荐：{len(self.selected_stocks)} 只",
            "",
            "=" * 50,
        ]
        
        for i, stock in enumerate(self.selected_stocks, 1):
            lines.append(f"\n【{i}】{stock.name} ({stock.code})")
            lines.append(f"💰 最新价：{stock.latest_price:.2f}  涨跌幅：{stock.pct_chg:+.2f}%")
            
            # 如果有 AI 分析结果，优先展示
            if stock.ai_analysis:
                lines.append(f"🤖 AI评分：{stock.ai_sentiment_score}/100  建议：{stock.ai_advice}")
                lines.append(f"📊 量化评分：{stock.total_score:.1f}/10")
                lines.append(f"💡 AI推荐理由：{stock.ai_core_reason}")
                
                # 显示 AI 给出的关键点位
                sniper_points = stock.ai_analysis.get_sniper_points()
                if sniper_points:
                    ideal_buy = sniper_points.get('ideal_buy', '')
                    stop_loss = sniper_points.get('stop_loss', '')
                    if ideal_buy or stop_loss:
                        lines.append(f"🎯 关键点位：买入 {ideal_buy} | 止损 {stop_loss}")
            else:
                lines.append(f"📊 综合评分：{stock.total_score:.1f}/10")
                lines.append(f"💡 推荐理由：{stock.reason}")
            
            lines.append(f"📈 均线：MA5={stock.ma5:.2f} MA10={stock.ma10:.2f} MA20={stock.ma20:.2f}")
            lines.append(f"📦 量比：{stock.volume_ratio:.2f}")
        
        return "\n".join(lines)


class StockSelector:
    """
    多因子选股服务（增强版 - 集成 AI 深度分析）
    
    实现策略：
    1. 第一阶段（规则筛选）：从配置的股票池获取成分股
       - 获取最近30天的日线数据
       - 计算多个技术指标和因子
       - 综合评分排序
       - 初步筛选出Top 30-50只候选股
    
    2. 第二阶段（AI深度分析）：
       - 对候选股进行 AI 深度分析
       - 结合基本面、技术面、舆情面
       - 生成详细的投资建议和理由
       - 最终筛选出Top 10-20只推荐股
    """
    
    # 选股参数
    LOOKBACK_DAYS = 30          # 回溯天数
    MIN_STOCKS = 10             # 最少推荐数量
    MAX_STOCKS = 10             # 最多推荐数量（默认推荐10只）
    MIN_TOTAL_SCORE = 6.0       # 最低综合评分
    
    # 🆕 AI 分析参数
    CANDIDATE_MULTIPLIER = 2.5  # 候选股倍数（推荐20只，则候选50只）
    AI_MIN_SCORE = 60           # AI 最低评分
    USE_AI_ANALYSIS = True      # 是否启用 AI 分析
    
    # 权重配置
    WEIGHTS = {
        'trend': 0.25,          # 趋势权重
        'volume': 0.20,         # 量能权重
        'volatility': 0.15,     # 波动率权重
        'bias': 0.15,           # 乖离率权重
        'market_cap': 0.10,     # 市值权重
        'turnover': 0.05,       # 换手率权重
        'performance': 0.10,    # 近期表现权重
    }
    
    def __init__(self, 
                 data_manager: Optional[DataFetcherManager] = None, 
                 ai_analyzer: Optional[GeminiAnalyzer] = None,
                 search_service: Optional[SearchService] = None,
                 test_mode: bool = False,
                 test_sample_size: int = 30,
                 fetch_only: bool = False,
                 analyze_only: bool = False):
        """
        初始化选股服务
        
        Args:
            data_manager: 数据管理器实例
            ai_analyzer: AI 分析器实例（用于深度分析）
            search_service: 搜索服务实例（用于获取新闻上下文）
            test_mode: 测试模式（随机选择少量股票）
            test_sample_size: 测试模式下的样本数量
            fetch_only: 仅获取数据，不进行AI分析
            analyze_only: 仅分析已获取的数据
        """
        self.data_manager = data_manager or DataFetcherManager()
        self.ai_analyzer = ai_analyzer
        self.search_service = search_service
        self.test_mode = test_mode
        self.test_sample_size = test_sample_size
        self.fetch_only = fetch_only
        self.analyze_only = analyze_only
        
        # fetch_only 模式下禁用 AI 分析
        if self.fetch_only:
            logger.info("[选股] fetch_only 模式，禁用 AI 分析")
            self.USE_AI_ANALYSIS = False
            self.ai_analyzer = None
        
        # 如果未提供且启用 AI 分析，尝试创建
        if self.USE_AI_ANALYSIS and not self.ai_analyzer and not self.fetch_only:
            try:
                self.ai_analyzer = GeminiAnalyzer()
                if not self.ai_analyzer.is_available():
                    logger.warning("[选股] AI 分析器不可用，将仅使用规则筛选")
                    self.ai_analyzer = None
            except Exception as e:
                logger.warning(f"[选股] AI 分析器初始化失败: {e}，将仅使用规则筛选")
                self.ai_analyzer = None
    
    def select_from_pool(self, pool: StockPool) -> SelectionResult:
        """
        从指定股票池选股
        
        Args:
            pool: 股票池枚举
            
        Returns:
            SelectionResult 选股结果
        """
        logger.info(f"[选股] 开始从 {pool.value} 选股...")
        
        # 1. 获取股票池成分股
        pool_stocks = self._get_pool_constituents(pool)
        logger.info(f"[选股] 获取到 {len(pool_stocks)} 只成分股")
        
        # 🧪 测试模式：随机选择少量股票
        if self.test_mode and len(pool_stocks) > self.test_sample_size:
            import random
            original_count = len(pool_stocks)
            pool_stocks = random.sample(pool_stocks, self.test_sample_size)
            logger.warning(f"[选股-测试模式] 从 {original_count} 只股票中随机抽取 {len(pool_stocks)} 只进行测试")
        
        if not pool_stocks:
            logger.warning(f"[选股] {pool.value} 成分股为空")
            return SelectionResult(
                date=datetime.now().strftime("%Y-%m-%d"),
                pool_name=pool.value,
                total_stocks=0
            )
        
        # 2. 批量获取股票数据并评分
        scored_stocks, skipped_count, skipped_codes = self._score_stocks(pool_stocks)
        logger.info(f"[选股] 完成评分，有效股票 {len(scored_stocks)} 只，跳过 {skipped_count} 只")
        
        # 3. 排序并筛选
        selected = self._filter_and_rank(scored_stocks)
        logger.info(f"[选股] 最终推荐 {len(selected)} 只股票")
        
        return SelectionResult(
            date=datetime.now().strftime("%Y-%m-%d"),
            pool_name=pool.value,
            total_stocks=len(pool_stocks),
            selected_stocks=selected,
            skipped_stocks=skipped_count,
            skipped_codes=skipped_codes,
            effective_stocks=len(scored_stocks)
        )
    
    def select_from_pools(self, pools: List[StockPool]) -> SelectionResult:
        """
        从多个股票池选股（合并去重）
        
        Args:
            pools: 股票池列表
            
        Returns:
            SelectionResult 选股结果
        """
        logger.info(f"[选股] 开始从 {len(pools)} 个股票池选股...")
        
        all_stocks = set()
        pool_names = []
        
        for pool in pools:
            constituents = self._get_pool_constituents(pool)
            all_stocks.update(constituents)
            pool_names.append(pool.value)
            logger.info(f"[选股] {pool.value} 贡献 {len(constituents)} 只股票")
        
        logger.info(f"[选股] 合并后共 {len(all_stocks)} 只股票（去重）")
        
        # 批量评分
        scored_stocks, skipped_count, skipped_codes = self._score_stocks(list(all_stocks))
        
        # 筛选排序
        selected = self._filter_and_rank(scored_stocks)
        
        return SelectionResult(
            date=datetime.now().strftime("%Y-%m-%d"),
            pool_name=" + ".join(pool_names),
            total_stocks=len(all_stocks),
            selected_stocks=selected,
            skipped_stocks=skipped_count,
            skipped_codes=skipped_codes,
            effective_stocks=len(scored_stocks)
        )
    
    def _get_pool_constituents(self, pool: StockPool) -> List[str]:
        """
        获取股票池成分股
        
        Args:
            pool: 股票池枚举
            
        Returns:
            股票代码列表
        """
        try:
            import akshare as ak
            
            # 根据不同股票池调用不同的接口
            if pool == StockPool.HS300:
                df = ak.index_stock_cons_csindex(symbol="000300")
            elif pool == StockPool.ZZ500:
                df = ak.index_stock_cons_csindex(symbol="000905")
            elif pool == StockPool.ZZ1000:
                df = ak.index_stock_cons_csindex(symbol="000852")
            elif pool == StockPool.SZ50:
                df = ak.index_stock_cons_csindex(symbol="000016")
            elif pool == StockPool.CYB50:
                df = ak.index_stock_cons_csindex(symbol="399673")
            elif pool == StockPool.KC50:
                df = ak.index_stock_cons_csindex(symbol="000688")
            else:
                logger.warning(f"[选股] 不支持的股票池: {pool}")
                return []
            
            if df is None or df.empty:
                logger.warning(f"[选股] {pool.value} 未获取到成分股数据")
                return []
            
            # 提取股票代码（通常列名为 '成分券代码' 或 '股票代码'）
            code_column = None
            for col in ['成分券代码', '股票代码', 'code', '代码']:
                if col in df.columns:
                    code_column = col
                    break
            
            if code_column is None:
                logger.error(f"[选股] 未找到股票代码列，可用列: {df.columns.tolist()}")
                return []
            
            codes = df[code_column].astype(str).tolist()
            # 去除可能的后缀（如 .SH, .SZ）
            codes = [code.split('.')[0] for code in codes]
            
            return codes
            
        except Exception as e:
            logger.error(f"[选股] 获取 {pool.value} 成分股失败: {e}")
            return []
    
    def _score_stocks(self, stock_codes: List[str]) -> Tuple[List[StockScore], int, List[str]]:
        """
        批量评分股票
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            (评分结果列表, 跳过数量, 跳过代码列表)
        """
        scored = []
        skipped_count = 0
        skipped_codes = []
        
        for i, code in enumerate(stock_codes):
            try:
                # 限流：每10只股票休眠一下
                if i > 0 and i % 10 == 0:
                    logger.info(f"[选股] 已处理 {i}/{len(stock_codes)} 只股票（成功{len(scored)}，跳过{skipped_count}）...")
                    time.sleep(2)
                
                # 获取数据
                df, source = self.data_manager.get_daily_data(
                    code, 
                    days=self.LOOKBACK_DAYS
                )
                
                if df is None or len(df) < 20:
                    logger.debug(f"[选股] {code} 数据不足，跳过")
                    skipped_count += 1
                    skipped_codes.append(code)
                    continue
                
                # 🆕 获取股票名称
                stock_name = self._get_stock_name(code, df)
                
                # 计算评分
                score = self._calculate_score(code, df)
                score.name = stock_name  # 设置股票名称
                
                if score.total_score > 0:
                    scored.append(score)
                else:
                    skipped_count += 1
                    skipped_codes.append(code)
                
            except Exception as e:
                logger.debug(f"[选股] {code} 评分失败: {e}")
                skipped_count += 1
                skipped_codes.append(code)
                continue
        
        logger.info(f"[选股] 评分完成：成功 {len(scored)} 只，跳过 {skipped_count} 只")
        return scored, skipped_count, skipped_codes
    
    def _get_stock_name(self, code: str, df: pd.DataFrame) -> str:
        """
        获取股票名称
        
        Args:
            code: 股票代码
            df: 日线数据（可能包含name列）
            
        Returns:
            股票名称
        """
        try:
            # 尝试从DataFrame获取
            if 'name' in df.columns:
                name = df.iloc[-1]['name']
                if name and str(name) != 'nan':
                    return str(name)
            
            # 尝试使用akshare获取
            try:
                import akshare as ak
                # 判断市场
                if code.startswith('6'):
                    symbol = f"sh{code}"
                elif code.startswith(('0', '3')):
                    symbol = f"sz{code}"
                else:
                    symbol = code
                
                # 获取实时数据（包含名称）
                df_realtime = ak.stock_zh_a_spot_em()
                if df_realtime is not None and '代码' in df_realtime.columns:
                    match = df_realtime[df_realtime['代码'] == code]
                    if not match.empty and '名称' in match.columns:
                        return str(match.iloc[0]['名称'])
            except:
                pass
            
            # 返回代码本身
            return code
            
        except Exception as e:
            logger.debug(f"[选股] 获取股票名称失败 {code}: {e}")
            return code
    
    def _calculate_score(self, code: str, df: pd.DataFrame) -> StockScore:
        """
        计算单只股票的综合评分
        
        Args:
            code: 股票代码
            df: 日线数据
            
        Returns:
            StockScore 评分对象
        """
        score = StockScore(code=code)
        
        try:
            # 确保数据按日期排序
            df = df.sort_values('date').reset_index(drop=True)
            latest = df.iloc[-1]
            
            # 基础数据
            score.latest_price = float(latest.get('close', 0))
            score.pct_chg = float(latest.get('pct_chg', 0))
            
            # 计算均线
            if 'ma5' in df.columns:
                score.ma5 = float(latest.get('ma5', 0))
            if 'ma10' in df.columns:
                score.ma10 = float(latest.get('ma10', 0))
            if 'ma20' in df.columns:
                score.ma20 = float(latest.get('ma20', 0))
            
            # 计算量比
            if 'volume' in df.columns and len(df) >= 5:
                avg_vol = df['volume'].iloc[-6:-1].mean()
                current_vol = float(latest['volume'])
                score.volume_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
            
            # === 1. 趋势评分 ===
            score.trend_score = self._score_trend(df)
            
            # === 2. 量能评分 ===
            score.volume_score = self._score_volume(df)
            
            # === 3. 波动率评分 ===
            score.volatility_score = self._score_volatility(df)
            
            # === 4. 乖离率评分 ===
            score.bias_score = self._score_bias(df)
            
            # === 5. 市值评分（暂用换手率代替）===
            score.market_cap_score = 5.0  # 默认中性
            
            # === 6. 换手率评分 ===
            score.turnover_score = self._score_turnover(df)
            
            # === 7. 近期表现评分 ===
            score.performance_score = self._score_performance(df)
            
            # === 计算综合评分 ===
            score.total_score = (
                score.trend_score * self.WEIGHTS['trend'] +
                score.volume_score * self.WEIGHTS['volume'] +
                score.volatility_score * self.WEIGHTS['volatility'] +
                score.bias_score * self.WEIGHTS['bias'] +
                score.market_cap_score * self.WEIGHTS['market_cap'] +
                score.turnover_score * self.WEIGHTS['turnover'] +
                score.performance_score * self.WEIGHTS['performance']
            ) * 10
            
            # === 生成推荐理由 ===
            score.reason = self._generate_reason(score, df)
            
        except Exception as e:
            logger.debug(f"[选股] {code} 评分计算失败: {e}")
            score.total_score = 0
        
        return score
    
    def _score_trend(self, df: pd.DataFrame) -> float:
        """
        趋势强度评分 (0-1)
        
        评判标准：
        - MA5 > MA10 > MA20：多头排列 +0.5
        - 均线间距扩大：趋势加强 +0.3
        - 收盘价在MA5上方：强势 +0.2
        """
        score = 0.0
        
        try:
            latest = df.iloc[-1]
            close = float(latest['close'])
            ma5 = float(latest.get('ma5', 0))
            ma10 = float(latest.get('ma10', 0))
            ma20 = float(latest.get('ma20', 0))
            
            # 多头排列
            if ma5 > ma10 > ma20 > 0:
                score += 0.5
            
            # 均线间距（相对强度）
            if ma20 > 0:
                spread = (ma5 - ma20) / ma20
                if spread > 0.05:  # 间距大于5%
                    score += 0.3
                elif spread > 0.02:
                    score += 0.15
            
            # 收盘价相对MA5位置
            if ma5 > 0:
                pos = (close - ma5) / ma5
                if -0.02 <= pos <= 0.05:  # 在MA5附近或略高
                    score += 0.2
                elif pos > 0.05:  # 过度偏离
                    score += 0.1
            
        except Exception as e:
            logger.debug(f"[选股] 趋势评分失败: {e}")
        
        return min(score, 1.0)
    
    def _score_volume(self, df: pd.DataFrame) -> float:
        """
        量能评分 (0-1)
        
        评判标准：
        - 量价配合（放量上涨）：+0.5
        - 缩量回调：+0.3
        - 量能稳定：+0.2
        """
        score = 0.0
        
        try:
            if len(df) < 5:
                return 0.0
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            current_vol = float(latest['volume'])
            prev_vol = float(prev['volume'])
            avg_vol = df['volume'].iloc[-6:-1].mean()
            
            pct_chg = float(latest.get('pct_chg', 0))
            
            # 量比
            vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
            
            # 量价配合：放量上涨
            if pct_chg > 2 and vol_ratio > 1.5:
                score += 0.5
            # 缩量回调（好信号）
            elif -2 < pct_chg < 0 and vol_ratio < 0.8:
                score += 0.3
            # 量能稳定
            elif 0.8 <= vol_ratio <= 1.2:
                score += 0.2
            
        except Exception as e:
            logger.debug(f"[选股] 量能评分失败: {e}")
        
        return min(score, 1.0)
    
    def _score_volatility(self, df: pd.DataFrame) -> float:
        """
        波动率评分 (0-1)
        
        评判标准：
        - 波动率适中（5-15%）：+0.5
        - 波动率过低（<3%）：+0.2
        - 波动率过高（>20%）：+0.1
        """
        score = 0.0
        
        try:
            if len(df) < 10:
                return 0.0
            
            # 计算最近10天的波动率（标准差）
            returns = df['close'].pct_change().iloc[-10:]
            volatility = returns.std() * np.sqrt(252) * 100  # 年化波动率
            
            if 5 <= volatility <= 15:
                score += 0.5
            elif volatility < 3:
                score += 0.2
            elif volatility > 20:
                score += 0.1
            else:
                score += 0.3
            
        except Exception as e:
            logger.debug(f"[选股] 波动率评分失败: {e}")
        
        return min(score, 1.0)
    
    def _score_bias(self, df: pd.DataFrame) -> float:
        """
        乖离率评分 (0-1)
        
        评判标准：
        - 乖离率在 -2% ~ +5% 之间：+0.5
        - 超买（>10%）：+0.1
        - 超卖（<-5%）：+0.3（可能反弹）
        """
        score = 0.0
        
        try:
            latest = df.iloc[-1]
            close = float(latest['close'])
            ma5 = float(latest.get('ma5', 0))
            
            if ma5 > 0:
                bias = (close - ma5) / ma5 * 100
                
                if -2 <= bias <= 5:
                    score += 0.5
                elif bias < -5:
                    score += 0.3  # 超卖，可能反弹
                elif bias > 10:
                    score += 0.1  # 超买，风险较高
                else:
                    score += 0.2
            
        except Exception as e:
            logger.debug(f"[选股] 乖离率评分失败: {e}")
        
        return min(score, 1.0)
    
    def _score_turnover(self, df: pd.DataFrame) -> float:
        """
        换手率评分 (0-1)
        
        评判标准：
        - 换手率适中（2-8%）：+0.5
        - 换手率过高（>15%）：+0.2
        - 换手率过低（<1%）：+0.2
        """
        score = 0.5  # 默认中性
        
        # TODO: 如果数据源提供换手率，可以进一步优化
        
        return score
    
    def _score_performance(self, df: pd.DataFrame) -> float:
        """
        近期表现评分 (0-1)
        
        评判标准：
        - 近5日涨幅 2-8%：+0.5
        - 近10日涨幅 5-15%：+0.3
        - 连续上涨：+0.2
        """
        score = 0.0
        
        try:
            if len(df) < 10:
                return 0.0
            
            # 近5日涨幅
            pct_5d = ((df['close'].iloc[-1] / df['close'].iloc[-5]) - 1) * 100
            if 2 <= pct_5d <= 8:
                score += 0.5
            elif pct_5d > 8:
                score += 0.3
            
            # 近10日涨幅
            if len(df) >= 10:
                pct_10d = ((df['close'].iloc[-1] / df['close'].iloc[-10]) - 1) * 100
                if 5 <= pct_10d <= 15:
                    score += 0.3
            
            # 连续上涨天数
            consecutive_up = 0
            for i in range(len(df) - 1, max(len(df) - 6, -1), -1):
                if df.iloc[i].get('pct_chg', 0) > 0:
                    consecutive_up += 1
                else:
                    break
            
            if consecutive_up >= 3:
                score += 0.2
            
        except Exception as e:
            logger.debug(f"[选股] 近期表现评分失败: {e}")
        
        return min(score, 1.0)
    
    def _generate_reason(self, score: StockScore, df: pd.DataFrame) -> str:
        """
        生成推荐理由（增强版，更详细）
        
        Args:
            score: 评分对象
            df: 日线数据
            
        Returns:
            推荐理由文本
        """
        reasons = []
        
        # 趋势分析（详细描述）
        if score.trend_score >= 0.7:
            latest = df.iloc[-1]
            ma5 = float(latest.get('ma5', 0))
            ma10 = float(latest.get('ma10', 0))
            ma20 = float(latest.get('ma20', 0))
            if ma5 > ma10 > ma20:
                reasons.append(f"多头排列强势(MA5>{ma5:.2f} MA10>{ma10:.2f} MA20>{ma20:.2f})")
            else:
                reasons.append("趋势向上")
        elif score.trend_score >= 0.5:
            reasons.append("趋势转好")
        
        # 量能分析（详细描述）
        if score.volume_score >= 0.5:
            if score.volume_ratio > 1.5:
                reasons.append(f"放量上涨(量比{score.volume_ratio:.2f})")
            else:
                reasons.append("量价配合良好")
        elif score.volume_score >= 0.3:
            if score.volume_ratio < 0.8:
                reasons.append(f"缩量回调(量比{score.volume_ratio:.2f}，洗盘信号)")
        
        # 乖离率分析（详细描述）
        if score.bias_score >= 0.5:
            latest = df.iloc[-1]
            close = float(latest['close'])
            ma5 = float(latest.get('ma5', 0))
            if ma5 > 0:
                bias = (close - ma5) / ma5 * 100
                if -2 <= bias <= 2:
                    reasons.append(f"回踩MA5支撑(乖离率{bias:.1f}%，最佳买点)")
                elif bias <= 5:
                    reasons.append(f"乖离率健康({bias:.1f}%，不追高)")
        elif score.bias_score >= 0.3:
            reasons.append("超卖反弹机会")
        
        # 近期表现（详细描述）
        if score.performance_score >= 0.5:
            try:
                if len(df) >= 5:
                    pct_5d = ((df['close'].iloc[-1] / df['close'].iloc[-5]) - 1) * 100
                    reasons.append(f"近5日涨{pct_5d:.1f}%")
            except:
                reasons.append("近期表现优异")
        
        # 如果没有理由，提供综合评分
        if not reasons:
            reasons.append(f"综合评分{score.total_score:.1f}/10")
        
        return "；".join(reasons)
    
    def _filter_and_rank(self, scored_stocks: List[StockScore]) -> List[StockScore]:
        """
        筛选并排序股票（两阶段）
        
        第一阶段：规则筛选
        - 筛选综合评分 >= 最低要求
        - 排序并取Top候选股（数量为最终推荐的2.5倍）
        
        第二阶段：AI 深度分析（如果启用）
        - 对候选股进行 AI 深度分析
        - 结合 AI 评分重新排序
        - 筛选出最终推荐股
        
        Args:
            scored_stocks: 评分列表
            
        Returns:
            筛选后的Top推荐股
        """
        # === 第一阶段：规则筛选 ===
        logger.info(f"[选股-阶段1] 规则筛选，候选股 {len(scored_stocks)} 只")
        
        # 筛选：综合评分 >= 最低要求
        filtered = [s for s in scored_stocks if s.total_score >= self.MIN_TOTAL_SCORE]
        logger.info(f"[选股-阶段1] 评分筛选后剩余 {len(filtered)} 只")
        
        # 排序：按综合评分降序
        filtered.sort(key=lambda x: x.total_score, reverse=True)
        
        # 取Top候选股（用于 AI 深度分析）
        candidate_count = int(self.MAX_STOCKS * self.CANDIDATE_MULTIPLIER)
        candidates = filtered[:candidate_count]
        logger.info(f"[选股-阶段1] 规则筛选Top {len(candidates)} 只候选股")
        
        # === 第二阶段：AI 深度分析 ===
        if self.ai_analyzer and self.USE_AI_ANALYSIS and len(candidates) > 0:
            logger.info(f"[选股-阶段2] 启动 AI 深度分析，分析 {len(candidates)} 只候选股...")
            final_stocks = self._ai_deep_analysis(candidates)
            logger.info(f"[选股-阶段2] AI 分析完成，最终推荐 {len(final_stocks)} 只")
            return final_stocks
        else:
            # 不使用 AI 分析，直接返回规则筛选结果
            logger.info(f"[选股] 未启用 AI 分析，返回规则筛选Top {self.MAX_STOCKS} 只")
            return candidates[:self.MAX_STOCKS]
    
    def _ai_deep_analysis(self, candidates: List[StockScore]) -> List[StockScore]:
        """
        AI 深度分析候选股
        
        流程：
        1. 为每只候选股构建分析上下文
        2. 调用 AI 进行深度分析
        3. 提取 AI 评分和建议
        4. 结合规则评分和 AI 评分重新排序
        5. 筛选出最终推荐股
        
        Args:
            candidates: 候选股列表
            
        Returns:
            AI 分析后的最终推荐股
        """
        from storage import get_db
        
        analyzed_stocks = []
        
        for i, stock in enumerate(candidates):
            try:
                logger.info(f"[AI分析] ({i+1}/{len(candidates)}) 分析 {stock.name}({stock.code})...")
                
                # 获取完整的分析上下文（包含技术面、实时行情、筹码等）
                db = get_db()
                context = db.get_analysis_context(stock.code)
                
                if not context:
                    logger.warning(f"[AI分析] {stock.code} 获取上下文失败，跳过")
                    continue
                
                # 获取新闻上下文（可选）
                news_context = None
                if self.search_service:
                    try:
                        news_context = self.search_service.search_stock_news(
                            stock_code=stock.code,
                            stock_name=stock.name,
                            days=7
                        )
                    except Exception as e:
                        logger.warning(f"[AI分析] {stock.code} 获取新闻失败: {e}")
                
                # 调用 AI 分析（使用选股推荐模式）
                ai_result = self.ai_analyzer.analyze(context, news_context=news_context, mode="stock_selection")
                
                if ai_result and ai_result.success:
                    # 提取 AI 分析结果
                    stock.ai_analysis = ai_result
                    stock.ai_sentiment_score = ai_result.sentiment_score
                    stock.ai_advice = ai_result.operation_advice
                    
                    # 提取核心理由
                    if ai_result.dashboard and 'core_conclusion' in ai_result.dashboard:
                        stock.ai_core_reason = ai_result.dashboard['core_conclusion'].get('one_sentence', ai_result.analysis_summary)
                    else:
                        stock.ai_core_reason = ai_result.key_points or ai_result.analysis_summary
                    
                    # 只保留 AI 评分 >= 最低要求的股票
                    if stock.ai_sentiment_score >= self.AI_MIN_SCORE:
                        analyzed_stocks.append(stock)
                        logger.info(f"[AI分析] {stock.name} AI评分: {stock.ai_sentiment_score}, 建议: {stock.ai_advice}")
                    else:
                        logger.info(f"[AI分析] {stock.name} AI评分过低({stock.ai_sentiment_score})，淘汰")
                else:
                    logger.warning(f"[AI分析] {stock.code} AI 分析失败")
                
                # 限流：每3只股票休眠
                if (i + 1) % 3 == 0 and i < len(candidates) - 1:
                    logger.info("[AI分析] 休眠3秒避免限流...")
                    time.sleep(3)
                    
            except Exception as e:
                logger.error(f"[AI分析] {stock.code} 分析异常: {e}")
                continue
        
        if not analyzed_stocks:
            logger.warning("[AI分析] 所有候选股AI分析均失败或评分过低，返回规则筛选结果")
            return candidates[:self.MAX_STOCKS]
        
        # 综合排序：AI 评分权重 70%，规则评分权重 30%
        for stock in analyzed_stocks:
            # 规则评分标准化到 0-100
            normalized_rule_score = (stock.total_score / 10.0) * 100
            # 综合评分
            stock.total_score = (stock.ai_sentiment_score * 0.7 + normalized_rule_score * 0.3) / 10.0
        
        # 按综合评分降序排序
        analyzed_stocks.sort(key=lambda x: x.ai_sentiment_score, reverse=True)
        
        # 取Top推荐股
        final = analyzed_stocks[:self.MAX_STOCKS]
        
        logger.info(f"[AI分析] 最终推荐 {len(final)} 只股票（AI评分范围：{final[-1].ai_sentiment_score}-{final[0].ai_sentiment_score}）")
        
        return final


# === 便捷函数 ===

def select_stocks(pools: List[str], test_mode: bool = False, test_sample_size: int = 30, 
                 fetch_only: bool = False, analyze_only: bool = False) -> SelectionResult:
    """
    便捷函数：从配置的股票池选股
    
    Args:
        pools: 股票池名称列表，如 ['沪深300', '中证500']
        test_mode: 测试模式（随机选择少量股票）
        test_sample_size: 测试模式下的样本数量
        fetch_only: 仅获取数据，不进行AI分析
        analyze_only: 仅分析已获取的数据
        
    Returns:
        SelectionResult 选股结果
    """
    if test_mode:
        logger.warning(f"[选股-测试模式] 启用测试模式，每个池随机抽取 {test_sample_size} 只股票")
    
    # 创建 AI 分析器和搜索服务（如果可用且不是 fetch_only 模式）
    ai_analyzer = None
    search_service = None
    
    if not fetch_only:
        try:
            ai_analyzer = GeminiAnalyzer()
            if not ai_analyzer.is_available():
                logger.warning("[选股] AI 分析器不可用，将仅使用规则筛选")
                ai_analyzer = None
        except Exception as e:
            logger.warning(f"[选股] AI 分析器创建失败: {e}")
        
        try:
            from search_service import SearchService
            search_service = SearchService()
        except Exception as e:
            logger.warning(f"[选股] 搜索服务创建失败: {e}")
    
    # 创建选股器
    selector = StockSelector(
        ai_analyzer=ai_analyzer,
        search_service=search_service,
        test_mode=test_mode,
        test_sample_size=test_sample_size,
        fetch_only=fetch_only,
        analyze_only=analyze_only
    )
    
    # 解析股票池
    pool_enums = []
    for pool_name in pools:
        pool_name = pool_name.strip()
        for pool_enum in StockPool:
            if pool_enum.value == pool_name:
                pool_enums.append(pool_enum)
                break
    
    if not pool_enums:
        logger.warning(f"[选股] 未找到有效的股票池配置: {pools}")
        return SelectionResult(
            date=datetime.now().strftime("%Y-%m-%d"),
            pool_name="未配置",
            total_stocks=0
        )
    
    # 执行选股
    return selector.select_from_pools(pool_enums)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )
    
    selector = StockSelector()
    
    # 测试：从沪深300选股
    result = selector.select_from_pool(StockPool.HS300)
    
    print("\n" + "=" * 60)
    print(result.format_report())
    print("=" * 60)
