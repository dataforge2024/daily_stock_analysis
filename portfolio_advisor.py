# -*- coding: utf-8 -*-
"""
===================================
持仓调仓建议模块
===================================

职责：
1. 基于现有持仓（STOCK_LIST）和市场行情
2. 结合个股表现和技术分析
3. 生成每日调仓建议
4. 优化持仓结构，提高投资回报率

调仓策略（两阶段）：
第一阶段：规则筛选
- 基于技术指标（趋势、量能、波动等）初步判断
第二阶段：AI 深度分析（可选）
- 调用 AI 分析器进行深度分析
- 生成更准确的调仓理由和风险提示
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

import pandas as pd

from data_provider import DataFetcherManager
from stock_analyzer import StockTrendAnalyzer, TrendAnalysisResult, BuySignal
from analyzer import GeminiAnalyzer, AnalysisResult

logger = logging.getLogger(__name__)


class AdjustAction(Enum):
    """调仓动作"""
    STRONG_BUY = "强烈买入"      # 空仓或低仓位时买入
    BUY = "加仓"                 # 现有仓位加仓
    HOLD = "持有"                # 保持当前仓位
    REDUCE = "减仓"              # 降低仓位
    SELL = "卖出"                # 清仓离场


@dataclass
class PositionConfig:
    """持仓配置"""
    code: str
    name: str = ""
    target_ratio: float = 100.0  # 目标仓位比例 (0-100)
    current_ratio: float = 100.0  # 当前仓位比例 (0-100)


@dataclass
class AdjustAdvice:
    """调仓建议"""
    code: str
    name: str = ""
    
    # 仓位信息
    current_ratio: float = 100.0
    target_ratio: float = 100.0
    suggested_ratio: float = 100.0
    
    # 建议动作
    action: AdjustAction = AdjustAction.HOLD
    
    # 理由
    reason: str = ""
    
    # 技术面信息
    latest_price: float = 0.0
    pct_chg: float = 0.0
    trend_status: str = ""
    signal: str = ""
    
    # 风险提示
    risk_alert: str = ""
    
    # AI 分析结果（可选）
    ai_analysis: Optional[AnalysisResult] = None
    ai_sentiment_score: Optional[int] = None
    ai_advice: Optional[str] = None
    ai_reason: Optional[str] = None


@dataclass
class PortfolioAdvice:
    """组合调仓建议"""
    date: str
    total_stocks: int
    advices: List[AdjustAdvice] = field(default_factory=list)
    summary: str = ""
    
    def format_report(self) -> str:
        """格式化调仓报告"""
        lines = [
            f"📋 持仓调仓建议 - {self.date}",
            f"📊 持仓数量：{self.total_stocks}",
            "",
            self.summary,
            "",
            "=" * 50,
        ]
        
        # 按动作分组
        buy_list = [a for a in self.advices if a.action in [AdjustAction.STRONG_BUY, AdjustAction.BUY]]
        reduce_list = [a for a in self.advices if a.action == AdjustAction.REDUCE]
        sell_list = [a for a in self.advices if a.action == AdjustAction.SELL]
        hold_list = [a for a in self.advices if a.action == AdjustAction.HOLD]
        
        # 加仓建议
        if buy_list:
            lines.append("\n🔺 加仓建议：")
            for i, adv in enumerate(buy_list, 1):
                lines.append(f"\n【{i}】{adv.name} ({adv.code})")
                lines.append(f"💰 最新价：{adv.latest_price:.2f}  涨跌幅：{adv.pct_chg:+.2f}%")
                lines.append(f"📊 当前仓位：{adv.current_ratio:.0f}% → 建议：{adv.suggested_ratio:.0f}%")
                
                # 优先显示 AI 分析结果
                if adv.ai_advice:
                    lines.append(f"🤖 AI建议：{adv.ai_advice} (评分: {adv.ai_sentiment_score}/100)")
                    lines.append(f"💡 AI理由：{adv.ai_reason}")
                else:
                    lines.append(f"📈 趋势：{adv.trend_status}  信号：{adv.signal}")
                    lines.append(f"💡 理由：{adv.reason}")
                
                if adv.risk_alert:
                    lines.append(f"⚠️ 风险：{adv.risk_alert}")
        
        # 减仓建议
        if reduce_list:
            lines.append("\n🔻 减仓建议：")
            for i, adv in enumerate(reduce_list, 1):
                lines.append(f"\n【{i}】{adv.name} ({adv.code})")
                lines.append(f"💰 最新价：{adv.latest_price:.2f}  涨跌幅：{adv.pct_chg:+.2f}%")
                lines.append(f"📊 当前仓位：{adv.current_ratio:.0f}% → 建议：{adv.suggested_ratio:.0f}%")
                
                # 优先显示 AI 分析结果
                if adv.ai_advice:
                    lines.append(f"🤖 AI建议：{adv.ai_advice} (评分: {adv.ai_sentiment_score}/100)")
                    lines.append(f"💡 AI理由：{adv.ai_reason}")
                else:
                    lines.append(f"📈 趋势：{adv.trend_status}  信号：{adv.signal}")
                    lines.append(f"💡 理由：{adv.reason}")
                
                if adv.risk_alert:
                    lines.append(f"⚠️ 风险：{adv.risk_alert}")
        
        # 卖出建议
        if sell_list:
            lines.append("\n❌ 卖出建议：")
            for i, adv in enumerate(sell_list, 1):
                lines.append(f"\n【{i}】{adv.name} ({adv.code})")
                lines.append(f"💰 最新价：{adv.latest_price:.2f}  涨跌幅：{adv.pct_chg:+.2f}%")
                lines.append(f"📊 当前仓位：{adv.current_ratio:.0f}% → 建议：清仓")
                
                # 优先显示 AI 分析结果
                if adv.ai_advice:
                    lines.append(f"🤖 AI建议：{adv.ai_advice} (评分: {adv.ai_sentiment_score}/100)")
                    lines.append(f"💡 AI理由：{adv.ai_reason}")
                else:
                    lines.append(f"📈 趋势：{adv.trend_status}  信号：{adv.signal}")
                    lines.append(f"💡 理由：{adv.reason}")
                
                if adv.risk_alert:
                    lines.append(f"⚠️ 风险：{adv.risk_alert}")
        
        # 持有建议
        if hold_list:
            lines.append(f"\n✅ 持有（{len(hold_list)}只）：")
            for adv in hold_list:
                lines.append(f"  • {adv.name} ({adv.code}) - {adv.reason}")
        
        return "\n".join(lines)


class PortfolioAdvisor:
    """
    持仓调仓顾问
    
    功能：
    1. 分析当前持仓的技术面表现
    2. 结合趋势分析给出调仓建议
    3. 动态调整仓位比例
    4. 提供风险提示
    """
    
    # 调仓阈值
    REDUCE_RATIO = 0.5          # 减仓比例（减至原来的50%）
    INCREASE_RATIO = 1.5        # 加仓比例（增至原来的150%）
    MAX_POSITION = 100.0        # 最大仓位
    MIN_POSITION = 0.0          # 最小仓位
    
    # AI 分析配置
    USE_AI_ANALYSIS = True      # 是否启用 AI 深度分析
    
    def __init__(
        self,
        data_manager: Optional[DataFetcherManager] = None,
        trend_analyzer: Optional[StockTrendAnalyzer] = None,
        ai_analyzer: Optional[GeminiAnalyzer] = None
    ):
        """
        初始化调仓顾问
        
        Args:
            data_manager: 数据管理器
            trend_analyzer: 趋势分析器
            ai_analyzer: AI 分析器（用于深度分析）
        """
        self.data_manager = data_manager or DataFetcherManager()
        self.trend_analyzer = trend_analyzer or StockTrendAnalyzer()
        self.ai_analyzer = ai_analyzer
        
        # 如果未提供且启用 AI 分析，尝试创建
        if self.USE_AI_ANALYSIS and not self.ai_analyzer:
            try:
                self.ai_analyzer = GeminiAnalyzer()
                if not self.ai_analyzer.is_available():
                    logger.warning("[调仓] AI 分析器不可用，将仅使用规则分析")
                    self.ai_analyzer = None
            except Exception as e:
                logger.warning(f"[调仓] AI 分析器初始化失败: {e}，将仅使用规则分析")
    
    def analyze_portfolio(
        self,
        positions: List[PositionConfig],
        stock_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> PortfolioAdvice:
        """
        分析持仓并生成调仓建议
        
        Args:
            positions: 持仓配置列表
            stock_data: 预加载的股票数据（可选）
            
        Returns:
            PortfolioAdvice 调仓建议
        """
        logger.info(f"[调仓] 开始分析持仓，共 {len(positions)} 只股票...")
        
        advices = []
        
        for pos in positions:
            try:
                # 获取股票数据
                if stock_data and pos.code in stock_data:
                    df = stock_data[pos.code]
                else:
                    df, _ = self.data_manager.get_daily_data(pos.code, days=30)
                
                if df is None or len(df) < 20:
                    logger.warning(f"[调仓] {pos.code} 数据不足")
                    continue
                
                # 趋势分析
                trend_result = self.trend_analyzer.analyze(df, pos.code)
                
                # 生成调仓建议
                advice = self._generate_advice(pos, trend_result, df)
                advices.append(advice)
                
            except Exception as e:
                logger.error(f"[调仓] {pos.code} 分析失败: {e}")
                continue
        
        # 生成总结
        summary = self._generate_summary(advices)
        
        return PortfolioAdvice(
            date=datetime.now().strftime("%Y-%m-%d"),
            total_stocks=len(positions),
            advices=advices,
            summary=summary
        )
    
    def _generate_advice(
        self,
        pos: PositionConfig,
        trend_result: TrendAnalysisResult,
        df: pd.DataFrame
    ) -> AdjustAdvice:
        """
        生成单只股票的调仓建议（两阶段）
        
        第一阶段：规则分析
        - 基于趋势分析结果初步判断
        
        第二阶段：AI 深度分析（可选）
        - 调用 AI 进行深度分析
        - 生成更准确的建议和理由
        
        Args:
            pos: 持仓配置
            trend_result: 趋势分析结果
            df: 日线数据
            
        Returns:
            AdjustAdvice 调仓建议
        """
        # === 第一阶段：规则分析 ===
        advice = AdjustAdvice(
            code=pos.code,
            name=pos.name or pos.code,
            current_ratio=pos.current_ratio,
            target_ratio=pos.target_ratio
        )
        
        latest = df.iloc[-1]
        advice.latest_price = float(latest['close'])
        advice.pct_chg = float(latest.get('pct_chg', 0))
        advice.trend_status = trend_result.trend_status.value
        advice.signal = trend_result.signal.value
        
        # 根据信号决定调仓动作
        self._apply_rule_based_advice(advice, trend_result, pos)
        
        # 风险提示
        advice.risk_alert = self._check_risk(trend_result, df)
        
        # === 第二阶段：AI 深度分析 ===
        if self.ai_analyzer and self.USE_AI_ANALYSIS:
            try:
                self._apply_ai_analysis(advice, pos, df)
            except Exception as e:
                logger.warning(f"[调仓] {pos.code} AI 分析失败: {e}")
        
        return advice
    
    def _apply_rule_based_advice(
        self,
        advice: AdjustAdvice,
        trend_result: TrendAnalysisResult,
        pos: PositionConfig
    ):
        """
        应用规则策略生成调仓建议
        
        Args:
            advice: 调仓建议对象（会被修改）
            trend_result: 趋势分析结果
            pos: 持仓配置
        """
        # 1. 强烈买入信号 → 加仓
        if trend_result.signal in [BuySignal.STRONG_BUY, BuySignal.BUY]:
            if pos.current_ratio < 80:
                advice.action = AdjustAction.BUY
                advice.suggested_ratio = min(
                    pos.current_ratio * self.INCREASE_RATIO,
                    self.MAX_POSITION
                )
                advice.reason = f"{trend_result.signal.value}，建议加仓"
            else:
                advice.action = AdjustAction.HOLD
                advice.suggested_ratio = pos.current_ratio
                advice.reason = "信号良好，但仓位已较高，建议持有"
        
        # 2. 持有信号 → 保持
        elif trend_result.signal == BuySignal.HOLD:
            advice.action = AdjustAction.HOLD
            advice.suggested_ratio = pos.current_ratio
            advice.reason = "趋势平稳，建议继续持有"
        
        # 3. 观望信号 → 减仓
        elif trend_result.signal == BuySignal.WAIT:
            if pos.current_ratio > 30:
                advice.action = AdjustAction.REDUCE
                advice.suggested_ratio = max(
                    pos.current_ratio * self.REDUCE_RATIO,
                    30.0
                )
                advice.reason = "趋势转弱，建议减仓观望"
            else:
                advice.action = AdjustAction.HOLD
                advice.suggested_ratio = pos.current_ratio
                advice.reason = "趋势转弱，仓位已较低，观望"
        
        # 4. 卖出信号 → 清仓
        elif trend_result.signal in [BuySignal.SELL, BuySignal.STRONG_SELL]:
            advice.action = AdjustAction.SELL
            advice.suggested_ratio = 0.0
            advice.reason = f"{trend_result.signal.value}，建议清仓离场"
            advice.risk_alert = "趋势破坏，及时止损"
        
        # 5. 其他情况 → 保持
        else:
            advice.action = AdjustAction.HOLD
            advice.suggested_ratio = pos.current_ratio
            advice.reason = "维持当前仓位"
    
    def _apply_ai_analysis(
        self,
        advice: AdjustAdvice,
        pos: PositionConfig,
        df: pd.DataFrame
    ):
        """
        应用 AI 深度分析
        
        Args:
            advice: 调仓建议对象（会被修改）
            pos: 持仓配置
            df: 日线数据
        """
        from storage import get_db
        
        logger.info(f"[调仓-AI] 分析 {pos.name}({pos.code})...")
        
        # 获取完整的分析上下文
        db = get_db()
        context = db.get_analysis_context(pos.code, days=30)
        
        if not context:
            logger.warning(f"[调仓-AI] {pos.code} 获取上下文失败")
            return
        
        # 调用 AI 分析（使用调仓建议模式）
        ai_result = self.ai_analyzer.analyze(context, news_context=None, mode="portfolio_adjustment")
        
        if ai_result and ai_result.success:
            # 保存 AI 分析结果
            advice.ai_analysis = ai_result
            advice.ai_sentiment_score = ai_result.sentiment_score
            advice.ai_advice = ai_result.operation_advice
            
            # 提取 AI 理由
            if ai_result.dashboard and 'core_conclusion' in ai_result.dashboard:
                advice.ai_reason = ai_result.dashboard['core_conclusion'].get('one_sentence', ai_result.analysis_summary)
            else:
                advice.ai_reason = ai_result.key_points or ai_result.analysis_summary
            
            # 根据 AI 评分调整建议（可选）
            # 如果 AI 评分与规则分析结果差异较大，可以调整建议
            if ai_result.sentiment_score >= 75:
                # AI 评分很高，但规则建议减仓或卖出 → 调整为持有或加仓
                if advice.action in [AdjustAction.REDUCE, AdjustAction.SELL]:
                    logger.info(f"[调仓-AI] {pos.code} AI评分{ai_result.sentiment_score}较高，调整建议从{advice.action.value}→持有")
                    advice.action = AdjustAction.HOLD
                    advice.suggested_ratio = pos.current_ratio
            elif ai_result.sentiment_score <= 40:
                # AI 评分很低，但规则建议持有或加仓 → 调整为减仓或卖出
                if advice.action in [AdjustAction.HOLD, AdjustAction.BUY]:
                    logger.info(f"[调仓-AI] {pos.code} AI评分{ai_result.sentiment_score}较低，调整建议从{advice.action.value}→减仓")
                    advice.action = AdjustAction.REDUCE
                    advice.suggested_ratio = max(pos.current_ratio * 0.5, 20.0)
            
            logger.info(f"[调仓-AI] {pos.name} AI评分: {ai_result.sentiment_score}, 建议: {ai_result.operation_advice}")
        else:
            logger.warning(f"[调仓-AI] {pos.code} AI 分析失败")
    
    def _check_risk(self, trend_result: TrendAnalysisResult, df: pd.DataFrame) -> str:
        """
        检查风险
        
        Args:
            trend_result: 趋势分析结果
            df: 日线数据
            
        Returns:
            风险提示文本
        """
        alerts = []
        
        # 乖离率过大
        if abs(trend_result.bias_ma5) > 10:
            alerts.append(f"乖离率{trend_result.bias_ma5:+.1f}%，注意回调风险")
        
        # 放量下跌
        latest = df.iloc[-1]
        if latest.get('pct_chg', 0) < -3 and len(df) >= 5:
            avg_vol = df['volume'].iloc[-6:-1].mean()
            if latest['volume'] > avg_vol * 1.5:
                alerts.append("放量下跌，资金出逃")
        
        # 跌破关键支撑
        if trend_result.support_level > 0:
            if latest['close'] < trend_result.support_level * 0.98:
                alerts.append(f"跌破支撑{trend_result.support_level:.2f}")
        
        return "；".join(alerts) if alerts else ""
    
    def _generate_summary(self, advices: List[AdjustAdvice]) -> str:
        """
        生成调仓总结
        
        Args:
            advices: 调仓建议列表
            
        Returns:
            总结文本
        """
        if not advices:
            return "暂无持仓"
        
        # 统计
        buy_count = len([a for a in advices if a.action in [AdjustAction.STRONG_BUY, AdjustAction.BUY]])
        reduce_count = len([a for a in advices if a.action == AdjustAction.REDUCE])
        sell_count = len([a for a in advices if a.action == AdjustAction.SELL])
        hold_count = len([a for a in advices if a.action == AdjustAction.HOLD])
        
        summary_parts = []
        
        if buy_count > 0:
            summary_parts.append(f"🔺 建议加仓 {buy_count} 只")
        if reduce_count > 0:
            summary_parts.append(f"🔻 建议减仓 {reduce_count} 只")
        if sell_count > 0:
            summary_parts.append(f"❌ 建议卖出 {sell_count} 只")
        if hold_count > 0:
            summary_parts.append(f"✅ 继续持有 {hold_count} 只")
        
        return "  |  ".join(summary_parts) if summary_parts else "所有持仓保持不变"


# === 便捷函数 ===

def analyze_portfolio(
    stock_list: List[str],
    position_ratios: Optional[Dict[str, float]] = None
) -> PortfolioAdvice:
    """
    便捷函数：分析持仓组合
    
    Args:
        stock_list: 股票代码列表
        position_ratios: 仓位比例字典 {code: ratio}，默认全部100%
        
    Returns:
        PortfolioAdvice 调仓建议
    """
    # 构建持仓配置
    positions = []
    for code in stock_list:
        ratio = position_ratios.get(code, 100.0) if position_ratios else 100.0
        positions.append(PositionConfig(
            code=code,
            target_ratio=ratio,
            current_ratio=ratio
        ))
    
    # 执行分析
    advisor = PortfolioAdvisor()
    return advisor.analyze_portfolio(positions)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )
    
    # 测试持仓
    test_stocks = ['600519', '300750', '002594']
    test_ratios = {'600519': 100.0, '300750': 80.0, '002594': 50.0}
    
    result = analyze_portfolio(test_stocks, test_ratios)
    
    print("\n" + "=" * 60)
    print(result.format_report())
    print("=" * 60)
