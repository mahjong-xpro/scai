#!/usr/bin/env python3
"""
SSH隧道脚本 - 访问远程服务器的训练仪表板

用法:
    python ssh_tunnel_dashboard.py --host <服务器地址> --user <用户名> --port <SSH端口>
    
示例:
    python ssh_tunnel_dashboard.py --host 192.168.1.100 --user root --port 22
    python ssh_tunnel_dashboard.py --host example.com --user ubuntu --key ~/.ssh/id_rsa
"""

import argparse
import subprocess
import sys
import time
import signal
import os
import webbrowser
from pathlib import Path


class SSHTunnel:
    """SSH隧道管理器"""
    
    def __init__(self, host, user, ssh_port=22, remote_port=5000, local_port=5000, 
                 key_file=None, password=None):
        self.host = host
        self.user = user
        self.ssh_port = ssh_port
        self.remote_port = remote_port
        self.local_port = local_port
        self.key_file = key_file
        self.password = password
        self.process = None
        
    def start(self):
        """启动SSH隧道"""
        # 构建SSH命令
        cmd = [
            'ssh',
            '-N',  # 不执行远程命令
            '-L', f'{self.local_port}:localhost:{self.remote_port}',  # 本地端口转发
            '-p', str(self.ssh_port),  # SSH端口
            '-o', 'StrictHostKeyChecking=no',  # 跳过主机密钥检查
            '-o', 'UserKnownHostsFile=/dev/null',  # 不保存主机密钥
            '-o', 'ServerAliveInterval=60',  # 每60秒发送保活信号
            '-o', 'ServerAliveCountMax=3',  # 最多3次保活失败后断开
        ]
        
        # 如果指定了密钥文件，添加 -i 参数
        if self.key_file:
            cmd.extend(['-i', self.key_file])
        
        # 添加用户名和主机
        cmd.append(f'{self.user}@{self.host}')
        
        print(f"正在建立SSH隧道...")
        print(f"  远程服务器: {self.user}@{self.host}:{self.ssh_port}")
        print(f"  端口转发: localhost:{self.local_port} -> {self.host}:{self.remote_port}")
        print(f"  访问地址: http://localhost:{self.local_port}")
        print()
        
        try:
            # 启动SSH进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
            )
            
            # 等待一下，检查进程是否正常启动
            time.sleep(1)
            
            if self.process.poll() is not None:
                # 进程已退出，说明连接失败
                stdout, stderr = self.process.communicate()
                error_msg = stderr.decode('utf-8', errors='ignore')
                raise Exception(f"SSH隧道启动失败: {error_msg}")
            
            print("✅ SSH隧道已建立")
            print(f"📊 训练仪表板: http://localhost:{self.local_port}")
            print()
            print("按 Ctrl+C 停止隧道")
            print("-" * 60)
            
            return True
            
        except FileNotFoundError:
            raise Exception("未找到 ssh 命令，请确保已安装 OpenSSH")
        except Exception as e:
            raise Exception(f"启动SSH隧道失败: {e}")
    
    def stop(self):
        """停止SSH隧道"""
        if self.process:
            print("\n正在关闭SSH隧道...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("✅ SSH隧道已关闭")
    
    def wait(self):
        """等待隧道进程结束"""
        if self.process:
            try:
                self.process.wait()
            except KeyboardInterrupt:
                self.stop()


def open_browser(url, delay=2):
    """在浏览器中打开URL"""
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
            print(f"✅ 已在浏览器中打开: {url}")
        except Exception as e:
            print(f"⚠️  无法自动打开浏览器: {e}")
            print(f"   请手动访问: {url}")
    
    import threading
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def main():
    parser = argparse.ArgumentParser(
        description='通过SSH隧道访问远程服务器的训练仪表板',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  python ssh_tunnel_dashboard.py --host 192.168.1.100 --user root
  
  # 指定SSH端口
  python ssh_tunnel_dashboard.py --host example.com --user ubuntu --ssh-port 2222
  
  # 使用密钥文件
  python ssh_tunnel_dashboard.py --host example.com --user ubuntu --key ~/.ssh/id_rsa
  
  # 指定本地端口
  python ssh_tunnel_dashboard.py --host 192.168.1.100 --user root --local-port 8080
  
  # 自动打开浏览器
  python ssh_tunnel_dashboard.py --host 192.168.1.100 --user root --open-browser
        """
    )
    
    parser.add_argument(
        '--host',
        required=True,
        help='远程服务器地址（IP或域名）'
    )
    
    parser.add_argument(
        '--user',
        required=True,
        help='SSH用户名'
    )
    
    parser.add_argument(
        '--ssh-port',
        type=int,
        default=22,
        help='SSH端口（默认: 22）'
    )
    
    parser.add_argument(
        '--remote-port',
        type=int,
        default=5000,
        help='远程服务器端口（默认: 5000，训练仪表板端口）'
    )
    
    parser.add_argument(
        '--local-port',
        type=int,
        default=5000,
        help='本地端口（默认: 5000）'
    )
    
    parser.add_argument(
        '--key',
        '--key-file',
        dest='key_file',
        help='SSH私钥文件路径（可选，默认使用 ~/.ssh/id_rsa）'
    )
    
    parser.add_argument(
        '--open-browser',
        action='store_true',
        help='自动在浏览器中打开仪表板'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='不自动打开浏览器（即使指定了 --open-browser）'
    )
    
    args = parser.parse_args()
    
    # 如果没有指定密钥文件，尝试使用默认的
    if not args.key_file:
        default_key = Path.home() / '.ssh' / 'id_rsa'
        if default_key.exists():
            args.key_file = str(default_key)
    
    # 创建SSH隧道
    tunnel = SSHTunnel(
        host=args.host,
        user=args.user,
        ssh_port=args.ssh_port,
        remote_port=args.remote_port,
        local_port=args.local_port,
        key_file=args.key_file,
    )
    
    # 注册信号处理，确保退出时关闭隧道
    def signal_handler(sig, frame):
        tunnel.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动隧道
        tunnel.start()
        
        # 如果需要，自动打开浏览器
        if args.open_browser and not args.no_browser:
            url = f'http://localhost:{args.local_port}'
            open_browser(url)
        
        # 等待隧道进程
        tunnel.wait()
        
    except KeyboardInterrupt:
        tunnel.stop()
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        tunnel.stop()
        sys.exit(1)


if __name__ == '__main__':
    main()

