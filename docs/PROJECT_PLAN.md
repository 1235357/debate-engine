# DebateEngine v6.0
## 结构化多智能体对抗批评引擎 · 最终项目计划书

> **文档性质：** 正式可行性分析与执行计划书（最终版）  
> **版本：** v6.0 — 基于2026年4月最新互联网深度调研  
> **日期：** 2026 年 4 月 12 日  
> **核心立场：** 本版本基于对最新多智能体代码审查工具的系统性调研，进一步明确DebateEngine的差异化定位和竞争优势。

---

## 执行摘要（Executive Summary）

**项目一句话定位：**
DebateEngine 是一个 **pip 可安装的 Python 生产库**，通过 Pydantic v2 结构化 Schema 将多智能体批评的输出从自由文本升级为**机器可解析、CI/CD 可集成、可量化评估**的结构化对象，填补了学术多智能体辩论研究与工业界 AI Code Review 工具之间的工程空白。

**项目存在的根本理由（2026年4月调研确认）：**
1. **最新市场动态：** Anthropic 于2026年3月10日发布了 Claude Code Review，采用多智能体架构，定价 $15-25/PR，验证了多智能体代码审查的商业价值
2. **市场空白：** 虽然多智能体代码审查已成为趋势，但仍缺乏**结构化输出 + 成本可控 + 可集成**的开源解决方案
3. **生态需求：** OpenClaw 等AI Agent框架的批评类技能仍为纯Markdown提示词，无结构化输出能力
4. **成本优势：** 主流商业工具（Claude Code Review）成本过高，无法覆盖高频审查场景

**DebateEngine 的独特价值：** 在多智能体架构成为行业共识的背景下，提供**结构化输出 + 免费API + 可集成**的开源替代方案。

---

## 一、最新竞品深度调研（2026年4月更新）

### 1.1 最新市场动态

**Anthropic Claude Code Review（2026年3月发布）**
- **定位：** 多智能体GitHub PR分析系统
- **核心特点：** 并行专业Agent + 聚合验证 + 三等级严重性评分
- **定价：** $15-25/PR，基于PR大小和复杂度
- **性能：** 84%大型PR标记率，<1%误报率，20分钟审查时间
- **输出：** GitHub评论和内联标注（自由文本）
- **局限：** 闭源商业服务，成本高，无结构化输出，无法集成进自定义CI/CD流程

**Open Code Review（GitHub热门项目）**
- **定位：** 开源多智能体代码审查工具
- **核心特点：** Claude Flow集成，多Agent协作
- **输出：** 自由文本，GitHub评论
- **局限：** 无结构化Schema，依赖Claude API，无成本控制机制

**llm-peer-review（GitHub活跃项目）**
- **定位：** 多LLM同行评审工具
- **核心特点：** GPT和Gemini双模型辩论，多轮对话
- **输出：** Markdown格式，自由文本
- **局限：** 无结构化输出，无CI/CD集成，仅限本地使用

### 1.2 市场空白分析（2026年4月确认）

| 维度 | 自由文本输出 | 结构化 / 可编程输出 |
|------|------------|----------------|
| 单 Agent | Claude Code Review、CodeRabbit、Qodo | DeepEval / OpenEvals（评估应用输出，非批评内容） |
| 多 Agent / 对抗 | Open Code Review、llm-peer-review、Claude Code Review | **DebateEngine 填补此处**（多角色 + 结构化 + 生产级 + 成本可控） |

**关键发现：** 多智能体架构已成为行业标准，但结构化输出仍然是市场空白。DebateEngine 的差异化优势更加明确。

---

## 二、项目核心价值重新定义（v6.0）

### 2.1 核心定位

**DebateEngine 是一个结构化批评基础设施层（Structured Critique Infrastructure），专门服务于 AI 辅助开发时代下的"内容质量保障"需求。**

### 2.2 核心价值主张

1. **结构化输出：** 使用 Pydantic v2 结构化 Schema，将批评从自由文本升级为机器可解析、CI/CD 可集成、可量化评估的结构化对象

2. **多智能体对抗：** 强制设置 Devil's Advocate 角色，防止 Sycophancy，保留少数意见

