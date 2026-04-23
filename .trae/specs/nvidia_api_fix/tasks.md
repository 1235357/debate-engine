# NVIDIA API Fix - 实施计划

## [x] Task 1: 分析NVIDIA API 500错误原因
- **Priority**: P0
- **Depends On**: None
- **Description**:
  - 分析现有的API调用代码，识别可能导致500错误的原因
  - 检查NVIDIA API文档，验证调用参数的正确性
  - 测试不同的API调用配置，找出最佳实践
- **Acceptance Criteria Addressed**: AC-1, AC-3
- **Test Requirements**:
  - `programmatic` TR-1.1: 验证API调用参数格式正确
  - `programmatic` TR-1.2: 测试不同参数组合的API调用成功率
- **Notes**: 重点关注模型格式、API密钥配置和请求参数

## [x] Task 2: 修复LLM Provider中的NVIDIA API调用
- **Priority**: P0
- **Depends On**: Task 1
- **Description**:
  - 修改`llm_provider.py`中的API调用逻辑
  - 确保正确处理NVIDIA模型格式
  - 实现更稳健的错误处理和重试机制
- **Acceptance Criteria Addressed**: AC-1, AC-3, AC-5
- **Test Requirements**:
  - `programmatic` TR-2.1: 验证API调用成功率达到95%以上
  - `programmatic` TR-2.2: 测试错误处理和重试机制
- **Notes**: 参考NVIDIA官方API文档确保调用方式正确

## [x] Task 3: 实现前端模型切换功能
- **Priority**: P1
- **Depends On**: Task 2
- **Description**:
  - 在前端HTML中添加模型选择下拉菜单
  - 修改JavaScript代码，将选择的模型传递给API
  - 更新前端UI，显示当前选择的模型
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `human-judgment` TR-3.1: 验证前端模型选择界面用户体验
  - `programmatic` TR-3.2: 验证模型参数正确传递给API
- **Notes**: 确保模型选择持久化，提升用户体验

## [x] Task 4: 优化API密钥管理和轮换
- **Priority**: P1
- **Depends On**: Task 2
- **Description**:
  - 增强APIKeyManager的密钥轮换机制
  - 实现密钥健康状态监控
  - 优化密钥选择算法，提高成功率
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-4.1: 验证多密钥轮换功能
  - `programmatic` TR-4.2: 测试密钥故障转移机制
- **Notes**: 最多支持10个API密钥，需要合理分配使用

## [x] Task 5: 增强错误处理和日志记录
- **Priority**: P1
- **Depends On**: Task 2
- **Description**:
  - 实现更详细的错误日志记录
  - 提供更友好的错误提示给用户
  - 增加监控指标，跟踪API调用状态
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `programmatic` TR-5.1: 验证错误日志的完整性
  - `human-judgment` TR-5.2: 评估错误提示的用户友好性
- **Notes**: 确保错误信息既对开发人员有用，又对用户友好

## [x] Task 6: 端到端测试和验证
- **Priority**: P0
- **Depends On**: Task 3, Task 4, Task 5
- **Description**:
  - 进行完整的端到端测试
  - 验证所有功能正常工作
  - 性能测试和稳定性测试
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-3, AC-4, AC-5
- **Test Requirements**:
  - `programmatic` TR-6.1: 验证端到端API调用成功率
  - `human-judgment` TR-6.2: 验证前端功能和用户体验
- **Notes**: 测试不同场景下的系统表现，确保稳定性

## [x] Task 7: 修复 LiteLLM Provider 缺失前缀问题
- **Priority**: P0
- **Depends On**: None
- **Description**:
  - 修复 `src/debate_engine/providers/llm_provider.py`，在 `_build_litellm_params` 方法中为 NVIDIA 模型添加正确的 LiteLLM 路由前缀（如 `openai/` 或 `nvidia_nim/`）。
  - 解决 `litellm.BadRequestError: LLM Provider NOT provided` 报错。
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-7.1: 验证调用 API 不再报 Provider NOT provided 错误。
- **Notes**: 需要修改 `model_param` 赋值逻辑，以确保兼容 LiteLLM 的调用规范。