# Gemini 代码分析功能

已为项目添加 Google Gemini API 支持，可以使用 Gemini 来分析现有项目代码。

## 功能特性

### 1. 基础支持

- ✅ 在 `LLMCoach` 中添加了 Gemini API 支持
- ✅ 支持 `gemini-pro` 和 `gemini-pro-vision` 模型
- ✅ 自动从环境变量读取 API 密钥

### 2. 专用代码分析器

**文件**: `python/scai/coach/gemini_code_analyzer.py`

提供了 `GeminiCodeAnalyzer` 类，专门用于代码分析：

- **分析单个文件**: 全面分析代码结构、bug、性能、质量等
- **分析整个项目**: 项目架构、代码组织、技术债务等
- **比较文件**: 比较两个文件的差异和优缺点
- **查找Bug**: 专门查找代码中的潜在bug
- **优化建议**: 提供性能、可读性、可维护性优化建议

## 使用方法

### 方法1: 使用 GeminiCodeAnalyzer

```python
from scai.coach import GeminiCodeAnalyzer

# 初始化分析器
analyzer = GeminiCodeAnalyzer(
    api_key=os.getenv('GOOGLE_API_KEY'),
    model_name='gemini-pro',
    temperature=0.3,  # 代码分析使用较低温度
)

# 分析单个文件
result = analyzer.analyze_file(
    file_path='rust/src/game/game_engine.rs',
    focus_areas=['bug', 'performance', 'design'],
)
print(result['analysis'])

# 分析整个项目
project_result = analyzer.analyze_project(
    project_root='.',
    file_patterns=['*.rs', '*.py'],
    max_files=50,
)

# 查找bug
bug_result = analyzer.find_bugs(
    file_path='rust/src/game/state.rs',
    context='测试失败：fill_unknown_cards 导致牌数不守恒',
)

# 优化建议
opt_result = analyzer.suggest_optimizations(
    file_path='python/scai/training/trainer.py',
    optimization_type='performance',
)
```

### 方法2: 使用 LLMCoach（通用接口）

```python
from scai.coach import LLMCoach, LLMCoachConfig

# 配置 Gemini
config = LLMCoachConfig(
    api_type='gemini',
    model_name='gemini-pro',
    api_key=os.getenv('GOOGLE_API_KEY'),
    temperature=0.7,
    max_tokens=8000,  # Gemini 支持更大的上下文
)

coach = LLMCoach(config)

# 分析代码
code_content = open('file.rs').read()
prompt = f"请分析以下代码：\n```rust\n{code_content}\n```"

analysis = coach._call_llm(prompt)
print(analysis)
```

## 环境变量

设置 Google API 密钥：

```bash
export GOOGLE_API_KEY="your-api-key"
# 或
export GEMINI_API_KEY="your-api-key"
```

获取 API 密钥：
1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 创建 API 密钥
3. 设置环境变量

## 示例脚本

### 示例1: 分析当前项目

运行 `python/scai/coach/gemini_code_analyzer.py`:

```bash
cd python
python -m scai.coach.gemini_code_analyzer
```

这会分析整个 SCAI 项目，包括：
- 项目整体架构
- 关键文件分析（game_engine.rs, state.rs, trainer.py等）

### 示例2: 使用示例脚本

运行 `python/examples/gemini_coach_example.py`:

```bash
cd python
python examples/gemini_coach_example.py
```

## 支持的模型

- `gemini-pro`: 标准 Gemini Pro 模型（推荐用于代码分析）
- `gemini-pro-vision`: 支持多模态的 Gemini Pro Vision（可用于分析代码截图）

## 优势

相比其他大模型，Gemini 在代码分析方面的优势：

1. **更大的上下文窗口**: 支持更大的代码文件分析
2. **免费额度**: Google 提供更慷慨的免费使用额度
3. **代码理解能力强**: 对代码结构和逻辑的理解较好
4. **多语言支持**: 支持多种编程语言的分析

## 注意事项

1. **API密钥**: 需要配置 `GOOGLE_API_KEY` 或 `GEMINI_API_KEY` 环境变量
2. **依赖安装**: 需要安装 `google-generativeai` 包
   ```bash
   pip install google-generativeai>=0.3.0
   ```
3. **温度参数**: 代码分析建议使用较低温度（0.3-0.5），以获得更确定性的结果
4. **上下文限制**: 虽然 Gemini 支持更大的上下文，但仍需注意单个文件不要过大

## 集成到训练流程

可以将 Gemini 代码分析集成到 CI/CD 流程中：

```python
# 在训练前分析代码
analyzer = GeminiCodeAnalyzer()
analysis = analyzer.analyze_file('rust/src/game/game_engine.rs')

# 如果发现严重问题，可以中断训练
if '严重bug' in analysis['analysis']:
    print("发现严重问题，请先修复代码")
    sys.exit(1)
```

## 与现有系统的集成

Gemini 代码分析器可以无缝集成到现有的 `LLMCoach` 系统中：

```python
from scai.coach import LLMCoach, LLMCoachConfig, GeminiCodeAnalyzer

# 使用 Gemini 进行代码分析
code_analyzer = GeminiCodeAnalyzer()

# 使用 Gemini 进行训练监督（通过 LLMCoach）
coach = LLMCoach(LLMCoachConfig(api_type='gemini', model_name='gemini-pro'))
```

两者可以配合使用，实现全面的代码分析和训练监督。