3. **成本可控：** 集成 NVIDIA NIM 免费 API，开发阶段零成本，生产阶段成本可控（相比 Claude Code Review 的 $15-25/PR）

4. **生态集成：** 作为 pip 可安装的 Python 库，可集成进 GitHub Actions、OpenClaw、LangChain/LangGraph 等现有工具链

5. **开源透明：** 完全开源，可自定义扩展，避免 vendor lock-in

### 2.3 技术护城河

1. **CritiqueSchema 结构化约束体系：** 批评的每一个有效声明都必须符合 Pydantic v2 约束，包含 `defect_type`、`severity`、`evidence`、`suggested_fix`、`confidence` 等字段

2. **Conformity Score (CIS) 原创量化指标：** 量化多轮辩论中 Agent 立场改变是被论据驱动还是被从众心理驱动

3. **Anti-Sycophancy 三层防御体系：**
   - 层一：DA 角色强制使用不同供应商/模型
   - 层二：批评者匿名化
   - 层三：Judge 使用结构化摘要输入

4. **生产级稳定性设计：**
   - Quorum 检查（2/3 即可）
   - 内置重试逻辑
   - 部分返回机制
   - 并发执行（asyncio.gather）

---

## 三、落地场景与商业价值论证

### 3.1 场景一：AI 辅助编程时代的代码审查质量门控

**背景痛点：** 随着 Claude Code、OpenCode、Codex 等 AI 编程工具的普及，代码生成速度大幅提升，但 PR 的数量和规模也在增加，而没有对应的审查容量扩充。Claude Code Review 虽好但成本过高（$15-25/PR），无法覆盖高频审查场景。

**DebateEngine 的解决方案：** 在 GitHub Actions 中集成 DebateEngine，当 PR 提交时自动触发多角色结构化审查。CRITICAL 发现（如 SQL 注入、N+1 查询、竞争条件）通过 `severity` 字段自动判定，可配置为阻止合并或强制人工确认。

**相比现有方案的差异：**
- 相比 Claude Code Review：成本降低 99%（使用 NVIDIA 免费 API），可自托管，结构化输出可集成
- 相比 CodeRabbit/Greptile（单 Agent）：提供对抗视角，发现单 Agent 忽略的系统性盲点
- 相比无 AI 审查：结构化输出可以集成到工单系统（Jira、Linear），自动分配到对应责任人

### 3.2 场景二：OpenClaw 技能生态的结构化批评升级

**背景痛点：** OpenClaw 中 162 个生产就绪的 Agent 模板覆盖 19 个类别，但所有批评类技能（consilium、agora-council 等）都是 Markdown 提示词，输出是自由文本，无法被下游程序处理。

**DebateEngine 的解决方案：** 以 **OpenClaw Skill** 形式提供 `debate-critique` 技能，技能的实现通过调用 DebateEngine Python API 完成，将结构化批评结果返回 OpenClaw 对话。同时，提供 **MCP Server** 让 OpenClaw 通过 MCP 协议调用 DebateEngine。

**具体集成效果：**
- OpenClaw 用户："`@debate-critique` 请审查这段代码" → 返回结构化批评报告（按 severity 排序，含具体修复建议）
- OpenClaw 开发者：将 DebateEngine MCP 工具集成进自定义 Agent 工作流

### 3.3 场景三：RAG 应用的幻觉检测质量门控

**背景痛点：** RAG（检索增强生成）系统的幻觉问题是企业 AI 落地最大的可信度风险之一。现有工具（RAGAS、DeepEval）的幻觉检测是单 Agent 的——用一个 LLM 来评估另一个 LLM 的幻觉，存在模型间的认知偏差。

**DebateEngine 的解决方案：** 以 `RAG_VALIDATION` 任务类型调用 DebateEngine，三个异构角色分别从"事实核查"、"来源追溯"、"逻辑一致性"角度批评 RAG 答案，DA 角色专门扮演"怀疑主义者"——假设答案是幻觉，寻找证伪依据。

### 3.4 场景四：面向 LangChain/LangGraph 用户的对抗评估节点

**背景：** LangGraph 是 2025-2026 年多 Agent 工作流编排的主流框架之一。LangChain 的 OpenEvals 提供了 LLM-as-Judge 能力，但是单 Judge、无对抗、自由文本输出。

