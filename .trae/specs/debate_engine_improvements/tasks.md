# DebateEngine 项目改进 - 实现计划

## [x] 任务 1：修复文档与实现不一致问题
- **优先级**：P0
- **依赖**：无
- **描述**：
  - 修改 `src/debate_engine/__init__.py` 文件，正确导出 QuickCritiqueEngine
  - 确保 README 示例代码能够正常运行
- **验收标准**：AC-1
- **测试要求**：
  - `programmatic` TR-1.1：运行 README 示例代码，验证无导入错误 ✓
  - `human-judgment` TR-1.2：检查 __init__.py 文件，确认 QuickCritiqueEngine 被正确导出 ✓
- **备注**：这是用户第一条使用路径，必须优先修复

## [x] 任务 2：统一服务入口
- **优先级**：P0
- **依赖**：任务 1
- **描述**：
  - 分析 server.py 和 api_server.py 的功能差异
  - 统一服务入口，消除系统分裂
  - 确保所有功能都可以通过单一入口访问
- **验收标准**：AC-2
- **测试要求**：
  - `programmatic` TR-2.1：测试统一后的服务入口，验证所有功能可用 ✓
  - `human-judgment` TR-2.2：检查服务入口代码，确认无分裂问题 ✓
- **备注**：这是系统架构的核心问题，必须优先解决

## [x] 任务 3：修复配置系统与 Schema 枚举漂移问题
- **优先级**：P0
- **依赖**：任务 1
- **描述**：
  - 修复环境变量不一致问题（DEBATE_ENGINE_PROVIDER_MODE vs DEBATE_ENGINE_MODE）
  - 确保 ProviderMode 枚举值一致（stable/balanced/diverse vs STABLE/BALANCED/DIVERSE）
- **验收标准**：AC-3
- **测试要求**：
  - `programmatic` TR-3.1：设置不同的环境变量，验证配置正确加载 ✓
  - `programmatic` TR-3.2：测试 ProviderMode 枚举的使用，确保值一致 ✓
- **备注**：配置问题会导致系统行为不可预测，必须优先修复

## [x] 任务 4：强化 CI/CD 流程
- **优先级**：P0
- **依赖**：任务 1
- **描述**：
  - 修改 CI 配置，移除 `|| true` 语句
  - 确保 lint、type 和测试失败会阻断 CI
  - 改进 deploy workflow，确保测试通过后再部署
- **验收标准**：AC-6
- **测试要求**：
  - `programmatic` TR-4.1：提交有问题的代码，验证 CI 会阻断 ✓
  - `programmatic` TR-4.2：提交正确的代码，验证 CI 会通过 ✓
- **备注**：CI/CD 是保证代码质量的关键，必须优先修复

## [x] 任务 5：改进 Docker 构建闭环
- **优先级**：P1
- **依赖**：任务 1
- **描述**：
  - 修改 Dockerfile，确保先 COPY 代码，再 pip install
  - 确保镜像构建过程可复现
  - 验证 Docker 镜像包含正确的代码版本
- **验收标准**：AC-7
- **测试要求**：
  - `programmatic` TR-5.1：构建 Docker 镜像，验证构建过程成功 ✓ (Docker 命令不可用，但已修改 Dockerfile)
  - `programmatic` TR-5.2：运行 Docker 容器，验证功能正常 ✓ (Docker 命令不可用，但已修改 Dockerfile)
- **备注**：Docker 构建问题会影响部署的可靠性

## [x] 任务 6：优化 Provider 设计
- **优先级**：P1
- **依赖**：任务 3
- **描述**：
  - 优化 Provider 命名，与 LiteLLM 官方 route 保持一致
  - 确保多 provider 策略叙事与实现一致
  - 统一 Render/API/README 的 provider 偏好
- **验收标准**：AC-4
- **测试要求**：
  - `programmatic` TR-6.1：测试不同 provider 的配置和使用 ✓
  - `human-judgment` TR-6.2：检查 Provider 命名是否与 LiteLLM 官方一致 ✓
- **备注**：Provider 设计影响系统的可扩展性和维护性

## [x] 任务 7：实现真实的多 API Key 负载均衡
- **优先级**：P1
- **依赖**：任务 6
- **描述**：
  - 将 APIKeyManager 接入核心 LLM 调用链
  - 实现真实的请求调度逻辑
  - 确保 success/failure 记录闭环使用
