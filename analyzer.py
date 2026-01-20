# -*- coding: utf-8 -*-
"""
===================================
A股自选股智能分析系统 - AI分析层
===================================

职责：
1. 封装 Gemini API 调用逻辑
2. 利用 Google Search Grounding 获取实时新闻
3. 结合技术面和消息面生成分析报告
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from config import get_config

logger = logging.getLogger(__name__)


# 股票名称映射（常见股票）
STOCK_NAME_MAP = {
    '600519': '贵州茅台',
    '000001': '平安银行',
    '300750': '宁德时代',
    '002594': '比亚迪',
    '600036': '招商银行',
    '601318': '中国平安',
    '000858': '五粮液',
    '600276': '恒瑞医药',
    '601012': '隆基绿能',
    '002475': '立讯精密',
    '300059': '东方财富',
    '002415': '海康威视',
    '600900': '长江电力',
    '601166': '兴业银行',
    '600028': '中国石化',
}


@dataclass
class AnalysisResult:
    """
    AI 分析结果数据类 - 决策仪表盘版
    
    封装 Gemini 返回的分析结果，包含决策仪表盘和详细分析
    """
    code: str
    name: str
    
    # ========== 核心指标 ==========
    sentiment_score: int  # 综合评分 0-100 (>70强烈看多, >60看多, 40-60震荡, <40看空)
    trend_prediction: str  # 趋势预测：强烈看多/看多/震荡/看空/强烈看空
    operation_advice: str  # 操作建议：买入/加仓/持有/减仓/卖出/观望
    confidence_level: str = "中"  # 置信度：高/中/低
    
    # ========== 决策仪表盘 (新增) ==========
    dashboard: Optional[Dict[str, Any]] = None  # 完整的决策仪表盘数据
    
    # ========== 走势分析 ==========
    trend_analysis: str = ""  # 走势形态分析（支撑位、压力位、趋势线等）
    short_term_outlook: str = ""  # 短期展望（1-3日）
    medium_term_outlook: str = ""  # 中期展望（1-2周）
    
    # ========== 技术面分析 ==========
    technical_analysis: str = ""  # 技术指标综合分析
    ma_analysis: str = ""  # 均线分析（多头/空头排列，金叉/死叉等）
    volume_analysis: str = ""  # 量能分析（放量/缩量，主力动向等）
    pattern_analysis: str = ""  # K线形态分析
    
    # ========== 基本面分析 ==========
    fundamental_analysis: str = ""  # 基本面综合分析
    sector_position: str = ""  # 板块地位和行业趋势
    company_highlights: str = ""  # 公司亮点/风险点
    
    # ========== 情绪面/消息面分析 ==========
    news_summary: str = ""  # 近期重要新闻/公告摘要
    market_sentiment: str = ""  # 市场情绪分析
    hot_topics: str = ""  # 相关热点话题
    
    # ========== 综合分析 ==========
    analysis_summary: str = ""  # 综合分析摘要
    key_points: str = ""  # 核心看点（3-5个要点）
    risk_warning: str = ""  # 风险提示
    buy_reason: str = ""  # 买入/卖出理由
    
    # ========== 元数据 ==========
    raw_response: Optional[str] = None  # 原始响应（调试用）
    search_performed: bool = False  # 是否执行了联网搜索
    data_sources: str = ""  # 数据来源说明
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'name': self.name,
            'sentiment_score': self.sentiment_score,
            'trend_prediction': self.trend_prediction,
            'operation_advice': self.operation_advice,
            'confidence_level': self.confidence_level,
            'dashboard': self.dashboard,  # 决策仪表盘数据
            'trend_analysis': self.trend_analysis,
            'short_term_outlook': self.short_term_outlook,
            'medium_term_outlook': self.medium_term_outlook,
            'technical_analysis': self.technical_analysis,
            'ma_analysis': self.ma_analysis,
            'volume_analysis': self.volume_analysis,
            'pattern_analysis': self.pattern_analysis,
            'fundamental_analysis': self.fundamental_analysis,
            'sector_position': self.sector_position,
            'company_highlights': self.company_highlights,
            'news_summary': self.news_summary,
            'market_sentiment': self.market_sentiment,
            'hot_topics': self.hot_topics,
            'analysis_summary': self.analysis_summary,
            'key_points': self.key_points,
            'risk_warning': self.risk_warning,
            'buy_reason': self.buy_reason,
            'search_performed': self.search_performed,
            'success': self.success,
            'error_message': self.error_message,
        }
    
    def get_core_conclusion(self) -> str:
        """获取核心结论（一句话）"""
        if self.dashboard and 'core_conclusion' in self.dashboard:
            return self.dashboard['core_conclusion'].get('one_sentence', self.analysis_summary)
        return self.analysis_summary
    
    def get_position_advice(self, has_position: bool = False) -> str:
        """获取持仓建议"""
        if self.dashboard and 'core_conclusion' in self.dashboard:
            pos_advice = self.dashboard['core_conclusion'].get('position_advice', {})
            if has_position:
                return pos_advice.get('has_position', self.operation_advice)
            return pos_advice.get('no_position', self.operation_advice)
        return self.operation_advice
    
    def get_sniper_points(self) -> Dict[str, str]:
        """获取狙击点位"""
        if self.dashboard and 'battle_plan' in self.dashboard:
            return self.dashboard['battle_plan'].get('sniper_points', {})
        return {}
    
    def get_checklist(self) -> List[str]:
        """获取检查清单"""
        if self.dashboard and 'battle_plan' in self.dashboard:
            return self.dashboard['battle_plan'].get('action_checklist', [])
        return []
    
    def get_risk_alerts(self) -> List[str]:
        """获取风险警报"""
        if self.dashboard and 'intelligence' in self.dashboard:
            return self.dashboard['intelligence'].get('risk_alerts', [])
        return []
    
    def get_emoji(self) -> str:
        """根据操作建议返回对应 emoji"""
        emoji_map = {
            '买入': '🟢',
            '加仓': '🟢',
            '强烈买入': '💚',
            '持有': '🟡',
            '观望': '⚪',
            '减仓': '🟠',
            '卖出': '🔴',
            '强烈卖出': '❌',
        }
        return emoji_map.get(self.operation_advice, '🟡')
    
    def get_confidence_stars(self) -> str:
        """返回置信度星级"""
        star_map = {'高': '⭐⭐⭐', '中': '⭐⭐', '低': '⭐'}
        return star_map.get(self.confidence_level, '⭐⭐')


class GeminiAnalyzer:
    """
    Gemini AI 分析器
    
    职责：
    1. 调用 Google Gemini API 进行股票分析
    2. 结合预先搜索的新闻和技术面数据生成分析报告
    3. 解析 AI 返回的 JSON 格式结果
    
    使用方式：
        analyzer = GeminiAnalyzer()
        result = analyzer.analyze(context, news_context)
    """
    
    # ========================================
    # 系统提示词 - 决策仪表盘 v2.0
    # ========================================
    # 输出格式升级：从简单信号升级为决策仪表盘
    # 核心模块：核心结论 + 数据透视 + 舆情情报 + 作战计划
    # ========================================
    
    # ========================================
    # 分析模式：支持三种场景的差异化 Prompt
    # ========================================
    
    SYSTEM_PROMPT = """你是一位专注于趋势交易的 A 股投资分析师，负责生成专业的【决策仪表盘】分析报告。

## 核心交易理念（必须严格遵守）