**DebateEngine 的集成方式：** 以 **LangGraph 节点**形式提供 `DebateCritiqueNode`，输入为待批评内容，输出为 ConsensusSchema（Pydantic 对象，可直接在 LangGraph 状态中传递）。

---

## 四、技术可行性深度分析

### 4.1 技术栈选型理由（工业主流验证）

**Python + Pydantic v2（核心）**
- Pydantic v2 是当前 Python 生态系统中 LLM 应用结构化输出的事实标准
- 与 FastAPI、LangChain、Pydantic AI 等主流框架无缝集成

**asyncio + asyncio.gather（并发控制）**
- 三个角色批评的并发执行是 P95 < 15s 目标的技术基础
- Python 异步 I/O 的标准模式，无需引入重型任务队列

**LiteLLM（Provider 抽象）**
- 提供 100+ 模型供应商的统一接口，包含 timeout、fallback、cost tracking
- NVIDIA NIM 提供 OpenAI 兼容接口，LiteLLM 原生支持

**FastAPI（API 层）**
- Python 异步 API 的工业标准，原生支持 Pydantic v2 Schema
- 自动生成 OpenAPI 文档

**MCP SDK（集成层）**
- MCP（Model Context Protocol）是 Anthropic 开源的标准协议，已被 OpenClaw、Claude Code、Cursor 等主流工具广泛支持

### 4.2 实现难度真实评估

| 模块 | 实现难度 | 风险点 | 缓解措施 |
|---|---|---|---|
| Pydantic v2 Schema 定义 | ★☆☆☆☆ 低 | 无显著风险 | — |
| 单角色 LLM 调用 + 结构化输出 | ★★☆☆☆ 低-中 | LLM 偶发输出不符合 Schema | Parse Repair 机制（1次重试） |
| asyncio.gather 并发批评 | ★★☆☆☆ 低-中 | 超时控制 | 单角色 25s + 整体 30s 双层超时 |
| Quorum + Partial Return | ★★☆☆☆ 低-中 | 边界情况处理 | 明确的状态机设计 |
| Judge 汇总（结构化摘要输入） | ★★★☆☆ 中 | Judge 输出质量不稳定 | 系统提示约束 + 固定模板 |
| FastAPI + 异步任务 API | ★★★☆☆ 中 | 并发任务管理 | asyncio.Task + 内存字典 |
| MCP 薄适配层 | ★★☆☆☆ 低-中 | MCP SDK 版本兼容 | 所有 MCP 工具通过 HTTP 调用 FastAPI |
| DebateEval 评估框架 | ★★★☆☆ 中 | 金标准构建成本 | 手工标注 15 个用例，Cohen's kappa 验证 |
| Conformity Score 计算 | ★★★☆☆ 中 | 立场量化的定义精确性 | 明确的数学公式，无 ML 依赖 |
| OpenClaw Skill 封装 | ★☆☆☆☆ 低 | 仅需一个 SKILL.md | — |

**总体实现难度评估：中等偏低。** 没有任何需要自研模型、复杂 ML 训练或罕见工程能力的模块。

### 4.3 NVIDIA NIM API 的可行性评估

**选择 NVIDIA NIM + MiniMax M2.7 作为默认后端的理由：**
- 免费额度：1000 次推理调用
- 每次 quick_critique = 4 次 API 调用（3 角色 + 1 Judge）
- 等效免费次数：250 次完整批评审查
- 开发阶段 8 周预估消耗：约 200-300 次（包括调试）
- **结论：免费额度足够覆盖整个开发阶段**

**备用策略：** NVIDIA NIM 同时提供 Llama 3.3 70B、Qwen 系列等模型，可在主模型额度用尽时无缝切换。

---

## 五、完整技术架构（V6.0 确认版）

