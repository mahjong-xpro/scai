#!/usr/bin/env python3
"""
课程学习使用示例

演示如何在训练中使用课程学习功能。
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scai.coach import (
    CurriculumLearning,
    TrainingDocumentGenerator,
    TrainingStage,
)


def example_basic_usage():
    """示例 1: 基础使用"""
    print("=" * 60)
    print("示例 1: 基础使用")
    print("=" * 60)
    
    # 创建文档生成器
    document_generator = TrainingDocumentGenerator(output_dir='./coach_documents')
    
    # 创建课程学习规划器
    curriculum = CurriculumLearning(document_generator=document_generator)
    
    # 获取当前课程
    current = curriculum.get_current_curriculum()
    print(f"\n当前阶段: {current.name}")
    print(f"课程描述: {current.description}")
    print(f"\n训练目标:")
    for i, obj in enumerate(current.objectives, 1):
        print(f"  {i}. {obj}")
    
    print(f"\n评估标准:")
    for criterion, threshold in current.evaluation_criteria.items():
        print(f"  - {criterion}: ≥ {threshold}")
    
    print(f"\n预计迭代次数: {current.estimated_iterations}")


def example_check_advancement():
    """示例 2: 检查是否应该进入下一阶段"""
    print("\n" + "=" * 60)
    print("示例 2: 检查阶段推进")
    print("=" * 60)
    
    curriculum = CurriculumLearning()
    
    # 模拟性能指标
    performance_metrics = {
        'win_rate': 0.35,          # 胜率 35%
        'flower_pig_rate': 0.03,   # 花猪率 3%
    }
    
    # 获取当前阶段的评估标准
    current = curriculum.get_current_curriculum()
    print(f"\n当前阶段: {current.name}")
    print(f"\n性能指标检查:")
    
    # 检查每个标准
    all_met = True
    for criterion, threshold in current.evaluation_criteria.items():
        value = performance_metrics.get(criterion, 0)
        met = value >= threshold if criterion != 'flower_pig_rate' else value <= threshold
        status = "✓ 满足" if met else "✗ 未满足"
        print(f"  {status} {criterion}: {value} (需要: {'≤' if criterion == 'flower_pig_rate' else '≥'} {threshold})")
        if not met:
            all_met = False
    
    # 判断是否应该进入下一阶段
    if curriculum.should_advance_stage(performance_metrics):
        print(f"\n✓ 满足所有条件，可以进入下一阶段！")
        curriculum.advance_to_next_stage()
        print(f"新阶段: {curriculum.current_stage.value}")
    else:
        print(f"\n✗ 尚未满足所有条件，继续当前阶段训练")


def example_generate_document():
    """示例 3: 生成课程规划文档"""
    print("\n" + "=" * 60)
    print("示例 3: 生成课程规划文档")
    print("=" * 60)
    
    # 创建文档生成器
    document_generator = TrainingDocumentGenerator(output_dir='./coach_documents')
    
    # 创建课程学习规划器
    curriculum = CurriculumLearning(document_generator=document_generator)
    
    # 模拟性能指标和问题
    performance_metrics = {
        'iteration': 1000,
        'win_rate': 0.35,
        'elo_rating': 1200,
        'avg_score': 8.0,
    }
    
    current_issues = [
        'AI 过度保守，不敢博清一色',
        'AI 在关键时刻容易点炮',
        'AI 对过胡策略理解不足',
    ]
    
    # 生成课程规划文档
    print(f"\n生成课程规划文档...")
    doc_path = curriculum.design_next_stage(
        performance_metrics=performance_metrics,
        current_issues=current_issues,
        iteration=1000,
    )
    
    if doc_path:
        print(f"✓ 文档已生成: {doc_path}")
        print(f"\n请打开该文档，复制内容并提交给大模型进行分析。")
    else:
        print("✗ 文档生成失败（文档生成器未设置）")


def example_manual_stage_control():
    """示例 4: 手动控制阶段"""
    print("\n" + "=" * 60)
    print("示例 4: 手动控制阶段")
    print("=" * 60)
    
    curriculum = CurriculumLearning()
    
    # 显示所有阶段
    print("\n所有训练阶段:")
    for stage in TrainingStage:
        print(f"  - {stage.value}")
    
    # 手动设置阶段
    print(f"\n当前阶段: {curriculum.current_stage.value}")
    
    # 切换到防御阶段
    curriculum.current_stage = TrainingStage.DEFENSIVE
    print(f"切换到: {curriculum.current_stage.value}")
    
    # 获取该阶段的课程
    current = curriculum.get_current_curriculum()
    print(f"\n课程名称: {current.name}")
    print(f"课程描述: {current.description}")
    print(f"评估标准: {current.evaluation_criteria}")


def example_stage_progression():
    """示例 5: 完整的阶段推进流程"""
    print("\n" + "=" * 60)
    print("示例 5: 完整的阶段推进流程")
    print("=" * 60)
    
    curriculum = CurriculumLearning()
    
    # 模拟训练过程
    stages_progress = [
        {
            'iteration': 5000,
            'metrics': {'win_rate': 0.25, 'flower_pig_rate': 0.08},
            'stage': TrainingStage.BASIC,
        },
        {
            'iteration': 10000,
            'metrics': {'win_rate': 0.35, 'flower_pig_rate': 0.03},
            'stage': TrainingStage.BASIC,
        },
        {
            'iteration': 15000,
            'metrics': {'discard_win_rate': 0.12, 'defensive_score': 0.65},
            'stage': TrainingStage.DEFENSIVE,
        },
        {
            'iteration': 20000,
            'metrics': {'discard_win_rate': 0.08, 'defensive_score': 0.75},
            'stage': TrainingStage.DEFENSIVE,
        },
    ]
    
    print("\n模拟训练过程:")
    for progress in stages_progress:
        curriculum.current_stage = progress['stage']
        iteration = progress['iteration']
        metrics = progress['metrics']
        
        print(f"\n迭代 {iteration}:")
        print(f"  当前阶段: {curriculum.current_stage.value}")
        print(f"  性能指标: {metrics}")
        
        if curriculum.should_advance_stage(metrics):
            print(f"  → 满足条件，推进到下一阶段")
            curriculum.advance_to_next_stage()
        else:
            print(f"  → 继续当前阶段训练")


def main():
    """主函数"""
    print("课程学习使用示例")
    print("=" * 60)
    
    # 运行所有示例
    example_basic_usage()
    example_check_advancement()
    example_generate_document()
    example_manual_stage_control()
    example_stage_progression()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)
    print("\n更多信息请参考: python/CURRICULUM_LEARNING_GUIDE.md")


if __name__ == '__main__':
    main()

