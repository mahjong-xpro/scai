"""
使用 Gemini API 进行代码分析的示例

展示如何使用 Google Gemini API 来分析项目代码。
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scai.coach import LLMCoach, LLMCoachConfig


def analyze_code_with_gemini(code_path: str, question: str):
    """
    使用 Gemini 分析代码
    
    参数：
    - code_path: 代码文件路径
    - question: 要问的问题
    """
    # 配置 Gemini
    config = LLMCoachConfig(
        api_type='gemini',
        model_name='gemini-pro',  # 或 'gemini-pro-vision' 用于多模态
        api_key=os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY'),
        temperature=0.7,
        max_tokens=4000,  # Gemini 支持更大的上下文
    )
    
    coach = LLMCoach(config)
    
    # 读取代码文件
    try:
        with open(code_path, 'r', encoding='utf-8') as f:
            code_content = f.read()
    except FileNotFoundError:
        print(f"文件未找到: {code_path}")
        return
    
    # 构建分析提示词
    prompt = f"""请分析以下代码文件：

文件路径: {code_path}

代码内容：
```python
{code_content}
```

问题：{question}

请提供：
1. 代码结构和功能分析
2. 潜在的bug或问题
3. 性能优化建议
4. 代码质量评价
"""
    
    # 调用 Gemini 分析
    print(f"正在使用 Gemini 分析代码: {code_path}")
    print("=" * 60)
    
    response = coach._call_llm(prompt)
    
    print(response)
    print("=" * 60)


def analyze_project_structure(project_root: str):
    """
    分析整个项目结构
    
    参数：
    - project_root: 项目根目录
    """
    config = LLMCoachConfig(
        api_type='gemini',
        model_name='gemini-pro',
        api_key=os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY'),
    )
    
    coach = LLMCoach(config)
    
    # 收集项目信息
    import subprocess
    
    # 获取主要文件列表
    try:
        result = subprocess.run(
            ['find', project_root, '-name', '*.rs', '-o', '-name', '*.py'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        files = result.stdout.strip().split('\n')[:20]  # 限制前20个文件
    except:
        files = []
    
    # 构建项目分析提示词
    prompt = f"""请分析以下项目结构：

项目根目录: {project_root}

主要文件列表：
{chr(10).join(f'- {f}' for f in files if f)}

请提供：
1. 项目架构分析
2. 代码组织评价
3. 潜在的设计问题
4. 改进建议
"""
    
    print("正在使用 Gemini 分析项目结构...")
    print("=" * 60)
    
    response = coach._call_llm(prompt)
    
    print(response)
    print("=" * 60)


def main():
    """主函数"""
    # 检查API密钥
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("警告: 未设置 GOOGLE_API_KEY 或 GEMINI_API_KEY 环境变量")
        print("将返回模拟响应")
        print()
    
    # 示例1: 分析单个文件
    print("示例1: 分析单个代码文件")
    analyze_code_with_gemini(
        code_path='../scai/training/trainer.py',
        question='这个训练器的设计是否合理？有什么可以改进的地方？'
    )
    
    print("\n" * 2)
    
    # 示例2: 分析项目结构
    print("示例2: 分析项目结构")
    analyze_project_structure(project_root='../..')


if __name__ == '__main__':
    main()