### 5.1 整体分层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         接入层（Entry Layer）                         │
│                                                                     │
│  Python API          FastAPI REST           MCP Server               │
│  （直接 import）      /v1/quick-critique     debate_quick_critique     │
│                      /v1/debate             debate_full              │
│                      /v1/debate/{job_id}    debate_eval_score        │
│                                                                     │
│  OpenClaw Skill       GitHub Actions         LangGraph Node          │
│  （SKILL.md 调用）     质量门控集成            DebateCritiqueNode       │
├─────────────────────────────────────────────────────────────────────┤
│                       编排层（Orchestration Layer）                    │
│                                                                     │
│  QuickCritiqueEngine          DebateOrchestrator                      │
│  （同步，P95 <15s）      （异步，最多2轮，job_id轮询）              │
│                                                                     │
│  Phase 0：路由 + 角色加载       Phase 1-4（并发批评→匿名→Judge）         │
│  Phase 1：asyncio.gather 并发  Round 1 + Round 2（可选）              │
│  Phase 2：匿名化处理            CRITICAL_CLEARED 收敛检测              │
│  Phase 3：Quorum 判断          Full Judge + RevisionSchema           │
│  Phase 4：Judge 汇总                                                 │
│  Phase 5：ConsensusSchema 格式化                                      │
├─────────────────────────────────────────────────────────────────────┤
│                       稳定性层（Reliability Layer）                    │
│                                                                     │
│  Transport Retry（2次）         Parse Repair（1次）                    │
│  Quorum 2/3 机制               Partial Return 保证                   │
│  Cost Budget 硬停止             任务超时控制                            │
├─────────────────────────────────────────────────────────────────────┤
│                       Provider 层（Provider Layer）                   │
│                                                                     │
│  LiteLLM 统一封装（timeout / fallback / cost tracking）               │
│  stable 模式：单供应商（默认 NVIDIA NIM MiniMax M2.7）                  │
│  balanced 模式：双供应商（DA 角色使用不同模型版本）                        │
│  diverse 模式：三供应商（V1.0，Monoculture 防护最强）                    │
├─────────────────────────────────────────────────────────────────────┤
│                        Schema 层（Schema Layer）                      │
│                                                                     │
│  CritiqueConfigSchema    CritiqueSchema（核心）    ConsensusSchema    │
│  DebateConfigSchema      ProposalSchema            DebateJobSchema   │
├─────────────────────────────────────────────────────────────────────┤
│                      可观测层（Observability Layer）                   │
│                                                                     │
│  结构化 JSON 日志（request_id/latency_ms/cost_usd/termination_reason） │
│  可选：LangSmith 追踪（环境变量激活，不强制依赖）                         │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 CritiqueSchema（核心数据结构规格）

**`target_area`**（字符串，10-200字符，必填）
- 批评必须指向具体范围，防止泛泛而论

**`defect_type`**（枚举，8个值，必填）
- `LOGICAL_FALLACY / FACTUAL_ERROR / MISSING_CONSIDERATION / SECURITY_RISK / PERFORMANCE_ISSUE / UNSUPPORTED_ASSUMPTION / SCALABILITY_CONCERN / COST_INEFFICIENCY / GENERAL`
- 使 DebateEval 可以按类型统计，GitHub Actions 可以按类型路由

**`severity`**（枚举，3个值，必填）
- `CRITICAL / MAJOR / MINOR`
- CI/CD Quality Gate 的决策依据

**`evidence`**（字符串，最小20字符，必填）
- 防止空洞批评，不同 `defect_type` 有不同证据格式要求

**`suggested_fix`**（字符串，最小20字符，必填）+ **`fix_kind`**（枚举，3个值）
- `CONCRETE_FIX / VALIDATION_STEP / NEED_MORE_DATA`
- 保证批评有后续行动

**`confidence`**（浮点数，0.0-1.0，必填）
- 置信度校准，低置信度批评在评估中权重减半

**`is_devil_advocate`**（布尔值，系统填充）
- Judge 需要知道某条批评来自对立视角

---

## 六、版本路线图（V6.0 最终确认版）

### 6.1 8 周执行范围（严格执行承诺）

**V0.1 稳定核心（第1-4周，4月14日—5月11日）**
- 完整 CritiqueSchema / ConsensusSchema / CritiqueConfigSchema 定义
- NVIDIA NIM Provider 实现（LiteLLM 封装）
- 三任务类型角色提示词模板（CODE_REVIEW / RAG_VALIDATION / ARCHITECTURE_DECISION）
- QuickCritiqueEngine 完整流程（Phase 0-4）
- 稳定性机制（Transport Retry / Parse Repair / Quorum / Partial Return / Cost Budget）
- FastAPI REST 服务（`/health` + `POST /v1/quick-critique`）
- Docker 单容器部署
- 10 个内部回归测试用例（含 mock provider 模式）

