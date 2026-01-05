"""
大模型监督接口 (LLM Coach Interface)

调用大模型API进行策略分析、奖励函数评价和课程学习规划。
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os


@dataclass
class LLMCoachConfig:
    """大模型教练配置"""
    # API类型：'openai', 'anthropic', 'custom'
    api_type: str = 'openai'
    # API密钥（从环境变量读取）
    api_key: Optional[str] = None
    # 模型名称
    model_name: str = 'gpt-4'
    # API基础URL（用于自定义API）
    base_url: Optional[str] = None
    # 温度参数
    temperature: float = 0.7
    # 最大token数
    max_tokens: int = 2000
    
    def __post_init__(self):
        """初始化后处理"""
        if self.api_key is None:
            # 从环境变量读取
            if self.api_type == 'openai':
                self.api_key = os.getenv('OPENAI_API_KEY')
            elif self.api_type == 'anthropic':
                self.api_key = os.getenv('ANTHROPIC_API_KEY')


class LLMCoach:
    """大模型教练
    
    使用大模型分析AI的训练表现，提供策略建议。
    """
    
    # 系统提示词
    SYSTEM_PROMPT = """你是一位四川麻将血战到底的大师。请分析以下 AI 的操作序列。

你的任务是：
1. 识别AI的策略缺陷和逻辑错误
2. 评估AI是否陷入"局部最优"或"规则漏洞"
3. 提供具体的改进建议

分析重点：
- 为什么AI在已经听大牌的情况下不选择过胡博自摸？
- 为什么AI在三家缺一门的情况下依然选择冒险打出该门牌？
- AI的决策是否符合"最大化期望收益"或"防御点炮"逻辑？

