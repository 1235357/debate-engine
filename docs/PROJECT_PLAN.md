# DebateEngine v6.0
## 结构化多智能体对抗批评引擎 · 正式项目计划书（深度调研修正版）

> **文档性质：** 正式可行性分析与执行计划书
> **版本：** v6.0 — 基于第二轮深度竞品调研的根本性战略修正
> **日期：** 2026 年 4 月 12 日
> **核心立场调整：** 本版本基于对 ARGUS、Quorum、Pydantic AI、AI Code Review 市场、多智能体辩论学术前沿的系统性调研，对项目的**差异化定位、技术路线和落地策略**进行了决定性修正。

---

## 执行摘要（Executive Summary）

**项目一句话定位：**
DebateEngine 是一个 **pip 可安装的 Python 生产库**，通过 Pydantic v2 结构化 Schema 将多智能体批评的输出从自由文本升级为**机器可解析、CI/CD 可集成、可量化评估**的结构化对象，填补了学术多智能体辩论研究与工业界 AI Code Review 工具之间的工程空白。

**v6.0 相比 v5.0 的关键修正：**

| 修正项 | v5.0 立场 | v6.0 修正 | 修正理由 |
|--------|-----------|-----------|----------|
| 直接竞品 | 未提及 ARGUS | ARGUS (argus-debate-ai v5.5.0) 是最接近的 Python 竞品 | 调研发现 ARGUS 已是成熟的多 Agent 辩论框架 |
| Conformity Score | 声称“行业首创” | 重新定位为“辩论因果影响指标”，与现有指标明确区分 | ICLR 2025 CRP、arXiv Identity Bias Conformity 等已存在类似概念 |
| OpenClaw 生态 | 声称 consilium/agora-council 存在 | 这些特定技能在公开 ClawHub 上不存在 | 实际调研未找到对应物 |
| 免费 API | 仅考虑 NVIDIA NIM | Google AI Studio + Groq + NVIDIA NIM 多源策略 | Google AI Studio (Gemini 2.5 Flash) 零成本且质量更高 |
| 技术栈 | LiteLLM + Instructor | LiteLLM + Instructor（确认官方支持） | 集成稳定，`instructor.from_litellm()` 一行可用 |
| 差异化 | “多角色 + 结构化” | 聚焦“代码审查质量门控”垂直场景 | 通用辩论框架竞争激烈，垂直场景有明确市场空白 |

---

## 一、深度竞品调研（2026 年 4 月更新）

### 1.1 直接竞品：ARGUS（最严峻挑战）

| 项目 | 详情 |
|------|------|
| **名称** | ARGUS — Agentic Research & Governance Unified System |
| **版本** | v5.5.0 |
| **PyPI** | `pip install argus-debate-ai` |
| **许可证** | MIT |
| **语言** | Python >=3.11 |
| **定位** | 生产级多 Agent AI 辩论框架，面向科学研究与事实核查 |

**ARGUS 核心能力：**
- **Conceptual Debate Graph (C-DAG)**：命题-证据-反驳的有向图结构，可视化辩论论点关系
- **Bayesian 聚合**：校准置信度，而非简单投票
- **EDDO 算法**：证据导向的辩论编排
- **Value of Information Planning**：决策论实验选择
- **W3C PROV-O Provenance 追踪**：完整审计链
- **50+ 工具集成**，支持 RAG、OpenAPI REST 生成
- **v5.0 扩展**：CHRONOS、PHALANX、FRACTAL、VERICHAIN 等 8 个扩展包
- **Agent 角色**：Moderator、Specialist、Refuter、Jury

**ARGUS 的局限（DebateEngine 的差异化机会）：**
1. **定位为科学研究/事实核查框架**，非代码审查工具
2. **无 CI/CD 集成** — 不输出 SARIF 格式
3. **无 GitHub Action** — 不能作为 PR 质量门控
4. **无 CritiqueSchema 级别的结构化批评输出**
5. **无 Anti-Sycophancy 专用设计**
6. **无 MCP Server**
7. **安装复杂度高** — 50+ 工具集成意味着陡峭的学习曲线

**DebateEngine vs ARGUS 差异化策略：**
> DebateEngine 不与 ARGUS 在“通用辩论框架”赛道竞争。DebateEngine 聚焦**代码审查质量门控**这一垂直场景，提供 ARGUS 不具备的 CI/CD 集成、结构化缺陷清单、GitHub Action 等工程能力。两者是**正交关系**。