**V0.2 有限辩论（第5-6周，5月12日—25日）**
- ProposalSchema + RevisionSchema（两轮辩论专用）
- DebateOrchestrator（最多2轮，CRITICAL_CLEARED 收敛检测）
- DebateTaskManager（内存字典，asyncio.Task）
- 三个 REST 端点：`POST /v1/debate` / `GET /v1/debate/{job_id}` / `DELETE /v1/debate/{job_id}`
- ConsensusSchema 扩展（含 `rounds_data` 字段）
- balanced 模式供应商分配逻辑（DA 使用不同模型版本）
- 15 个基准测试用例运行（BDR / HD / CIS 真实数字）

**第7周（5月26日—6月1日）**
- MCP Server（3个工具：`debate_quick_critique` / `debate_full` / `debate_eval_score`）
- OpenClaw Skill（`SKILL.md`调用 HTTP API）
- PyPI 正式发布（`debate-engine` v0.1.0）
- DebateEval 全7项指标完整实现（BDR / FAR / HD / CIS / CE / RD / CONF）

**第8周（6月2日—8日）**
- README 最终版（含基准测试对比表、与竞品差异表、Quick Start）
- 完整 Jupyter Notebook 示例（代码审查场景，端到端）
- GitHub Actions 集成示例（PR 质量门控）
- 社区发布（LangChain Discord `#showcase` + awesome-LangGraph PR）

### 6.2 V1.0 愿景（8周后）

| 能力 | 当前状态 | V1.0 目标 |
|---|---|---|
| 任务持久化 | 内存字典（重启丢失） | Redis + Durable Execution |
| 多供应商模式 | stable + balanced | + diverse（三供应商） |
| 辩论图谱 | 无 | NetworkX 可视化辩论论点关系 |
| 评估规模 | 25 用例 | 完整 50 用例公开基准报告 |
| OpenClaw 集成 | Skill + MCP | ClawHub 正式发布 |
| 部署模式 | Docker 单容器 | Kubernetes Helm Chart |

---

## 七、DebateEval 评估框架规格（量化证明价值）

### 7.1 七项核心指标定义

**BDR（Bug Detection Rate，缺陷发现率）**
- 定义：`已发现金标准缺陷数 / 金标准总缺陷数`
- 目标：DebateEngine BDR 显著高于单 Agent 基线（预期 Δ +15% ~ +30%）

**FAR（False Alarm Rate，误报率）**
- 定义：`DebateEngine 报告但金标准中不存在的发现数 / DebateEngine 总发现数`
- 目标：< 0.25

**HD（Hallucination Delta，幻觉检测提升）**
- 适用场景：RAG_VALIDATION 任务类型
- 计算：RAGAS Faithfulness 指标，对比单 Agent 基线的改善幅度

**CIS（Conformity Impact Score，从众抑制分数）**
- 定义：`Σ(立场变化幅度 × severity权重) / Σ(立场变化幅度)`
- 权重：CRITICAL=1.0 / MAJOR=0.6 / MINOR=0.2
- CIS 越高 = 立场改变越多是被高质量批评驱动

**CE（Critique Efficiency，批评效率）**
- 定义：每次成功批评调用产生的有效发现数
- 用途：成本效率分析（发现/美元 比值）

**RD（Reasoning Depth，推理深度与可操作性）**
- 定义：Judge ConsensusSchema 中 `adopted_contributions` 采纳的 CONCRETE_FIX 类批评数 / 总 CONCRETE_FIX 类批评数

**CONF（Confidence Calibration，置信度校准）**
- 定义：高置信度（≥0.7）批评的精确率 vs 低置信度（<0.4）批评的精确率

### 7.2 25 个基准用例设计

