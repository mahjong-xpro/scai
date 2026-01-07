#!/usr/bin/env python3
"""
阶段1训练检查脚本

用法:
    python scripts/check_stage1.py [--log-dir <日志目录>]
    
示例:
    python scripts/check_stage1.py
    python scripts/check_stage1.py --log-dir ./logs
"""

import argparse
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def parse_log_file(log_file):
    """解析日志文件"""
    results = {
        'stage': None,
        'reward_config': {},
        'trajectories': [],
        'losses': [],
        'iterations': [],
        'validation_stats': [],
        'errors': [],
    }
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        print(f"❌ 读取日志文件失败: {e}")
        return results
    
    # 检查阶段信息
    if "定缺阶段" in content or "DECLARE_SUIT" in content:
        results['stage'] = "阶段1（定缺与生存）"
    
    # 提取奖励配置
    reward_config_match = re.search(r"Reward config for stage.*?:\s*({[^}]+})", content)
    if reward_config_match:
        try:
            config_str = reward_config_match.group(1)
            # 简单的字典解析
            for key, value in re.findall(r"'(\w+)':\s*([-\d.]+)", config_str):
                results['reward_config'][key] = float(value)
        except:
            pass
    
    # 提取轨迹数量
    for match in re.finditer(r'num_trajectories=(\d+)', content):
        results['trajectories'].append(int(match.group(1)))
    
    # 提取训练损失
    for match in re.finditer(
        r'Training step \d+ \(iteration=(\d+), policy_loss=([-\d.]+), value_loss=([-\d.]+), entropy_loss=([-\d.]+), total_loss=([-\d.]+)\)',
        content
    ):
        iteration = int(match.group(1))
        policy_loss = float(match.group(2))
        value_loss = float(match.group(3))
        entropy_loss = float(match.group(4))
        total_loss = float(match.group(5))
        results['losses'].append({
            'iteration': iteration,
            'policy_loss': policy_loss,
            'value_loss': value_loss,
            'entropy_loss': entropy_loss,
            'total_loss': total_loss,
        })
        results['iterations'].append(iteration)
    
    # 提取验证统计
    for match in re.finditer(
        r'Valid trajectories: (\d+).*?Invalid trajectories: (\d+).*?Valid rate: ([\d.]+)%',
        content,
        re.DOTALL
    ):
        results['validation_stats'].append({
            'valid': int(match.group(1)),
            'invalid': int(match.group(2)),
            'valid_rate': float(match.group(3)),
        })
    
    # 提取错误信息
    error_patterns = [
        r'Error: ([^\n]+)',
        r'Warning: ([^\n]+)',
        r'Failed: ([^\n]+)',
    ]
    for pattern in error_patterns:
        for match in re.finditer(pattern, content):
            results['errors'].append(match.group(1))
    
    return results


