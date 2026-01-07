#!/usr/bin/env python3
"""
诊断仪表板未启动的问题

用法:
    python scripts/diagnose_dashboard.py
"""

import sys
import yaml
from pathlib import Path


def check_imports():
    """检查必要的模块是否可导入"""
    print("1️⃣  检查模块导入...")
    
    issues = []
    
    # 检查 Flask
    try:
        import flask
        print(f"   ✅ Flask 已安装 (版本: {flask.__version__})")
    except ImportError:
        print("   ❌ Flask 未安装")
        issues.append("pip install flask")
    
    # 检查 flask_cors
    try:
        import flask_cors
        print(f"   ✅ flask_cors 已安装")
    except ImportError:
        print("   ⚠️  flask_cors 未安装（可选，但推荐安装）")
        issues.append("pip install flask-cors")
    
    # 检查课程学习模块
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "python"))
        from scai.coach.web_server import start_server
        print("   ✅ 课程学习模块可导入")
    except ImportError as e:
        print(f"   ❌ 课程学习模块导入失败: {e}")
        issues.append("检查 scai.coach 模块是否正确安装")
    
    print()
    return issues


def check_config():
    """检查配置文件"""
    print("2️⃣  检查配置文件...")
    
    config_file = Path("python/config.yaml")
    if not config_file.exists():
        print(f"   ❌ 配置文件不存在: {config_file}")
        return []
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"   ❌ 读取配置文件失败: {e}")
        return []
    
    issues = []
    
    # 检查课程学习配置
    curriculum = config.get('curriculum_learning', {})
    if not curriculum:
        print("   ❌ 未找到 curriculum_learning 配置")
        issues.append("在 config.yaml 中添加 curriculum_learning 配置")
        return issues
    
    if not curriculum.get('enabled', False):
        print("   ❌ curriculum_learning.enabled = false")
        issues.append("设置 curriculum_learning.enabled: true")
    else:
        print("   ✅ curriculum_learning.enabled = true")
    
    # 检查仪表板配置
    dashboard = curriculum.get('dashboard', {})
    if not dashboard:
        print("   ❌ 未找到 dashboard 配置")
        issues.append("在 curriculum_learning 中添加 dashboard 配置")
        return issues
    
    if not dashboard.get('enabled', False):
        print("   ❌ dashboard.enabled = false")
        issues.append("设置 dashboard.enabled: true")
    else:
        print("   ✅ dashboard.enabled = true")
    
    port = dashboard.get('port', 5000)
    host = dashboard.get('host', '0.0.0.0')
    print(f"   ✅ 监听地址: {host}:{port}")
    
    print()
    return issues


def check_logs():
    """检查日志文件"""
    print("3️⃣  检查训练日志...")
    
    log_dir = Path("logs")
    if not log_dir.exists():
        print("   ⚠️  日志目录不存在: logs/")
        print("   💡 可能训练脚本还未运行")
        print()
        return []
    
    log_files = sorted(log_dir.glob("training_*.log"), reverse=True)
    if not log_files:
        print("   ⚠️  未找到训练日志文件")
        print("   💡 可能训练脚本还未运行")
        print()
        return []
    
    latest_log = log_files[0]
    print(f"   📄 最新日志: {latest_log.name}")
    
    try:
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 检查课程学习相关日志
        if "Curriculum learning enabled" in content:
            print("   ✅ 课程学习已启用")
        else:
            print("   ⚠️  未找到课程学习启用日志")
        
        # 检查仪表板相关日志
        if "仪表板" in content or "dashboard" in content.lower():
            print("   ✅ 找到仪表板相关日志")
            # 查找相关行
            lines = content.split('\n')
            dashboard_lines = [line for line in lines if '仪表板' in line or 'dashboard' in line.lower()]
            if dashboard_lines:
                print("   📋 相关日志:")
                for line in dashboard_lines[-5:]:  # 显示最后5行
                    print(f"      {line[:80]}...")
        else:
            print("   ❌ 未找到仪表板相关日志")
            print("   💡 仪表板可能未启动")
        
        # 检查错误
        if "Error" in content or "error" in content.lower():
            error_lines = [line for line in lines if 'error' in line.lower() and 'dashboard' in line.lower()]
            if error_lines:
                print("   ⚠️  发现仪表板相关错误:")
                for line in error_lines[-3:]:
                    print(f"      {line[:80]}...")
    
    except Exception as e:
        print(f"   ❌ 读取日志失败: {e}")
    
    print()
    return []


def check_process():
    """检查训练进程"""
    print("4️⃣  检查训练进程...")
    
    import subprocess
    
    try:
        # 检查是否有训练进程
        result = subprocess.run(
            ['pgrep', '-f', 'train.py'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"   ✅ 找到训练进程: {', '.join(pids)}")
        else:
            print("   ⚠️  未找到训练进程")
            print("   💡 训练脚本可能未运行")
    
    except FileNotFoundError:
        # pgrep 不可用，尝试使用 ps
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            if 'train.py' in result.stdout:
                print("   ✅ 找到训练进程")
            else:
                print("   ⚠️  未找到训练进程")
        except:
            print("   ⚠️  无法检查进程（需要 ps 或 pgrep 命令）")
    
    print()


def main():
    print("=" * 60)
    print("🔍 诊断仪表板未启动问题")
    print("=" * 60)
    print()
    
    all_issues = []
    
    # 检查模块导入
    import_issues = check_imports()
    all_issues.extend(import_issues)
    
    # 检查配置
    config_issues = check_config()
    all_issues.extend(config_issues)
    
    # 检查日志
    check_logs()
    
    # 检查进程
    check_process()
    
    # 总结
    print("=" * 60)
    print("📋 诊断总结")
    print("=" * 60)
    print()
    
    if all_issues:
        print("❌ 发现以下问题：")
        for i, issue in enumerate(all_issues, 1):
            print(f"   {i}. {issue}")
        print()
        print("💡 解决建议：")
        print()
        if "pip install" in str(all_issues):
            print("1. 安装缺失的依赖：")
            for issue in all_issues:
                if "pip install" in issue:
                    print(f"   {issue}")
            print()
        if "enabled" in str(all_issues).lower():
            print("2. 修改配置文件 python/config.yaml：")
            print("   curriculum_learning:")
            print("     enabled: true")
            print("     dashboard:")
            print("       enabled: true")
            print("       port: 5000")
            print()
        print("3. 重启训练脚本")
    else:
        print("✅ 所有检查通过")
        print()
        print("💡 如果仪表板仍未启动，可能的原因：")
        print("   1. 训练脚本启动时出现错误（查看日志）")
        print("   2. 仪表板线程启动失败（检查是否有端口冲突）")
        print("   3. Flask应用初始化失败（查看完整日志）")
        print()
        print("建议：")
        print("   - 查看完整的训练日志: tail -f logs/training_*.log")
        print("   - 检查端口是否被占用: lsof -i :5000")
        print("   - 尝试手动启动仪表板测试: python -c 'from scai.coach.web_server import start_server; start_server()'")
    print()


if __name__ == '__main__':
    main()

