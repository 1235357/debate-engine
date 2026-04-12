#!/usr/bin/env python3
"""
DebateEngine Demo Script
演示 DebateEngine 的核心功能
"""

import asyncio
import sys
from typing import Any

print("=" * 60)
print("DebateEngine Demo")
print("=" * 60)
print()

try:
    print("正在导入 DebateEngine 模块...")
    from debate_engine.schemas import (
        CritiqueConfigSchema,
        TaskType,
    )
    print("✓ DebateEngine 模块导入成功")
    print()
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    print()
    print("请先运行: pip install -e .")
    sys.exit(1)

print("=" * 60)
print("功能验证")
print("=" * 60)
print()

# 验证 1: Schema 实例化
print("1. 验证 Schema 实例化...")
try:
    config = CritiqueConfigSchema(
        content="""
def login(username, password):
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    return db.execute(query)
        """,
        task_type=TaskType.CODE_REVIEW,
    )
    print(f"✓ CritiqueConfigSchema 实例化成功")
    print(f"  - 任务类型: {config.task_type}")
    print(f"  - 内容长度: {len(config.content)} 字符")
except Exception as e:
    print(f"✗ Schema 实例化失败: {e}")
print()

# 验证 2: 枚举类型
print("2. 验证枚举类型...")
try:
    from debate_engine.schemas import (
        DefectType,
        Severity,
        FixKind,
        ProviderMode,
    )
    print("✓ 枚举类型导入成功")
    print(f"  - DefectType: {list(DefectType.__members__.keys())}")
    print(f"  - Severity: {list(Severity.__members__.keys())}")
    print(f"  - FixKind: {list(FixKind.__members__.keys())}")
except Exception as e:
    print(f"✗ 枚举类型验证失败: {e}")
print()

# 验证 3: 评估指标
print("3. 验证评估指标...")
try:
    from debate_engine.eval.metrics import (
        MetricName,
        MetricResult,
        compute_bdr,
        compute_far,
        compute_hd,
    )
    print("✓ 评估指标导入成功")
    
    # 测试 BDR 计算
    gold = [{"description": "SQL injection vulnerability"}]
    discovered = [{"description": "SQL injection vulnerability in query"}]
    bdr_result = compute_bdr(discovered, gold)
    print(f"✓ BDR 计算成功: {bdr_result.value:.2%}")
    
    # 测试 FAR 计算
    far_result = compute_far(discovered, gold)
    print(f"✓ FAR 计算成功: {far_result.value:.2%}")
    
    # 测试 HD 计算
    hd_result = compute_hd(debate_faithfulness=0.85, baseline_faithfulness=0.6)
    print(f"✓ HD 计算成功: {hd_result.value:+.2%}")
except Exception as e:
    print(f"✗ 评估指标验证失败: {e}")
print()

# 验证 4: Provider 配置
print("4. 验证 Provider 配置...")
try:
    from debate_engine.providers.config import ProviderConfig
    config = ProviderConfig()
    print("✓ ProviderConfig 初始化成功")
    print(f"  - 主提供商: {config.primary_provider}")
    print(f"  - 主模型: {config.primary_model}")
    print(f"  - 模式: {config.mode}")
except Exception as e:
    print(f"✗ Provider 配置验证失败: {e}")
print()

print("=" * 60)
print("使用示例")
print("=" * 60)
print()
print("1. Python API 示例:")
print("""
import asyncio
from debate_engine import QuickCritiqueEngine
from debate_engine.schemas import CritiqueConfigSchema, TaskType

async def main():
    engine = QuickCritiqueEngine()
    
    config = CritiqueConfigSchema(
        content='''def login(username, password):
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    return db.execute(query)''',
        task_type=TaskType.CODE_REVIEW,
    )
    
    consensus = await engine.critique(config)
    print(consensus.final_conclusion)
    print(f"置信度: {consensus.consensus_confidence}")

asyncio.run(main())
""")
print()

print("2. REST API 示例:")
print("""
# 启动服务器
debate-engine serve

# 快速批评
curl -X POST http://localhost:8765/v1/quick-critique \\
  -H "Content-Type: application/json" \\
  -d '{
    "content": "Your code or proposal here...",
    "task_type": "CODE_REVIEW"
  }'
""")
print()

print("3. Docker 部署:")
print("""
# 构建并运行
docker-compose up -d

# 或直接运行
docker run -e GOOGLE_API_KEY=your-key -p 8765:8765 debate-engine:latest
""")
print()

print("=" * 60)
print("✓ Demo 完成！")
print("=" * 60)
print()
print("下一步:")
print("1. 设置环境变量: cp .env.example .env 并编辑 .env")
print("2. 获取免费 API Key:")
print("   - Google AI Studio: https://makersuite.google.com/app/apikey")
print("   - Groq: https://console.groq.com/keys")
print("3. 运行测试: pytest tests/ -v")
print("4. 启动服务器: debate-engine serve")
print("5. 访问文档: http://localhost:8765/docs")
print()
