"""
Gemini 代码分析器

专门用于使用 Gemini API 分析项目代码的工具。
"""

import os
import subprocess
from typing import List, Dict, Optional
from pathlib import Path

from .llm_interface import LLMCoach, LLMCoachConfig


class GeminiCodeAnalyzer:
    """Gemini 代码分析器
    
    使用 Google Gemini API 分析项目代码，提供代码审查、bug检测、性能优化建议等。
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = 'gemini-pro',
        temperature: float = 0.3,  # 代码分析使用较低温度，更确定性
    ):
        """
        参数：
        - api_key: Google API 密钥（如果为None，从环境变量读取）
        - model_name: Gemini 模型名称（默认 'gemini-pro'）
        - temperature: 温度参数（默认 0.3，代码分析需要更确定性）
        """
        config = LLMCoachConfig(
            api_type='gemini',
            model_name=model_name,
            api_key=api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY'),
            temperature=temperature,
            max_tokens=8000,  # Gemini 支持更大的上下文
        )
        
        self.coach = LLMCoach(config)
        self.model_name = model_name
    
    def analyze_file(
        self,
        file_path: str,
        focus_areas: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        分析单个代码文件
        
        参数：
        - file_path: 文件路径
        - focus_areas: 重点关注领域（如 ['bug', 'performance', 'design']）
        
        返回：
        - 分析结果字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
        except Exception as e:
            return {
                'error': f"无法读取文件: {str(e)}",
                'file_path': file_path,
            }
        
        # 确定文件类型
        file_ext = Path(file_path).suffix
        language = {
            '.rs': 'Rust',
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.cpp': 'C++',
            '.c': 'C',
        }.get(file_ext, 'Unknown')
        
        # 构建分析提示词
        focus_text = ""
        if focus_areas:
            focus_text = f"\n重点关注：{', '.join(focus_areas)}"
        
        prompt = f"""请详细分析以下{language}代码文件：

文件路径: {file_path}
文件类型: {language}

代码内容：
```{language.lower()}
{code_content}
```

{focus_text}

请从以下角度进行全面分析：
1. **代码结构和功能**：代码的主要功能是什么？结构是否清晰？
2. **潜在Bug**：是否存在逻辑错误、边界条件处理不当、空指针等问题？
3. **性能问题**：是否有性能瓶颈？可以如何优化？
4. **代码质量**：代码风格、可读性、可维护性如何？
5. **安全性**：是否存在安全漏洞？
6. **最佳实践**：是否符合该语言的最佳实践？

请提供详细、具体的分析结果，包括：
- 发现的问题（如果有）
- 改进建议
- 代码质量评分（0-100分）
"""
        
        # 调用 Gemini
        response = self.coach._call_llm(prompt)
        
        return {
            'file_path': file_path,
            'language': language,
            'analysis': response,
            'model': self.model_name,
        }
    
    def analyze_project(
        self,
        project_root: str,
        file_patterns: Optional[List[str]] = None,
        max_files: int = 50,
    ) -> Dict[str, any]:
        """
        分析整个项目
        
        参数：
        - project_root: 项目根目录
        - file_patterns: 文件模式列表（如 ['*.rs', '*.py']）
        - max_files: 最大分析文件数
        
        返回：
        - 项目分析结果
        """
        if file_patterns is None:
            file_patterns = ['*.rs', '*.py']
        
        # 收集文件
        files = []
        for pattern in file_patterns:
            for file_path in Path(project_root).rglob(pattern):
                if file_path.is_file():
                    files.append(str(file_path))
                    if len(files) >= max_files:
                        break
            if len(files) >= max_files:
                break
        
        # 获取项目统计信息
        stats = self._get_project_stats(project_root, files)
        
        # 构建项目分析提示词
        prompt = f"""请分析以下项目的整体架构和代码质量：

项目根目录: {project_root}

项目统计：
- 总文件数: {stats['total_files']}
- Rust文件: {stats['rust_files']}
- Python文件: {stats['python_files']}
- 总代码行数: {stats['total_lines']} (估算)

主要文件列表（前20个）：
{chr(10).join(f'- {f}' for f in files[:20])}

请从以下角度分析：
1. **项目架构**：整体架构设计是否合理？模块划分是否清晰？
2. **代码组织**：代码组织是否符合最佳实践？
3. **潜在问题**：是否存在架构层面的问题？
4. **改进建议**：如何改进项目结构和代码质量？
5. **技术债务**：是否存在技术债务？如何解决？