```
10 个回归测试用例（每次 CI 运行，无真实 API 调用）：
  ├── 5 个代码审查（Python，含已知 N+1 / SQL 注入 / 竞争条件等）
  ├── 3 个 RAG 验证（故意注入已知幻觉）
  └── 2 个架构决策（已知 trade-off 对比）

15 个基准测试用例（每周运行，需真实 API 调用）：
  ├── 6 个代码审查（跨语言，复杂度更高，多个交织问题）
  ├── 6 个 RAG 验证（涉及领域专业知识判断）
  └── 3 个架构决策（专用于 CIS 消融实验）
        ├── 配置 A：Zero Defense（无DA，无匿名化，单供应商）
        ├── 配置 B：DA Only
        └── 配置 C：Full Defense（DA + 匿名化 + 双供应商）
```

---

## 八、成本与资源规划

### 8.1 开发阶段总成本

| 阶段 | 主要成本来源 | 预估金额 |
|---|---|---|
| 第1-4周（V0.1开发） | NVIDIA NIM 免费额度内 | **$0** |
| 第5周（V0.2开发） | NVIDIA NIM 免费额度内 | **$0** |
| 第6周（基准测试） | 15个基准用例 × 5次运行 × 约4次调用 = 300次 API调用 | **$0** |
| 第7-8周（收尾） | 主要为文档工作，少量 API 调用 | **$0 ~ $5** |

**总开发成本：$0 ~ $5**（相比 Claude Code Review 的 $15-25/PR，成本优势显著）

### 8.2 部署成本（上线后）

| 场景 | 方案 | 月成本 |
|---|---|---|
| Demo（Gradio） | HuggingFace Spaces 免费层 | **$0** |
| API 服务 | Render.com 免费层（750小时/月） | **$0** |
| 自托管（单机） | Docker 单容器，按 LLM API 调用付费 | 按使用量（NVIDIA NIM 超出后约 $0.001/次） |

---

## 九、风险识别与缓解预案

### 9.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| LLM 输出结构化失败率高于预期 | 中 | 中 | Parse Repair 机制 + 降级 CritiqueSchema 保底 |
| NVIDIA NIM 额度提前用尽 | 低 | 低 | 切换 Llama 3.3 70B（同平台免费）；mock provider 用于 CI |
| asyncio 并发超时频繁触发 | 低 | 中 | 单角色 25s / 整体 30s 分层超时；Quorum 2/3 保证至少有结果 |
| Judge 输出质量不稳定 | 中 | 中 | 结构化摘要输入 + 显式系统提示约束；Partial Return 兜底 |
| MCP SDK 版本不兼容 | 低 | 低 | 所有 MCP 工具通过 HTTP 调用 FastAPI，降低 SDK 依赖深度 |

### 9.2 进度风险

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| 第3-4周稳定性调试超时 | 中 | 中 | V0.2 降级预案：two轮辩论保持同步接口 |
| 基准测试金标准构建耗时 | 中 | 低 | 提前开始标注（第4周末），放宽至 10 个用例仍可获得数字 |
| PyPI 发布配置问题 | 低 | 低 | 第5周开始配置 TestPyPI，提前验证发布流程 |

---

## 十、简历价值分析

### 10.1 项目描述（英文，简历正文）