def check_stage1_training(log_dir="./logs"):
    """检查阶段1训练效果"""
    log_dir = Path(log_dir)
    
    if not log_dir.exists():
        print(f"❌ 日志目录不存在: {log_dir}")
        return
    
    # 查找最新的训练日志
    log_files = sorted(log_dir.glob("training_*.log"), reverse=True)
    
    if not log_files:
        print(f"❌ 未找到训练日志文件: {log_dir}/training_*.log")
        return
    
    latest_log = log_files[0]
    print("=" * 60)
    print(f"📄 检查日志: {latest_log.name}")
    print(f"📅 修改时间: {datetime.fromtimestamp(latest_log.stat().st_mtime)}")
    print("=" * 60)
    print()
    
    # 解析日志
    results = parse_log_file(latest_log)
    
    # 1. 检查阶段信息
    print("1️⃣  阶段信息")
    if results['stage']:
        print(f"   ✅ 当前阶段: {results['stage']}")
    else:
        print("   ⚠️  未找到阶段1信息，可能已进入其他阶段")
    print()
    
    # 2. 检查奖励配置
    print("2️⃣  奖励配置")
    if results['reward_config']:
        print("   ✅ 奖励配置:")
        for key, value in results['reward_config'].items():
            print(f"      - {key}: {value}")
        
        # 检查关键奖励
        if 'lack_color_discard' in results['reward_config']:
            print("   ✅ 包含 lack_color_discard（打缺门牌奖励）")
        else:
            print("   ⚠️  未找到 lack_color_discard 奖励配置")
    else:
        print("   ⚠️  未找到奖励配置信息")
    print()
    
    # 3. 检查数据收集
    print("3️⃣  数据收集")
    if results['trajectories']:
        latest_trajectories = results['trajectories'][-1]
        print(f"   ✅ 最新数据收集: {latest_trajectories} 条轨迹")
        
        if len(results['trajectories']) > 1:
            first = results['trajectories'][0]
            last = results['trajectories'][-1]
            if last > first:
                print(f"   ✅ 轨迹数量在增长: {first} -> {last}")
            else:
                print(f"   ⚠️  轨迹数量未增长: {first} -> {last}")
    else:
        print("   ⚠️  未找到数据收集信息")
    print()
    
    # 4. 检查验证统计
    print("4️⃣  数据验证")
    if results['validation_stats']:
        latest = results['validation_stats'][-1]
        valid_rate = latest['valid_rate']
        print(f"   ✅ 最新验证统计:")
        print(f"      - 有效轨迹: {latest['valid']}")
        print(f"      - 无效轨迹: {latest['invalid']}")
        print(f"      - 有效率: {valid_rate:.2f}%")
        
        if valid_rate >= 90:
            print("   ✅ 有效率良好（>= 90%）")
        elif valid_rate >= 70:
            print("   ⚠️  有效率一般（70-90%）")
        else:
            print("   ❌ 有效率较低（< 70%）")
    else:
        print("   ⚠️  未找到验证统计信息")
    print()
    
    # 5. 检查训练损失
    print("5️⃣  训练损失")
    if results['losses']:
        if len(results['losses']) >= 2:
            first_loss = results['losses'][0]
            last_loss = results['losses'][-1]
            
            print(f"   📊 损失变化:")
            print(f"      - 策略损失: {first_loss['policy_loss']:.4f} -> {last_loss['policy_loss']:.4f}")
            print(f"      - 价值损失: {first_loss['value_loss']:.4f} -> {last_loss['value_loss']:.4f}")
            print(f"      - 总损失: {first_loss['total_loss']:.4f} -> {last_loss['total_loss']:.4f}")
            
            # 检查是否下降
            policy_improved = abs(last_loss['policy_loss']) < abs(first_loss['policy_loss'])
            value_improved = last_loss['value_loss'] < first_loss['value_loss']
            total_improved = last_loss['total_loss'] < first_loss['total_loss']
            
            if policy_improved:
                print("   ✅ 策略损失在下降")
            else:
                print("   ⚠️  策略损失未下降")
            
            if value_improved:
                print("   ✅ 价值损失在下降")
            else:
                print("   ⚠️  价值损失未下降")
            
            if total_improved:
                print("   ✅ 总损失在下降")
            else:
                print("   ⚠️  总损失未下降")
        else:
            print(f"   ⚠️  损失数据不足（只有 {len(results['losses'])} 条记录）")
    else:
        print("   ⚠️  未找到训练损失信息")
    print()
    
    # 6. 检查迭代进度
    print("6️⃣  训练进度")
    if results['iterations']:
        latest_iteration = max(results['iterations'])
        print(f"   ✅ 最新迭代: {latest_iteration}")
        
        if latest_iteration < 2000:
            print("   ⚠️  迭代次数不足（< 2000），阶段1至少需要2000次迭代")
        elif latest_iteration >= 8000:
            print("   ⚠️  迭代次数已超过8000，应该推进到阶段2")
        else:
            print(f"   ✅ 迭代进度正常（{latest_iteration}/8000）")
    else:
        print("   ⚠️  未找到迭代信息")
    print()
    
    # 7. 检查错误
    print("7️⃣  错误检查")
    if results['errors']:
        unique_errors = list(set(results['errors'][-20:]))  # 最近20个错误
        print(f"   ⚠️  发现 {len(results['errors'])} 个错误/警告")
        if len(unique_errors) <= 5:
            print("   📋 最近的错误:")
            for error in unique_errors[:5]:
                print(f"      - {error[:80]}...")
        else:
            print(f"   📋 最近的错误（显示前5个）:")
            for error in unique_errors[:5]:
                print(f"      - {error[:80]}...")
    else:
        print("   ✅ 未发现错误")
    print()
    
    # 总结
    print("=" * 60)
    print("📋 检查总结")
    print("=" * 60)
    
    checks = []
    if results['stage']:
        checks.append("✅ 阶段信息正确")
    if 'lack_color_discard' in results['reward_config']:
        checks.append("✅ 奖励配置正确")
    if results['trajectories']:
        checks.append("✅ 数据收集正常")
    if results['losses'] and len(results['losses']) >= 2:
        first = results['losses'][0]
        last = results['losses'][-1]
        if last['total_loss'] < first['total_loss']:
            checks.append("✅ 训练损失下降")
    
    if checks:
        print("\n".join(checks))
        print("\n🎉 阶段1训练看起来正常！")
    else:
        print("⚠️  部分检查项未通过，请查看上述详细信息")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='检查阶段1训练效果',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--log-dir',
        default='./logs',
        help='日志目录（默认: ./logs）'
    )
    
    args = parser.parse_args()
    check_stage1_training(args.log_dir)


if __name__ == '__main__':
    main()

