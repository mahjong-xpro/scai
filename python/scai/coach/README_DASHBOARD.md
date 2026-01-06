# 课程学习中心 Web 仪表板

## 功能概述

课程学习中心 Web 仪表板提供实时训练进度监控和课程学习状态可视化，帮助您：

- 📊 实时查看训练进度和迭代次数
- 🎯 监控当前训练阶段和阶段进度
- 📈 查看性能指标（胜率、听牌率、花猪率等）
- 🎁 查看当前阶段的奖励配置
- 🎯 查看阶段目标和评估标准

## 使用方法

### 1. 启用仪表板

在 `config.yaml` 中启用课程学习和仪表板：

```yaml
curriculum_learning:
  enabled: true
  dashboard:
    enabled: true
    host: 0.0.0.0
    port: 5000
```

### 2. 启动训练

运行训练脚本：

```bash
python train.py --config config.yaml
```

训练启动后，您会看到类似以下输出：

```
课程学习中心 Web 仪表板已启动: http://0.0.0.0:5000
```

### 3. 访问仪表板

在浏览器中打开：

```
http://localhost:5000
```

或者如果从远程访问：

```
http://<服务器IP>:5000
```

## 界面说明

### 状态栏

- **当前迭代**: 当前训练迭代次数
- **总迭代数**: 总计划迭代次数
- **训练进度**: 整体训练进度百分比
- **当前阶段**: 当前课程学习阶段名称

### 阶段进度卡片

显示当前阶段的详细信息：
- 阶段名称和描述
- 阶段进度条（基于迭代次数或评估标准）

### 性能指标卡片

实时显示关键性能指标：
- 胜率 (win_rate)
- 听牌率 (ready_rate)
- 花猪率 (flower_pig_rate)
- 平均番数 (average_fan)
- Elo 评分 (elo_score)
- 游戏局数 (games_played)

### 阶段目标卡片

列出当前阶段的学习目标，帮助理解 AI 正在学习什么。

### 奖励配置卡片

显示当前阶段的奖励函数配置，包括：
- 基础胡牌奖励
- 听牌奖励
- 向听数奖励
- 缺门弃牌奖励
- 点炮惩罚
- 等等

## 实时更新

仪表板使用 Server-Sent Events (SSE) 实现实时更新：

- 自动刷新训练状态
- 无需手动刷新页面
- 连接断开时自动重连

## 技术实现

### 架构

- **后端**: Flask Web 服务器
- **前端**: HTML + CSS + JavaScript
- **实时通信**: Server-Sent Events (SSE)
- **状态管理**: 线程安全的状态管理器

### 文件结构

```
python/scai/coach/
├── dashboard.py      # 状态管理器
├── web_server.py     # Web 服务器
└── README_DASHBOARD.md  # 本文档
```

### API 端点

- `GET /`: 主页面
- `GET /api/status`: 获取当前状态（REST API）
- `GET /api/stream`: Server-Sent Events 流式更新

## 自定义

### 修改端口

在 `config.yaml` 中修改：

```yaml
curriculum_learning:
  dashboard:
    port: 8080  # 改为您想要的端口
```

### 修改监听地址

```yaml
curriculum_learning:
  dashboard:
    host: 127.0.0.1  # 仅本地访问
    # 或
    host: 0.0.0.0    # 允许远程访问
```

## 故障排除

### 端口被占用

如果端口 5000 已被占用，修改 `config.yaml` 中的端口号。

### 无法访问

1. 检查防火墙设置
2. 确认 `host` 配置正确（`0.0.0.0` 允许远程访问）
3. 检查训练是否正在运行

### 数据不更新

1. 确认课程学习已启用（`curriculum_learning.enabled: true`）
2. 检查浏览器控制台是否有错误
3. 确认训练循环正在运行

## 注意事项

- 仪表板在后台线程运行，不会阻塞训练
- 如果训练停止，仪表板也会停止
- 建议在训练服务器上使用 `screen` 或 `tmux` 运行训练，以便远程访问

