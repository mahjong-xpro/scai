# 仪表板历史记录功能

## 功能说明

为了解决"性能指标和奖励配置一直在变化，不方便查看"的问题，已添加历史记录功能。

## 新增功能

### 1. 历史数据存储

- **自动保存**：每次状态更新时自动保存历史记录
- **容量限制**：最多保存1000条历史记录（可配置）
- **按迭代过滤**：支持按迭代次数范围查询历史记录

### 2. 历史趋势可视化

- **性能指标趋势图**：显示各项指标随时间的变化趋势
- **奖励配置趋势图**：显示奖励配置随时间的变化
- **交互式图表**：使用 Chart.js 绘制，支持缩放和悬停查看

### 3. 新增API端点

- `GET /api/history`：获取历史记录
  - 参数：
    - `limit`：最多返回的记录数
    - `start_iteration`：起始迭代次数
    - `end_iteration`：结束迭代次数
- `GET /api/history/summary`：获取历史记录摘要

## 使用方法

### 查看性能指标历史趋势

1. 在Web界面中，找到"📈 性能指标"卡片
2. 点击"查看历史趋势"按钮
3. 图表会显示各项指标的历史变化趋势
4. 可以悬停在数据点上查看具体数值

### 查看奖励配置历史变化

1. 在Web界面中，找到"🎁 奖励配置"卡片
2. 点击"查看历史变化"按钮
3. 图表会显示各项奖励配置的历史变化
4. 可以悬停在数据点上查看具体数值

## 技术实现

### 后端（dashboard.py）

```python
class DashboardStateManager:
    def __init__(self, max_history: int = 1000):
        self._history: List[Dict[str, Any]] = []  # 历史记录列表
        self._max_history = max_history
    
    def update_status(...):
        # 保存历史记录
        status_dict = asdict(self._status)
        self._history.append(status_dict.copy())
        
        # 限制历史记录数量
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_history(...):
        # 获取历史记录，支持过滤
        ...
```

### 前端（web_server.py）

- 使用 Chart.js 绘制趋势图
- 通过 `/api/history` 获取历史数据
- 实时更新图表（每5秒）

## 配置

历史记录容量可以通过修改 `DashboardStateManager` 的 `max_history` 参数调整：

```python
# 在 dashboard.py 中
_state_manager = DashboardStateManager(max_history=2000)  # 保存2000条记录
```

## 注意事项

1. **内存使用**：历史记录保存在内存中，如果记录过多可能占用较多内存
2. **数据持久化**：当前实现不持久化历史记录，重启训练后历史记录会丢失
3. **性能影响**：历史记录功能对性能影响很小，但建议不要设置过大的 `max_history`

## 未来改进

1. **数据持久化**：将历史记录保存到文件或数据库
2. **更多图表类型**：添加柱状图、散点图等
3. **数据导出**：支持导出历史数据为CSV或JSON
4. **自定义时间范围**：允许用户选择查看特定时间范围的历史数据