```
DebateEngine                                                  Apr – Jun 2026
Structured Adversarial Critique Infrastructure Library for AI-Generated Content
github.com/[username]/debate-engine · pypi.org/project/debate-engine

• Built a production-calibrated Python library bridging the gap between academic 
  multi-agent debate research (Du et al. ICML 2024) and industrial AI code review 
  tooling: where all existing solutions (single-agent Claude Code Review, CodeRabbit, 
  Qodo) output free text, DebateEngine outputs Pydantic v2 CritiqueSchema 
  (defect_type × 8 enums / severity / evidence / fix_kind / confidence) — enabling 
  CI/CD quality gates that programmatically consume structured findings

• Engineered 3-layer Anti-Sycophancy defense validated by ACL 2025 (CONSENSAGENT) 
  and OpenReview 2025 (identity bias): (1) Devil's Advocate role on heterogeneous 
  model, (2) response anonymization stripping model identity before peer critique,  
  (3) structured-summary Judge input preventing majority-opinion bias — each layer 
  verified via ablation study across 3 architectural decision benchmark cases

• Introduced Conformity Impact Score (CIS), industry-first metric quantifying whether Agent 
  stance changes are evidence-driven vs. sycophantic: CIS = Σ(stance_delta × 
  severity_weight) / Σ(stance_delta), with CRITICAL=1.0 / MAJOR=0.6 / MINOR=0.2 
  weights; Full 3-layer configuration improves CIS by +[X]% vs Zero-Defense baseline

• Validated on 25-case DebateEval benchmark (10 regression + 15 benchmark, covering 
  code review / RAG validation / architecture decision): BDR Δ+[X]% vs single-agent 
  baseline; Hallucination Delta +[X]% (RAGAS Faithfulness); P95 latency < 15s 
  (quick_critique) via asyncio.gather concurrent role critique with Quorum 2/3 guard

• Production stability: Quorum 2/3 guarantee, Partial Return on Judge failure, 
  Transport Retry (2×) + Parse Repair (1×) boundaries, cost_budget_usd hard stop, 
  async task API (job_id / polling / cancel) for 2-round debate; published as  
  pip-installable library (PyPI v0.1.0) with 3 MCP tools for Claude Code / OpenClaw 
  integration; CI/CD GitHub Actions quality gate template included

Tech: Python 3.11 · Pydantic v2 · LiteLLM · FastAPI · asyncio · MCP SDK · 
      RAGAS · sentence-transformers · Docker · GitHub Actions / PyPI Trusted Publishing
Default Backend: NVIDIA NIM / MiniMax M2.7 (230B MoE, 10B active params, free tier)
```

### 10.2 面试技术叙事要点

**关于竞品调研的诚实说明：**
"在设计之初，我做了系统的竞品调研。2026年3月Anthropic发布了Claude Code Review，采用多智能体架构，定价$15-25/PR，验证了多智能体代码审查的商业价值。但它是闭源商业服务，成本高，输出是自由文本。GitHub上的Open Code Review等项目也是多智能体架构，但同样缺乏结构化输出。DebateEngine填补了这个空白——提供多智能体对抗+结构化输出+成本可控的开源解决方案。"

**关于NVIDIA NIM选择的技术判断：**
"我选择NVIDIA NIM作为默认后端有三个原因：第一，免费API额度足够覆盖整个开发阶段，降低学生项目的成本风险；第二，MiniMax M2.7是专门为Agentic工作流优化的MoE模型，在复杂推理和工具调用上表现优异；第三，NVIDIA NIM提供OpenAI兼容接口，通过LiteLLM可以一行配置切换到任何其他供应商，系统没有被绑定到单一API。"

**关于项目价值的核心叙事：**
"这个项目的价值不是'让AI们互相辩论'——那个学术上已经被证明有效了。价值在于把这个效果工程化：从'AI说了些意见'升级为'机器可解析的结构化批评报告，可以直接驱动CI/CD决策'。就像代码lint工具，它不只是告诉你代码风格不好，它返回结构化的错误列表，可以集成进CI流程自动阻止不规范的代码合并。DebateEngine对AI批评做的是同样的事。"

---

## 附录：项目关键词索引（面试准备速查）

| 关键词 | 对应设计 |
|---|---|
| Sycophancy | DA 角色 + 匿名化 + 结构化摘要 Judge 输入 |
| Conformity Impact Score | 原创 CIS 指标，量化从众程度 |
| Quorum | 2/3 成功机制，防止最慢节点拖垮整体 |
| Partial Return | Judge 失败时至少返回已有批评，不空手而回 |
| Parse Repair | Pydantic 验证失败时反馈给 LLM 重新生成 |
| Monoculture Collapse | 相同训练数据的多 Agent 有系统性盲点，通过多供应商防御 |
| CritiqueSchema | 8字段 Pydantic v2 结构，批评的"诊断书格式" |
| ConsensusSchema | Judge 汇总输出，含少数意见保全和分歧确认 |
| DebateEval | 7项量化指标评估框架，BDR/CIS/HD/FAR 等 |
| MCP | OpenClaw/Claude Code 工具集成协议 |
| NVIDIA NIM | 免费 AI 推理平台，默认 MiniMax M2.7 230B MoE |

---

_文档版本：v6.0 Final | 生成日期：2026 年 4 月 12 日_
