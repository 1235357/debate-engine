from typing import Dict, List
from .llm_provider import LLMProvider
from ..schemas.enums import ProviderMode, RoleType


class ProviderConfig:
    """供应商配置"""
    
    # NVIDIA NIM 配置
    NVIDIA_CONFIG = {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": "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",
        "model": "minimaxai/minimax-m2.7",
        "params": {
            "temperature": 1.0,
            "top_p": 0.95,
            "max_tokens": 8192,
        },
    }
    
    # 模型映射
    MODEL_MAPPING = {
        "stable": {
            RoleType.ROLE_A: NVIDIA_CONFIG,
            RoleType.ROLE_B: NVIDIA_CONFIG,
            RoleType.DA_ROLE: NVIDIA_CONFIG,
            RoleType.JUDGE: NVIDIA_CONFIG,
        },
        "balanced": {
            RoleType.ROLE_A: NVIDIA_CONFIG,
            RoleType.ROLE_B: NVIDIA_CONFIG,
            RoleType.DA_ROLE: NVIDIA_CONFIG,  # 可以使用不同的模型
            RoleType.JUDGE: NVIDIA_CONFIG,
        },
        "diverse": {
            RoleType.ROLE_A: NVIDIA_CONFIG,
            RoleType.ROLE_B: NVIDIA_CONFIG,
            RoleType.DA_ROLE: NVIDIA_CONFIG,  # 可以使用不同的模型
            RoleType.JUDGE: NVIDIA_CONFIG,
        },
    }
    
    @classmethod
    def get_provider(cls, role_type: RoleType, mode: ProviderMode = ProviderMode.STABLE) -> LLMProvider:
        """获取供应商"""
        config = cls.MODEL_MAPPING.get(mode.value, cls.MODEL_MAPPING["stable"])
        role_config = config.get(role_type, cls.NVIDIA_CONFIG)
        return LLMProvider(**role_config)