请用专业、简洁的语言指出问题，并提供可操作的建议。"""
    
    def __init__(self, config: Optional[LLMCoachConfig] = None):
        """
        参数：
        - config: 大模型配置（如果为None，使用默认配置）
        """
        self.config = config or LLMCoachConfig()
        self._client = None
    
    def analyze_strategy(
        self,
        game_logs: List[Dict[str, Any]],
        focus_anomalies: bool = True,
    ) -> Dict[str, Any]:
        """
        策略合理性审计
        
        参数：
        - game_logs: 游戏日志列表（每局游戏的决策序列）
        - focus_anomalies: 是否重点关注异常决策
        
        返回：
        - 分析结果字典，包含：
          - issues: 发现的问题列表
          - suggestions: 改进建议列表
          - score: 策略评分（0-100）
        """
        # 准备提示词
        prompt = self._build_strategy_analysis_prompt(game_logs, focus_anomalies)
        
        # 调用大模型
        response = self._call_llm(prompt)
        
        # 解析响应
        analysis = self._parse_analysis_response(response)
        
        return analysis
    
    def evaluate_reward_function(
        self,
        reward_config: Dict[str, Any],
        loss_curve: List[float],
        elo_scores: List[float],
        behavior_issues: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        奖励函数评价
        
        参数：
        - reward_config: 当前奖励函数配置
        - loss_curve: 损失曲线数据
        - elo_scores: Elo分数历史
        - behavior_issues: 行为问题描述（如"过度保守"、"不敢博清一色"）
        
        返回：
        - 评价结果字典，包含：
          - current_issues: 当前奖励函数的问题
          - suggested_changes: 建议的调整
          - new_config: 建议的新配置
        """
        prompt = self._build_reward_evaluation_prompt(
            reward_config,
            loss_curve,
            elo_scores,
            behavior_issues,
        )
        
        response = self._call_llm(prompt)
        evaluation = self._parse_evaluation_response(response)
        
        return evaluation
    
    def design_curriculum(
        self,
        current_stage: str,
        performance_metrics: Dict[str, float],
        issues: List[str],
    ) -> Dict[str, Any]:
        """
        课程学习规划
        
        参数：
        - current_stage: 当前训练阶段
        - performance_metrics: 性能指标（如胜率、平均得分等）
        - issues: 当前阶段的问题列表
        
        返回：
        - 课程规划字典，包含：
          - next_stage: 下一阶段名称
          - training_objectives: 训练目标
          - curriculum_steps: 课程步骤列表
        """
        prompt = self._build_curriculum_prompt(
            current_stage,
            performance_metrics,
            issues,
        )
        
        response = self._call_llm(prompt)
        curriculum = self._parse_curriculum_response(response)
        
        return curriculum
    
    def _build_strategy_analysis_prompt(
        self,
        game_logs: List[Dict[str, Any]],
        focus_anomalies: bool,
    ) -> str:
        """构建策略分析提示词"""
        prompt = f"""请分析以下AI的对局决策序列：

{focus_anomalies and "（重点关注异常决策）" or ""}

游戏日志：
{json.dumps(game_logs, ensure_ascii=False, indent=2)}

请从以下角度分析：
1. 策略合理性：AI的决策是否符合麻将策略？
2. 风险控制：AI是否过度保守或过度冒险？
3. 机会把握：AI是否错过了高价值机会？
4. 规则理解：AI是否正确理解了游戏规则？

请提供：
- 发现的主要问题（3-5个）
- 具体的改进建议
- 策略评分（0-100分）"""
        
        return prompt
    
    def _build_reward_evaluation_prompt(
        self,
        reward_config: Dict[str, Any],
        loss_curve: List[float],
        elo_scores: List[float],
        behavior_issues: Optional[List[str]],
    ) -> str:
        """构建奖励函数评价提示词"""
        prompt = f"""请评价当前的奖励函数配置：

当前配置：
{json.dumps(reward_config, ensure_ascii=False, indent=2)}

训练数据：
- 损失曲线趋势：{self._describe_trend(loss_curve)}
- Elo分数趋势：{self._describe_trend(elo_scores)}
{f"- 行为问题：{', '.join(behavior_issues)}" if behavior_issues else ""}

请分析：
1. 当前奖励机制是否存在问题？
2. 是否过度惩罚了点炮，导致AI不敢博清一色？
3. 是否需要调整Entropy Loss或Reward Scale？

请提供：
- 问题诊断
- 调整建议
- 建议的新配置参数"""
        
        return prompt
    
    def _build_curriculum_prompt(
        self,
        current_stage: str,
        performance_metrics: Dict[str, float],
        issues: List[str],
    ) -> str:
        """构建课程学习规划提示词"""
        prompt = f"""请设计下一阶段的训练课程：

当前阶段：{current_stage}

性能指标：
{json.dumps(performance_metrics, ensure_ascii=False, indent=2)}

当前问题：
{chr(10).join(f"- {issue}" for issue in issues)}

请设计：
1. 下一阶段的训练目标
2. 分阶段的课程步骤（例如：第一阶段学定缺和基本胡牌，第二阶段引入避炮策略）
3. 每个阶段的评估标准

请提供详细的课程规划。"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """
        调用大模型API
        
        参数：
        - prompt: 提示词
        
        返回：
        - 模型响应文本
        """
        if self.config.api_type == 'openai':
            return self._call_openai(prompt)
        elif self.config.api_type == 'anthropic':
            return self._call_anthropic(prompt)
        elif self.config.api_type == 'custom':
            return self._call_custom(prompt)
        else:
            raise ValueError(f"Unsupported API type: {self.config.api_type}")
    
    def _call_openai(self, prompt: str) -> str:
        """调用OpenAI API"""
        try:
            # 尝试使用新版本 openai (>=1.0.0)
            try:
                from openai import OpenAI
                
                if self._client is None:
                    self._client = OpenAI(api_key=self.config.api_key)
                
                response = self._client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                
                return response.choices[0].message.content
            except (ImportError, AttributeError):
                # 回退到旧版本 openai (<1.0.0)
                import openai
                
                if self._client is None:
                    openai.api_key = self.config.api_key
                    self._client = openai
                
                response = openai.ChatCompletion.create(
                    model=self.config.model_name,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                
                return response.choices[0].message.content
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
        except Exception as e:
            # 如果API调用失败，返回模拟响应
            return f"[模拟响应] 由于API调用失败（{str(e)}），返回模拟分析结果。请配置正确的API密钥。"
    
    def _call_anthropic(self, prompt: str) -> str:
        """调用Anthropic API"""
        try:
            import anthropic
            
            if self._client is None:
                self._client = anthropic.Anthropic(api_key=self.config.api_key)
            
            response = self._client.messages.create(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")
        except Exception as e:
            return f"[模拟响应] 由于API调用失败（{str(e)}），返回模拟分析结果。请配置正确的API密钥。"
    
    def _call_custom(self, prompt: str) -> str:
        """调用自定义API"""
        # 这里可以实现自定义API调用逻辑
        # 例如：使用requests库调用自定义的API端点
        return "[模拟响应] 自定义API调用未实现，请实现 _call_custom 方法。"
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """解析策略分析响应"""
        # 简单解析：尝试提取JSON或结构化文本
        # 实际应用中可以使用更复杂的解析逻辑
        
        return {
            'raw_response': response,
            'issues': self._extract_list_items(response, '问题', 'issues'),
            'suggestions': self._extract_list_items(response, '建议', 'suggestions'),
            'score': self._extract_score(response),
        }
    
    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """解析奖励函数评价响应"""
        return {
            'raw_response': response,
            'current_issues': self._extract_list_items(response, '问题', 'issues'),
            'suggested_changes': self._extract_list_items(response, '调整', 'changes'),
            'new_config': self._extract_config(response),
        }
    
    def _parse_curriculum_response(self, response: str) -> Dict[str, Any]:
        """解析课程学习规划响应"""
        return {
            'raw_response': response,
            'next_stage': self._extract_stage_name(response),
            'training_objectives': self._extract_list_items(response, '目标', 'objectives'),
            'curriculum_steps': self._extract_curriculum_steps(response),
        }
    
    def _extract_list_items(self, text: str, keyword: str, fallback: str) -> List[str]:
        """从文本中提取列表项"""
        # 简单实现：查找包含关键字的行
        items = []
        lines = text.split('\n')
        for line in lines:
            if keyword in line or fallback in line.lower():
                # 尝试提取列表项
                if line.strip().startswith(('-', '*', '1.', '2.', '3.')):
                    items.append(line.strip())
        return items if items else [f"未找到{keyword}，请查看原始响应"]
    
    def _extract_score(self, text: str) -> Optional[float]:
        """从文本中提取评分"""
        import re
        # 查找数字（0-100）
        match = re.search(r'(\d+(?:\.\d+)?)\s*分', text)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_config(self, text: str) -> Dict[str, Any]:
        """从文本中提取配置参数"""
        # 简单实现：查找JSON格式的配置
        import re
        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return {}
    
    def _extract_stage_name(self, text: str) -> str:
        """从文本中提取阶段名称"""
        # 查找"阶段"、"Stage"等关键字
        import re
        match = re.search(r'阶段[：:]\s*([^\n]+)', text)
        if match:
            return match.group(1).strip()
        return "未知阶段"
    
    def _extract_curriculum_steps(self, text: str) -> List[Dict[str, str]]:
        """从文本中提取课程步骤"""
        steps = []
        lines = text.split('\n')
        current_step = None
        
        for line in lines:
            if '阶段' in line or 'Step' in line:
                if current_step:
                    steps.append(current_step)
                current_step = {'name': line.strip(), 'description': ''}
            elif current_step:
                current_step['description'] += line + '\n'
        
        if current_step:
            steps.append(current_step)
        
        return steps if steps else [{'name': '未找到课程步骤', 'description': '请查看原始响应'}]
    
    def _describe_trend(self, values: List[float]) -> str:
        """描述数值趋势"""
        if len(values) < 2:
            return "数据不足"
        
        recent = values[-10:] if len(values) > 10 else values
        if recent[-1] > recent[0]:
            return "上升趋势"
        elif recent[-1] < recent[0]:
            return "下降趋势"
        else:
            return "平稳"

