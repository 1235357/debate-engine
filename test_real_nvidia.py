#!/usr/bin/env python3
"""真正的NVIDIA API测试，使用官方文档的方式"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 方法1: 直接使用OpenAI客户端
print("=" * 60)
print("方法1: 直接使用OpenAI客户端（官方文档方式）")
print("=" * 60)
try:
    from openai import AsyncOpenAI
    
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("❌ 未找到NVIDIA_API_KEY环境变量")
    else:
        client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        
        print(f"✅ 客户端创建成功")
        print(f"📋 模型名称: minimaxai/minimax-m2.7")
        print(f"🔗 API地址: https://integrate.api.nvidia.com/v1")
        
        # 发送简单请求
        response = await client.chat.completions.create(
            model="minimaxai/minimax-m2.7",
            messages=[{"role": "user", "content": "Hello, please reply with 'OK'"}],
            temperature=1,
            top_p=0.95,
            max_tokens=100,
            stream=False
        )
        
        print(f"✅ 请求成功！")
        print(f"📝 响应: {response.choices[0].message.content}")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("方法2: 使用LiteLLM测试")
print("=" * 60)
try:
    import litellm
    
    api_key = os.getenv("NVIDIA_API_KEY")
    
    # 测试多种配置
    test_cases = [
        {
            "name": "使用custom_llm_provider=openai",
            "model": "minimaxai/minimax-m2.7",
            "api_base": "https://integrate.api.nvidia.com/v1",
            "custom_llm_provider": "openai",
        },
        {
            "name": "不使用前缀，直接传model",
            "model": "minimaxai/minimax-m2.7",
            "api_base": "https://integrate.api.nvidia.com/v1",
        }
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\n--- 测试 {i+1}: {test['name']} ---")
        try:
            params = {
                "model": test["model"],
                "messages": [{"role": "user", "content": "Hello, reply with 'OK'"}],
                "api_key": api_key,
                "api_base": test["api_base"],
            }
            if "custom_llm_provider" in test:
                params["custom_llm_provider"] = test["custom_llm_provider"]
            
            print(f"🔧 参数: {params}")
            
            response = await litellm.acompletion(**params)
            print(f"✅ 成功！响应: {response.choices[0].message.content}")
            
        except Exception as e:
            print(f"❌ 失败: {e}")
            
except Exception as e:
    print(f"❌ LiteLLM测试错误: {e}")
    import traceback
    traceback.print_exc()
