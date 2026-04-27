#!/usr/bin/env python3
"""
批量重跑所有阶段的回测
修复因子权重/风格因子配置bug后的完整验证
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

PACKAGE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE_ROOT / "core"))

PRESETS = {
    "stage1": [
        "presets/stage1_f1_momentum20_only.json",
        "presets/stage1_f2_momentum20_60.json", 
        "presets/stage1_f3_add_strength.json",
        "presets/stage1_f4_add_volatility_reward.json",
        "presets/stage1_f5_add_r_squared.json",
        "presets/stage1_f6_full_factor.json",
    ],
    "stage2": [
        "presets/stage2_f4_style_on.json",
        "presets/stage2_f4_style_off.json",
        "presets/stage2_f5_style_on.json",
        "presets/stage2_f5_style_off.json",
        "presets/stage2_f6_style_on.json",
        "presets/stage2_f6_style_off.json",
    ],
    "stage3": [
        "presets/stage3_f6_top2_style_off.json",
        "presets/stage3_f6_top3_style_off.json",
        "presets/stage3_f6_top4_style_off.json",
    ],
    "stage4": [
        "presets/stage4_cooldown5_style_off.json",
        "presets/stage4_cooldown10_style_off.json",
        "presets/stage4_cooldown14_style_off.json",
        "presets/stage4_cooldown15_style_off.json",
        "presets/stage4_cooldown20_style_off.json",
    ],
}

def run_preset(preset_path: str):
    """运行单个preset"""
    cmd = [
        sys.executable, 
        str(PACKAGE_ROOT / "core" / "run_preset.py"),
        str(PACKAGE_ROOT / preset_path)
    ]
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Running: {preset_path}")
    print('='*60)
    
    result = subprocess.run(cmd, cwd=str(PACKAGE_ROOT), capture_output=False)
    return result.returncode == 0

def main():
    print("="*60)
    print("ETF策略回测 - 全阶段重跑")
    print("原因: 修复factor_weights/style_factors配置bug")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = {}
    
    for stage, presets in PRESETS.items():
        print(f"\n\n{'#'*60}")
        print(f"# {stage.upper()}")
        print('#'*60)
        
        stage_results = []
        for preset in presets:
            success = run_preset(preset)
            stage_results.append((preset, success))
        
        results[stage] = stage_results
        
        # 阶段统计
        success_count = sum(1 for _, s in stage_results if s)
        print(f"\n{stage} 完成: {success_count}/{len(stage_results)} 成功")
    
    # 总结
    print("\n\n" + "="*60)
    print("执行完成汇总")
    print("="*60)
    
    total_success = 0
    total_count = 0
    for stage, stage_results in results.items():
        success = sum(1 for _, s in stage_results if s)
        total = len(stage_results)
        total_success += success
        total_count += total
        failed = [p for p, s in stage_results if not s]
        status = "✅" if success == total else f"⚠️ {len(failed)}失败"
        print(f"  {stage}: {success}/{total} {status}")
        if failed:
            for f in failed:
                print(f"    - {f}")
    
    print(f"\n总计: {total_success}/{total_count}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
