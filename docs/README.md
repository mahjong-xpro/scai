# 项目文档索引

## 📚 文档结构

```
docs/
├── README.md                    # 本文档（文档索引）
├── setup/                       # 环境配置文档
│   └── GPU_CONFIGURATION.md     # GPU 配置指南
├── architecture/                # 架构相关文档
│   ├── ARCHITECTURE_SUMMARY.md  # 架构完整性总结
│   ├── TRAINING_READINESS.md    # 训练就绪性分析
│   └── ...
├── training/                    # 训练相关文档
│   ├── TRAINING_GUIDE.md        # 训练完整指南
│   ├── CURRICULUM_LEARNING.md   # 课程学习指南
│   ├── CHECKPOINT.md            # 检查点管理
│   ├── EVALUATION.md            # 模型评估
│   └── LOGGING.md               # 日志系统
├── features/                    # 功能特性文档
│   ├── FEEDING_GAMES.md         # 喂牌机制
│   ├── SHANTEN_FEATURE.md       # 向听数特征
│   ├── OPPONENT_POOL.md         # 对手池系统
│   └── DATA_VALIDATION.md       # 数据验证
└── history/                     # 历史文档（归档）
    ├── COMPREHENSIVE_CODE_REVIEW.md
    ├── DEEP_ANALYSIS.md
    └── ...
```

---

## 🚀 快速开始

### 新用户入门

1. **[GPU 配置](./setup/GPU_CONFIGURATION.md)** - GPU 环境配置（多 GPU 服务器）
2. **[训练指南](./training/TRAINING_GUIDE.md)** - 完整的训练流程和配置说明
3. **[课程学习](./training/CURRICULUM_LEARNING.md)** - 分阶段训练策略
4. **[检查点管理](./training/CHECKPOINT.md)** - 模型保存和恢复

### 开发者文档

1. **[架构总结](./architecture/ARCHITECTURE_SUMMARY.md)** - 系统架构概览
2. **[训练就绪性](./architecture/TRAINING_READINESS.md)** - 系统完整性检查
3. **[功能特性](./features/)** - 各功能模块详细说明

---

## 📖 文档分类

### 架构文档 (`architecture/`)

- **ARCHITECTURE_SUMMARY.md** - 架构完整性总结，系统组件概览
- **TRAINING_READINESS.md** - 训练就绪性分析，系统完整性检查

### 训练文档 (`training/`)

- **TRAINING_GUIDE.md** - 训练完整指南，从环境准备到高级配置
- **CURRICULUM_LEARNING.md** - 课程学习完整指南，包括阶段详解和喂牌机制
- **CHECKPOINT.md** - 检查点管理，模型保存和恢复
- **EVALUATION.md** - 模型评估，Elo评分和性能指标
- **LOGGING.md** - 日志系统，结构化日志和监控

### 功能特性文档 (`features/`)

- **FEEDING_GAMES.md** - 喂牌机制实现和使用
- **SHANTEN_FEATURE.md** - 向听数特征说明
- **OPPONENT_POOL.md** - 对手池系统
- **DATA_VALIDATION.md** - 数据验证器

### 历史文档 (`history/`)

历史分析和审查文档，已归档但保留供参考。

---

## 🔍 按主题查找

### 训练相关

- [训练指南](./training/TRAINING_GUIDE.md) - 完整训练流程
- [课程学习](./training/CURRICULUM_LEARNING.md) - 分阶段训练
- [检查点管理](./training/CHECKPOINT.md) - 模型保存
- [模型评估](./training/EVALUATION.md) - 性能评估

### 功能特性

- [喂牌机制](./features/FEEDING_GAMES.md) - 辅助训练机制
- [向听数特征](./features/SHANTEN_FEATURE.md) - 手牌质量特征
- [对手池](./features/OPPONENT_POOL.md) - 历史模型管理
- [数据验证](./features/DATA_VALIDATION.md) - 数据质量保证

### 系统架构

- [架构总结](./architecture/ARCHITECTURE_SUMMARY.md) - 系统概览
- [训练就绪性](./architecture/TRAINING_READINESS.md) - 完整性检查

---

## 📝 文档维护

### 文档更新原则

1. **保持最新**: 代码变更时同步更新文档
2. **结构清晰**: 使用统一的文档结构
3. **示例完整**: 提供可运行的代码示例
4. **链接有效**: 确保文档间链接正确

### 添加新文档

1. 根据主题选择合适目录
2. 遵循现有文档格式
3. 更新本文档索引
4. 添加必要的交叉引用

---

## 🔗 外部资源

- [项目主 README](../README.md)
- [Rust 引擎文档](../rust/README.md)
- [Python 训练框架](../python/README.md)

---

## 📧 反馈

如有文档问题或建议，请提交 Issue 或 Pull Request。

