# DebateEngine 项目分析报告

## 1. 项目概述

DebateEngine 是一个**结构化多代理批评与共识引擎**，旨在将自由文本 AI 投票升级为结构化的跨批评循环。它使用 Pydantic v2 `CritiqueSchema` 约束批评输出，通过角色轮换保留不同观点，并通过法官层综合多角色意见，同时明确保留少数派意见。

### 核心价值主张
- **结构化批评**：使用 Pydantic v2 模式确保批评输出可被程序解析、路由和测量
- **反谄媚防御**：通过匿名跨批评、魔鬼代言人角色和提供商多样性来减少 AI 谄媚行为
- **少数派意见保护**：明确保留和量化少数派观点，避免群体思维
- **量化评估**：提供 7 种评估指标，包括原创的一致性影响评分 (CIS)
- **免费 API 策略**：完全基于免费 tier API 提供商运行，无需付费 API 密钥

## 2. 项目架构

DebateEngine 采用分层架构设计，各层职责明确：

### 2.1 架构层次

| 层 | 组件 | 功能 |
|----|------|------|
| **入口层** | Python API、FastAPI REST、MCP 服务器 | 提供多种接口接入方式 |
| **编排层** | QuickCritiqueEngine (v0.1 同步)、DebateOrchestrator (v0.2 异步) | 管理辩论工作流和任务编排 |
| **提供程序层** | LiteLLM (100+ 提供商) | 支持稳定、平衡、多样三种模式 |
| **模式层** | Pydantic v2 | 定义 CritiqueSchema、ConsensusSchema 等数据结构 |
| **评估层** | DebateEval | 提供 BDR、FAR、CV、CIS、CE、RD、HD 7 种指标 |
| **输出层** | Markdown、SARIF、JSON | 支持多种输出格式 |

### 2.2 核心流程

**多轮辩论流程**：
1. **第 1 轮**：生成提案 → 交叉批评 → 匿名化 → 法定人数检查
2. **收敛检查**：评估是否达到收敛（如无严重问题）
3. **第 2 轮**（如需）：基于第 1 轮批评生成修订 → 交叉批评 → 匿名化 → 法定人数检查
4. **最终**：法官总结和共识生成

## 3. 核心功能模块

### 3.1 快速批评引擎 (QuickCritiqueEngine)
- 单轮多角色批评
- 结构化 Markdown 输出，按严重程度排序的发现
- 延迟：5-15 秒
- 适用于快速代码审查和初步评估

### 3.2 辩论编排器 (DebateOrchestrator)
- 异步多轮辩论
- 支持作业管理（提交/轮询/取消）
- 后台任务执行，通过 job_id 跟踪状态
- 延迟：30-120 秒
- 适用于复杂决策和深度分析

### 3.3 反谄媚防御机制
1. **提供商多样性法定人数**：2/3 成功阈值
2. **魔鬼代言人**：对抗性角色，使用定制系统提示
3. **响应匿名化**：在同行批评前剥离模型身份

### 3.4 一致性影响评分 (CIS)
- 量化代理立场变化是**基于证据**还是**谄媚**的指标
- 计算公式：`CIS = Sum(stance_change * severity_weight * context_relevance) / Sum(stance_change * context_relevance)`
- 范围：
  - **CIS ~ 1.0**：基于高严重性、上下文相关批评的立场变化（良好）
  - **CIS ~ 0.0**：基于低严重性或不相关批评的立场变化（不良）
  - **CIS ~ 0.5**：混合行为，需要调查

### 3.5 评估指标 (DebateEval)

| 指标 | 测量内容 | 用例 |
|------|---------|------|
| BDR | 错误发现率 | 代码审查质量 |
| FAR | 误报率 | 批评精度 |
| CV | 共识有效性 | 答案准确性 |
| CIS | 一致性影响评分 | 反谄媚（原创，改进版） |
| CE | 收敛效率 | 成本效益 |
| RD | 推理深度 | 修复质量 |
| HD | 幻觉 delta | RAG 忠实度 |