---

### 1.2 直接竞品：Quorum（TypeScript 辩论框架）

| 项目 | 详情 |
|------|------|
| **名称** | Quorum — Multi-AI Deliberation Framework |
| **版本** | v1.0+ |
| **语言** | TypeScript |
| **许可证** | MIT |

**Quorum vs DebateEngine 差异化：**
1. **语言生态**：TypeScript vs Python
2. **结构化输出**：Quorum 使用 Zod 但无 Pydantic 级别的 LLM 输出强制约束
3. **安装方式**：npm 全局 CLI vs pip install Python 库
4. **可编程性**：Quorum CLI-first，API 标记为 @experimental；DebateEngine 库-first
5. **代码审查聚焦**：Quorum 是通用辩论工具；DebateEngine 专注代码审查场景

---

### 1.3 间接竞品：AI Code Review 工具（市场空白分析）

| 工具 | 多 Agent？ | 结构化输出？ | CI/CD 集成？ | 价格 |
|------|-----------|-------------|-------------|------|
| CodeRabbit | 否 | 否 | GitHub App | $12/月 |
| Qodo (PR-Agent) | 否 | 否 | GitHub App | 免费/$19/月 |
| Greptile | 否 | 否 | GitHub App | $30/月 |
| Claude Code Review | 否 | 否 | GitHub 集成 | $15-25/次 |
| Open Code Review | 否 | SARIF | GitHub Action | 免费+开源 |
| **DebateEngine** | **是（3 角色）** | **是（Pydantic）** | **是（Action）** | **免费+开源** |

**DebateEngine 的市场空白定位：**
> 当前市场上**不存在**同时满足“多 Agent 对抗 + 结构化 Pydantic 输出 + GitHub Action CI/CD 集成 + 免费开源”的代码审查工具。

---

## 二、Conformity Impact Score (CIS) 重新定位（v6.0 关键修正）

### 2.1 问题：v5.0 的“行业首创”声明不成立

调研发现，以下指标已存在且与 Conformity Score 概念重叠：

| 现有指标 | 来源 | 定义 | 与 CS 的重叠 |
|----------|------|------|-------------|
| Conformity Rate (CRP) | ICLR 2025 | 正确→错误的从众概率 | 高 |
| Conformity | arXiv 2510.07517 | 分歧时转向同伴答案的条件概率 | 高 |
| Sycophancy Score (SS) | arXiv 2509.23055 | LLM-as-Judge 评估的谄媚程度 | 中 |

### 2.2 解决方案：重新定位为“辩论质量退化指标”

**v6.0 重新定义：Conformity Impact Score (CIS)**

> CIS 不是一个度量“从众行为频率”的指标，而是一个度量**从众行为对辩论最终答案质量的因果影响**的指标。

**近似计算方法：**
```
CIS_approx = 1 - (Σ(adopted_high_severity_changes) / Σ(total_stance_changes))
```

**CIS ≈ 0**：从众行为未造成质量损失（辩论是有效的）
**CIS > 0**：从众行为导致了质量退化
**CIS ≈ 1.0**：从众行为导致了严重质量损失

---

## 三、项目核心价值重新定义

### 3.1 从“通用辩论引擎”到“代码审查对抗批评基础设施”

**DebateEngine 是一个专为 AI 辅助编程时代设计的代码审查质量门控库。**

1. **精确的市场空白**：AI Code Review 市场 2025 年达 $7.5 亿，但所有工具都是单 Agent。
2. **可量化的价值主张**：预期 BDR 提升 15-30%
3. **与主流工具链的直接集成**：GitHub Action / MCP Server / Python API / SARIF

### 3.2 三个核心技术护城河

1. **代码审查专用的 CritiqueSchema** — 9 值 defect_type 枚举、三级 severity 直接映射 CI/CD 决策
2. **Conformity Impact Score (CIS)** — 首个度量从众行为对答案质量因果影响的指标
3. **三层 Anti-Sycophancy + 代码审查专用角色模板** — DA 异构模型 + 匿名化 + 结构化摘要 Judge

---

## 四、落地场景与商业价值论证

### 4.1 场景一：GitHub PR 质量门控（核心场景）

痛点：84% 开发者使用 AI 编码工具，41% 的 commits 是 AI 辅助的，但审查容量未同步扩充。

### 4.2 场景二：Claude Code / Cursor MCP 集成

### 4.3 场景三：RAG 应用幻觉检测

