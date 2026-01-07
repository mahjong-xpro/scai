#!/usr/bin/env python3
"""
检查训练仪表板是否运行

用法:
    python scripts/check_dashboard.py [--port 5000] [--host localhost]
"""

import argparse
import socket
import sys
import requests
from urllib.parse import urljoin


def check_port(host, port, timeout=2):
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        return False


def check_dashboard(host='localhost', port=5000):
    """检查仪表板是否可访问"""
    url = f'http://{host}:{port}'
    
    print("=" * 60)
    print("🔍 检查训练仪表板")
    print("=" * 60)
    print()
    
    # 1. 检查端口是否开放
    print(f"1️⃣  检查端口 {port} 是否开放...")
    if check_port(host, port):
        print(f"   ✅ 端口 {port} 已开放")
    else:
        print(f"   ❌ 端口 {port} 未开放或无法访问")
        print()
        print("可能的原因：")
        print("   1. 训练脚本未运行")
        print("   2. 仪表板未启用（curriculum_learning.dashboard.enabled: false）")
        print("   3. 防火墙阻止了端口")
        print("   4. 服务启动失败")
        return False
    print()
    
    # 2. 检查HTTP服务
    print(f"2️⃣  检查HTTP服务...")
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"   ✅ HTTP服务正常（状态码: {response.status_code}）")
            print(f"   📊 仪表板地址: {url}")
            return True
        else:
            print(f"   ⚠️  HTTP服务返回异常状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ 无法连接到 {url}")
        print("   可能的原因：")
        print("   - 服务未启动")
        print("   - 端口被占用")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ 连接超时")
        return False
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        return False
    print()


def check_config():
    """检查配置"""
    import yaml
    from pathlib import Path
    
    config_file = Path("python/config.yaml")
    if not config_file.exists():
        print("⚠️  配置文件不存在: python/config.yaml")
        return
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        curriculum = config.get('curriculum_learning', {})
        dashboard = curriculum.get('dashboard', {})
        
        print("3️⃣  检查配置...")
        if not curriculum.get('enabled', False):
            print("   ⚠️  课程学习未启用（curriculum_learning.enabled: false）")
            print("   💡 仪表板需要课程学习才能运行")
            return
        
        if not dashboard.get('enabled', False):
            print("   ⚠️  仪表板未启用（curriculum_learning.dashboard.enabled: false）")
            print("   💡 需要在配置文件中启用仪表板")
            return
        
        print("   ✅ 配置正确")
        print(f"   - 课程学习: 已启用")
        print(f"   - 仪表板: 已启用")
        print(f"   - 监听地址: {dashboard.get('host', '0.0.0.0')}")
        print(f"   - 监听端口: {dashboard.get('port', 5000)}")
    except Exception as e:
        print(f"   ❌ 读取配置失败: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='检查训练仪表板是否运行',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--host',
        default='localhost',
        help='主机地址（默认: localhost）'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='端口号（默认: 5000）'
    )
    
    parser.add_argument(
        '--check-config',
        action='store_true',
        help='同时检查配置文件'
    )
    
    args = parser.parse_args()
    
    # 检查配置
    if args.check_config:
        check_config()
        print()
    
    # 检查仪表板
    success = check_dashboard(args.host, args.port)
    
    if not success:
        print()
        print("=" * 60)
        print("💡 解决建议")
        print("=" * 60)
        print()
        print("1. 确认训练脚本正在运行：")
        print("   ps aux | grep train.py")
        print()
        print("2. 检查配置文件中的仪表板设置：")
        print("   curriculum_learning:")
        print("     enabled: true")
        print("     dashboard:")
        print("       enabled: true")
        print("       port: 5000")
        print()
        print("3. 检查端口是否被占用：")
        print(f"   lsof -i :{args.port}")
        print("   或")
        print(f"   netstat -an | grep {args.port}")
        print()
        print("4. 检查防火墙设置：")
        print("   - Linux: sudo ufw status")
        print("   - macOS: 系统偏好设置 -> 安全性与隐私 -> 防火墙")
        print()
        print("5. 查看训练日志：")
        print("   tail -f logs/training_*.log | grep -i dashboard")
        print()
        sys.exit(1)
    else:
        print()
        print("=" * 60)
        print("✅ 仪表板运行正常！")
        print("=" * 60)
        print()
        print(f"📊 访问地址: http://{args.host}:{args.port}")
        print()


if __name__ == '__main__':
    main()

