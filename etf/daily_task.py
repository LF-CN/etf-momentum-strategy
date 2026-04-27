#!/usr/bin/env python3
"""
ETF 策略每日任务（兼容入口）

说明：
- 旧版 daily_task.py 曾使用简化版 strategy.py，参数与回测主线不一致。
- 当前统一转发到 daily_task_full.run_daily_task()，确保与正式回测核心同源。
"""
import json

from daily_task_full import run_daily_task as run_daily_task_full


def run_daily_task():
    """执行每日任务（统一走正式链路）"""
    return run_daily_task_full()


if __name__ == '__main__':
    result = run_daily_task()
    
    # 输出 JSON 供外部调用
    print("\n__JSON_OUTPUT__")
    print(json.dumps(result, ensure_ascii=False))