### 4.4 场景四：LangGraph 工作流节点

---

## 五、技术可行性深度分析

### 5.1 技术栈选型

| 组件 | 选型 | 版本 | 维护状态 |
|------|------|------|----------|
| 结构化输出 | Pydantic v2 | v2.x | 极活跃 |
| LLM 调用 | LiteLLM | v1.83+ | 极活跃（日更） |
| 结构化输出增强 | Instructor | v1.13+ | 活跃 |
| API 框架 | FastAPI | v0.115+ | 极活跃 |
| MCP Server | FastMCP | v1.24+ | 极活跃 |
| CI/CD | GitHub Actions | — | — |
| 容器化 | Docker | — | — |

### 5.2 免费 LLM API 策略

| 优先级 | 提供商 | 免费额度 | 最佳模型 |
|--------|--------|----------|----------|
| 1 | Google AI Studio | 充足 (2-15 RPM) | Gemini 2.5 Flash |
| 2 | Groq | 14,400 req/天 | Llama 3.3 70B |
| 3 | NVIDIA NIM | 无限 (40 RPM) | MiniMax M2.7 |

**自动降级链：** Google AI Studio 429 → Groq → NVIDIA NIM → 本地 Ollama

---

## 六、与热门生态的互补关系

- **Claude Code**: 天然上下游关系（生成 → 批评）
- **GitHub Actions**: SARIF + CRITICAL 阻止合并
- **LangGraph**: 质量检查点节点
- **ARGUS**: 竞品转互补（通用辩论 → 代码审查门控）

---

## 七、DebateEval 评估框架

| 指标 | 定义 | 原创性 |
|------|------|--------|
| **BDR** | Bug Discovery Rate | 已有概念 |
| **FAR** | False Alarm Rate | 已有概念 |
| **HD** | Hallucination Delta | 已有概念 |
| **CIS** | Conformity Impact Score | **原创** |
| **CE** | Convergence Efficiency | 已有概念 |
| **RD** | Reasoning Depth | 已有概念 |
| **CV** | Consensus Validity | 已有概念 |

---

## 八、版本路线图

### 8.1 第一阶段：核心重构 + GitHub Action（当前执行）

**交付物：**
1. Pydantic v2 Schema 体系（CritiqueSchema + ConsensusSchema + CIS）
2. LiteLLM + Instructor Provider 层（多源降级链）
3. QuickCritiqueEngine 编排层（5 阶段管线）
4. FastAPI REST API（5 个端点）
5. GitHub Action（PR 质量门控 + SARIF 输出）
6. MCP Server（3 个工具）
7. DebateEval 评估框架（7 项指标）
8. 158 测试全通过
9. Docker 部署
10. 完整 README

### 8.2 第二阶段：完善 + 发布

- PyPI 正式发布
- 15 个基准测试用例运行
- GitHub Actions CI/CD
- Jupyter Notebook 示例

---

## 九、简历呈现规格

```
DebateEngine                                                  Apr – Jun 2026
Structured Adversarial Code Review Engine — Multi-Agent Critique with Pydantic v2
github.com/1235357/debate-engine

• Built a pip-installable Python library filling the gap between academic multi-agent
  debate research (Du et al. ICML 2024, DTE EMNLP 2025) and industrial AI code
  review tooling: outputs Pydantic v2 CritiqueSchema enabling CI/CD quality gates

• Engineered 3-layer Anti-Sycophancy defense validated by ACL 2025 (CONSENSAGENT),
  ICLR 2025 (Conformity Rate), and arXiv 2510.07517 (Identity Bias + Anonymization)

• Introduced Conformity Impact Score (CIS), quantifying causal quality degradation
  from sycophantic stance changes — distinct from frequency-based measures

• Shipped GitHub Action for PR quality gating with SARIF output, MCP Server (3 tools
  for Claude Code / Cursor), FastAPI REST API, Docker deployment; 158 tests passing

Tech: Python 3.11 · Pydantic v2 · LiteLLM · Instructor · FastAPI · asyncio ·
      FastMCP · Docker · GitHub Actions
```

---

_文档版本：v6.0 Final | 生成日期：2026 年 4 月 12 日_
_基础：v5.0 计划书 + 第二轮深度竞品调研（ARGUS/Quorum/学术前沿/免费 API）_
_执行范围：推倒重构 → GitHub 发布 → GitHub Actions CI/CD → 可用 Demo_
_项目负责人：Tony Ye (Zhentong Ye)_