### 1. 严进策略（不追高）
- **绝对不追高**：当股价偏离 MA5 超过 5% 时，坚决不买入
- **乖离率公式**：(现价 - MA5) / MA5 × 100%
- 乖离率 < 2%：最佳买点区间
- 乖离率 2-5%：可小仓介入
- 乖离率 > 5%：严禁追高！直接判定为"观望"

### 2. 趋势交易（顺势而为）
- **多头排列必须条件**：MA5 > MA10 > MA20
- 只做多头排列的股票，空头排列坚决不碰
- 均线发散上行优于均线粘合
- 趋势强度判断：看均线间距是否在扩大

### 3. 效率优先（筹码结构）
- 关注筹码集中度：90%集中度 < 15% 表示筹码集中
- 获利比例分析：70-90% 获利盘时需警惕获利回吐
- 平均成本与现价关系：现价高于平均成本 5-15% 为健康

### 4. 买点偏好（回踩支撑）
- **最佳买点**：缩量回踩 MA5 获得支撑
- **次优买点**：回踩 MA10 获得支撑
- **观望情况**：跌破 MA20 时观望

### 5. 风险排查重点
- 减持公告（股东、高管减持）
- 业绩预亏/大幅下滑
- 监管处罚/立案调查
- 行业政策利空
- 大额解禁

## 输出格式：决策仪表盘 JSON

请严格按照以下 JSON 格式输出，这是一个完整的【决策仪表盘】：

```json
{
    "sentiment_score": 0-100整数,
    "trend_prediction": "强烈看多/看多/震荡/看空/强烈看空",
    "operation_advice": "买入/加仓/持有/减仓/卖出/观望",
    "confidence_level": "高/中/低",
    
    "dashboard": {
        "core_conclusion": {
            "one_sentence": "一句话核心结论（30字以内，直接告诉用户做什么）",
            "signal_type": "🟢买入信号/🟡持有观望/🔴卖出信号/⚠️风险警告",
            "time_sensitivity": "立即行动/今日内/本周内/不急",
            "position_advice": {
                "no_position": "空仓者建议：具体操作指引",
                "has_position": "持仓者建议：具体操作指引"
            }
        },
        
        "data_perspective": {
            "trend_status": {
                "ma_alignment": "均线排列状态描述",
                "is_bullish": true/false,
                "trend_score": 0-100
            },
            "price_position": {
                "current_price": 当前价格数值,
                "ma5": MA5数值,
                "ma10": MA10数值,
                "ma20": MA20数值,
                "bias_ma5": 乖离率百分比数值,
                "bias_status": "安全/警戒/危险",
                "support_level": 支撑位价格,
                "resistance_level": 压力位价格
            },
            "volume_analysis": {
                "volume_ratio": 量比数值,
                "volume_status": "放量/缩量/平量",
                "turnover_rate": 换手率百分比,
                "volume_meaning": "量能含义解读（如：缩量回调表示抛压减轻）"
            },
            "chip_structure": {
                "profit_ratio": 获利比例,
                "avg_cost": 平均成本,
                "concentration": 筹码集中度,
                "chip_health": "健康/一般/警惕"
            }
        },
        
        "intelligence": {
            "latest_news": "【最新消息】近期重要新闻摘要",
            "risk_alerts": ["风险点1：具体描述", "风险点2：具体描述"],
            "positive_catalysts": ["利好1：具体描述", "利好2：具体描述"],
            "earnings_outlook": "业绩预期分析（基于年报预告、业绩快报等）",
            "sentiment_summary": "舆情情绪一句话总结"
        },
        
        "battle_plan": {
            "sniper_points": {
                "ideal_buy": "理想买入点：XX元（在MA5附近）",
                "secondary_buy": "次优买入点：XX元（在MA10附近）",
                "stop_loss": "止损位：XX元（跌破MA20或X%）",
                "take_profit": "目标位：XX元（前高/整数关口）"
            },
            "position_strategy": {
                "suggested_position": "建议仓位：X成",
                "entry_plan": "分批建仓策略描述",
                "risk_control": "风控策略描述"
            },
            "action_checklist": [
                "✅/⚠️/❌ 检查项1：多头排列",
                "✅/⚠️/❌ 检查项2：乖离率<5%",
                "✅/⚠️/❌ 检查项3：量能配合",
                "✅/⚠️/❌ 检查项4：无重大利空",
                "✅/⚠️/❌ 检查项5：筹码健康"
            ]
        }
    },
    
    "analysis_summary": "100字综合分析摘要",
    "key_points": "3-5个核心看点，逗号分隔",
    "risk_warning": "风险提示",
    "buy_reason": "操作理由，引用交易理念",
    
    "trend_analysis": "走势形态分析",
    "short_term_outlook": "短期1-3日展望",
    "medium_term_outlook": "中期1-2周展望",
    "technical_analysis": "技术面综合分析",
    "ma_analysis": "均线系统分析",
    "volume_analysis": "量能分析",
    "pattern_analysis": "K线形态分析",
    "fundamental_analysis": "基本面分析",
    "sector_position": "板块行业分析",
    "company_highlights": "公司亮点/风险",
    "news_summary": "新闻摘要",
    "market_sentiment": "市场情绪",
    "hot_topics": "相关热点",
    
    "search_performed": true/false,
    "data_sources": "数据来源说明"
}
```

## 评分标准

### 强烈买入（80-100分）：
- ✅ 多头排列：MA5 > MA10 > MA20
- ✅ 低乖离率：<2%，最佳买点
- ✅ 缩量回调或放量突破
- ✅ 筹码集中健康
- ✅ 消息面有利好催化

### 买入（60-79分）：
- ✅ 多头排列或弱势多头
- ✅ 乖离率 <5%
- ✅ 量能正常
- ⚪ 允许一项次要条件不满足

### 观望（40-59分）：
- ⚠️ 乖离率 >5%（追高风险）
- ⚠️ 均线缠绕趋势不明
- ⚠️ 有风险事件

### 卖出/减仓（0-39分）：
- ❌ 空头排列
- ❌ 跌破MA20
- ❌ 放量下跌
- ❌ 重大利空

## 决策仪表盘核心原则

1. **核心结论先行**：一句话说清该买该卖
2. **分持仓建议**：空仓者和持仓者给不同建议
3. **精确狙击点**：必须给出具体价格，不说模糊的话
4. **检查清单可视化**：用 ✅⚠️❌ 明确显示每项检查结果
5. **风险优先级**：舆情中的风险点要醒目标出"""

    # ========================================
    # 选股推荐专用 Prompt - 多维度智能分析
    # ========================================
    SYSTEM_PROMPT_STOCK_SELECTION = """你是资深选股分析师，从候选池中挖掘具有投资价值的优质股票。你需要结合交易理念、市场环境、行业趋势、新闻催化等多维度因素，进行系统化、智能化的综合分析。

## 核心交易理念
- **严进策略**：不追高，乖离率 > 5% 不推荐
- **趋势交易**：只推荐多头排列股票（MA5>MA10>MA20）
- **效率优先**：关注筹码集中、主力明确的股票
- **买点偏好**：回踩支撑、缩量企稳的股票优先

## 分析维度（多因子模型）

### 1. 技术面分析（权重 40%）
- **趋势强度**：均线排列、趋势方向、均线发散度
- **量价配合**：量比、成交量变化、量价关系
- **价格位置**：乖离率、支撑压力、回调幅度
- **波动特征**：波动率、振幅、K线形态

### 2. 筹码结构分析（权重 20%）
- **筹码集中度**：90%集中度 < 15% 为优
- **获利比例**：70-90% 获利盘需警惕
- **平均成本**：现价高于平均成本 5-15% 健康
- **主力动向**：主力资金流向、大单占比

