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
                <div style="margin-bottom: 16px;">
                    <button onclick="toggleMetricsHistory()" id="metrics-history-btn" style="padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        查看历史趋势
                    </button>
                </div>
                <div id="metrics" class="metrics-grid">
                    <div class="loading">加载中...</div>
                </div>
                <div id="metrics-history" style="display: none; margin-top: 20px;">
                    <canvas id="metrics-chart" style="max-height: 400px;"></canvas>
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
            <h2>🎮 牌局回放</h2>
            <div style="margin-bottom: 16px;">
                <button onclick="showReplayList()" id="replay-list-btn" style="padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 8px;">
                    查看回放列表
                </button>
                <button onclick="hideReplayList()" id="replay-close-btn" style="display: none; padding: 8px 16px; background: #999; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    关闭
                </button>
            </div>
            <div id="replay-list" style="display: none;">
                <div class="loading">加载中...</div>
            </div>
            <div id="replay-viewer" style="display: none;">
                <div style="margin-bottom: 16px;">
                    <button onclick="hideReplayViewer()" style="padding: 8px 16px; background: #999; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 8px;">
                        ← 返回列表
                    </button>
                    <span id="replay-game-info" style="font-weight: bold; color: #667eea;"></span>
                </div>
                <div id="replay-controls" style="margin-bottom: 16px; display: flex; gap: 8px; align-items: center;">
                    <button onclick="replayStep(-1)" style="padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        ⏮ 上一步
                    </button>
                    <button onclick="replayToggle()" id="replay-play-btn" style="padding: 8px 16px; background: #43e97b; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        ▶ 播放
                    </button>
                    <button onclick="replayStep(1)" style="padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        下一步 ⏭
                    </button>
                    <span id="replay-step-info" style="margin-left: 16px; color: #666;">步骤: 0 / 0</span>
                </div>
                <div id="replay-content" style="background: #f5f5f5; padding: 16px; border-radius: 8px; min-height: 200px;">
                    <div class="loading">加载中...</div>
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
            
            // 更新性能指标（显示所有指标，固定排序）
            const metricsDiv = document.getElementById('metrics');
            let metricsHTML = '';
            
            // 按照固定顺序显示所有指标
            ALL_METRICS_ORDER.forEach(key => {
                const value = data.metrics && data.metrics[key] !== undefined ? data.metrics[key] : null;
                const displayValue = value !== null ? formatMetricValue(value) : '-';
                const label = formatMetricName(key);
                
                metricsHTML += `
                    <div class="metric-item">
                        <div class="metric-label">${label}</div>
                        <div class="metric-value" style="color: ${value !== null ? '#667eea' : '#999'}">${displayValue}</div>
                    </div>
                `;
            });
            
            metricsDiv.innerHTML = metricsHTML || '<div class="metric-item"><div class="metric-label">暂无数据</div></div>';
            
            // 更新阶段目标
            const objectivesList = document.getElementById('objectives');
            if (data.curriculum_info && data.curriculum_info.objectives) {
                objectivesList.innerHTML = data.curriculum_info.objectives.map(obj => 
                    `<li>${obj}</li>`
                ).join('');
            } else {
                objectivesList.innerHTML = '<li>暂无目标</li>';
            }
            
            // 更新奖励配置（显示所有奖励项，固定排序）
            const rewardConfigDiv = document.getElementById('reward-config');
            let rewardHTML = '';
            
            // 按照固定顺序显示所有奖励项
            ALL_REWARDS_ORDER.forEach(key => {
                const value = data.reward_config && data.reward_config[key] !== undefined ? data.reward_config[key] : null;
                const displayValue = value !== null ? value.toFixed(2) : '-';
                const label = formatRewardName(key);
                const color = value !== null ? (value >= 0 ? '#667eea' : '#c62828') : '#999';
                
                rewardHTML += `
                    <div class="reward-item">
                        <span class="reward-label">${label}</span>
                        <span class="reward-value" style="color: ${color}">${displayValue}</span>
                    </div>
                `;
            });
            
            rewardConfigDiv.innerHTML = rewardHTML || '<div class="reward-item"><span class="reward-label">暂无配置</span></div>';
            
            // 更新时间戳
            if (data.timestamp) {
                const date = new Date(data.timestamp);
                document.getElementById('timestamp').textContent = 
                    '最后更新: ' + date.toLocaleString('zh-CN');
            }
        }
        
        // 定义所有可能的指标（固定顺序）
        const ALL_METRICS_ORDER = [
            'win_rate',              // 胜率
            'ready_rate',            // 听牌率
            'flower_pig_rate',      // 花猪率
            'declare_suit_correct_rate', // 定缺选择正确率
            'average_fan',           // 平均番数
            'gen_count',             // 平均根数
            'elo_score',             // Elo评分
            'games_played',          // 游戏局数
            'hu_types_learned',      // 学会的胡牌类型数
            'policy_loss',           // 策略损失
            'value_loss',            // 价值损失
            'entropy_loss',          // 熵损失
            'total_loss',            // 总损失
        ];
        
        const METRIC_NAMES = {
            'win_rate': '胜率',
            'ready_rate': '听牌率',
            'flower_pig_rate': '花猪率',
            'declare_suit_correct_rate': '定缺正确率',
            'average_fan': '平均番数',
            'gen_count': '平均根数',
            'elo_score': 'Elo评分',
            'games_played': '游戏局数',
            'hu_types_learned': '学会的胡牌类型',
            'policy_loss': '策略损失',
            'value_loss': '价值损失',
            'entropy_loss': '熵损失',
            'total_loss': '总损失',
        };
        
        function formatMetricName(key) {
            return METRIC_NAMES[key] || key;
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
        
        // 定义所有可能的奖励配置（固定顺序）
        const ALL_REWARDS_ORDER = [
            'base_win',                 // 基础胡牌奖励
            'ready_reward',             // 听牌奖励
            'ready_hand',               // 听牌一次性重奖
            'shanten_reward',           // 向听数奖励权重
            'shanten_decrease',         // 向听数减少奖励
            'shanten_increase',         // 向听数增加惩罚
            'lack_color_discard',       // 缺门弃牌奖励
            'illegal_action_attempt',   // 非法动作惩罚
            'flower_pig_penalty',       // 花猪惩罚
            'point_loss',               // 点炮惩罚
            'fan_multiplier',           // 番数倍数
            'gen_reward',               // 根奖励
            'shouting_penalty',         // 查大叫罚分
            'safe_discard_bonus',       // 安全弃牌奖励
            'pass_hu_success',          // 过胡成功奖励
            'call_transfer_loss',       // 呼叫转移损失
        ];
        
        const REWARD_NAMES = {
            'base_win': '基础胡牌奖励',
            'ready_reward': '听牌奖励',
            'ready_hand': '听牌一次性重奖',
            'shanten_reward': '向听数奖励权重',
            'shanten_decrease': '向听数减少奖励',
            'shanten_increase': '向听数增加惩罚',
            'lack_color_discard': '缺门弃牌奖励',
            'illegal_action_attempt': '非法动作惩罚',
            'flower_pig_penalty': '花猪惩罚',
            'point_loss': '点炮惩罚',
            'fan_multiplier': '番数倍数',
            'gen_reward': '根奖励',
            'shouting_penalty': '查大叫罚分',
            'safe_discard_bonus': '安全弃牌奖励',
            'pass_hu_success': '过胡成功奖励',
            'call_transfer_loss': '呼叫转移损失',
        };
        
        function formatRewardName(key) {
            return REWARD_NAMES[key] || key;
        }
        
        // 历史记录相关变量
        let metricsChart = null;
        let rewardChart = null;
        let metricsHistoryVisible = false;
        let rewardHistoryVisible = false;
        
        // 加载 Chart.js（用于绘制图表）
        const chartScript = document.createElement('script');
        chartScript.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js';
        chartScript.onload = function() {
            console.log('Chart.js loaded');
        };
        document.head.appendChild(chartScript);
        
        function toggleMetricsHistory() {
            metricsHistoryVisible = !metricsHistoryVisible;
            const historyDiv = document.getElementById('metrics-history');
            const btn = document.getElementById('metrics-history-btn');
            
            if (metricsHistoryVisible) {
                historyDiv.style.display = 'block';
                btn.textContent = '隐藏历史趋势';
                loadMetricsHistory();
            } else {
                historyDiv.style.display = 'none';
                btn.textContent = '查看历史趋势';
            }
        }
        
        function toggleRewardHistory() {
            rewardHistoryVisible = !rewardHistoryVisible;
            const historyDiv = document.getElementById('reward-history');
            const btn = document.getElementById('reward-history-btn');
            
            if (rewardHistoryVisible) {
                historyDiv.style.display = 'block';
                btn.textContent = '隐藏历史变化';
                loadRewardHistory();
            } else {
                historyDiv.style.display = 'none';
                btn.textContent = '查看历史变化';
            }
        }
        
        async function loadMetricsHistory() {
            try {
                const response = await fetch('/api/history?limit=100');
                const data = await response.json();
                
                if (!data.history || data.history.length === 0) {
                    document.getElementById('metrics-history').innerHTML = '<p style="text-align: center; color: #666;">暂无历史数据</p>';
                    return;
                }
                
                // 提取数据（按照固定顺序）
                const iterations = data.history.map(h => h.current_iteration || 0);
                const metrics = {};
                
                // 按照固定顺序初始化
                ALL_METRICS_ORDER.forEach(key => {
                    metrics[key] = [];
                });
                
                // 填充数据
                data.history.forEach(h => {
                    if (h.metrics) {
                        ALL_METRICS_ORDER.forEach(key => {
                            metrics[key].push(h.metrics[key] !== undefined ? h.metrics[key] : null);
                        });
                    } else {
                        ALL_METRICS_ORDER.forEach(key => {
                            metrics[key].push(null);
                        });
                    }
                });
                
                // 创建图表
                const ctx = document.getElementById('metrics-chart');
                if (metricsChart) {
                    metricsChart.destroy();
                }
                
                const colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe', '#43e97b', '#fa709a', '#fee140', '#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd'];
                
                const datasets = ALL_METRICS_ORDER.map((key, index) => {
                    // 只显示有数据的指标
                    const hasData = metrics[key].some(v => v !== null);
                    if (!hasData) return null;
                    
                    return {
                        label: formatMetricName(key),
                        data: metrics[key],
                        borderColor: colors[index % colors.length],
                        backgroundColor: colors[index % colors.length] + '20',
                        tension: 0.4,
                        spanGaps: true,  // 跳过null值
                    };
                }).filter(d => d !== null);
                
                if (datasets.length === 0) {
                    document.getElementById('metrics-history').innerHTML = '<p style="text-align: center; color: #666;">暂无有效数据</p>';
                    return;
                }
                
                metricsChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: iterations,
                        datasets: datasets,
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                            },
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top',
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                            },
                        },
                    },
                });
            } catch (e) {
                console.error('Error loading metrics history:', e);
                document.getElementById('metrics-history').innerHTML = '<p style="text-align: center; color: #c62828;">加载历史数据失败</p>';
            }
        }
        
        async function loadRewardHistory() {
            try {
                const response = await fetch('/api/history?limit=100');
                const data = await response.json();
                
                if (!data.history || data.history.length === 0) {
                    document.getElementById('reward-history').innerHTML = '<p style="text-align: center; color: #666;">暂无历史数据</p>';
                    return;
                }
                
                // 提取数据（按照固定顺序）
                const iterations = data.history.map(h => h.current_iteration || 0);
                const rewards = {};
                
                // 按照固定顺序初始化
                ALL_REWARDS_ORDER.forEach(key => {
                    rewards[key] = [];
                });
                
                // 填充数据
                data.history.forEach(h => {
                    if (h.reward_config) {
                        ALL_REWARDS_ORDER.forEach(key => {
                            rewards[key].push(h.reward_config[key] !== undefined ? h.reward_config[key] : null);
                        });
                    } else {
                        ALL_REWARDS_ORDER.forEach(key => {
                            rewards[key].push(null);
                        });
                    }
                });
                
                // 创建图表
                const ctx = document.getElementById('reward-chart');
                if (rewardChart) {
                    rewardChart.destroy();
                }
                
                const colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe', '#43e97b', '#fa709a', '#fee140', '#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd', '#00d2d3', '#ff9ff3', '#54a0ff'];
                
                const datasets = ALL_REWARDS_ORDER.map((key, index) => {
                    // 只显示有数据的奖励项
                    const hasData = rewards[key].some(v => v !== null);
                    if (!hasData) return null;
                    
                    return {
                        label: formatRewardName(key),
                        data: rewards[key],
                        borderColor: colors[index % colors.length],
                        backgroundColor: colors[index % colors.length] + '20',
                        tension: 0.4,
                        spanGaps: true,  // 跳过null值
                    };
                }).filter(d => d !== null);
                
                if (datasets.length === 0) {
                    document.getElementById('reward-history').innerHTML = '<p style="text-align: center; color: #666;">暂无有效数据</p>';
                    return;
                }
                
                rewardChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: iterations,
                        datasets: datasets,
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        scales: {
                            y: {
                                beginAtZero: false,  // 奖励值可能为负
                            },
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top',
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                            },
                        },
                    },
                });
            } catch (e) {
                console.error('Error loading reward history:', e);
                document.getElementById('reward-history').innerHTML = '<p style="text-align: center; color: #c62828;">加载历史数据失败</p>';
            }
        }
        
        // 回放相关变量
        let currentReplay = null;
        let currentReplayStep = 0;
        let replayInterval = null;
        let isReplayPlaying = false;
        
        // 显示回放列表
        async function showReplayList() {
            const listDiv = document.getElementById('replay-list');
            const viewerDiv = document.getElementById('replay-viewer');
            const listBtn = document.getElementById('replay-list-btn');
            const closeBtn = document.getElementById('replay-close-btn');
            
            listDiv.style.display = 'block';
            viewerDiv.style.display = 'none';
            listBtn.style.display = 'none';
            closeBtn.style.display = 'inline-block';
            
            try {
                const response = await fetch('/api/replays?limit=20');
                const data = await response.json();
                
                if (data.replays && data.replays.length > 0) {
                    listDiv.innerHTML = `
                        <div style="margin-bottom: 16px; color: #666;">
                            共 ${data.count} 局游戏（显示最近 20 局）
                        </div>
                        <div style="display: grid; gap: 12px;">
                            ${data.replays.map(replay => `
                                <div onclick="loadReplay(${replay.game_id})" style="background: white; padding: 16px; border-radius: 8px; cursor: pointer; border: 2px solid #e0e0e0; transition: all 0.2s;" 
                                     onmouseover="this.style.borderColor='#667eea'; this.style.transform='translateY(-2px)'" 
                                     onmouseout="this.style.borderColor='#e0e0e0'; this.style.transform='translateY(0)'">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <div>
                                            <div style="font-weight: bold; color: #667eea; margin-bottom: 4px;">
                                                ${replay.iteration !== undefined && replay.game_index_in_iteration !== undefined 
                                                    ? `迭代 ${replay.iteration} - 第 ${replay.game_index_in_iteration + 1} 局` 
                                                    : `游戏 #${replay.game_id}`}
                                                ${replay.total_games_in_iteration ? ` (共 ${replay.total_games_in_iteration} 局)` : ''}
                                            </div>
                                            <div style="color: #666; font-size: 14px;">
                                                步骤数: ${replay.num_steps} | 
                                                ${replay.game_info.final_score !== undefined ? `最终得分: ${replay.game_info.final_score}` : ''}
                                                ${replay.game_info.is_winner ? ' 🏆' : ''}
                                            </div>
                                        </div>
                                        <div style="color: #999; font-size: 12px;">
                                            ${new Date(replay.timestamp).toLocaleString('zh-CN')}
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                } else {
                    listDiv.innerHTML = '<div style="text-align: center; color: #666; padding: 40px;">暂无回放数据</div>';
                }
            } catch (e) {
                console.error('Error loading replays:', e);
                listDiv.innerHTML = '<div style="text-align: center; color: #c62828; padding: 40px;">加载失败</div>';
            }
        }
        
        // 隐藏回放列表
        function hideReplayList() {
            const listDiv = document.getElementById('replay-list');
            const listBtn = document.getElementById('replay-list-btn');
            const closeBtn = document.getElementById('replay-close-btn');
            
            listDiv.style.display = 'none';
            listBtn.style.display = 'inline-block';
            closeBtn.style.display = 'none';
        }
        
        // 加载单个回放
        async function loadReplay(gameId) {
            const listDiv = document.getElementById('replay-list');
            const viewerDiv = document.getElementById('replay-viewer');
            const contentDiv = document.getElementById('replay-content');
            const infoSpan = document.getElementById('replay-game-info');
            
            listDiv.style.display = 'none';
            viewerDiv.style.display = 'block';
            contentDiv.innerHTML = '<div class="loading">加载中...</div>';
            
            try {
                const response = await fetch(`/api/replays/${gameId}`);
                
                // 检查响应状态
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({error: 'Unknown error'}));
                    throw new Error(errorData.error || `HTTP ${response.status}`);
                }
                
                const replay = await response.json();
                
                // 检查数据格式
                if (!replay || !replay.trajectory) {
                    throw new Error('Invalid replay data: missing trajectory');
                }
                
                if (!replay.trajectory.states || !Array.isArray(replay.trajectory.states)) {
                    throw new Error('Invalid replay data: missing or invalid states');
                }
                
                if (replay.trajectory.states.length === 0) {
                    throw new Error('Invalid replay data: empty trajectory');
                }
                
                currentReplay = replay;
                currentReplayStep = 0;
                isReplayPlaying = false;
                
                // 更新游戏信息
                let gameTitle = '';
                if (replay.iteration !== undefined && replay.game_index_in_iteration !== undefined) {
                    gameTitle = `迭代 ${replay.iteration} - 第 ${replay.game_index_in_iteration + 1} 局`;
                    if (replay.total_games_in_iteration) {
                        gameTitle += ` (共 ${replay.total_games_in_iteration} 局)`;
                    }
                } else {
                    gameTitle = `游戏 #${replay.game_id}`;
                }
                infoSpan.textContent = gameTitle;
                
                // 渲染第一步
                renderReplayStep(0);
            } catch (e) {
                console.error('Error loading replay:', e);
                const errorMsg = e.message || '加载失败';
                contentDiv.innerHTML = `
                    <div style="text-align: center; color: #c62828; padding: 40px;">
                        <div style="font-size: 18px; margin-bottom: 8px;">加载失败</div>
                        <div style="font-size: 14px; color: #999;">${errorMsg}</div>
                        <button onclick="showReplayList()" style="margin-top: 16px; padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer;">
                            返回列表
                        </button>
                    </div>
                `;
            }
        }
        
        // 隐藏回放查看器
        function hideReplayViewer() {
            const viewerDiv = document.getElementById('replay-viewer');
            viewerDiv.style.display = 'none';
            if (replayInterval) {
                clearInterval(replayInterval);
                replayInterval = null;
                isReplayPlaying = false;
            }
        }
        
        // 渲染回放步骤
        function renderReplayStep(step) {
            if (!currentReplay || !currentReplay.trajectory) {
                return;
            }
            
            const trajectory = currentReplay.trajectory;
            const states = trajectory.states || [];
            const actions = trajectory.actions || [];
            const rewards = trajectory.rewards || [];
            const readableStates = trajectory.readable_states || [];
            
            if (step < 0 || step >= states.length) {
                return;
            }
            
            currentReplayStep = step;
            
            // 更新步骤信息
            document.getElementById('replay-step-info').textContent = `步骤: ${step + 1} / ${states.length}`;
            
            // 渲染当前步骤
            const contentDiv = document.getElementById('replay-content');
            const action = actions[step];
            const reward = rewards[step];
            const readableState = readableStates[step] || {};
            
            // 如果有可读状态，显示4人麻将桌
            if (readableState.players && readableState.players.length === 4) {
                contentDiv.innerHTML = renderMahjongTable(readableState, action, reward, step);
            } else {
                // 回退到简单显示
                contentDiv.innerHTML = `
                    <div style="background: white; padding: 16px; border-radius: 8px;">
                        <h3 style="color: #667eea; margin-bottom: 12px;">步骤 ${step + 1}</h3>
                        <div style="margin-bottom: 8px;">
                            <strong>动作:</strong> ${formatAction(action)}
                        </div>
                        <div style="margin-bottom: 8px;">
                            <strong>奖励:</strong> <span style="color: ${reward >= 0 ? '#43e97b' : '#ff6b6b'}">${typeof reward === 'number' ? reward.toFixed(3) : reward}</span>
                        </div>
                        <div style="color: #999; font-size: 12px; margin-top: 16px;">
                            可读状态信息不可用
                        </div>
                    </div>
                `;
            }
        }
        
        // 渲染麻将桌（4人布局）
        function renderMahjongTable(readableState, action, reward, step) {
            const currentPlayer = readableState.current_player || 0;
            const players = readableState.players || [];
            const actionType = readableState.action_type || 'unknown';
            const actionTileIndex = readableState.action_tile_index;
            const actionResult = readableState.action_result || {};
            const actionResultType = readableState.action_result_type || '';
            
            // 玩家位置：0=下家(自己), 1=对家, 2=上家, 3=右家
            const playerPositions = ['下家 (自己)', '对家', '上家', '右家'];
            const playerColors = ['#667eea', '#764ba2', '#f093fb', '#4facfe'];
            
            let html = `
                <div style="background: #f5f5f5; padding: 20px; border-radius: 12px;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <div style="display: inline-block; background: white; padding: 8px 16px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <span style="font-weight: bold; color: #667eea;">回合 ${readableState.turn || step + 1}</span>
                            <span style="margin: 0 8px; color: #999;">|</span>
                            <span style="color: #666;">当前玩家: 玩家${currentPlayer} (${playerPositions[currentPlayer]})</span>
                            <span style="margin: 0 8px; color: #999;">|</span>
                            <span style="color: ${reward >= 0 ? '#43e97b' : '#ff6b6b'}">奖励: ${typeof reward === 'number' ? reward.toFixed(3) : reward}</span>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
            `;
            
            // 渲染每个玩家
            for (let i = 0; i < 4; i++) {
                const player = players[i] || {};
                const isCurrentPlayer = i === currentPlayer;
                const hand = player.hand || {};
                const declaredSuit = player.declared_suit || '未定缺';
                const isReady = player.is_ready || false;
                
                // 计算手牌总数
                const handCount = Object.values(hand).reduce((sum, count) => sum + count, 0);
                
                html += `
                    <div style="background: white; padding: 16px; border-radius: 8px; border: 2px solid ${isCurrentPlayer ? playerColors[i] : '#e0e0e0'}; ${isCurrentPlayer ? 'box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);' : ''}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div style="font-weight: bold; color: ${playerColors[i]};">
                                玩家${i} (${playerPositions[i]})
                                ${isCurrentPlayer ? ' 👈 当前' : ''}
                            </div>
                            ${isReady ? '<span style="background: #43e97b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">听牌</span>' : ''}
                        </div>
                        
                        <div style="margin-bottom: 8px;">
                            <div style="font-size: 12px; color: #666; margin-bottom: 4px;">定缺: <strong>${declaredSuit}</strong></div>
                            <div style="font-size: 12px; color: #666;">手牌: <strong>${handCount} 张</strong></div>
                        </div>
                        
                        <div style="background: #f9f9f9; padding: 8px; border-radius: 4px; min-height: 60px; max-height: 120px; overflow-y: auto;">
                            ${renderPlayerHand(hand)}
                        </div>
                    </div>
                `;
            }
            
            html += `
                    </div>
                    
                    <div style="background: white; padding: 16px; border-radius: 8px; margin-top: 16px;">
                        <div style="font-weight: bold; color: #667eea; margin-bottom: 12px;">当前动作</div>
                        <div style="margin-bottom: 8px;">
                            <strong>动作类型:</strong> ${formatActionType(actionType, actionTileIndex)}
                        </div>
                        ${actionResultType ? `
                            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e0e0e0;">
                                <strong>动作结果:</strong> 
                                <span style="color: ${actionResultType === 'won' ? '#43e97b' : '#666'}">
                                    ${formatActionResult(actionResultType, actionResult)}
                                </span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
            
            return html;
        }
        
        // 渲染玩家手牌
        function renderPlayerHand(hand) {
            if (!hand || Object.keys(hand).length === 0) {
                return '<div style="color: #999; font-size: 12px;">手牌信息不可用</div>';
            }
            
            let html = '<div style="display: flex; flex-wrap: wrap; gap: 4px;">';
            for (const [tile, count] of Object.entries(hand)) {
                if (count > 0) {
                    const tileName = formatTileName(tile);
                    for (let i = 0; i < count; i++) {
                        html += `<span style="background: #fff; border: 1px solid #ddd; padding: 4px 8px; border-radius: 4px; font-size: 11px; color: #333;">${tileName}</span>`;
                    }
                }
            }
            html += '</div>';
            return html;
        }
        
        // 格式化牌名
        function formatTileName(tileStr) {
            // 将 "Wan(1)" 格式转换为 "一万"
            const match = tileStr.match(/(\w+)\((\d+)\)/);
            if (match) {
                const suit = match[1];
                const rank = match[2];
                const suitMap = {'Wan': '万', 'Tong': '筒', 'Tiao': '条'};
                const suitName = suitMap[suit] || suit;
                const rankNames = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九'];
                const rankName = rankNames[parseInt(rank)] || rank;
                return rankName + suitName;
            }
            return tileStr;
        }
        
        // 格式化动作类型
        function formatActionType(actionType, tileIndex) {
            const actionNames = {
                'discard': '出牌',
                'pong': '碰',
                'gang': '杠',
                'win': '胡',
                'pass': '过',
                'draw': '摸牌',
            };
            const name = actionNames[actionType] || actionType;
            if (tileIndex !== undefined && tileIndex !== null) {
                return `${name} (牌索引: ${tileIndex})`;
            }
            return name;
        }
        
        // 格式化动作结果
        function formatActionResult(resultType, result) {
            if (resultType === 'won') {
                const playerId = result.player_id !== undefined ? result.player_id : '?';
                return `玩家${playerId} 胡牌！`;
            } else if (resultType === 'ponged') {
                return '碰牌成功';
            } else if (resultType === 'ganged') {
                return '杠牌成功';
            } else if (resultType === 'passed') {
                return '过';
            }
            return resultType;
        }
        
        // 获取数组维度
        function getArrayDimensions(arr) {
            if (!Array.isArray(arr)) {
                return '非数组';
            }
            let dims = [];
            let current = arr;
            while (Array.isArray(current) && current.length > 0) {
                dims.push(current.length);
                current = current[0];
            }
            return dims.length > 0 ? dims.join(' × ') : '空数组';
        }
        
        // 格式化动作
        function formatAction(actionIndex) {
            if (actionIndex < 108) {
                return `出牌 (索引: ${actionIndex})`;
            } else if (actionIndex < 216) {
                return `碰 (索引: ${actionIndex - 108})`;
            } else if (actionIndex < 324) {
                return `杠 (索引: ${actionIndex - 216})`;
            } else if (actionIndex < 432) {
                return `胡 (索引: ${actionIndex - 324})`;
            } else if (actionIndex === 432) {
                return '过';
            } else if (actionIndex === 433) {
                return '摸牌';
            }
            return `未知动作 (${actionIndex})`;
        }
        
        // 回放步骤控制
        function replayStep(delta) {
            if (!currentReplay || !currentReplay.trajectory) {
                return;
            }
            
            const newStep = currentReplayStep + delta;
            const maxStep = (currentReplay.trajectory.states || []).length - 1;
            
            if (newStep >= 0 && newStep <= maxStep) {
                renderReplayStep(newStep);
            }
        }
        
        // 播放/暂停回放
        function replayToggle() {
            if (!currentReplay || !currentReplay.trajectory) {
                return;
            }
            
            const maxStep = (currentReplay.trajectory.states || []).length - 1;
            
            if (isReplayPlaying) {
                // 暂停
                if (replayInterval) {
                    clearInterval(replayInterval);
                    replayInterval = null;
                }
                isReplayPlaying = false;
                document.getElementById('replay-play-btn').textContent = '▶ 播放';
                document.getElementById('replay-play-btn').style.background = '#43e97b';
            } else {
                // 播放
                if (currentReplayStep >= maxStep) {
                    currentReplayStep = 0; // 从头开始
                }
                isReplayPlaying = true;
                document.getElementById('replay-play-btn').textContent = '⏸ 暂停';
                document.getElementById('replay-play-btn').style.background = '#ff6b6b';
                
                replayInterval = setInterval(() => {
                    if (currentReplayStep < maxStep) {
                        replayStep(1);
                    } else {
                        replayToggle(); // 播放完毕，自动暂停
                    }
                }, 1000); // 每秒一步
            }
        }
        
        // 初始化
        connectSSE();
        
        // 定期获取最新状态（作为 SSE 的备用）
        setInterval(async () => {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateUI(data);
                
                // 如果历史图表可见，更新图表
                if (metricsHistoryVisible && metricsChart) {
                    loadMetricsHistory();
                }
                if (rewardHistoryVisible && rewardChart) {
                    loadRewardHistory();
                }
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


@app.route('/api/replays')
def get_replays():
    """获取游戏回放列表"""
    from flask import request
    state_manager = get_state_manager()
    
    # 获取查询参数
    limit = request.args.get('limit', type=int)
    iteration = request.args.get('iteration', type=int)
    
    replays = state_manager.get_game_replays(
        limit=limit,
        iteration=iteration,
    )
    
    # 简化返回数据（不包含完整的轨迹，只包含元信息）
    simplified_replays = []
    for replay in replays:
        simplified = {
            'game_id': replay.get('game_id'),
            'iteration': replay.get('iteration'),
            'game_index_in_iteration': replay.get('game_index_in_iteration'),
            'total_games_in_iteration': replay.get('total_games_in_iteration'),
            'timestamp': replay.get('timestamp'),
            'game_info': replay.get('game_info', {}),
            'num_steps': len(replay.get('trajectory', {}).get('states', [])) if 'trajectory' in replay else 0,
        }
        simplified_replays.append(simplified)
    
    return jsonify({
        'replays': simplified_replays,
        'count': len(simplified_replays),
    })


@app.route('/api/replays/<int:game_id>')
def get_replay(game_id: int):
    """获取单个游戏回放"""
    import numpy as np
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        state_manager = get_state_manager()
        replay = state_manager.get_game_replay(game_id)
        
        if replay is None:
            logger.warning(f"Game {game_id} not found in replay storage")
            return jsonify({'error': f'Game {game_id} not found'}), 404
        
        # 处理numpy数组的序列化
        def convert_numpy(obj):
            """递归转换numpy数组为列表"""
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj
        
        # 转换轨迹数据中的numpy数组
        if 'trajectory' in replay:
            try:
                replay = convert_numpy(replay)
            except Exception as e:
                logger.error(f"Error converting numpy arrays in replay {game_id}: {e}")
                return jsonify({'error': f'Failed to serialize replay data: {str(e)}'}), 500
        
        # 验证数据完整性
        if 'trajectory' not in replay:
            logger.error(f"Replay {game_id} missing trajectory data")
            return jsonify({'error': 'Invalid replay data: missing trajectory'}), 500
        
        trajectory = replay['trajectory']
        if 'states' not in trajectory or not trajectory['states']:
            logger.error(f"Replay {game_id} has empty or missing states")
            return jsonify({'error': 'Invalid replay data: empty states'}), 500
        
        logger.info(f"Successfully retrieved replay {game_id} with {len(trajectory.get('states', []))} steps")
        return jsonify(replay)
        
    except Exception as e:
        logger.error(f"Error retrieving replay {game_id}: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


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