请提供全面的项目分析报告。
"""
        
        response = self.coach._call_llm(prompt)
        
        return {
            'project_root': project_root,
            'stats': stats,
            'files_analyzed': len(files),
            'analysis': response,
            'model': self.model_name,
        }
    
    def compare_files(
        self,
        file1_path: str,
        file2_path: str,
        question: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        比较两个代码文件
        
        参数：
        - file1_path: 第一个文件路径
        - file2_path: 第二个文件路径
        - question: 要问的具体问题（可选）
        
        返回：
        - 比较结果
        """
        try:
            with open(file1_path, 'r', encoding='utf-8') as f:
                code1 = f.read()
            with open(file2_path, 'r', encoding='utf-8') as f:
                code2 = f.read()
        except Exception as e:
            return {'error': f"无法读取文件: {str(e)}"}
        
        question_text = question or "请比较这两个文件的差异、优缺点和改进建议"
        
        prompt = f"""请比较以下两个代码文件：

文件1: {file1_path}
```python
{code1}
```

文件2: {file2_path}
```python
{code2}
```

问题：{question_text}

请提供：
1. 两个文件的主要差异
2. 各自的优缺点
3. 哪个设计更好？为什么？
4. 如何改进？
"""
        
        response = self.coach._call_llm(prompt)
        
        return {
            'file1': file1_path,
            'file2': file2_path,
            'comparison': response,
            'model': self.model_name,
        }
    
    def find_bugs(
        self,
        file_path: str,
        context: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        专门查找代码中的bug
        
        参数：
        - file_path: 文件路径
        - context: 额外的上下文信息（如错误日志、测试失败信息）
        
        返回：
        - Bug分析结果
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
        except Exception as e:
            return {'error': f"无法读取文件: {str(e)}"}
        
        context_text = f"\n额外上下文：\n{context}" if context else ""
        
        prompt = f"""请仔细检查以下代码，查找所有潜在的bug：

文件路径: {file_path}

代码内容：
```python
{code_content}
```

{context_text}

请重点检查：
1. **逻辑错误**：条件判断、循环逻辑是否正确？
2. **边界条件**：是否处理了边界情况（空值、负数、溢出等）？
3. **资源泄漏**：是否有内存泄漏、文件未关闭等问题？
4. **并发问题**：是否存在竞态条件、死锁等？
5. **类型错误**：类型使用是否正确？
6. **异常处理**：异常处理是否完善？

对于每个发现的bug，请提供：
- Bug描述
- 可能的影响
- 修复建议
- 严重程度（高/中/低）
"""
        
        response = self.coach._call_llm(prompt)
        
        return {
            'file_path': file_path,
            'bug_analysis': response,
            'model': self.model_name,
        }
    
    def suggest_optimizations(
        self,
        file_path: str,
        optimization_type: str = 'performance',
    ) -> Dict[str, str]:
        """
        提供代码优化建议
        
        参数：
        - file_path: 文件路径
        - optimization_type: 优化类型（'performance', 'readability', 'maintainability'）
        
        返回：
        - 优化建议
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
        except Exception as e:
            return {'error': f"无法读取文件: {str(e)}"}
        
        optimization_focus = {
            'performance': '性能优化（算法复杂度、内存使用、I/O操作等）',
            'readability': '可读性优化（代码风格、命名、注释等）',
            'maintainability': '可维护性优化（模块化、解耦、测试等）',
        }.get(optimization_type, '综合优化')
        
        prompt = f"""请分析以下代码，提供{optimization_focus}建议：

文件路径: {file_path}

代码内容：
```python
{code_content}
```

请提供：
1. 当前代码的问题点
2. 具体的优化建议（包括代码示例）
3. 优化后的预期效果
4. 实施难度评估
"""
        
        response = self.coach._call_llm(prompt)
        
        return {
            'file_path': file_path,
            'optimization_type': optimization_type,
            'suggestions': response,
            'model': self.model_name,
        }
    
    def _get_project_stats(self, project_root: str, files: List[str]) -> Dict[str, int]:
        """获取项目统计信息"""
        stats = {
            'total_files': len(files),
            'rust_files': len([f for f in files if f.endswith('.rs')]),
            'python_files': len([f for f in files if f.endswith('.py')]),
            'total_lines': 0,
        }
        
        # 估算总行数（只统计前10个文件）
        for file_path in files[:10]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    stats['total_lines'] += len(f.readlines())
            except:
                pass
        
        # 估算总行数（基于样本）
        if stats['total_files'] > 0:
            avg_lines = stats['total_lines'] / min(10, stats['total_files'])
            stats['total_lines'] = int(avg_lines * stats['total_files'])
        
        return stats


def analyze_current_project():
    """分析当前项目（SCAI项目）"""
    project_root = os.path.join(os.path.dirname(__file__), '../../..')
    
    analyzer = GeminiCodeAnalyzer()
    
    print("=" * 60)
    print("使用 Gemini 分析 SCAI 项目")
    print("=" * 60)
    print()
    
    # 分析项目整体
    print("1. 项目整体分析")
    print("-" * 60)
    project_analysis = analyzer.analyze_project(project_root, max_files=30)
    print(project_analysis['analysis'])
    print()
    
    # 分析关键文件
    key_files = [
        'rust/src/game/game_engine.rs',
        'rust/src/game/state.rs',
        'python/scai/training/trainer.py',
        'python/scai/coach/llm_interface.py',
    ]
    
    for file_path in key_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            print(f"2. 分析关键文件: {file_path}")
            print("-" * 60)
            analysis = analyzer.analyze_file(full_path, focus_areas=['bug', 'design'])
            print(analysis['analysis'])
            print()


if __name__ == '__main__':
    analyze_current_project()