## 4. 技术实现细节

### 4.1 角色系统
- **ROLE_A**：主要批评者角色
- **ROLE_B**：次要批评者角色
- **DA_ROLE**：魔鬼代言人角色（对抗性观点）
- 每个角色使用特定的系统提示模板，根据任务类型定制

### 4.2 匿名化机制
- 使用 `Critic Alpha`、`Critic Beta`、`Critic Gamma` 等匿名标签
- 保留 `is_devil_advocate` 标志，使法官能够识别对抗性观点
- 防止模型身份偏见影响批评

### 4.3 法定人数检查
- 要求至少 2/3 的角色成功返回（SUCCESS 或 PARSE_FAILED 带内容）
- 未达到法定人数时返回部分结果

### 4.4 提供商模式

| 模式 | 描述 | 所需 API 密钥 |
|------|------|---------------|
| **稳定**（默认） | 单一提供商，所有角色 | 仅 `GOOGLE_API_KEY` |
| **平衡** | DA 角色使用不同提供商 | `GOOGLE_API_KEY` + `GROQ_API_KEY` |
| **多样**（v1.0） | 三个提供商，最大多样性 | 添加 `NVIDIA_API_KEY` |

### 4.5 免费 API 策略
- **Google AI Studio** (Gemini)：15 RPM / 1M tokens/天，主要提供商（稳定模式）
- **Groq** (Llama, Mixtral)：30 RPM / 无限制，魔鬼代言人角色（平衡模式）
- **NVIDIA NIM**：提供免费 tier，多样模式的第三个提供商

## 5. 集成与部署

### 5.1 GitHub Action - PR 质量门控
- 自动审查 PR 使用多代理辩论
- 将结构化发现作为 PR 评论发布
- 上传 SARIF 结果到 GitHub Security 标签
- 如果发现 CRITICAL 问题，PR 失败

