"""
课程学习中心 Web 服务器

使用 Flask 提供 Web 界面和 API。
"""

import json
import threading
from typing import Dict, Any
from flask import Flask, render_template_string, jsonify, Response
from flask_cors import CORS
import time

from .dashboard import get_state_manager

# 创建 Flask 应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 加载 HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>课程学习中心 - 训练监控</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            color: #667eea;
            margin-bottom: 8px;
        }
        
        .status-bar {
            display: flex;
            gap: 20px;
            margin-top: 16px;
            flex-wrap: wrap;
        }
        
        .status-item {
            flex: 1;
            min-width: 200px;
        }
        
        .status-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        
        .status-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        @media (max-width: 1024px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 16px;
            font-size: 20px;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 16px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 12px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }
        
        .metric-item {
            text-align: center;
            padding: 16px;
            background: #f5f5f5;
            border-radius: 8px;
        }
        
        .metric-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }
        
        .objectives-list {
            list-style: none;
            padding: 0;
        }
        
        .objectives-list li {
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .objectives-list li:last-child {
            border-bottom: none;
        }
        
        .objectives-list li::before {
            content: "✓ ";
            color: #4caf50;
            font-weight: bold;
            margin-right: 8px;
        }
        
        .reward-config {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-top: 16px;
        }
        
        .reward-item {
            padding: 12px;
            background: #f5f5f5;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
        }
        
        .reward-label {
            font-size: 14px;
            color: #666;
        }
        
        .reward-value {
            font-size: 16px;
            font-weight: bold;
            color: #667eea;
        }
        
        .timestamp {
            text-align: right;
            color: #999;
            font-size: 12px;
            margin-top: 16px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 16px;
            border-radius: 8px;
            margin: 16px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 课程学习中心</h1>
            <p>实时训练进度监控</p>
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-label">当前迭代</div>
                    <div class="status-value" id="current-iteration">0</div>
                </div>
                <div class="status-item">
                    <div class="status-label">总迭代数</div>
                    <div class="status-value" id="total-iterations">0</div>
                </div>
                <div class="status-item">
                    <div class="status-label">训练进度</div>
                    <div class="status-value" id="overall-progress">0%</div>
                </div>
                <div class="status-item">
                    <div class="status-label">当前阶段</div>
                    <div class="status-value" id="current-stage">-</div>
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="card">
                <h2>📊 阶段进度</h2>
                <div id="stage-info">
                    <div class="loading">加载中...</div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="stage-progress" style="width: 0%">0%</div>
                </div>
            </div>
            
            <div class="card">
                <h2>📈 性能指标</h2>
                <div id="metrics" class="metrics-grid">
                    <div class="loading">加载中...</div>
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="card">
                <h2>🎯 阶段目标</h2>
                <ul id="objectives" class="objectives-list">
                    <li class="loading">加载中...</li>
                </ul>
            </div>
            
            <div class="card">
                <h2>🎁 奖励配置</h2>
                <div style="margin-bottom: 16px;">
                    <button onclick="toggleRewardHistory()" id="reward-history-btn" style="padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        查看历史变化
                    </button>
                </div>
                <div id="reward-config" class="reward-config">
                    <div class="loading">加载中...</div>
                </div>
                <div id="reward-history" style="display: none; margin-top: 20px;">
                    <canvas id="reward-chart" style="max-height: 400px;"></canvas>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="timestamp" id="timestamp">最后更新: -</div>
        </div>
    </div>
    
    <script>
        let eventSource = null;
        
        function connectSSE() {
            eventSource = new EventSource('/api/stream');
            
            eventSource.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    updateUI(data);
                } catch (e) {
                    console.error('Error parsing SSE data:', e);
                }
            };
            
            eventSource.onerror = function(event) {
                console.error('SSE connection error');
                eventSource.close();
                // 重连
                setTimeout(connectSSE, 3000);
            };
        }
        
        function updateUI(data) {
            // 更新状态栏
            document.getElementById('current-iteration').textContent = data.current_iteration || 0;
            document.getElementById('total-iterations').textContent = data.total_iterations || 0;
            
            const overallProgress = data.total_iterations > 0 
                ? Math.round((data.current_iteration / data.total_iterations) * 100) 
                : 0;
            document.getElementById('overall-progress').textContent = overallProgress + '%';
            document.getElementById('current-stage').textContent = data.current_stage || '-';
            
            // 更新阶段信息
            const stageInfo = document.getElementById('stage-info');
            if (data.curriculum_info && data.curriculum_info.name) {
                stageInfo.innerHTML = `
                    <h3>${data.curriculum_info.name}</h3>
                    <p style="color: #666; margin-top: 8px;">${data.curriculum_info.description || ''}</p>
                `;
            }
            
            // 更新阶段进度条
            const stageProgress = (data.stage_progress * 100).toFixed(1);
            document.getElementById('stage-progress').style.width = stageProgress + '%';
            document.getElementById('stage-progress').textContent = stageProgress + '%';
            
            // 更新性能指标
            const metricsDiv = document.getElementById('metrics');
            if (data.metrics && Object.keys(data.metrics).length > 0) {
                metricsDiv.innerHTML = Object.entries(data.metrics).map(([key, value]) => `
                    <div class="metric-item">
                        <div class="metric-label">${formatMetricName(key)}</div>
                        <div class="metric-value">${formatMetricValue(value)}</div>
                    </div>
                `).join('');
            } else {
                metricsDiv.innerHTML = '<div class="metric-item"><div class="metric-label">暂无数据</div></div>';
            }
            
            // 更新阶段目标
            const objectivesList = document.getElementById('objectives');
            if (data.curriculum_info && data.curriculum_info.objectives) {
                objectivesList.innerHTML = data.curriculum_info.objectives.map(obj => 
                    `<li>${obj}</li>`
                ).join('');
            } else {
                objectivesList.innerHTML = '<li>暂无目标</li>';
            }
            
            // 更新奖励配置
            const rewardConfigDiv = document.getElementById('reward-config');
            if (data.reward_config && Object.keys(data.reward_config).length > 0) {
                rewardConfigDiv.innerHTML = Object.entries(data.reward_config).map(([key, value]) => `
                    <div class="reward-item">
                        <span class="reward-label">${formatRewardName(key)}</span>
                        <span class="reward-value">${value.toFixed(2)}</span>
                    </div>
                `).join('');
            } else {
                rewardConfigDiv.innerHTML = '<div class="reward-item"><span class="reward-label">暂无配置</span></div>';
            }
            
            // 更新时间戳
            if (data.timestamp) {
                const date = new Date(data.timestamp);
                document.getElementById('timestamp').textContent = 
                    '最后更新: ' + date.toLocaleString('zh-CN');
            }
        }
        
        function formatMetricName(key) {
            const names = {
                'win_rate': '胜率',
                'ready_rate': '听牌率',
                'flower_pig_rate': '花猪率',
                'average_fan': '平均番数',
                'elo_score': 'Elo评分',
                'games_played': '游戏局数',
            };
            return names[key] || key;
        }
        
        function formatMetricValue(value) {
            if (typeof value === 'number') {
                if (value < 1) {
                    return (value * 100).toFixed(1) + '%';
                }
                return value.toFixed(2);
            }
            return value;
        }
        
        function formatRewardName(key) {
            const names = {
                'base_win': '基础胡牌奖励',
                'ready_reward': '听牌奖励',
                'shanten_reward': '向听数奖励',
                'lack_color_discard': '缺门弃牌奖励',
                'point_loss': '点炮惩罚',
                'fan_multiplier': '番数倍数',
            };
            return names[key] || key;
        }
        
        // 初始化
        connectSSE();
        
        // 定期获取最新状态（作为 SSE 的备用）
        setInterval(async () => {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateUI(data);
            } catch (e) {
                console.error('Error fetching status:', e);
            }
        }, 5000);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/status')
