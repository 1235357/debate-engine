# DebateEngine 项目改进 - 产品需求文档

## 概述
- **摘要**：对 DebateEngine 项目进行全面工程闭环优化，解决文档与实现不一致、服务入口分裂、配置系统漂移等核心问题，将其从研究型原型转变为可交付的工程项目。
- **目的**：提高项目的可靠性、一致性和可维护性，确保文档、代码、配置、评测、部署与宣传之间的一致性。
- **目标用户**：开发者、团队协作成员、最终用户

## 目标
- 解决文档与实现不一致问题，确保用户第一条使用路径畅通
- 统一服务入口，消除系统分裂
- 修复配置系统与 Schema 枚举漂移问题
- 优化 Provider 设计，与 LiteLLM 语义保持一致
- 实现真实的多 API Key 负载均衡
- 强化 CI/CD 流程，确保代码质量
- 改进 Docker 构建闭环
- 统一评测指标体系
- 提升 SARIF 输出质量
- 加强 API 安全机制
- 实现状态持久化
- 改进 Demo 系统，使其反映真实状态
- 增加用户路径测试覆盖
- 清理历史版本残留

## 非目标（范围外）
- 不改变核心算法和业务逻辑
- 不引入新的依赖项
- 不修改现有的评测指标计算公式
- 不重写整个代码库

## 背景与上下文
DebateEngine 是一个结构化多智能体批判与共识引擎，采用 Pydantic v2 进行结构化输出验证，使用 LiteLLM 进行 LLM 提供商抽象，支持多种评测指标和 SARIF 输出。然而，当前项目存在工程闭环不完整的问题，导致整体可信度下降，更接近"研究型原型"而非"可交付工程项目"。

## 功能需求
- **FR-1**：修复文档与实现不一致问题，确保 QuickCritiqueEngine 正确导出
- **FR-2**：统一服务入口，消除双服务入口导致的系统分裂
- **FR-3**：修复配置系统与 Schema 枚举漂移问题
- **FR-4**：优化 Provider 设计，与 LiteLLM 语义保持一致
- **FR-5**：实现真实的多 API Key 负载均衡
- **FR-6**：强化 CI/CD 流程，确保代码质量
- **FR-7**：改进 Docker 构建闭环
- **FR-8**：统一评测指标体系
- **FR-9**：提升 SARIF 输出质量
- **FR-10**：加强 API 安全机制
- **FR-11**：实现状态持久化
- **FR-12**：改进 Demo 系统，使其反映真实状态
- **FR-13**：增加用户路径测试覆盖
- **FR-14**：清理历史版本残留

## 非功能需求
- **NFR-1**：确保代码质量，通过所有 lint、type 和测试检查
- **NFR-2**：保持向后兼容性，不破坏现有 API
- **NFR-3**：提高系统可靠性和可维护性
- **NFR-4**：确保 Docker 镜像构建的可复现性
- **NFR-5**：提升 SARIF 输出的质量和标准符合性

## 约束
- **技术**：Python 3.11+，FastAPI，Pydantic v2，LiteLLM
- **业务**：保持项目的核心功能和设计理念
- **依赖**：现有依赖项不变

## 假设
- 项目将继续使用 LiteLLM 作为 LLM 提供商抽象
- 项目将保持现有的核心算法和业务逻辑
- 项目将继续支持现有的评测指标

## 验收标准

### AC-1：文档与实现一致
- **Given**：用户按照 README 示例代码导入和使用 QuickCritiqueEngine
- **When**：用户运行示例代码
- **Then**：代码能够正常运行，无导入错误
- **Verification**：programmatic

### AC-2：服务入口统一
- **Given**：用户访问统一的 API 端点
- **When**：用户发送请求到统一的服务入口
- **Then**：所有功能都可以通过单一入口访问，行为一致
- **Verification**：programmatic

### AC-3：配置系统与 Schema 枚举一致
- **Given**：用户设置环境变量并使用 ProviderMode 枚举
- **When**：用户运行系统
- **Then**：配置能够正确加载，枚举值一致
- **Verification**：programmatic

### AC-4：Provider 设计与 LiteLLM 语义一致
- **Given**：用户配置不同的 LLM 提供商
- **When**：系统使用这些提供商
- **Then**：Provider 命名与 LiteLLM 官方 route 一致
- **Verification**：programmatic

### AC-5：多 API Key 负载均衡实现
- **Given**：用户配置多个 API Key
- **When**：系统处理多个请求
- **Then**：请求能够在多个 API Key 之间均衡分配，失败时能够正确处理
- **Verification**：programmatic

### AC-6：CI/CD 流程强化
- **Given**：提交代码到仓库
- **When**：CI/CD 流程运行
- **Then**：lint、type 和测试失败会阻断 CI，确保代码质量
- **Verification**：programmatic

### AC-7：Docker 构建闭环改进
- **Given**：构建 Docker 镜像
- **When**：运行构建命令
- **Then**：镜像构建过程可复现，包含正确的代码版本
- **Verification**：programmatic

### AC-8：评测指标体系统一
- **Given**：使用评测指标
- **When**：系统计算和报告指标
- **Then**：所有模块使用一致的指标定义和计算方法
- **Verification**：programmatic

### AC-9：SARIF 输出质量提升
- **Given**：生成 SARIF 输出
- **When**：查看 SARIF 文件
- **Then**：SARIF 输出包含真实的 file path、region 信息和完整的 rule metadata
- **Verification**：programmatic

### AC-10：API 安全机制加强
- **Given**：访问 API 端点
- **When**：发送请求到 API
- **Then**：API 安全机制能够正确验证请求，CORS 配置合理
- **Verification**：programmatic

### AC-11：状态持久化实现
- **Given**：系统重启
- **When**：系统重新启动
- **Then**：之前的任务状态能够恢复，多实例能够共享状态
- **Verification**：programmatic

### AC-12：Demo 系统改进
- **Given**：访问 Demo 系统
- **When**：使用 Demo 系统
- **Then**：Demo 系统展示真实的后端状态，不使用 mock 数据
- **Verification**：human-judgment

### AC-13：用户路径测试覆盖增加
- **Given**：运行测试套件
- **When**：执行测试
- **Then**：测试套件包含 FastAPI integration test、CLI test、MCP test、Docker smoke test 和 README example test
- **Verification**：programmatic

### AC-14：历史版本残留清理
- **Given**：查看代码库
- **When**：检查代码和配置
- **Then**：代码库中不存在 CS/CIS 混用、旧字段和口径不一致的问题
- **Verification**：human-judgment

## 开放问题
- [ ] 是否需要引入新的依赖项来实现状态持久化？
- [ ] 如何平衡向后兼容性和系统改进？
- [ ] 是否需要修改现有的 API 端点路径？