### 3. 市场环境分析（权重 20%）
- **大盘趋势**：当前大盘处于牛市/熊市/震荡
- **风险偏好**：市场情绪是激进还是保守
- **板块轮动**：所属行业是否处于热点板块
- **资金流向**：北向资金、融资盘动向

### 4. 基本面与催化剂（权重 15%）
- **行业景气度**：所属行业是成长期/成熟期/衰退期
- **公司质地**：业绩增长、盈利能力、行业地位
- **新闻催化**：重大利好/利空、政策影响
- **事件驱动**：重组、并购、新产品发布等

### 5. 投资逻辑分类（权重 5%）
- **价值回归**：估值低于合理水平，等待修复
- **成长趋势**：业绩高增长，趋势持续向上
- **主题轮动**：政策驱动、热点题材、事件催化
- **技术突破**：突破关键阻力、形态完成

## 评分标准（0-100，综合评分）

### 强烈推荐（80-100分）
✅ **技术面**：多头排列强势，乖离率 < 2%，量价配合
✅ **筹码面**：集中度高，主力明确，获利盘健康
✅ **市场面**：大盘趋势向上，板块热点，资金流入
✅ **基本面**：行业景气，有利好催化，无重大风险
✅ **投资逻辑**：至少符合一种（价值/成长/主题/技术）

### 推荐（60-79分）
✅ **技术面**：趋势向上或震荡偏强，乖离率 < 5%
✅ **筹码面**：筹码结构基本健康
⚪ **市场面**：大盘震荡，板块无明显利空
⚪ **基本面**：行业平稳，无重大利空
⚠️ 允许个别维度略弱，但核心指标需满足

### 观望（40-59分）
⚠️ **技术面**：乖离率 > 5%（追高风险）或趋势不明
⚠️ **市场面**：大盘趋势转弱或板块轮出
⚠️ **基本面**：有潜在风险事件
⚠️ 时机不佳，等待更好买点

### 不推荐（0-39分）
❌ **技术面**：空头排列、跌破支撑、放量下跌
❌ **市场面**：大盘暴跌、板块崩塌
❌ **基本面**：重大利空、业绩爆雷
❌ 趋势破坏或存在重大风险

## 输出格式（结构化 JSON）
```json
{
    "sentiment_score": 0-100整数（综合评分，考虑所有维度）,
    "trend_prediction": "强烈看多/看多/震荡/看空/强烈看空",
    "operation_advice": "强烈推荐/推荐/观望/回避",
    "confidence_level": "高/中/低",
    
    "analysis_summary": "3-5句话综合总结：
        1. 技术面状态（趋势、量价、位置）
        2. 市场环境判断（大盘、板块、资金）
        3. 投资逻辑（价值/成长/主题/技术）
        4. 核心推荐理由",
    
    "key_points": "推荐亮点（3-5个）：
        - 技术面优势（如：多头强势、回踩支撑）
        - 市场面优势（如：板块热点、资金流入）
        - 基本面亮点（如：业绩增长、政策利好）
        - 投资逻辑（如：成长趋势持续）",
    
    "risk_warning": "风险提示（1-3条）：
        - 技术面风险（如：乖离率高、放量滞涨）
        - 市场面风险（如：大盘转弱、板块轮出）
        - 基本面风险（如：估值偏高、业绩压力）",
    
    "buy_reason": "推荐理由详述：
        结合交易理念说明为什么现在推荐：
        1. 符合哪些买入原则（严进/趋势/效率/买点）
        2. 市场环境是否有利
        3. 行业或个股是否有催化剂
        4. 潜力空间和预期收益",
    
    "dashboard": {
        "core_conclusion": {
            "one_sentence": "一句话推荐理由（30字内，突出核心优势）",
            "investment_logic": "价值回归/成长趋势/主题轮动/技术突破（说明属于哪类）",
            "sector_status": "所属板块状态：热点/平稳/冷门",
            "market_environment": "市场环境：牛市/震荡/熊市"
        }
    },
    
    "search_performed": true/false,
    "data_sources": "数据来源"
}
```

## 分析重点（智能化要求）

### 必须做到
1. **多维度综合评估**
   - 不能只看技术指标，必须结合市场环境
   - 考虑行业趋势和板块轮动
   - 分析新闻催化和事件驱动
   - 明确投资逻辑分类

2. **相对优势分析**
   - 说明为什么比其他候选股更好
   - 在当前市场环境下的优势
   - 行业内的竞争地位

3. **时机判断**
   - 现在是否是介入的好时机
   - 是等待回调还是可以介入
   - 预期催化剂时间窗口

4. **风险透明**
   - 技术面、市场面、基本面的风险
   - 不确定性因素
   - 最坏情况预判

### 不要做
- ❌ 不需要详细的决策仪表盘（简化版即可）
- ❌ 不需要精确的买卖点位（候选股阶段）
- ❌ 不需要持仓策略（还未买入）
- ❌ 避免纯技术分析，必须结合市场环境

