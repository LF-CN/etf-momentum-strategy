#!/bin/bash
# ETF 策略运行脚本
# 使用 AkShare 项目的虚拟环境

SCRIPT_DIR="/opt/data/scripts/etf"
AKSHARE_DIR="/opt/data/scripts/AkShare"

# 检查是否有 Windows 风格的 venv
if [ -f "$AKSHARE_DIR/.venv/Scripts/python.exe" ]; then
    echo "检测到 Windows 虚拟环境，使用系统 Python"
    PYTHON="python3"
elif [ -f "$AKSHARE_DIR/.venv/bin/python" ]; then
    PYTHON="$AKSHARE_DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

cd "$SCRIPT_DIR"

case "$1" in
    summary)
        $PYTHON -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from etf_service import ETFService
import json
service = ETFService()
result = service.get_portfolio_summary()
print(json.dumps(result, ensure_ascii=False, indent=2))
"
        ;;
    signals)
        $PYTHON -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from etf_service import ETFService
import json
service = ETFService()
result = service.calculate_signals()
print(json.dumps(result, ensure_ascii=False, indent=2))
"
        ;;
    update)
        $PYTHON -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
sys.path.insert(0, '$AKSHARE_DIR')
from data_manager import DataManager
dm = DataManager()
dm.update_all()
"
        ;;
    *)
        echo "用法: $0 {summary|signals|update}"
        echo "  summary - 查看持仓概览"
        echo "  signals - 计算策略信号"
        echo "  update  - 更新数据"
        exit 1
        ;;
esac
