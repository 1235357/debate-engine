import asyncio
import argparse
import json
from .orchestration import QuickCritiqueEngine
from .schemas import CritiqueConfigSchema, TaskType


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(description="DebateEngine CLI")
    parser.add_argument("--content", type=str, required=True, help="待批评的内容")
    parser.add_argument("--task-type", type=str, default="CODE_REVIEW", help="任务类型")
    parser.add_argument("--max-rounds", type=int, default=2, help="最大轮数")
    parser.add_argument("--provider-mode", type=str, default="stable", help="供应商模式")
    parser.add_argument("--output", type=str, default="json", help="输出格式")
    
    args = parser.parse_args()
    
    asyncio.run(run_critique(args))


async def run_critique(args):
    """运行批评"""
    engine = QuickCritiqueEngine()
    
    config = CritiqueConfigSchema(
        content=args.content,
        task_type=args.task_type,
        max_rounds=args.max_rounds,
        provider_mode=args.provider_mode,
    )
    
    try:
        consensus = await engine.critique(config)
        
        if args.output == "json":
            print(json.dumps(consensus.model_dump(), ensure_ascii=False, indent=2))
        else:
            print("=== DebateEngine 批评结果 ===")
            print(f"最终结论: {consensus.final_conclusion}")
            print(f"共识置信度: {consensus.consensus_confidence:.2f}")
            print(f"总批评数: {consensus.total_critiques}")
            print(f"严重批评数: {consensus.critical_critiques}")
            print(f"主要批评数: {consensus.major_critiques}")
            print(f"次要批评数: {consensus.minor_critiques}")
            print(f"执行时间: {consensus.execution_time:.2f}秒")
            print(f"从众分数: {consensus.conformity_score:.2f}")
            
            print("\n=== 批评摘要 ===")
            for i, critique in enumerate(consensus.critiques_summary):
                print(f"\n批评 {i+1}:")
                print(f"  目标区域: {critique.target_area}")
                print(f"  缺陷类型: {critique.defect_type}")
                print(f"  严重程度: {critique.severity}")
                print(f"  证据: {critique.evidence}")
                print(f"  建议修复: {critique.suggested_fix}")
                print(f"  置信度: {critique.confidence:.2f}")
            
            if consensus.preserved_minority_opinions:
                print("\n=== 少数意见 ===")
                for i, opinion in enumerate(consensus.preserved_minority_opinions):
                    print(f"\n意见 {i+1}:")
                    print(f"  内容: {opinion.opinion}")
                    print(f"  严重程度: {opinion.source_critique_severity}")
                    print(f"  潜在风险: {opinion.potential_risk_if_ignored}")
                    
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()