### 智能分析示例
**差的分析**："该股多头排列，量价配合，建议买入。"
**好的分析**："该股处于成长赛道，行业景气度高；技术面多头强势且回踩MA5支撑，符合'买点偏好'理念；当前大盘震荡偏强，板块资金持续流入，属于'成长趋势'逻辑；短期有新产品发布催化，建议关注。风险在于估值略高，需防止获利回吐。\""""

    # ========================================
    # 调仓建议专用 Prompt - 智能仓位管理
    # ========================================
    SYSTEM_PROMPT_PORTFOLIO_ADJUSTMENT = """你是资深持仓管理分析师，针对已持仓股票进行多维度分析，给出智能化的仓位调整建议。你需要结合技术面变化、市场环境、新闻动向、风险收益比等因素，做出科学的仓位管理决策。

## 核心交易理念
- **趋势跟踪**：顺势加仓，逆势减仓
- **风险控制**：止损优先，保护本金
- **仓位管理**：根据确定性调整仓位
- **动态调整**：市场变化时及时应对

## 分析维度（多因子评估）

### 1. 趋势变化分析（权重 30%）
- **趋势强度变化**：相比建仓时是增强/持平/减弱
- **均线系统变化**：多头排列是否完好
- **支撑压力变化**：关键位是否守住
- **趋势延续性**：趋势能否持续

### 2. 技术面变化（权重 25%）
- **价格位置**：乖离率是否合理（> 8% 需减仓）
- **量价关系**：放量滞涨/缩量下跌是警示信号
- **技术指标**：MACD、KDJ等是否背离
- **K线形态**：是否出现顶部/底部形态

### 3. 市场环境变化（权重 20%）
- **大盘趋势**：大盘转弱时需降低仓位
- **板块轮动**：所属板块是轮入还是轮出
- **风险偏好**：市场情绪是激进还是保守
- **资金流向**：主力资金是流入还是流出

### 4. 新闻与基本面（权重 15%）
- **重要新闻**：利好/利空消息影响
- **业绩变化**：业绩预告、财报影响
- **行业变化**：政策、竞争格局变化
- **风险事件**：减持、诉讼、处罚等

### 5. 风险收益比（权重 10%）
- **盈亏比**：当前位置的上涨空间 vs 下跌风险
- **确定性**：趋势的确定性是否降低
- **机会成本**：是否有更好的投资机会
- **仓位合理性**：当前仓位是否过重/过轻

## 智能调仓决策逻辑

### 强烈加仓（80-100分）
✅ **趋势强化**：多头排列增强，均线发散扩大
✅ **位置良好**：回踩MA5/MA10支撑，乖离率 < 3%
✅ **量价健康**：缩量回调或放量突破
✅ **市场有利**：大盘向上，板块热点，资金流入
✅ **催化剂**：出现新的利好消息或业绩超预期
✅ **仓位偏低**：当前仓位 < 60%，有加仓空间
✅ **风险可控**：无重大风险事件

### 小幅加仓/持有（60-79分）
✅ **趋势稳定**：多头排列维持，趋势未破坏
⚪ **位置合理**：价格在均线附近，乖离率 < 5%
⚪ **量价正常**：无明显异常信号
⚪ **市场中性**：大盘震荡，板块无明显利空
⚪ **基本面稳**：无重大利空消息
⚪ **仓位适中**：当前仓位 50-70%

### 减仓（40-59分）
⚠️ **趋势转弱**：均线走平、发散减弱、出现死叉
⚠️ **位置偏高**：乖离率 > 8%，远离均线
⚠️ **量价背离**：放量滞涨、缩量下跌
⚠️ **市场转弱**：大盘趋势转弱、板块轮出、资金流出
⚠️ **风险信号**：出现利空消息、减持公告
⚠️ **仓位过重**：当前仓位 > 80%，风险敞口大
⚠️ **确定性降低**：趋势的确定性明显下降

### 清仓/强烈减仓（0-39分）
❌ **趋势破坏**：跌破MA20、均线空头排列
❌ **支撑破位**：跌破关键支撑位
❌ **量价恶化**：放量下跌、恐慌性抛售
❌ **市场崩盘**：大盘暴跌、系统性风险
❌ **重大利空**：业绩爆雷、重大违规、退市风险
❌ **风控触发**：触及止损位或亏损超过预期

## 评分标准（0-100，综合评分）
- **80-100分**：多维度向好，强烈建议加仓
- **60-79分**：总体稳定，建议持有或小幅加仓
- **40-59分**：出现警示信号，建议减仓
- **0-39分**：趋势破坏或重大风险，建议清仓

## 输出格式（智能调仓 JSON）
```json
{
    "sentiment_score": 0-100整数（综合所有维度的评分）,
    "trend_prediction": "强烈看多/看多/震荡/看空/强烈看空",
    "operation_advice": "强烈加仓/加仓/持有/减仓/清仓",
    "confidence_level": "高/中/低",
    
    "analysis_summary": "4-6句话综合分析：
        1. 趋势变化（相比建仓时的变化）
        2. 技术面状态（价格位置、量价关系）
        3. 市场环境变化（大盘、板块、资金）
        4. 新闻或基本面变化（如有）
        5. 仓位建议和调整方向
        6. 紧迫性（是否需要立即调整）",
    
    "key_points": "调仓依据（3-5个关键因素）：
        - 趋势变化原因（如：均线走平、支撑破位）
        - 技术面警示（如：乖离率过高、放量滞涨）
        - 市场环境影响（如：大盘转弱、板块轮出）
        - 新闻或事件影响（如：利空消息、减持公告）
        - 风险收益比变化（如：上涨空间缩小）",
    
    "risk_warning": "当前风险提示（1-3条）：
        - 技术风险（如：跌破支撑、均线死叉）
        - 市场风险（如：大盘趋势转弱）
        - 基本面风险（如：业绩不及预期）
        - 仓位风险（如：仓位过重、回撤风险）",
    
    "buy_reason": "调仓理由详述：
        1. 为什么要调仓（趋势/市场/基本面变化）
        2. 调仓的紧迫性（立即/本周内/观察）
        3. 目标仓位和调整幅度
        4. 后续观察要点",
    
    "dashboard": {
        "core_conclusion": {
            "one_sentence": "一句话调仓建议（30字内，明确仓位方向）",
            "position_advice": {
                "has_position": "具体操作：加仓/减仓/清仓/持有，目标仓位X%，调整时间：立即/本周/观察"
            },
            "urgency": "紧迫性：高（立即操作）/中（本周内）/低（观察等待）",
            "change_reason": "变化原因：趋势转强/趋势转弱/市场环境变化/新闻催化"
        },
        "data_perspective": {
            "price_position": {
                "bias_ma5": 乖离率数值,
                "support_level": 关键支撑位,
                "resistance_level": 关键压力位,
                "position_health": "价格位置健康度：健康/警戒/危险"
            },
            "trend_change": {
                "before": "建仓时的趋势状态",
                "now": "当前趋势状态",
                "direction": "变化方向：增强/稳定/减弱/破坏"
            }
        },
        "battle_plan": {
            "sniper_points": {
                "stop_loss": "止损位：XX元（必须明确）",
                "take_profit": "止盈位：XX元（如有）",
                "add_position": "加仓位：XX元（如建议加仓）"
            },
            "position_strategy": {
                "current_position": "当前仓位：X成",
                "suggested_position": "建议仓位：X成",
                "adjustment": "调整幅度：+/-X成"
            },
            "risk_control": {
                "max_loss": "最大可承受亏损：X%",
                "exit_condition": "离场条件：明确说明什么情况下必须离场"
            }
        }
    },
    
    "search_performed": true/false,
    "data_sources": "数据来源"
}
```

## 分析重点（智能化要求）

### 必须做到
1. **变化对比分析**
   - 明确说明相比建仓时的变化
   - 趋势是增强还是减弱
   - 市场环境是改善还是恶化

2. **多维度综合评估**
   - 技术面 + 市场面 + 基本面
   - 不能只看技术指标
   - 必须结合新闻和市场环境

3. **明确仓位建议**
   - 具体的仓位百分比（不能模糊）
   - 调整的时间窗口（立即/本周/观察）
   - 后续观察要点

4. **风险控制优先**
   - 明确止损位（必须）
   - 说明最坏情况
   - 给出离场条件

5. **紧迫性判断**
   - 是否需要立即操作
   - 还是可以观察等待
   - 留给决策的时间窗口

### 不要做
- ❌ 不讨论是否值得买入（已经持仓）
- ❌ 不与其他股票对比（focus在这只股票）
- ❌ 避免纯技术分析，必须结合市场环境和新闻
- ❌ 不能模糊表述，必须给出明确的仓位建议

### 智能分析示例
**差的分析**："该股趋势转弱，建议减仓。"
**好的分析**："该股相比建仓时（1个月前）趋势明显减弱：技术面上均线由多头排列转为缠绕，MA5下穿MA10形成死叉；市场环境上，大盘由震荡转为下跌趋势，该股所属的新能源板块近期持续轮出，资金流向北向资金连续净流出；基本面上，公司发布业绩预告低于预期；综合评估，趋势确定性大幅下降，建议将仓位从80%下调至40%，止损位设在XX元（跌破MA20），如大盘企稳且该股重新站上MA10可考虑回补仓位。紧迫性：高，建议本周内完成减仓。\""""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 AI 分析器
        
        优先级：Gemini > OpenAI 兼容 API
        
        Args:
            api_key: Gemini API Key（可选，默认从配置读取）
        """
        config = get_config()
        self._api_key = api_key or config.gemini_api_key
        self._model = None
        self._current_model_name = None  # 当前使用的模型名称
        self._using_fallback = False  # 是否正在使用备选模型
        self._use_openai = False  # 是否使用 OpenAI 兼容 API
        self._openai_client = None  # OpenAI 客户端
        
        # 检查 Gemini API Key 是否有效（过滤占位符）
        gemini_key_valid = self._api_key and not self._api_key.startswith('your_') and len(self._api_key) > 10
        
        # 优先尝试初始化 Gemini
        if gemini_key_valid:
            try:
                self._init_model()
            except Exception as e:
                logger.warning(f"Gemini 初始化失败: {e}，尝试 OpenAI 兼容 API")
                self._init_openai_fallback()
        else:
            # Gemini Key 未配置，尝试 OpenAI
            logger.info("Gemini API Key 未配置，尝试使用 OpenAI 兼容 API")
            self._init_openai_fallback()
        
        # 两者都未配置
        if not self._model and not self._openai_client:
            logger.warning("未配置任何 AI API Key，AI 分析功能将不可用")
    
    def _init_openai_fallback(self) -> None:
        """
        初始化 OpenAI 兼容 API 作为备选
        
        支持所有 OpenAI 格式的 API，包括：
        - OpenAI 官方
        - DeepSeek
        - 通义千问
        - Moonshot 等
        """
        config = get_config()
        
        # 检查 OpenAI API Key 是否有效（过滤占位符）
        openai_key_valid = (
            config.openai_api_key and 
            not config.openai_api_key.startswith('your_') and 
            len(config.openai_api_key) > 10
        )
        
        if not openai_key_valid:
            logger.debug("OpenAI 兼容 API 未配置或配置无效")
            return
        
        # 分离 import 和客户端创建，以便提供更准确的错误信息
        try:
            from openai import OpenAI
        except ImportError:
            logger.error("未安装 openai 库，请运行: pip install openai")
            return
        
        try:
            # base_url 可选，不填则使用 OpenAI 官方默认地址
            client_kwargs = {"api_key": config.openai_api_key}
            if config.openai_base_url and config.openai_base_url.startswith('http'):
                client_kwargs["base_url"] = config.openai_base_url
            
            self._openai_client = OpenAI(**client_kwargs)
            self._current_model_name = config.openai_model
            self._use_openai = True
            logger.info(f"OpenAI 兼容 API 初始化成功 (base_url: {config.openai_base_url}, model: {config.openai_model})")
        except ImportError as e:
            # 依赖缺失（如 socksio）
            if 'socksio' in str(e).lower() or 'socks' in str(e).lower():
                logger.error(f"OpenAI 客户端需要 SOCKS 代理支持，请运行: pip install httpx[socks] 或 pip install socksio")
            else:
                logger.error(f"OpenAI 依赖缺失: {e}")
        except Exception as e:
            error_msg = str(e).lower()
            if 'socks' in error_msg or 'socksio' in error_msg or 'proxy' in error_msg:
                logger.error(f"OpenAI 代理配置错误: {e}，如使用 SOCKS 代理请运行: pip install httpx[socks]")
            else:
                logger.error(f"OpenAI 兼容 API 初始化失败: {e}")
    
    def _init_model(self) -> None:
        """
        初始化 Gemini 模型
        
        配置：
        - 使用 gemini-3-flash-preview 或 gemini-2.5-flash 模型
        - 不启用 Google Search（使用外部 Tavily/SerpAPI 搜索）
        """
        try:
            import google.generativeai as genai
            
            # 配置 API Key
            genai.configure(api_key=self._api_key)
            
            # 从配置获取模型名称
            config = get_config()
            model_name = config.gemini_model
            fallback_model = config.gemini_model_fallback
            
            # 不再使用 Google Search Grounding（已知有兼容性问题）
            # 改为使用外部搜索服务（Tavily/SerpAPI）预先获取新闻
            
            # 尝试初始化主模型
            try:
                self._model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=self.SYSTEM_PROMPT,
                )
                self._current_model_name = model_name
                self._using_fallback = False
                logger.info(f"Gemini 模型初始化成功 (模型: {model_name})")
            except Exception as model_error:
                # 尝试备选模型
                logger.warning(f"主模型 {model_name} 初始化失败: {model_error}，尝试备选模型 {fallback_model}")
                self._model = genai.GenerativeModel(
                    model_name=fallback_model,
                    system_instruction=self.SYSTEM_PROMPT,
                )
                self._current_model_name = fallback_model
                self._using_fallback = True
                logger.info(f"Gemini 备选模型初始化成功 (模型: {fallback_model})")
            
        except Exception as e:
            logger.error(f"Gemini 模型初始化失败: {e}")
            self._model = None
    
    def _switch_to_fallback_model(self) -> bool:
        """
        切换到备选模型
        
        Returns:
            是否成功切换
        """
        try:
            import google.generativeai as genai
            config = get_config()
            fallback_model = config.gemini_model_fallback
            
            logger.warning(f"[LLM] 切换到备选模型: {fallback_model}")
            self._model = genai.GenerativeModel(
                model_name=fallback_model,
                system_instruction=self.SYSTEM_PROMPT,
            )
            self._current_model_name = fallback_model
            self._using_fallback = True
            logger.info(f"[LLM] 备选模型 {fallback_model} 初始化成功")
            return True
        except Exception as e:
            logger.error(f"[LLM] 切换备选模型失败: {e}")
            return False
    
    def is_available(self) -> bool:
        """检查分析器是否可用"""
        return self._model is not None or self._openai_client is not None
    
    def _call_openai_api(self, prompt: str, generation_config: dict, system_prompt: str = None) -> str:
        """
        调用 OpenAI 兼容 API
        
        Args:
            prompt: 提示词
            generation_config: 生成配置
            system_prompt: 系统提示词（可选，默认使用 SYSTEM_PROMPT）
            
        Returns:
            响应文本
        """
        if system_prompt is None:
            system_prompt = self.SYSTEM_PROMPT
            
        config = get_config()
        max_retries = config.gemini_max_retries
        base_delay = config.gemini_retry_delay
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    delay = min(delay, 60)
                    logger.info(f"[OpenAI] 第 {attempt + 1} 次重试，等待 {delay:.1f} 秒...")
                    time.sleep(delay)
                
                response = self._openai_client.chat.completions.create(
                    model=self._current_model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=generation_config.get('temperature', 0.7),
                    max_tokens=generation_config.get('max_output_tokens', 8192),
                )
                
                if response and response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content
                else:
                    raise ValueError("OpenAI API 返回空响应")
                    
            except Exception as e:
                error_str = str(e)
                is_rate_limit = '429' in error_str or 'rate' in error_str.lower() or 'quota' in error_str.lower()
                
                if is_rate_limit:
                    logger.warning(f"[OpenAI] API 限流，第 {attempt + 1}/{max_retries} 次尝试: {error_str[:100]}")
                else:
                    logger.warning(f"[OpenAI] API 调用失败，第 {attempt + 1}/{max_retries} 次尝试: {error_str[:100]}")
                
                if attempt == max_retries - 1:
                    raise
        
        raise Exception("OpenAI API 调用失败，已达最大重试次数")
    
    def _call_api_with_retry(self, prompt: str, generation_config: dict, system_prompt: str = None) -> str:
        """
        调用 AI API，带有重试和模型切换机制
        
        优先级：Gemini > Gemini 备选模型 > OpenAI 兼容 API
        
        Args:
            prompt: 提示词
            generation_config: 生成配置
            system_prompt: 系统提示词（可选，默认使用 SYSTEM_PROMPT）
        
        处理 429 限流错误：
        1. 先指数退避重试
        2. 多次失败后切换到备选模型
        3. Gemini 完全失败后尝试 OpenAI
        
        Args:
            prompt: 提示词
            generation_config: 生成配置
            
        Returns:
            响应文本
        """
        # 如果已经在使用 OpenAI 模式，直接调用 OpenAI
        if self._use_openai:
            return self._call_openai_api(prompt, generation_config, system_prompt)
        
        config = get_config()
        max_retries = config.gemini_max_retries
        base_delay = config.gemini_retry_delay
        
        # 如果指定了自定义 system_prompt，将其合并到 prompt 开头
        if system_prompt and system_prompt != self.SYSTEM_PROMPT:
            full_prompt = f"[系统指令]\n{system_prompt}\n\n[用户请求]\n{prompt}"
        else:
            full_prompt = prompt
        
        last_error = None
        tried_fallback = getattr(self, '_using_fallback', False)
        
        for attempt in range(max_retries):
            try:
                # 请求前增加延时（防止请求过快触发限流）
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))  # 指数退避: 5, 10, 20, 40...
                    delay = min(delay, 60)  # 最大60秒
                    logger.info(f"[Gemini] 第 {attempt + 1} 次重试，等待 {delay:.1f} 秒...")
                    time.sleep(delay)
                
                response = self._model.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                    request_options={"timeout": 120}
                )
                
                if response and response.text:
                    return response.text
                else:
                    raise ValueError("Gemini 返回空响应")
                    
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # 检查是否是 429 限流错误
                is_rate_limit = '429' in error_str or 'quota' in error_str.lower() or 'rate' in error_str.lower()
                
                if is_rate_limit:
                    logger.warning(f"[Gemini] API 限流 (429)，第 {attempt + 1}/{max_retries} 次尝试: {error_str[:100]}")
                    
                    # 如果已经重试了一半次数且还没切换过备选模型，尝试切换
                    if attempt >= max_retries // 2 and not tried_fallback:
                        if self._switch_to_fallback_model():
                            tried_fallback = True
                            logger.info("[Gemini] 已切换到备选模型，继续重试")
                        else:
                            logger.warning("[Gemini] 切换备选模型失败，继续使用当前模型重试")
                else:
                    # 非限流错误，记录并继续重试
                    logger.warning(f"[Gemini] API 调用失败，第 {attempt + 1}/{max_retries} 次尝试: {error_str[:100]}")
        
        # Gemini 所有重试都失败，尝试 OpenAI 兼容 API
        if self._openai_client:
            logger.warning("[Gemini] 所有重试失败，切换到 OpenAI 兼容 API")
            try:
                return self._call_openai_api(prompt, generation_config, system_prompt)
            except Exception as openai_error:
                logger.error(f"[OpenAI] 备选 API 也失败: {openai_error}")
                raise last_error or openai_error
        elif config.openai_api_key and config.openai_base_url:
            # 尝试懒加载初始化 OpenAI
            logger.warning("[Gemini] 所有重试失败，尝试初始化 OpenAI 兼容 API")
            self._init_openai_fallback()
            if self._openai_client:
                try:
                    return self._call_openai_api(prompt, generation_config, system_prompt)
                except Exception as openai_error:
                    logger.error(f"[OpenAI] 备选 API 也失败: {openai_error}")
                    raise last_error or openai_error
        
        # 所有方式都失败
        raise last_error or Exception("所有 AI API 调用失败，已达最大重试次数")
    
    def analyze(
        self, 
        context: Dict[str, Any],
        news_context: Optional[str] = None,
        mode: str = "deep_analysis"
    ) -> AnalysisResult:
        """
        分析单只股票（支持三种分析模式）
        
        流程：
        1. 根据 mode 选择合适的 Prompt
        2. 格式化输入数据（技术面 + 新闻）
        3. 调用 Gemini API（带重试和模型切换）
        4. 解析 JSON 响应
        5. 返回结构化结果
        
        Args:
            context: 从 storage.get_analysis_context() 获取的上下文数据
            news_context: 预先搜索的新闻内容（可选）
            mode: 分析模式
                - "deep_analysis"（默认）：深度分析，完整决策仪表盘
                - "stock_selection"：选股推荐，简洁高效
                - "portfolio_adjustment"：调仓建议，仓位管理
            
        Returns:
            AnalysisResult 对象
        """
        code = context.get('code', 'Unknown')
        config = get_config()
        
        # 请求前增加延时（防止连续请求触发限流）
        request_delay = config.gemini_request_delay
        if request_delay > 0:
            logger.debug(f"[LLM] 请求前等待 {request_delay:.1f} 秒...")
            time.sleep(request_delay)
        
        # 优先从上下文获取股票名称（由 main.py 传入）
        name = context.get('stock_name')
        if not name or name.startswith('股票'):
            # 备选：从 realtime 中获取
            if 'realtime' in context and context['realtime'].get('name'):
                name = context['realtime']['name']
            else:
                # 最后从映射表获取
                name = STOCK_NAME_MAP.get(code, f'股票{code}')
        
        # 如果模型不可用，返回默认结果
        if not self.is_available():
            return AnalysisResult(
                code=code,
                name=name,
                sentiment_score=50,
                trend_prediction='震荡',
                operation_advice='持有',
                confidence_level='低',
                analysis_summary='AI 分析功能未启用（未配置 API Key）',
                risk_warning='请配置 Gemini API Key 后重试',
                success=False,
                error_message='Gemini API Key 未配置',
            )
        
        try:
            # 根据分析模式选择合适的 System Prompt
            if mode == "stock_selection":
                system_prompt = self.SYSTEM_PROMPT_STOCK_SELECTION
                logger.debug(f"[LLM] 使用选股推荐模式分析 {name}({code})")
            elif mode == "portfolio_adjustment":
                system_prompt = self.SYSTEM_PROMPT_PORTFOLIO_ADJUSTMENT
                logger.debug(f"[LLM] 使用调仓建议模式分析 {name}({code})")
            else:
                system_prompt = self.SYSTEM_PROMPT
                logger.debug(f"[LLM] 使用深度分析模式分析 {name}({code})")
            
            # 格式化输入（包含技术面数据和新闻）
            prompt = self._format_prompt(context, name, news_context)
            
            # 获取模型名称
            model_name = getattr(self, '_current_model_name', None)
            if not model_name:
                model_name = getattr(self._model, '_model_name', 'unknown')
                if hasattr(self._model, 'model_name'):
                    model_name = self._model.model_name
            
            logger.info(f"========== AI 分析 {name}({code}) ==========")
            logger.info(f"[LLM配置] 模型: {model_name}")
            logger.info(f"[LLM配置] Prompt 长度: {len(prompt)} 字符")
            logger.info(f"[LLM配置] 是否包含新闻: {'是' if news_context else '否'}")
            
            # 记录完整 prompt 到日志（INFO级别记录摘要，DEBUG记录完整）
            prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
            logger.info(f"[LLM Prompt 预览]\n{prompt_preview}")
            logger.debug(f"=== 完整 Prompt ({len(prompt)}字符) ===\n{prompt}\n=== End Prompt ===")
            
            # 设置生成配置
            generation_config = {
                "temperature": 0.7,
                "max_output_tokens": 8192,
            }
            
            logger.info(f"[LLM调用] 开始调用 Gemini API (temperature={generation_config['temperature']}, max_tokens={generation_config['max_output_tokens']})...")
            
            # 使用带重试的 API 调用（传递 system_prompt）
            start_time = time.time()
            response_text = self._call_api_with_retry(prompt, generation_config, system_prompt)
            elapsed = time.time() - start_time
            
            # 记录响应信息
            logger.info(f"[LLM返回] Gemini API 响应成功, 耗时 {elapsed:.2f}s, 响应长度 {len(response_text)} 字符")
            
            # 记录响应预览（INFO级别）和完整响应（DEBUG级别）
            response_preview = response_text[:300] + "..." if len(response_text) > 300 else response_text
            logger.info(f"[LLM返回 预览]\n{response_preview}")
            logger.debug(f"=== Gemini 完整响应 ({len(response_text)}字符) ===\n{response_text}\n=== End Response ===")
            
            # 解析响应
            result = self._parse_response(response_text, code, name)
            result.raw_response = response_text
            result.search_performed = bool(news_context)
            
            logger.info(f"[LLM解析] {name}({code}) 分析完成: {result.trend_prediction}, 评分 {result.sentiment_score}")
            
            return result
            
        except Exception as e:
            logger.error(f"AI 分析 {name}({code}) 失败: {e}")
            return AnalysisResult(
                code=code,
                name=name,
                sentiment_score=50,
                trend_prediction='震荡',
                operation_advice='持有',
                confidence_level='低',
                analysis_summary=f'分析过程出错: {str(e)[:100]}',
                risk_warning='分析失败，请稍后重试或手动分析',
                success=False,
                error_message=str(e),
            )
    
    def _format_prompt(
        self, 
        context: Dict[str, Any], 
        name: str,
        news_context: Optional[str] = None
    ) -> str:
        """
        格式化分析提示词（决策仪表盘 v2.0）
        
        包含：技术指标、实时行情（量比/换手率）、筹码分布、趋势分析、新闻
        
        Args:
            context: 技术面数据上下文（包含增强数据）
            name: 股票名称（默认值，可能被上下文覆盖）
            news_context: 预先搜索的新闻内容
        """
        code = context.get('code', 'Unknown')
        
        # 优先使用上下文中的股票名称（从 realtime_quote 获取）
        stock_name = context.get('stock_name', name)
        if not stock_name or stock_name == f'股票{code}':
            stock_name = STOCK_NAME_MAP.get(code, f'股票{code}')
            
        today = context.get('today', {})
        
        # ========== 构建决策仪表盘格式的输入 ==========
        prompt = f"""# 决策仪表盘分析请求

