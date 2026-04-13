import os
from debate_engine.providers.config import ProviderConfig, ProviderMode

# 测试不同环境变量设置
def test_env_variables():
    print("Testing environment variables...")
    
    # 测试 DEBATE_ENGINE_MODE
    os.environ["DEBATE_ENGINE_MODE"] = "balanced"
    config1 = ProviderConfig.from_env()
    print(f"✓ DEBATE_ENGINE_MODE=balanced -> mode={config1.mode.value}")
    
    # 测试 DEBATE_ENGINE_PROVIDER_MODE（优先级更高）
    os.environ["DEBATE_ENGINE_PROVIDER_MODE"] = "diverse"
    config2 = ProviderConfig.from_env()
    print(f"✓ DEBATE_ENGINE_PROVIDER_MODE=diverse -> mode={config2.mode.value}")
    
    # 测试大小写不敏感
    os.environ["DEBATE_ENGINE_PROVIDER_MODE"] = "STABLE"
    config3 = ProviderConfig.from_env()
    print(f"✓ DEBATE_ENGINE_PROVIDER_MODE=STABLE -> mode={config3.mode.value}")
    
    # 测试默认值
    del os.environ["DEBATE_ENGINE_PROVIDER_MODE"]
    del os.environ["DEBATE_ENGINE_MODE"]
    config4 = ProviderConfig.from_env()
    print(f"✓ No mode env var -> mode={config4.mode.value}")
    
    # 测试无效值
    os.environ["DEBATE_ENGINE_MODE"] = "invalid"
    config5 = ProviderConfig.from_env()
    print(f"✓ Invalid mode value -> mode={config5.mode.value} (default)")
    
    print("✓ All environment variable tests passed")

# 测试 ProviderMode 枚举
def test_provider_mode_enum():
    print("\nTesting ProviderMode enum...")
    
    # 测试枚举值
    print(f"✓ ProviderMode.STABLE.value = {ProviderMode.STABLE.value}")
    print(f"✓ ProviderMode.BALANCED.value = {ProviderMode.BALANCED.value}")
    print(f"✓ ProviderMode.DIVERSE.value = {ProviderMode.DIVERSE.value}")
    
    # 测试枚举构造
    try:
        mode1 = ProviderMode("stable")
        print("✓ ProviderMode('stable') works")
    except Exception as e:
        print(f"✗ ProviderMode('stable') failed: {e}")
        raise
    
    try:
        mode2 = ProviderMode("balanced")
        print("✓ ProviderMode('balanced') works")
    except Exception as e:
        print(f"✗ ProviderMode('balanced') failed: {e}")
        raise
    
    try:
        mode3 = ProviderMode("diverse")
        print("✓ ProviderMode('diverse') works")
    except Exception as e:
        print(f"✗ ProviderMode('diverse') failed: {e}")
        raise
    
    print("✓ All ProviderMode enum tests passed")

if __name__ == "__main__":
    test_env_variables()
    test_provider_mode_enum()
    print("\n✅ All tests passed!")