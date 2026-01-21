# -*- coding: utf-8 -*-
"""
===================================
Notion 数据库集成服务
===================================

功能：
1. 保存股票分析报告到 Notion 数据库
2. 保存调仓建议到 Notion 数据库  
3. 保存大盘复盘到 Notion 数据库
4. 保存推荐股票列表到 Notion 数据库

使用方法：
1. 在 Notion 中创建 Integration（https://www.notion.so/my-integrations）
2. 获取 Internal Integration Token
3. 创建数据库并分享给 Integration
4. 配置环境变量：
   - NOTION_TOKEN: Integration Token
   - NOTION_STOCK_ANALYSIS_DB: 股票分析数据库ID
   - NOTION_PORTFOLIO_DB: 调仓建议数据库ID
   - NOTION_MARKET_REVIEW_DB: 大盘复盘数据库ID
   - NOTION_STOCK_SELECTION_DB: 推荐股票数据库ID
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from notion_client import Client
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False
    logger.warning("notion-client 未安装，Notion 功能不可用。安装: pip install notion-client")


@dataclass
class NotionConfig:
    """Notion 配置"""
    token: str
    stock_analysis_db: Optional[str] = None  # 股票分析数据库
    portfolio_db: Optional[str] = None       # 调仓建议数据库
    market_review_db: Optional[str] = None   # 大盘复盘数据库
    stock_selection_db: Optional[str] = None # 推荐股票数据库


class NotionService:
    """Notion 数据库服务"""
    
    def __init__(self, config: Optional[NotionConfig] = None):
        """
        初始化 Notion 服务
        
        Args:
            config: Notion 配置（可选，默认从环境变量读取）
        """
        if not NOTION_AVAILABLE:
            self.client = None
            self.config = None
            logger.warning("[Notion] notion-client 未安装，服务不可用")
            return
        
        if config is None:
            config = self._load_from_env()
        
        self.config = config
        
        if not self.config or not self.config.token:
            self.client = None
            logger.warning("[Notion] 未配置 NOTION_TOKEN，服务不可用")
            return
        
        try:
            self.client = Client(auth=self.config.token)
            logger.info("[Notion] 服务初始化成功")
        except Exception as e:
            self.client = None
            logger.error(f"[Notion] 初始化失败: {e}")
    
    def _load_from_env(self) -> NotionConfig:
        """从环境变量加载配置"""
        return NotionConfig(
            token=os.getenv('NOTION_TOKEN', ''),
            stock_analysis_db=os.getenv('NOTION_STOCK_ANALYSIS_DB'),
            portfolio_db=os.getenv('NOTION_PORTFOLIO_DB'),
            market_review_db=os.getenv('NOTION_MARKET_REVIEW_DB'),
            stock_selection_db=os.getenv('NOTION_STOCK_SELECTION_DB'),
        )
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.client is not None
    
    def save_stock_analysis(self, results: List[Any]) -> bool:
        """
        保存股票分析报告到 Notion
        
        Args:
            results: AnalysisResult 列表
            
        Returns:
            是否成功
        """
        if not self.is_available() or not self.config.stock_analysis_db:
            logger.warning("[Notion] 股票分析数据库未配置")
            return False
        
        try:
            for result in results:
                # 构建页面属性
                properties = {
                    "Name": {"title": [{"text": {"content": f"{result.name}({result.code})"}}]},
                    "Code": {"rich_text": [{"text": {"content": result.code}}]},
                    "Date": {"date": {"start": datetime.now().isoformat()}},
                    "Score": {"number": result.sentiment_score},
                    "Action": {"select": {"name": result.operation_advice}},
                    "Trend": {"rich_text": [{"text": {"content": result.trend_prediction}}]},
                }
                
                # 构建页面内容
                children = [
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "📊 分析摘要"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": result.analysis_summary}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "🎯 关键要点"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": result.key_points or "无"}}]
                        }
                    },
                ]
                
                # 添加完整报告
                if result.full_report:
                    children.append({
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "📄 完整报告"}}]
                        }
                    })
                    # 将报告按段落分割
                    for para in result.full_report.split('\n\n'):
                        if para.strip():
                            children.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"type": "text", "text": {"content": para.strip()}}]
                                }
                            })
                
                # 创建页面
                self.client.pages.create(
                    parent={"database_id": self.config.stock_analysis_db},
                    properties=properties,
                    children=children
                )
                
                logger.info(f"[Notion] 保存 {result.name}({result.code}) 分析报告成功")
            
            return True
            
        except Exception as e:
            logger.error(f"[Notion] 保存股票分析失败: {e}")
            return False
    
    def save_portfolio_advice(self, advice: Any) -> bool:
        """
        保存调仓建议到 Notion
        
        Args:
            advice: PortfolioAdvice 对象
            
        Returns:
            是否成功
        """
        if not self.is_available() or not self.config.portfolio_db:
            logger.warning("[Notion] 调仓建议数据库未配置")
            return False
        
        try:
            # 创建主页面
            properties = {
                "Title": {"title": [{"text": {"content": f"持仓调仓建议 - {advice.date}"}}]},
                "Date": {"date": {"start": advice.date}},
                "Count": {"number": len(advice.advices)},
            }
            
            # 构建内容
            children = [
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": "📊 持仓调仓建议"}}]
                    }
                }
            ]
            
            # 添加每只股票的建议
            for adv in advice.advices:
                # 获取中文操作
                action_text = adv.action.value if hasattr(adv.action, 'value') else str(adv.action).replace('AdjustAction.', '')
                
                children.extend([
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": f"📈 {adv.name} ({adv.code})"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": f"💰 最新价格：{adv.latest_price:.2f} 元 | 涨跌幅：{adv.pct_chg:+.2f}%"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": f"📊 当前仓位：{adv.current_ratio:.0f}% → 建议仓位：{adv.suggested_ratio:.0f}%"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": f"🎯 操作建议：{action_text}"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": f"📈 趋势状态：{adv.trend_status} | 信号：{adv.signal}"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": f"💡 理由分析：{adv.reason}"}}]
                        }
                    },
                ])
                
                # 如果有AI分析，添加AI部分
                if adv.ai_advice:
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": f"🤖 AI建议：{adv.ai_advice} (评分: {adv.ai_sentiment_score}/100)\n💭 AI分析：{adv.ai_reason}"}}]
                        }
                    })
                
                if adv.risk_alert:
                    children.append({
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [{"type": "text", "text": {"content": f"⚠️ {adv.risk_alert}"}}],
                            "icon": {"emoji": "⚠️"}
                        }
                    })
            
            # 创建页面
            self.client.pages.create(
                parent={"database_id": self.config.portfolio_db},
                properties=properties,
                children=children
            )
            
            logger.info(f"[Notion] 保存调仓建议成功")
            return True
            
        except Exception as e:
            logger.error(f"[Notion] 保存调仓建议失败: {e}")
            return False
    
    def save_market_review(self, review: str, date: str = None) -> bool:
        """
        保存大盘复盘到 Notion
        
        Args:
            review: 复盘报告文本
            date: 日期（可选，默认今天）
            
        Returns:
            是否成功
        """
        if not self.is_available() or not self.config.market_review_db:
            logger.warning("[Notion] 大盘复盘数据库未配置")
            return False
        
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # 构建页面属性
            properties = {
                "Title": {"title": [{"text": {"content": f"大盘复盘 - {date}"}}]},
                "Date": {"date": {"start": date}},
            }
            
            # 构建内容
            children = [
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": "🎯 大盘复盘"}}]
                    }
                }
            ]
            
            # 将报告按段落分割
            for para in review.split('\n\n'):
                if para.strip():
                    # 如果是标题行（包含#或emoji）
                    if para.startswith('#') or any(emoji in para[:10] for emoji in ['📊', '🎯', '💡', '📈', '📉', '⚡', '🔥']):
                        children.append({
                            "object": "block",
                            "type": "heading_2",
                            "heading_2": {
                                "rich_text": [{"type": "text", "text": {"content": para.replace('#', '').strip()}}]
                            }
                        })
                    else:
                        children.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": para.strip()}}]
                            }
                        })
            
            # 创建页面
            self.client.pages.create(
                parent={"database_id": self.config.market_review_db},
                properties=properties,
                children=children
            )
            
            logger.info(f"[Notion] 保存大盘复盘成功")
            return True
            
        except Exception as e:
            logger.error(f"[Notion] 保存大盘复盘失败: {e}")
            return False
    
    def save_stock_selection(self, selection: Any) -> bool:
        """
        保存推荐股票列表到 Notion
        
        Args:
            selection: SelectionResult 对象
            
        Returns:
            是否成功
        """
        if not self.is_available() or not self.config.stock_selection_db:
            logger.warning("[Notion] 推荐股票数据库未配置")
            return False
        
        try:
            for stock in selection.selected_stocks:
                # 构建页面属性
                properties = {
                    "Name": {"title": [{"text": {"content": f"{stock.name}({stock.code})"}}]},
                    "Code": {"rich_text": [{"text": {"content": stock.code}}]},
                    "Date": {"date": {"start": selection.date}},
                    "Pool": {"select": {"name": selection.pool_name}},
                    "TotalScore": {"number": stock.total_score},
                    "Price": {"number": stock.latest_price},
                    "Change": {"number": stock.pct_chg},
                }
                
                # 如果有AI分析
                if stock.ai_analysis:
                    properties["AIScore"] = {"number": stock.ai_sentiment_score}
                    properties["AIAction"] = {"select": {"name": stock.ai_advice}}
                
                # 构建内容
                children = [
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "💡 推荐理由"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": stock.ai_core_reason if stock.ai_core_reason else stock.reason}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "📈 技术指标"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": f"MA5: {stock.ma5:.2f}"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": f"MA10: {stock.ma10:.2f}"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": f"MA20: {stock.ma20:.2f}"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": f"量比: {stock.volume_ratio:.2f}"}}]
                        }
                    },
                ]
                
                # 创建页面
                self.client.pages.create(
                    parent={"database_id": self.config.stock_selection_db},
                    properties=properties,
                    children=children
                )
                
                logger.info(f"[Notion] 保存推荐股票 {stock.name}({stock.code}) 成功")
            
            return True
            
        except Exception as e:
            logger.error(f"[Notion] 保存推荐股票失败: {e}")
            return False


def get_notion_service() -> NotionService:
    """获取 Notion 服务实例（单例）"""
    if not hasattr(get_notion_service, '_instance'):
        get_notion_service._instance = NotionService()
    return get_notion_service._instance


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    service = get_notion_service()
    if service.is_available():
        print("✅ Notion 服务可用")
    else:
        print("❌ Notion 服务不可用")