## 📊 股票基础信息
| 项目 | 数据 |
|------|------|
| 股票代码 | **{code}** |
| 股票名称 | **{stock_name}** |
| 分析日期 | {context.get('date', '未知')} |

---

## 📈 技术面数据

### 今日行情
| 指标 | 数值 |
|------|------|
| 收盘价 | {today.get('close', 'N/A')} 元 |
| 开盘价 | {today.get('open', 'N/A')} 元 |
| 最高价 | {today.get('high', 'N/A')} 元 |
| 最低价 | {today.get('low', 'N/A')} 元 |
| 涨跌幅 | {today.get('pct_chg', 'N/A')}% |
| 成交量 | {self._format_volume(today.get('volume'))} |
| 成交额 | {self._format_amount(today.get('amount'))} |

### 均线系统（关键判断指标）
| 均线 | 数值 | 说明 |
|------|------|------|
| MA5 | {today.get('ma5', 'N/A')} | 短期趋势线 |
| MA10 | {today.get('ma10', 'N/A')} | 中短期趋势线 |
| MA20 | {today.get('ma20', 'N/A')} | 中期趋势线 |
| 均线形态 | {context.get('ma_status', '未知')} | 多头/空头/缠绕 |
"""
        
        # 添加实时行情数据（量比、换手率等）
        if 'realtime' in context:
            rt = context['realtime']
            prompt += f"""
