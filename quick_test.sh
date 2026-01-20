#!/bin/bash
# ==============================================
# AI 智能选股和调仓 - 一键测试脚本
# ==============================================
#
# 使用方法：
#   1. 配置 .env 文件（参考 .env.example.test）
#   2. 运行：./quick_test.sh
#
# ==============================================

set -e  # 遇到错误立即退出

echo "=================================================="
echo "  AI 智能选股和调仓 - 快速测试"
echo "=================================================="
echo ""

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "❌ 错误：未找到 .env 文件"
    echo ""
    echo "请执行以下步骤："
    echo "  1. 复制示例配置："
    echo "     cp .env.example.test .env"
    echo ""
    echo "  2. 编辑 .env 文件，填入你的 GEMINI_API_KEY"
    echo ""
    echo "  3. 重新运行：./quick_test.sh"
    echo ""
    exit 1
fi

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 python3"
    echo "请先安装 Python 3.8+"
    exit 1
fi

echo "✅ 环境检查通过"
echo ""

# 检查依赖
echo "📦 检查依赖包..."
if ! python3 -c "import akshare" 2>/dev/null; then
    echo "⚠️  未安装依赖，正在安装..."
    pip3 install -r requirements.txt
fi
echo "✅ 依赖包已就绪"
echo ""

# 选择测试模式
echo "请选择测试模式："
echo "  1. 测试 AI 智能选股（从沪深300选3只股票）"
echo "  2. 测试 AI 调仓建议（分析2只测试持仓）"
echo "  3. 完整测试（选股 + 调仓）"
echo ""
read -p "请输入选项 (1/2/3，默认1): " choice
choice=${choice:-1}

echo ""
echo "=================================================="

case $choice in
    1)
        echo "🚀 开始测试：AI 智能选股"
        echo "=================================================="
        python3 test_ai_selection.py selection
        ;;
    2)
        echo "🚀 开始测试：AI 调仓建议"
        echo "=================================================="
        python3 test_ai_selection.py portfolio
        ;;
    3)
        echo "🚀 开始完整测试：AI 智能选股 + 调仓建议"
        echo "=================================================="
        echo ""
        echo "【1/2】测试 AI 智能选股..."
        echo "--------------------------------------------------"
        python3 test_ai_selection.py selection
        echo ""
        echo ""
        echo "【2/2】测试 AI 调仓建议..."
        echo "--------------------------------------------------"
        python3 test_ai_selection.py portfolio
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "=================================================="
echo "✅ 测试完成！"
echo "=================================================="
echo ""
echo "💡 提示："
echo "  - 查看日志：logs/ 目录"
echo "  - 修改测试参数：编辑 test_ai_selection.py"
echo "  - 完整运行：python3 main.py"
echo ""
