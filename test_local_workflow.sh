#!/bin/bash
# 本地测试 GitHub Actions Workflow 的脚本

set -e  # 遇到错误立即退出

echo "=================================================="
echo "🧪 本地测试 GitHub Actions Workflow"
echo "=================================================="
echo ""

# 检查必需的环境变量
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ 错误：GEMINI_API_KEY 未设置"
    echo "💡 请先设置：export GEMINI_API_KEY='your_api_key'"
    exit 1
fi

echo "✅ GEMINI_API_KEY 已配置"
echo ""

# 测试模式选择
echo "请选择测试模式："
echo "1) 智能选股测试（TEST_MODE=true，30只股票）"
echo "2) 个股分析测试（STOCK_LIST=600519,000858）"
echo "3) 全功能测试（智能选股+个股分析+调仓+大盘）"
echo "4) GitHub Actions 完整模拟"
echo ""
read -p "请选择 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 开始测试：智能选股（测试模式）"
        echo "=================================================="
        export TEST_MODE=true
        export TEST_SAMPLE_SIZE=30
        export STOCK_POOLS="沪深300"
        export RECOMMEND_ENABLED=true
        
        python3 main.py --no-market-review --no-notify
        ;;
    
    2)
        echo ""
        echo "🚀 开始测试：个股分析"
        echo "=================================================="
        export STOCK_LIST="600519,000858,002594"
        export PORTFOLIO_ADVICE_ENABLED=false
        
        python3 main.py --no-market-review --no-notify
        ;;
    
    3)
        echo ""
        echo "🚀 开始测试：全功能（智能选股+个股+调仓+大盘）"
        echo "=================================================="
        export TEST_MODE=true
        export TEST_SAMPLE_SIZE=20
        export STOCK_POOLS="沪深300"
        export STOCK_LIST="600519,000858"
        export POSITION_RATIOS="600519:100,000858:80"
        export RECOMMEND_ENABLED=true
        export PORTFOLIO_ADVICE_ENABLED=true
        export MARKET_REVIEW_ENABLED=true
        
        python3 main.py --no-notify
        ;;
    
    4)
        echo ""
        echo "🚀 开始测试：GitHub Actions 完整模拟"
        echo "=================================================="
        echo "⚠️  这将完全模拟 GitHub Actions 环境"
        echo ""
        
        # 模拟 GitHub Actions 环境变量
        export GITHUB_ACTIONS=true
        export TEST_MODE=true
        export TEST_SAMPLE_SIZE=25
        export STOCK_POOLS="${STOCK_POOLS:-沪深300}"
        export STOCK_LIST="${STOCK_LIST:-}"
        export RECOMMEND_ENABLED=true
        export LOG_LEVEL=INFO
        export DATA_DAYS=60
        export MAX_CONCURRENT=3
        
        # 创建目录
        mkdir -p data logs reports
        
        echo "环境配置："
        echo "  - STOCK_POOLS: $STOCK_POOLS"
        echo "  - STOCK_LIST: ${STOCK_LIST:-<未配置>}"
        echo "  - TEST_MODE: $TEST_MODE"
        echo "  - TEST_SAMPLE_SIZE: $TEST_SAMPLE_SIZE"
        echo ""
        
        python3 main.py
        
        echo ""
        echo "📊 生成的报告："
        ls -lh reports/ 2>/dev/null || echo "  (无报告文件)"
        echo ""
        echo "📋 日志文件："
        ls -lh logs/*.log 2>/dev/null || echo "  (无日志文件)"
        ;;
    
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "=================================================="
echo "✅ 测试完成！"
echo "=================================================="
echo ""
echo "💡 提示："
echo "  - 日志查看：tail -f logs/stock_analysis_*.log"
echo "  - 报告目录：ls -lh reports/"
echo "  - 测试其他模式：重新运行此脚本"
echo ""