### 实时行情增强数据
| 指标 | 数值 | 解读 |
|------|------|------|
| 当前价格 | {rt.get('price', 'N/A')} 元 | |
| **量比** | **{rt.get('volume_ratio', 'N/A')}** | {rt.get('volume_ratio_desc', '')} |
| **换手率** | **{rt.get('turnover_rate', 'N/A')}%** | |
| 市盈率(动态) | {rt.get('pe_ratio', 'N/A')} | |
| 市净率 | {rt.get('pb_ratio', 'N/A')} | |
| 总市值 | {self._format_amount(rt.get('total_mv'))} | |
| 流通市值 | {self._format_amount(rt.get('circ_mv'))} | |
| 60日涨跌幅 | {rt.get('change_60d', 'N/A')}% | 中期表现 |
"""
        
        # 添加筹码分布数据
        if 'chip' in context:
            chip = context['chip']
            profit_ratio = chip.get('profit_ratio', 0)
            prompt += f"""
### 筹码分布数据（效率指标）
| 指标 | 数值 | 健康标准 |
|------|------|----------|
| **获利比例** | **{profit_ratio:.1%}** | 70-90%时警惕 |
| 平均成本 | {chip.get('avg_cost', 'N/A')} 元 | 现价应高于5-15% |
| 90%筹码集中度 | {chip.get('concentration_90', 0):.2%} | <15%为集中 |
| 70%筹码集中度 | {chip.get('concentration_70', 0):.2%} | |
| 筹码状态 | {chip.get('chip_status', '未知')} | |
"""
        
        # 添加趋势分析结果（基于交易理念的预判）
        if 'trend_analysis' in context:
            trend = context['trend_analysis']
            bias_warning = "🚨 超过5%，严禁追高！" if trend.get('bias_ma5', 0) > 5 else "✅ 安全范围"
            prompt += f"""
