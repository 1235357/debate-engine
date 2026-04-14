import asyncio

from debate_engine import QuickCritiqueEngine
from debate_engine.schemas import CritiqueConfigSchema, TaskType


async def main():
    print("Testing README example...")
    try:
        engine = QuickCritiqueEngine()
        print("✓ QuickCritiqueEngine initialized successfully")

        config = CritiqueConfigSchema(
            content="""def login(username, password):
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    return db.execute(query)""",
            task_type=TaskType.CODE_REVIEW,
        )
        print("✓ CritiqueConfigSchema created successfully")

        # 由于我们没有配置 API Key，这里会失败，但至少验证导入和初始化没有问题
        try:
            await engine.critique(config)
            print("✓ critique() method executed successfully")
        except Exception as e:
            print(f"⚠ critique() method failed (expected without API Key): {e}")
            print("✓ Import and initialization test passed")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