### 5.2 SARIF 输出
- 支持 [SARIF 格式](https://sarif-web.azurewebsites.net/) 集成
- 映射 DebateEngine 发现到标准 SARIF 规则：
  - **CRITICAL** → `error` 级别
  - **MAJOR** → `warning` 级别
  - **MINOR** → `note` 级别

### 5.3 MCP 集成
- 支持 Claude Code / Cursor MCP 服务器
- 可用工具：`debate_quick_critique`、`debate_full`、`debate_eval_score`

### 5.4 部署选项
- **pip 安装**：`pip install debate-engine` 或 `pip install "debate-engine[mcp]"`
- **Docker**：`docker run -e GOOGLE_API_KEY=xxx -e GROQ_API_KEY=xxx -p 8765:8765 debate-engine:latest`
- **REST API**：`debate-engine serve` 启动服务器

## 6. 用例场景

### 6.1 代码审查
- 检测安全漏洞（如 SQL 注入）
- 识别代码质量问题
- 提供结构化反馈和修复建议

### 6.2 RAG 验证
- 评估检索增强生成的忠实度
- 检测幻觉和不一致之处
- 提高 RAG 系统的可靠性

### 6.3 架构决策
- 评估技术选择的优缺点
- 考虑不同观点和权衡
- 生成结构化决策建议

### 6.4 PR 质量门控
- 自动审查 PR 变更
- 识别潜在问题
- 确保代码质量标准

## 7. 竞争优势

| 功能 | DebateEngine | ARGUS | Quorum | Prompt-only Councils | AutoGen GroupChat |
|------|-------------|-------|--------|---------------------|------------------|
| 结构化批评模式 | Pydantic v2 | 部分 | 否 | 自由文本 | 自由文本 |
| 魔鬼代言人角色 | 强制 | 否 | 可选 | 可选 | 否 |
| 匿名跨批评 | 身份剥离 | 否 | 否 | 否 | 否 |
| 少数派意见保护 | 强制 | 否 | 否 | 否 | 否 |
| 一致性影响评分 (CIS) | 原创指标 | 否 | 否 | 否 | 否 |
| pip 安装 | 是 | 否 | 否 | N/A | 是 |
| 量化评估 | DebateEval 7 指标 | 3 指标 | 2 指标 | 否 | 否 |
| SARIF 输出 | 是 | 否 | 否 | 否 | 否 |
| GitHub Action 集成 | 是 | 否 | 否 | 否 | 否 |

## 8. 学术基础

DebateEngine 基于多项最新研究：

| 论文 | 发现 | 对 DebateEngine 的影响 |
|------|------|------------------------|
| Du et al., ICML 2024 | 多代理辩论提高推理能力 | 项目基础 |
| CONSENSAGENT, ACL 2025 | 量化辩论中的谄媚行为 | 一致性影响评分设计 |
| Identity Bias in MAD, arXiv 2025 | 匿名化减少偏见 | 交叉批评匿名化 |
| AgentAuditor, 2026 | 结构化摘要减少法官谄媚 | 法官输入设计 |
| DTE: Debate & Thought Evaluation, EMNLP 2025 | 辩论质量评估框架 | DebateEval 指标校准 |
| Improving Multi-Agent Debate via Role Specialization, arXiv 2025 | 角色多样性提高结果 | 角色模板设计 |
| On the Conformity of Language Models, arXiv 2025 | LLM 表现出系统性谄媚 | 三层反谄媚防御 |

## 9. 路线图

- [x] v0.1: QuickCritiqueEngine（同步，单轮）
- [x] v0.1: Pydantic v2 CritiqueSchema + ConsensusSchema
- [x] v0.1: 魔鬼代言人 + 匿名化 + 少数派意见
- [x] v0.1: 2/3 法定人数 + 部分返回
- [x] v0.2: DebateOrchestrator（异步，多轮）
- [x] v0.2: 作业 API（提交/轮询/取消）
- [x] v0.2: SARIF 输出 + GitHub Action 集成
- [x] v0.2: 免费 API 策略（Google AI Studio + Groq + NVIDIA NIM）
- [x] v0.2: 一致性影响评分 (CIS) 替换 CS
- [ ] v0.2: SSE 进度流
- [x] MCP 适配器（3 工具）
- [x] DebateEval（7 指标）
- [ ] v1.0: Redis 持久化 + NetworkX 辩论图
- [ ] v1.0: 多样模式（3 提供商）
- [ ] v1.0: 完整 30 案例基准报告

## 10. 技术栈

- **编程语言**：Python 3.11+
- **核心依赖**：
  - Pydantic v2（数据验证）
  - FastAPI（REST API）
  - LiteLLM（LLM 提供商抽象）
  - AsyncIO（异步处理）
- **部署**：
  - Docker
  - GitHub Actions
  - Render（云部署）

## 11. 配置与环境变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `GOOGLE_API_KEY` | 必填 | 主要 LLM 提供商（Google AI Studio，免费） |
| `GROQ_API_KEY` | 可选 | 魔鬼代言人的备份提供商（免费） |
| `NVIDIA_API_KEY` | 可选 | 多样模式的第三个提供商 |
| `DEBATE_ENGINE_PROVIDER_MODE` | `stable` | `stable`、`balanced` 或 `diverse` |
| `DEBATE_ENGINE_LOG_LEVEL` | `INFO` | 日志级别 |

## 12. 结论

DebateEngine 是一个创新的多代理辩论系统，通过结构化批评、反谄媚防御和量化评估，为 AI 辅助决策提供了更可靠、更透明的框架。它的设计理念——保留不同观点、防止群体思维、基于证据的共识——使其成为代码审查、RAG 验证和架构决策等场景的理想工具。

通过免费 API 策略和多种集成选项，DebateEngine 提供了一个低成本、高价值的解决方案，适用于从个人开发者到大型组织的各种场景。其学术基础和持续的改进路线图也确保了它将继续发展和适应新兴的 AI 研究和应用需求。