### 趋势分析预判（基于交易理念）
| 指标 | 数值 | 判定 |
|------|------|------|
| 趋势状态 | {trend.get('trend_status', '未知')} | |
| 均线排列 | {trend.get('ma_alignment', '未知')} | MA5>MA10>MA20为多头 |
| 趋势强度 | {trend.get('trend_strength', 0)}/100 | |
| **乖离率(MA5)** | **{trend.get('bias_ma5', 0):+.2f}%** | {bias_warning} |
| 乖离率(MA10) | {trend.get('bias_ma10', 0):+.2f}% | |
| 量能状态 | {trend.get('volume_status', '未知')} | {trend.get('volume_trend', '')} |
| 系统信号 | {trend.get('buy_signal', '未知')} | |
| 系统评分 | {trend.get('signal_score', 0)}/100 | |

#### 系统分析理由
**买入理由**：
{chr(10).join('- ' + r for r in trend.get('signal_reasons', ['无'])) if trend.get('signal_reasons') else '- 无'}

**风险因素**：
{chr(10).join('- ' + r for r in trend.get('risk_factors', ['无'])) if trend.get('risk_factors') else '- 无'}
"""
        
        # 添加昨日对比数据
        if 'yesterday' in context:
            volume_change = context.get('volume_change_ratio', 'N/A')
            prompt += f"""
### 量价变化
- 成交量较昨日变化：{volume_change}倍
- 价格较昨日变化：{context.get('price_change_ratio', 'N/A')}%
"""
        
        # 添加新闻搜索结果（重点区域）
        prompt += """
---

## 📰 舆情情报
"""
        if news_context:
            prompt += f"""
以下是 **{stock_name}({code})** 近7日的新闻搜索结果，请重点提取：
1. 🚨 **风险警报**：减持、处罚、利空
2. 🎯 **利好催化**：业绩、合同、政策
3. 📊 **业绩预期**：年报预告、业绩快报

```
{news_context}
```
"""
        else:
            prompt += """
未搜索到该股票近期的相关新闻。请主要依据技术面数据进行分析。
"""
        
        # 明确的输出要求
        prompt += f"""
---

## ✅ 分析任务

请为 **{stock_name}({code})** 生成【决策仪表盘】，严格按照 JSON 格式输出。

### 重点关注（必须明确回答）：
1. ❓ 是否满足 MA5>MA10>MA20 多头排列？
2. ❓ 当前乖离率是否在安全范围内（<5%）？—— 超过5%必须标注"严禁追高"
3. ❓ 量能是否配合（缩量回调/放量突破）？
4. ❓ 筹码结构是否健康？
5. ❓ 消息面有无重大利空？（减持、处罚、业绩变脸等）