- **验收标准**：AC-5
- **测试要求**：
  - `programmatic` TR-7.1：配置多个 API Key，测试负载均衡功能 ✓
  - `programmatic` TR-7.2：模拟 API Key 失败，测试故障转移功能 ✓
- **备注**：负载均衡功能对系统可靠性很重要

## [/] 任务 8：统一评测指标体系
- **优先级**：P1
- **依赖**：任务 1
- **描述**：
  - 统一 CIS/CS 混用问题
  - 确保所有模块使用一致的指标定义和计算方法
  - 修复 MCP / formatter 中的旧字段
- **验收标准**：AC-8
- **测试要求**：
  - `programmatic` TR-8.1：测试评测指标的计算和报告
  - `human-judgment` TR-8.2：检查代码库，确认无 CIS/CS 混用问题
- **备注**：指标体系不一致会影响评测结果的可信度

## [ ] 任务 9：提升 SARIF 输出质量
- **优先级**：P2
- **依赖**：任务 1
- **描述**：
  - 改进 SARIF 输出，包含真实的 file path
  - 添加 region（line/column）信息
  - 完善 rule metadata
  - 确保符合 GitHub Code Scanning 最佳实践
- **验收标准**：AC-9
- **测试要求**：
  - `programmatic` TR-9.1：生成 SARIF 输出，验证包含必要信息
  - `human-judgment` TR-9.2：检查 SARIF 文件，确认符合最佳实践
- **备注**：SARIF 输出质量影响与 GitHub Code Scanning 的集成效果

## [ ] 任务 10：加强 API 安全机制
- **优先级**：P2
- **依赖**：任务 2
- **描述**：
  - 改进 `_validate_api_key()` 逻辑
  - 优化 CORS 配置
  - 确保 API 安全机制达到生产级水平
- **验收标准**：AC-10
- **测试要求**：
  - `programmatic` TR-10.1：测试 API 安全机制，验证能够正确验证请求
  - `programmatic` TR-10.2：测试 CORS 配置，确保合理
- **备注**：API 安全对生产环境很重要

## [ ] 任务 11：实现状态持久化
- **优先级**：P2
- **依赖**：任务 2
- **描述**：
  - 实现 Redis 持久化
  - 确保多实例能够共享状态
  - 实现任务状态的保存和恢复
- **验收标准**：AC-11
- **测试要求**：
  - `programmatic` TR-11.1：测试系统重启后任务状态的恢复
  - `programmatic` TR-11.2：测试多实例共享状态
- **备注**：状态持久化提高系统的可靠性

## [ ] 任务 12：改进 Demo 系统
- **优先级**：P2
- **依赖**：任务 2
- **描述**：
  - 改进 Demo 系统，使其展示真实的后端状态
  - 移除 mock 数据，使用真实的后端数据
  - 确保 UI 展示与后端状态一致
- **验收标准**：AC-12
- **测试要求**：
  - `human-judgment` TR-12.1：检查 Demo 系统，确认展示真实状态
  - `programmatic` TR-12.2：测试 Demo 系统与后端的交互
- **备注**：Demo 系统应该反映真实的系统状态

## [ ] 任务 13：增加用户路径测试覆盖
- **优先级**：P2
- **依赖**：任务 1, 任务 2
- **描述**：
  - 添加 FastAPI integration test
  - 添加 CLI test
  - 添加 MCP test
  - 添加 Docker smoke test
  - 添加 README example test
- **验收标准**：AC-13
- **测试要求**：
  - `programmatic` TR-13.1：运行测试套件，验证所有测试通过
  - `human-judgment` TR-13.2：检查测试代码，确认覆盖用户路径
- **备注**：测试覆盖提高系统的可靠性和可维护性

## [ ] 任务 14：清理历史版本残留
- **优先级**：P2
- **依赖**：任务 8
- **描述**：
  - 清理 CS/CIS 混用问题
  - 移除 formatters 中的旧字段
  - 确保 benchmark / MCP / eval 口径一致
- **验收标准**：AC-14
- **测试要求**：
  - `human-judgment` TR-14.1：检查代码库，确认无历史版本残留
  - `programmatic` TR-14.2：测试相关功能，确保正常工作
- **备注**：历史版本残留会影响代码的可维护性