def get_status():
    """获取当前状态（REST API）"""
    state_manager = get_state_manager()
    status = state_manager.get_status()
    return jsonify(status)


@app.route('/api/history')
def get_history():
    """获取历史记录（REST API）"""
    from flask import request
    state_manager = get_state_manager()
    
    # 获取查询参数
    limit = request.args.get('limit', type=int)
    start_iteration = request.args.get('start_iteration', type=int)
    end_iteration = request.args.get('end_iteration', type=int)
    
    history = state_manager.get_history(
        limit=limit,
        start_iteration=start_iteration,
        end_iteration=end_iteration,
    )
    
    return jsonify({
        'history': history,
        'count': len(history),
    })


@app.route('/api/history/summary')
def get_history_summary():
    """获取历史记录摘要"""
    state_manager = get_state_manager()
    summary = state_manager.get_history_summary()
    return jsonify(summary)


@app.route('/api/stream')
def stream_status():
    """Server-Sent Events 流式更新"""
    def generate():
        state_manager = get_state_manager()
        subscriber_queue = None
        
        try:
            subscriber_queue = state_manager.subscribe()
            
            # 立即发送当前状态
            try:
                current_status = state_manager.get_status()
                yield f"data: {json.dumps(current_status)}\n\n"
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': f'Failed to get initial status: {str(e)}'})}\n\n"
            
            # 监听更新
            while True:
                try:
                    status = subscriber_queue.get(timeout=1)
                    yield f"data: {json.dumps(status)}\n\n"
                except queue.Empty:
                    # 超时，发送心跳
                    yield ": heartbeat\n\n"
                except Exception as e:
                    # 处理其他异常
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                    break
        except Exception as e:
            # 处理订阅异常
            yield f"event: error\ndata: {json.dumps({'error': f'Failed to subscribe: {str(e)}'})}\n\n"
        finally:
            # 确保取消订阅
            if subscriber_queue is not None:
                try:
                    state_manager.unsubscribe(subscriber_queue)
                except Exception:
                    pass  # 忽略取消订阅时的异常
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


def start_server(host='0.0.0.0', port=5000, debug=False):
    """启动 Web 服务器"""
    print(f"启动课程学习中心 Web 服务器: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    start_server(port=5000, debug=True)