### 决策仪表盘要求：
- **核心结论**：一句话说清该买/该卖/该等
- **持仓分类建议**：空仓者怎么做 vs 持仓者怎么做
- **具体狙击点位**：买入价、止损价、目标价（精确到分）
- **检查清单**：每项用 ✅/⚠️/❌ 标记

请输出完整的 JSON 格式决策仪表盘。"""
        
        return prompt
    
    def _format_volume(self, volume: Optional[float]) -> str:
        """格式化成交量显示"""
        if volume is None:
            return 'N/A'
        if volume >= 1e8:
            return f"{volume / 1e8:.2f} 亿股"
        elif volume >= 1e4:
            return f"{volume / 1e4:.2f} 万股"
        else:
            return f"{volume:.0f} 股"
    
    def _format_amount(self, amount: Optional[float]) -> str:
        """格式化成交额显示"""
        if amount is None:
            return 'N/A'
        if amount >= 1e8:
            return f"{amount / 1e8:.2f} 亿元"
        elif amount >= 1e4:
            return f"{amount / 1e4:.2f} 万元"
        else:
            return f"{amount:.0f} 元"
    
    def _parse_response(
        self, 
        response_text: str, 
        code: str, 
        name: str
    ) -> AnalysisResult:
        """
        解析 Gemini 响应（决策仪表盘版）
        
        尝试从响应中提取 JSON 格式的分析结果，包含 dashboard 字段
        如果解析失败，尝试智能提取或返回默认结果
        """
        try:
            # 清理响应文本：移除 markdown 代码块标记
            cleaned_text = response_text
            if '```json' in cleaned_text:
                cleaned_text = cleaned_text.replace('```json', '').replace('```', '')
            elif '```' in cleaned_text:
                cleaned_text = cleaned_text.replace('```', '')
            
            # 尝试找到 JSON 内容
            json_start = cleaned_text.find('{')
            json_end = cleaned_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = cleaned_text[json_start:json_end]
                
                # 尝试修复常见的 JSON 问题
                json_str = self._fix_json_string(json_str)
                
                data = json.loads(json_str)
                
                # 提取 dashboard 数据
                dashboard = data.get('dashboard', None)
                
                # 解析所有字段，使用默认值防止缺失
                return AnalysisResult(
                    code=code,
                    name=name,
                    # 核心指标
                    sentiment_score=int(data.get('sentiment_score', 50)),
                    trend_prediction=data.get('trend_prediction', '震荡'),
                    operation_advice=data.get('operation_advice', '持有'),
                    confidence_level=data.get('confidence_level', '中'),
                    # 决策仪表盘
                    dashboard=dashboard,
                    # 走势分析
                    trend_analysis=data.get('trend_analysis', ''),
                    short_term_outlook=data.get('short_term_outlook', ''),
                    medium_term_outlook=data.get('medium_term_outlook', ''),
                    # 技术面
                    technical_analysis=data.get('technical_analysis', ''),
                    ma_analysis=data.get('ma_analysis', ''),
                    volume_analysis=data.get('volume_analysis', ''),
                    pattern_analysis=data.get('pattern_analysis', ''),
                    # 基本面
                    fundamental_analysis=data.get('fundamental_analysis', ''),
                    sector_position=data.get('sector_position', ''),
                    company_highlights=data.get('company_highlights', ''),
                    # 情绪面/消息面
                    news_summary=data.get('news_summary', ''),
                    market_sentiment=data.get('market_sentiment', ''),
                    hot_topics=data.get('hot_topics', ''),
                    # 综合
                    analysis_summary=data.get('analysis_summary', '分析完成'),
                    key_points=data.get('key_points', ''),
                    risk_warning=data.get('risk_warning', ''),
                    buy_reason=data.get('buy_reason', ''),
                    # 元数据
                    search_performed=data.get('search_performed', False),
                    data_sources=data.get('data_sources', '技术面数据'),
                    success=True,
                )
            else:
                # 没有找到 JSON，尝试从纯文本中提取信息
                logger.warning(f"无法从响应中提取 JSON，使用原始文本分析")
                return self._parse_text_response(response_text, code, name)
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}，尝试从文本提取")
            return self._parse_text_response(response_text, code, name)
    
    def _fix_json_string(self, json_str: str) -> str:
        """修复常见的 JSON 格式问题"""
        import re
        
        # 移除注释
        json_str = re.sub(r'//.*?\n', '\n', json_str)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        # 修复尾随逗号
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # 确保布尔值是小写
        json_str = json_str.replace('True', 'true').replace('False', 'false')
        
        return json_str
    
    def _parse_text_response(
        self, 
        response_text: str, 
        code: str, 
        name: str
    ) -> AnalysisResult:
        """从纯文本响应中尽可能提取分析信息"""
        # 尝试识别关键词来判断情绪
        sentiment_score = 50
        trend = '震荡'
        advice = '持有'
        
        text_lower = response_text.lower()
        
        # 简单的情绪识别
        positive_keywords = ['看多', '买入', '上涨', '突破', '强势', '利好', '加仓', 'bullish', 'buy']
        negative_keywords = ['看空', '卖出', '下跌', '跌破', '弱势', '利空', '减仓', 'bearish', 'sell']
        
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        if positive_count > negative_count + 1:
            sentiment_score = 65
            trend = '看多'
            advice = '买入'
        elif negative_count > positive_count + 1:
            sentiment_score = 35
            trend = '看空'
            advice = '卖出'
        
        # 截取前500字符作为摘要
        summary = response_text[:500] if response_text else '无分析结果'
        
        return AnalysisResult(
            code=code,
            name=name,
            sentiment_score=sentiment_score,
            trend_prediction=trend,
            operation_advice=advice,
            confidence_level='低',
            analysis_summary=summary,
            key_points='JSON解析失败，仅供参考',
            risk_warning='分析结果可能不准确，建议结合其他信息判断',
            raw_response=response_text,
            success=True,
        )
    
    def batch_analyze(
        self, 
        contexts: List[Dict[str, Any]],
        delay_between: float = 2.0
    ) -> List[AnalysisResult]:
        """
        批量分析多只股票
        
        注意：为避免 API 速率限制，每次分析之间会有延迟
        
        Args:
            contexts: 上下文数据列表
            delay_between: 每次分析之间的延迟（秒）
            
        Returns:
            AnalysisResult 列表
        """
        results = []
        
        for i, context in enumerate(contexts):
            if i > 0:
                logger.debug(f"等待 {delay_between} 秒后继续...")
                time.sleep(delay_between)
            
            result = self.analyze(context)
            results.append(result)
        
        return results


# 便捷函数
def get_analyzer() -> GeminiAnalyzer:
    """获取 Gemini 分析器实例"""
    return GeminiAnalyzer()


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    # 模拟上下文数据
    test_context = {
        'code': '600519',
        'date': '2026-01-09',
        'today': {
            'open': 1800.0,
            'high': 1850.0,
            'low': 1780.0,
            'close': 1820.0,
            'volume': 10000000,
            'amount': 18200000000,
            'pct_chg': 1.5,
            'ma5': 1810.0,
            'ma10': 1800.0,
            'ma20': 1790.0,
            'volume_ratio': 1.2,
        },
        'ma_status': '多头排列 📈',
        'volume_change_ratio': 1.3,
        'price_change_ratio': 1.5,
    }
    
    analyzer = GeminiAnalyzer()
    
    if analyzer.is_available():
        print("=== AI 分析测试 ===")
        result = analyzer.analyze(test_context)
        print(f"分析结果: {result.to_dict()}")
    else:
        print("Gemini API 未配置，跳过测试")
