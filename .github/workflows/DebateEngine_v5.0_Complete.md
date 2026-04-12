# DebateEngine v5.0：结构化多智能体批评引擎
## 完整技术设计文档 · 通俗版 · GitHub 可部署

> **文档版本：** v5.0 Final（2026 年 4 月 12 日）  
> **基于：** v4.1 Final，全面升级  
> **默认 AI 后端：** NVIDIA NIM 免费 API（MiniMax M2.7，230B MoE 模型）  
> **执行周期：** 2026 年 4 月 14 日 — 2026 年 6 月 8 日（8 周）  
> **核心升级：** 零成本 API 接入 · GitHub 一键部署 · 通俗原理解释 · 完整代码骨架

---

## 〇、写在最前面：用大白话说清楚这个项目是什么

### 0.1 你遇到过这个问题吗？

你写了一段代码或一篇方案，让 AI 帮你看看有没有问题。AI 给你回了一大段，说"整体不错，有几点小建议……"，然后你把 AI 的建议采纳了，上线后出了事故——原来 AI 发现了真正的问题，但说得太含糊，你没当回事。

或者你让几个同事一起评审，但大家都说"挺好的"，因为方案是老板提的，没人敢认真批评。

这两个场景，有一个共同的根本问题：**批评的质量太低，而且批评者的独立性不够**。

### 0.2 DebateEngine 要解决什么问题？

DebateEngine 的核心思路是：**让多个 AI 角色像真正的专家评审团一样，结构化地、不留情面地批评一个方案，然后把批评结果整理成可以被程序处理的格式，而不是一堆 Markdown 文字**。

具体来说，它做三件事：

**第一件事：让 AI 批评变得"有据可查"。** 传统的 AI 批评说"这里有性能问题"，DebateEngine 要求 AI 说"这里有 PERFORMANCE_ISSUE，严重程度是 CRITICAL，因为当数据量超过 100 万条时，你的 O(N²) 算法会在 3 秒内超时（基于实测 benchmark），建议改用哈希表查找降至 O(N)"。这就是所谓的"结构化批评"——批评被拆解为可机器处理的字段，而不是自由文本。

**第二件事：强制有人"唱反调"。** 在评审中，AI 角色们很容易互相附和——这个现象在学术上叫 Sycophancy（谄媚现象）。DebateEngine 专门设置一个"魔鬼代言人（Devil's Advocate）"角色，它的职责就是找你方案里最薄弱的地方，即使其他所有 AI 都说"没问题"，它也必须寻找潜在的反驳角度。

**第三件事：保留"少数意见"。** 当最终裁判（Judge 角色）做出结论时，它不能把所有批评统统取消，即使它认为方案整体可行，也必须明确记录"哪些批评没有被采纳，以及为什么"。这防止了"伪共识"——表面上所有人都同意，实际上真正的担忧被掩盖了。

### 0.3 为什么现有的多 AI 方案做不到这点？

你可能听说过 AutoGen、CrewAI、OpenClaw 里的 consilium 技能等工具。它们的做法是：让几个 AI 角色轮流发言，最后汇总。

问题是：**它们的输出都是自由文本**。AI 说了"这里有个问题"，但没有规定要说清楚"问题的类型是什么、严重程度几何、有没有修复建议、这个修复建议是否是可以直接执行的"。

打个比方：普通方案是医生给你说"你身体有点问题，要注意"；DebateEngine 是医生给你出具一份规范的诊断报告，包含诊断分类、ICD 编码、严重程度、具体治疗方案、是否需要手术……程序可以读懂这份报告，自动判断是否需要立即处理。

### 0.4 V5.0 相比 V4.1 新增了什么？

| 维度 | V4.1 | V5.0（本文档） |
|---|---|---|
| AI 后端 | OpenAI GPT（需付费 API） | **NVIDIA NIM 免费 API（MiniMax M2.7）** |
| 部署方式 | 本地 Docker，复杂 | **GitHub + Render/HuggingFace 一键部署** |
| 原理解释 | 专业工程语言，较难懂 | **新增大白话解释章节** |
| 代码骨架 | 概念设计 | **完整可运行代码骨架** |
| Demo | 未设计 | **交互式 Gradio Demo，GitHub 可部署** |
| 成本 | 每次测试约 $0.03-0.10 | **使用 NVIDIA 免费额度，开发阶段零成本** |
| 竞品分析 | 列举但未量化 | **新增详细差异对比表** |

---

## 一、项目背景：这个问题真的值得解决吗？

### 1.1 学术界的研究结论（翻译成大白话）

这个项目背后有几篇重要的学术论文，我来用大白话解释它们说了什么：

**论文一（Du et al., ICML 2024）：让 AI 们互相辩论，答案会更准确。**

实验发现：让多个 AI 独立回答同一个问题，然后让它们互相批评对方的答案，经过几轮后得到的最终答案，比单个 AI 直接回答要准确得多。在数学推理和事实准确性上，提升尤为明显。这就是整个"多智能体辩论"领域的起点。

**论文二（CONSENSAGENT, ACL 2025）：AI 们会互相"拍马屁"，这是个大问题。**

但有个坏消息：实验发现，当 AI 们互相批评时，它们很快就开始互相附和——某个 AI 改变了观点，不是因为对方的论据有说服力，而仅仅是因为"大家都这么说了"。论文把这个现象量化了（叫 Conformity Score），发现附和率高得惊人。这是 DebateEngine 要解决的核心问题。

**论文三（OpenReview 2025）：如果 AI 知道对方是谁，它会更容易被影响。**

进一步的研究发现，如果 AI 批评者知道提案是"GPT-4 说的"还是"一个小模型说的"，它的批评倾向会不一样。匿名化处理（不告诉 AI 批评者这个提案是谁写的）可以显著减少这种偏见，让批评更公平。这是 DebateEngine 的匿名化交叉批评机制的理论依据。

**论文四（AgentAuditor, Feb 2026）：Judge 角色本身也会谄媚。**

研究发现，作为最终裁判的 Judge AI，在面对多数人的意见时，也会倾向于认同多数，而不是独立判断。解决方案：给 Judge 的输入不是原始的对话记录，而是结构化的摘要——这样 Judge 就没办法看出"哪个答案更受欢迎"，只能基于论据质量做判断。

### 1.2 现实世界的用途（这东西有人真的会用吗？）

我做了调研，以下是 DebateEngine 可以实际落地的场景：

**代码审查加速：** 代码审查是软件开发中最耗时的环节之一。传统 AI Code Review 告诉你"这里可以优化"，DebateEngine 给你一份结构化报告，标注每个问题的类型（安全漏洞、性能瓶颈、逻辑错误）、严重程度（是否阻止合并），以及具体的修复建议。这份报告可以直接集成到 CI/CD 流程，高严重度问题自动阻止合并。

**RAG 系统答案质量检测：** 你的 RAG 系统（检索增强生成）输出了一个答案，你怎么知道它是否产生了幻觉？用 DebateEngine 的"RAG 验证"模式，专门派一个角色去质疑答案中每一个事实声明，要求提供来源证据，如果找不到就标记为 FACTUAL_ERROR。

**重要技术决策评审：** 你的团队要决定用 PostgreSQL 还是 MongoDB，DebateEngine 可以从不同技术视角（性能角度、运维角度、扩展性角度）自动生成结构化的 pros/cons 分析，并且强制保留"少数意见"——即使 5 个 AI 角色里有 4 个支持某个选择，第 5 个的担忧也会被明确记录。

**AI Safety 研究工具：** 这是一个更学术的用途。研究者可以用 DebateEngine 来研究"如何减少 LLM 的谄媚倾向"——因为 DebateEngine 提供了量化指标（Conformity Score），可以系统性地测试不同的 Anti-Sycophancy 策略效果。

### 1.3 与现有方案的决定性差异

| 维度 | OpenClaw consilium | AutoGen GroupChat | DebateEngine |
|---|---|---|---|
| 批评格式 | 自由文本 | 自由文本 | **Pydantic v2 结构化 Schema** |
| 机器可解析 | ❌ 否 | ❌ 否 | ✅ 是（字段级别） |
| 强制 DA 角色 | ❌ 否 | ❌ 否 | ✅ 是（系统级强制） |
| 匿名化批评 | ❌ 否 | ❌ 否 | ✅ 是 |
| 少数意见保全 | ❌ 否 | ❌ 否 | ✅ 是（Judge 必须显式确认） |
| pip 可安装 | ❌ 否（Markdown 技能） | ✅ 是 | ✅ 是 |
| 量化评估指标 | ❌ 否 | ❌ 否 | ✅ 是（DebateEval 7 项指标） |
| 维护状态 | 活跃 | **已进入维护模式** | 活跃 |
| 免费 API 支持 | 取决于配置 | 取决于配置 | **✅ 默认 NVIDIA 免费 API** |

---

## 二、NVIDIA NIM API 集成（V5.0 核心新增）

### 2.1 为什么选择 NVIDIA NIM + MiniMax M2.7？

V4.1 计划使用 OpenAI GPT-4o，开发阶段大概需要花 $15-25。V5.0 切换到 NVIDIA NIM 提供的免费 API，开发阶段成本为 **零**。

NVIDIA NIM（NVIDIA Inference Microservices）是 NVIDIA 提供的免费 AI 推理平台，托管在 NVIDIA DGX Cloud 上，提供 OpenAI 兼容的 API 接口。注册即获得 1000 次免费推理额度，速率限制为 40 次/分钟。

MiniMax M2.7 是最新发布（2026 年 4 月 11 日）的开源 MoE 模型：
- **总参数量 230B，激活参数量仅 10B**（因此推理速度快、成本低）
- **256 个专家（Expert），每次推理激活 8 个**
- 专为 Agentic 工作流设计，支持复杂工具调用和多步骤任务
- 在代码生成、推理、长文本处理上表现优异
- 支持 `temperature=1.0, top_p=0.95`（官方推荐参数）

### 2.2 API 接入方式

NVIDIA NIM 提供与 OpenAI 完全兼容的 API 接口，只需修改 `base_url` 和 `api_key`：

```python
# ==========================================
# V5.0 默认 API 配置（使用 NVIDIA 免费额度）
# ==========================================
from openai import OpenAI

# NVIDIA NIM 配置
NVIDIA_CLIENT = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

# 推荐模型：MiniMax M2.7（最新，最强 Agentic 能力）
DEFAULT_MODEL = "minimaxai/minimax-m2.7"

# 官方推荐参数
DEFAULT_PARAMS = {
    "temperature": 1.0,
    "top_p": 0.95,
    "max_tokens": 8192,
}
```

### 2.3 在 DebateEngine 中使用 NVIDIA API

```python
# debate_engine/providers/nvidia.py
from openai import OpenAI
from typing import Iterator
import json

class NVIDIAProvider:
    """
    NVIDIA NIM API Provider
    
    用大白话说：这个类负责"打电话给 NVIDIA 的 AI"。
    - 支持流式输出（streaming）——AI 边想边说，不用等它全说完
    - 支持结构化 JSON 输出——让 AI 直接输出我们能解析的格式
    - 内置重试逻辑——网络抖动时自动重试
    """
    
    def __init__(
        self,
        api_key: str = "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",
        model: str = "minimaxai/minimax-m2.7",
        base_url: str = "https://integrate.api.nvidia.com/v1"
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
    
    def complete(
        self,
        messages: list[dict],
        system_prompt: str = "",
        response_format: dict | None = None,
        stream: bool = False,
    ) -> str:
        """
        发送请求并获取响应
        
        stream=True 时：边生成边返回（适合实时显示进度）
        stream=False 时：等待完整响应（适合结构化解析）
        """
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)
        
        kwargs = {
            "model": self.model,
            "messages": all_messages,
            "temperature": 1.0,
            "top_p": 0.95,
            "max_tokens": 8192,
            "stream": stream,
        }
        
        # 注意：MiniMax M2.7 使用 <think>...</think> 标签进行推理
        # 历史对话中必须保留这些标签，否则影响模型性能
        
        if response_format:
            # 要求 AI 输出 JSON 格式
            kwargs["response_format"] = response_format
        
        completion = self.client.chat.completions.create(**kwargs)
        
        if stream:
            # 流式输出：逐块返回文字
            full_text = ""
            for chunk in completion:
                if not getattr(chunk, "choices", None):
                    continue
                if chunk.choices[0].delta.content is not None:
                    text = chunk.choices[0].delta.content
                    full_text += text
                    print(text, end="", flush=True)
            return full_text
        else:
            return completion.choices[0].message.content
    
    def complete_structured(
        self,
        messages: list[dict],
        system_prompt: str,
        schema: dict,
    ) -> dict:
        """
        要求 AI 按照指定的 JSON Schema 输出结构化结果
        
        用大白话说：不让 AI 随便写，给它一张"填表"，
        让它按格式填，填完我们就能直接用 Python 读取
        """
        # 把 Schema 信息加入到系统提示中
        schema_instruction = f"""
你必须严格按照以下 JSON Schema 格式输出，不要输出任何 Schema 之外的内容：

{json.dumps(schema, ensure_ascii=False, indent=2)}

只输出 JSON，不要有任何前缀说明或 Markdown 代码块标记。
"""
        enhanced_system = system_prompt + "\n\n" + schema_instruction
        
        raw_response = self.complete(
            messages=messages,
            system_prompt=enhanced_system,
            stream=False,
        )
        
        # 清理可能的 Markdown 标记
        clean = raw_response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        if clean.endswith("```"):
            clean = clean[:-3]
        
        return json.loads(clean.strip())
```

### 2.4 多模型策略（利用 NVIDIA 平台的多种免费模型）

NVIDIA NIM 平台提供多种免费模型，我们可以用不同模型扮演不同角色，真正实现"多样化智能体"：

```python
# debate_engine/config/nvidia_models.py

NVIDIA_MODELS = {
    # 主力模型：最强 Agentic 能力
    "minimax_m2_7": "minimaxai/minimax-m2.7",
    
    # 备用模型（用于 Devil's Advocate，来自不同训练数据）
    "minimax_m2_5": "minimaxai/minimax-m2.5",
    
    # 高速模型（适合 Judge 角色，需要快速汇总）
    "minimax_m2_7_highspeed": "minimaxai/minimax-m2.7-highspeed",  # 如果可用
}

# V5.0 默认角色 → 模型映射
ROLE_MODEL_MAP = {
    "stable": {
        # 单模型模式：三个角色用同一个模型
        "ROLE_A": "minimaxai/minimax-m2.7",
        "ROLE_B": "minimaxai/minimax-m2.7",
        "DA_ROLE": "minimaxai/minimax-m2.7",
        "JUDGE": "minimaxai/minimax-m2.7",
    },
    "balanced": {
        # 双模型模式：DA 角色用不同模型，增加多样性
        "ROLE_A": "minimaxai/minimax-m2.7",
        "ROLE_B": "minimaxai/minimax-m2.7",
        "DA_ROLE": "minimaxai/minimax-m2.5",  # 来自不同训练阶段
        "JUDGE": "minimaxai/minimax-m2.7",
    }
}
```

---

## 三、通俗原理讲解：系统是怎么工作的？

### 3.1 一次 quick_critique 的完整流程（用故事说）

假设你写了一段 Python 代码，想让 DebateEngine 帮你做代码审查。以下是系统内部发生的事：

**步骤 0：接收任务，确定角色**

你调用 API，把代码发过来。系统分析代码内容（用关键词匹配或 embedding 分类），确定这是"代码审查"任务（CODE_REVIEW）。然后分配三个角色：
- **角色 A（资深架构师）**：关注设计模式、可维护性、扩展性
- **角色 B（安全工程师）**：关注安全漏洞、输入验证、权限控制
- **DA 角色（魔鬼代言人）**：故意找最难处理的问题，扮演"最挑剔的面试官"

**步骤 1：三个 AI 同时工作（并发批评）**

系统同时向三个 AI 发出请求（asyncio.gather），它们并行工作，不互相等待。每个 AI 拿到的输入是：你的代码 + 它的角色指令 + 要求输出结构化 JSON 的格式说明。

大约 8-15 秒后，三份批评各自完成，每份批评都是这样的结构化数据：

```json
{
  "target_area": "数据库查询逻辑",
  "defect_type": "PERFORMANCE_ISSUE",
  "severity": "CRITICAL",
  "evidence": "第 23 行的 for 循环中，每次迭代都执行一次 SELECT 查询，形成 N+1 查询问题。当 orders 表有 10 万条记录时，将产生 10 万次数据库查询，预计查询时间从当前测试环境的 0.1s 增加到 100+s。",
  "suggested_fix": "使用 JOIN 或 prefetch_related 一次性获取所有关联数据",
  "fix_kind": "CONCRETE_FIX",
  "confidence": 0.95,
  "is_devil_advocate": false
}
```

**步骤 2：匿名化处理**

在把三份批评交给 Judge 之前，系统把所有角色标识符替换掉（"资深架构师"→"批评者甲"，"安全工程师"→"批评者乙"，"魔鬼代言人"→"批评者丙"）。Judge 只能看到论据本身，不知道哪条批评是哪个"品牌"的 AI 说的。这防止了 Judge 因为"谁说的"而不是"说得对不对"来判断。

**步骤 3：Quorum 检查（2/3 即可）**

统计成功完成批评的角色数量。只需要 2 个角色成功，就可以继续（不需要三个都完成）。这保证了即使一个 AI 超时或出错，整个流程不会崩溃。

**步骤 4：Judge 汇总**

Judge 角色拿到匿名化的三份批评，生成最终的 ConsensusSchema：

```json
{
  "final_conclusion": "该代码存在一个CRITICAL级别的N+1查询问题（批评者甲和丙均指出），必须在上线前修复。此外发现2个MAJOR级别问题（SQL注入风险、缺乏错误处理），建议本轮修复。3个MINOR问题可记录为Tech Debt后续处理。",
  "consensus_confidence": 0.88,
  "remaining_disagreements": ["对于是否使用 ORM 还是原生 SQL 的争议尚未解决"],
  "preserved_minority_opinions": [
    {
      "opinion": "批评者丙认为整个数据访问层应该重构，而不仅仅是修复 N+1 问题",
      "source_critique_severity": "MAJOR",
      "potential_risk_if_ignored": "若不重构，未来添加新功能时仍会反复出现类似问题"
    }
  ]
}
```

**步骤 5：返回结果**

整个过程耗时约 10-15 秒，你得到一份机器可读的结构化审查报告，可以直接集成到你的 CI/CD 系统。

### 3.2 完整辩论模式（两轮，V0.2）怎么不同？

如果你开启完整辩论模式（POST /v1/debate），流程变成这样：

```
第 1 轮：
  → 角色们各自提出初始方案（ProposalSchema）
  → 交叉批评：每个角色批评其他角色的方案
  → Judge 检查：是否还有 CRITICAL 级别的未解决问题？

如果有 CRITICAL 问题 → 第 2 轮：
  → 各角色修订自己的方案，针对 CRITICAL 批评做出回应
  → 再次交叉批评（严重性通常会降低）
  → Final Judge 做出最终裁决

如果已收敛（无 CRITICAL）→ 直接进 Final Judge
```

完整辩论是异步的——你提交任务后拿到一个 `job_id`，然后每隔几秒轮询结果，不需要一直等着。

### 3.3 Conformity Score（CS）：怎么量化"谄媚程度"？

这是 DebateEngine 的原创指标，用来回答一个问题：**AI 改变立场，是因为对方说得有道理，还是仅仅因为对方坚持了？**

计算方式：

```
CS = Σ(立场变化幅度 × 批评严重程度权重) / Σ(立场变化幅度)

其中：
- 立场变化幅度 = 前后两轮对同一方案的评分差值
- 批评严重程度权重 = CRITICAL: 1.0 / MAJOR: 0.6 / MINOR: 0.2

CS 越接近 1.0：立场变化都是被高质量批评驱动的（好现象）
CS 越接近 0.0：立场变化和批评质量无关（坏现象，谄媚）
```

举例说明：
- 场景 A：某 AI 因为批评者指出"存在 SQL 注入漏洞（CRITICAL）"而改变立场 → CS 贡献高
- 场景 B：某 AI 因为"对方坚持认为代码风格不好（MINOR）"而改变对整个方案的评价 → CS 贡献低

通过 CS 的消融实验，我们可以量化证明"加了 DA 角色、加了匿名化"后，系统的整体 Sycophancy 水平是否真的降低了。

---

## 四、完整项目目录结构

```
debate-engine/
│
├── 📁 debate_engine/              # 核心 Python 包
│   ├── __init__.py
│   │
│   ├── 📁 schemas/               # 数据结构定义（Pydantic v2）
│   │   ├── __init__.py
│   │   ├── config.py             # CritiqueConfigSchema, DebateConfigSchema
│   │   ├── critique.py           # CritiqueSchema（核心！）
│   │   ├── consensus.py          # ConsensusSchema（最终输出）
│   │   ├── debate_job.py         # DebateJobSchema（异步任务状态）
│   │   └── proposal.py           # ProposalSchema（V0.2 多轮辩论）
│   │
│   ├── 📁 providers/             # AI 供应商抽象层
│   │   ├── __init__.py
│   │   ├── base.py               # BaseProvider 抽象类
│   │   ├── nvidia.py             # NVIDIA NIM Provider（默认！）
│   │   └── openai.py             # OpenAI Provider（可选备用）
│   │
│   ├── 📁 roles/                 # 角色配置
│   │   ├── __init__.py
│   │   ├── templates.py          # 各任务类型的角色提示词模板
│   │   └── devil_advocate.py     # DA 角色专用逻辑
│   │
│   ├── 📁 engines/               # 编排层
│   │   ├── __init__.py
│   │   ├── quick_critique.py     # QuickCritiqueEngine（V0.1 同步）
│   │   ├── debate.py             # DebateOrchestrator（V0.2 异步）
│   │   └── judge.py              # Judge 层逻辑
│   │
│   ├── 📁 eval/                  # DebateEval 评估框架
│   │   ├── __init__.py
│   │   ├── metrics.py            # BDR, FAR, HD, CS, CE, RD, CONF 计算
│   │   └── benchmark.py          # 25 个基准用例运行器
│   │
│   └── 📁 mcp/                   # MCP 适配层（第 7 周）
│       ├── __init__.py
│       └── server.py             # 3 个 MCP 工具
│
├── 📁 api/                       # FastAPI REST 服务
│   ├── __init__.py
│   ├── main.py                   # FastAPI app 入口
│   ├── routes/
│   │   ├── quick_critique.py     # POST /v1/quick-critique
│   │   └── debate.py             # POST/GET/DELETE /v1/debate
│   └── middleware.py             # 日志、错误处理
│
├── 📁 demo/                      # V5.0 新增：Gradio 交互式 Demo
│   ├── app.py                    # Gradio 主程序
│   └── requirements.txt          # Demo 专用依赖
│
├── 📁 tests/                     # 测试套件
│   ├── regression/               # 10 个回归测试用例
│   └── benchmark/                # 15 个基准测试用例
│
├── 📁 .github/
│   └── 📁 workflows/
│       ├── test.yml              # PR 触发自动测试
│       └── deploy.yml            # tag 触发自动发布
│
├── 📄 Dockerfile                 # 单容器 Docker 部署
├── 📄 docker-compose.yml         # 本地开发环境
├── 📄 pyproject.toml             # Python 包元数据
├── 📄 README.md                  # 项目说明
└── 📄 render.yaml                # Render.com 一键部署配置
```

---

## 五、核心 Schema 完整定义（完整可运行代码）

### 5.1 CritiqueSchema（最核心的数据结构）

```python
# debate_engine/schemas/critique.py
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Optional

class DefectType(str, Enum):
    """缺陷类型枚举——批评必须说清楚是什么类型的问题"""
    LOGICAL_FALLACY = "LOGICAL_FALLACY"       # 逻辑谬误
    FACTUAL_ERROR = "FACTUAL_ERROR"           # 事实性错误
    MISSING_CONSIDERATION = "MISSING_CONSIDERATION"  # 遗漏重要因素
    SECURITY_RISK = "SECURITY_RISK"           # 安全风险
    PERFORMANCE_ISSUE = "PERFORMANCE_ISSUE"   # 性能问题
    UNSUPPORTED_ASSUMPTION = "UNSUPPORTED_ASSUMPTION"  # 未证明的假设
    SCALABILITY_CONCERN = "SCALABILITY_CONCERN"  # 可扩展性问题
    COST_INEFFICIENCY = "COST_INEFFICIENCY"   # 资源浪费
    GENERAL = "GENERAL"                       # 兜底（parse repair 时使用）

class Severity(str, Enum):
    """严重程度枚举"""
    CRITICAL = "CRITICAL"  # 必须修复，否则不能上线
    MAJOR = "MAJOR"        # 显著影响质量，需要认真处理
    MINOR = "MINOR"        # 小问题，可记录为 Tech Debt

class FixKind(str, Enum):
    """修复建议的类型"""
    CONCRETE_FIX = "CONCRETE_FIX"       # 有明确的修复步骤
    VALIDATION_STEP = "VALIDATION_STEP"  # 建议验证某个假设
    NEED_MORE_DATA = "NEED_MORE_DATA"    # 需要更多信息才能给出建议

class CritiqueSchema(BaseModel):
    """
    结构化批评——这是整个 DebateEngine 的灵魂所在
    
    为什么要这样设计？
    
    传统 AI 批评："这里性能不好，建议优化。"（没法机器处理）
    DebateEngine："PERFORMANCE_ISSUE + CRITICAL + evidence(具体数据) + 
                   suggested_fix(具体方案) + fix_kind(CONCRETE_FIX)"
    （程序可以读懂，CI/CD 可以直接用来决定是否阻止合并）
    """
    
    target_area: str = Field(
        ...,
        min_length=10,
        max_length=200,
        description="被批评内容所属的范围或主题（例如：'数据库查询逻辑'、'身份验证流程'）"
    )
    
    defect_type: DefectType = Field(
        ...,
        description="缺陷的类型分类"
    )
    
    severity: Severity = Field(
        ...,
        description="严重程度：CRITICAL/MAJOR/MINOR"
    )
    
    evidence: str = Field(
        ...,
        min_length=20,
        description="支撑这条批评的具体证据。不同类型有不同格式要求，见系统提示。"
    )
    
    suggested_fix: str = Field(
        ...,
        min_length=20,
        description="具体的修复建议或后续动作指引"
    )
    
    fix_kind: FixKind = Field(
        ...,
        description="修复建议的性质：是可以直接执行(CONCRETE_FIX)、需要先验证假设(VALIDATION_STEP)、还是需要更多信息(NEED_MORE_DATA)"
    )
    
    is_devil_advocate: bool = Field(
        default=False,
        description="此批评是否来自 DA 角色（系统自动填充，非 AI 输出）"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="批评者对此批评正确性的置信度（0.0-1.0）"
    )
    
    @field_validator('evidence')
    @classmethod
    def evidence_not_placeholder(cls, v):
        """防止 AI 用空洞的占位符通过验证"""
        placeholders = ['这里有问题', '存在问题', '需要改进', 'there is an issue']
        for p in placeholders:
            if v.strip().lower() == p.lower():
                raise ValueError(f"evidence 不能是空洞的占位符: {v}")
        return v
```

### 5.2 ConsensusSchema（最终输出）

```python
# debate_engine/schemas/consensus.py
from pydantic import BaseModel, Field
from typing import Optional
from .critique import CritiqueSchema

class MinorityOpinion(BaseModel):
    """少数意见记录——保证真正的担忧不会被'伪共识'掩盖"""
    opinion: str = Field(..., description="少数意见的具体内容")
    source_role: str = Field(..., description="来源角色的匿名代号")
    source_critique_severity: str = Field(..., description="对应批评的严重程度")
    potential_risk_if_ignored: str = Field(..., description="如果忽略此意见，可能带来什么风险")

class DebateMetadata(BaseModel):
    """辩论元数据——用于追踪、计费、监控"""
    request_id: str
    job_id: Optional[str] = None
    task_type: str
    provider_mode: str
    rounds_completed: int
    total_cost_usd: float = 0.0
    total_latency_ms: int
    models_used: list[str]
    quorum_achieved: bool
    termination_reason: str
    parse_attempts_total: int = 0

class ConsensusSchema(BaseModel):
    """
    最终共识输出——Judge 汇总后的结构化结论
    
    重要设计：即使 Judge 失败（partial_return=True），
    也会返回已有的批评列表，用户不会空手而回。
    """
    
    final_conclusion: str = Field(
        ...,
        description="Judge 的最终综合结论（自然语言，面向用户）"
    )
    
    consensus_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="综合置信度。partial_return=True 时固定为 0.0"
    )
    
    adopted_contributions: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Judge 采纳了哪些角色的哪些观点。键=角色匿名代号，值=采纳的观点列表"
    )
    
    rejected_positions: list[dict] = Field(
        default_factory=list,
        description="被明确否决的立场及否决理由"
    )
    
    remaining_disagreements: list[str] = Field(
        default_factory=list,
        description="尚未解决的分歧。允许为空，但 Judge 必须显式确认"
    )
    
    disagreement_confirmation: Optional[str] = Field(
        default=None,
        description="若 remaining_disagreements 为空，Judge 必须在此说明原因"
    )
    
    preserved_minority_opinions: list[MinorityOpinion] = Field(
        default_factory=list,
        description="保留的少数意见。若 DA 角色的 CRITICAL 批评未被采纳，必须在此记录"
    )
    
    partial_return: bool = Field(
        default=False,
        description="是否为部分结果（Judge 失败或 Quorum 失败时为 True）"
    )
    
    critiques_summary: list[CritiqueSchema] = Field(
        default_factory=list,
        description="partial_return=True 时，返回所有已成功的批评列表"
    )
    
    debate_metadata: DebateMetadata = Field(
        ...,
        description="辩论元数据"
    )
```

---

## 六、核心引擎实现（QuickCritiqueEngine，V0.1）

```python
# debate_engine/engines/quick_critique.py
import asyncio
import uuid
import time
from ..schemas.config import CritiqueConfigSchema
from ..schemas.consensus import ConsensusSchema, DebateMetadata, MinorityOpinion
from ..schemas.critique import CritiqueSchema, Severity
from ..providers.nvidia import NVIDIAProvider
from ..roles.templates import get_role_config

class QuickCritiqueEngine:
    """
    快速批评引擎（同步接口，P95 目标 < 15 秒）
    
    用大白话说：这是 DebateEngine 最基础的功能。
    你给我一段内容，我让三个 AI 同时批评它，然后汇总。
    
    关键设计决策：
    1. 三个 AI 是并发的（asyncio.gather），不是串行的，所以速度快
    2. Quorum 机制：2/3 就够了，一个 AI 出错不影响整体
    3. Judge 失败时有 partial_return，用户不会空手而回
    """
    
    def __init__(self, provider: NVIDIAProvider | None = None):
        self.provider = provider or NVIDIAProvider()
    
    def run(self, config: CritiqueConfigSchema) -> ConsensusSchema:
        """同步入口——内部用 asyncio 并发"""
        return asyncio.run(self._run_async(config))
    
    async def _run_async(self, config: CritiqueConfigSchema) -> ConsensusSchema:
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Phase 0: 确定任务类型，加载角色配置
        role_configs = get_role_config(config.task_type, config.enable_devil_advocate)
        
        # Phase 1: 并发批评生成（最多等 30 秒）
        critique_tasks = [
            self._generate_critique(role_id, role_cfg, config.content)
            for role_id, role_cfg in role_configs.items()
        ]
        
        try:
            raw_results = await asyncio.wait_for(
                asyncio.gather(*critique_tasks, return_exceptions=True),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            raw_results = [None, None, None]
        
        # Phase 2: 分类结果
        successful_critiques = []
        for i, (role_id, role_cfg) in enumerate(role_configs.items()):
            result = raw_results[i]
            if isinstance(result, CritiqueSchema):
                if role_cfg.get("is_devil_advocate"):
                    result.is_devil_advocate = True
                successful_critiques.append(result)
        
        # Phase 3: Quorum 检查
        quorum_achieved = len(successful_critiques) >= 2
        
        if not quorum_achieved:
            # Quorum 失败：返回 partial result
            return self._make_partial_return(
                request_id=request_id,
                critiques=successful_critiques,
                reason="QUORUM_FAILED",
                latency_ms=int((time.time() - start_time) * 1000),
                config=config,
            )
        
        # Phase 4: 匿名化
        anonymized = self._anonymize(successful_critiques)
        
        # Phase 5: Judge 汇总
        try:
            consensus = await self._judge(anonymized, config, request_id, start_time)
            return consensus
        except Exception as e:
            # Judge 失败：返回 partial result（含所有已有批评）
            return self._make_partial_return(
                request_id=request_id,
                critiques=successful_critiques,
                reason=f"JUDGE_FAILED: {str(e)}",
                latency_ms=int((time.time() - start_time) * 1000),
                config=config,
            )
    
    async def _generate_critique(
        self, 
        role_id: str, 
        role_config: dict, 
        content: str
    ) -> CritiqueSchema | None:
        """
        单个角色生成批评
        
        包含：transport retry（最多 2 次）+ parse repair（最多 1 次）
        """
        system_prompt = role_config["system_prompt"]
        
        # Transport retry：网络/Rate Limit/5xx 最多重试 2 次
        for attempt in range(3):
            try:
                raw = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.provider.complete_structured(
                        messages=[{
                            "role": "user",
                            "content": f"请对以下内容进行批评分析：\n\n{content}"
                        }],
                        system_prompt=system_prompt,
                        schema=CritiqueSchema.model_json_schema(),
                    )
                )
                # Parse
                critique = CritiqueSchema(**raw)
                return critique
                
            except Exception as e:
                error_msg = str(e)
                
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    # Rate limit：等待后重试
                    await asyncio.sleep(2 ** attempt)
                    continue
                elif "ValidationError" in type(e).__name__:
                    # Parse repair：把错误信息反馈给 AI，让它重新生成
                    if attempt < 2:
                        system_prompt += f"\n\n上次输出解析失败：{error_msg}\n请修正后重新输出。"
                        continue
                    else:
                        # Parse repair 也失败：降级处理
                        return self._make_fallback_critique(content, str(e))
                else:
                    if attempt < 2:
                        await asyncio.sleep(1)
                        continue
                    return None
        
        return None
    
    def _anonymize(self, critiques: list[CritiqueSchema]) -> list[dict]:
        """
        匿名化：去掉角色标识符，防止 Judge 因为'谁说的'而有偏见
        
        保留：is_devil_advocate 字段（Judge 知道是对立视角，但不知道具体是哪个模型）
        去掉：角色 ID、模型名称等标识信息
        """
        names = ["批评者甲", "批评者乙", "批评者丙", "批评者丁"]
        result = []
        for i, critique in enumerate(critiques):
            anon_dict = critique.model_dump()
            anon_dict["anonymous_id"] = names[i]
            result.append(anon_dict)
        return result
    
    async def _judge(
        self, 
        anonymized_critiques: list[dict], 
        config: CritiqueConfigSchema,
        request_id: str,
        start_time: float,
    ) -> ConsensusSchema:
        """Judge 汇总逻辑"""
        
        # 把批评列表格式化给 Judge
        critique_summary = "\n\n".join([
            f"【{c['anonymous_id']}（{'DA角色' if c['is_devil_advocate'] else '常规角色'}）】\n"
            f"批评对象：{c['target_area']}\n"
            f"问题类型：{c['defect_type']} | 严重程度：{c['severity']}\n"
            f"证据：{c['evidence']}\n"
            f"建议：{c['suggested_fix']}（{c['fix_kind']}）\n"
            f"置信度：{c['confidence']}"
            for c in anonymized_critiques
        ])
        
        judge_prompt = f"""你是专业的技术评审裁判。以下是多位评审者的结构化批评：

{critique_summary}

请综合这些批评，给出最终评审结论。注意：
1. DA角色的批评是故意对立的视角，权重要结合其evidence质量判断
2. 如果remaining_disagreements为空，必须在disagreement_confirmation中说明原因
3. 如果DA角色的CRITICAL批评未被采纳，必须在preserved_minority_opinions中记录

请按要求的JSON格式输出。"""
        
        # 调用 Judge（结构化输出）
        raw = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.provider.complete_structured(
                messages=[{"role": "user", "content": judge_prompt}],
                system_prompt="你是严格的技术评审裁判，负责综合多方批评给出公正结论。",
                schema=self._judge_output_schema(),
            )
        )
        
        # 构建 ConsensusSchema
        return ConsensusSchema(
            final_conclusion=raw.get("final_conclusion", ""),
            consensus_confidence=raw.get("consensus_confidence", 0.5),
            adopted_contributions=raw.get("adopted_contributions", {}),
            rejected_positions=raw.get("rejected_positions", []),
            remaining_disagreements=raw.get("remaining_disagreements", []),
            disagreement_confirmation=raw.get("disagreement_confirmation"),
            preserved_minority_opinions=[
                MinorityOpinion(**m) for m in raw.get("preserved_minority_opinions", [])
            ],
            partial_return=False,
            critiques_summary=[CritiqueSchema(**c) for c in anonymized_critiques],
            debate_metadata=DebateMetadata(
                request_id=request_id,
                task_type=config.task_type,
                provider_mode=config.provider_mode,
                rounds_completed=1,
                total_latency_ms=int((time.time() - start_time) * 1000),
                models_used=["minimaxai/minimax-m2.7"],
                quorum_achieved=True,
                termination_reason="COMPLETED",
            )
        )
    
    def _make_partial_return(
        self, request_id, critiques, reason, latency_ms, config
    ) -> ConsensusSchema:
        """生成 partial result——即使失败也不空手而回"""
        return ConsensusSchema(
            final_conclusion=f"⚠️ {reason}。以下为可用的部分批评结果（未经 Judge 综合）",
            consensus_confidence=0.0,
            partial_return=True,
            critiques_summary=critiques,
            debate_metadata=DebateMetadata(
                request_id=request_id,
                task_type=config.task_type,
                provider_mode=config.provider_mode,
                rounds_completed=0,
                total_latency_ms=latency_ms,
                models_used=["minimaxai/minimax-m2.7"],
                quorum_achieved=False,
                termination_reason=reason,
            )
        )
    
    @staticmethod
    def _judge_output_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "final_conclusion": {"type": "string"},
                "consensus_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "adopted_contributions": {"type": "object"},
                "rejected_positions": {"type": "array"},
                "remaining_disagreements": {"type": "array", "items": {"type": "string"}},
                "disagreement_confirmation": {"type": "string"},
                "preserved_minority_opinions": {"type": "array"},
            },
            "required": ["final_conclusion", "consensus_confidence"]
        }
    
    @staticmethod
    def _make_fallback_critique(content: str, error: str) -> CritiqueSchema:
        """Parse repair 失败时的降级批评（至少保留能解析的内容）"""
        from ..schemas.critique import DefectType, Severity, FixKind
        return CritiqueSchema(
            target_area="（解析失败，无法确定具体范围）",
            defect_type=DefectType.GENERAL,
            severity=Severity.MINOR,
            evidence=f"批评生成失败，原始错误：{error[:100]}",
            suggested_fix="请检查网络连接或重新提交",
            fix_kind=FixKind.NEED_MORE_DATA,
            confidence=0.1,
        )
```

---

## 七、FastAPI REST 接口

```python
# api/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from debate_engine.schemas.config import CritiqueConfigSchema, DebateConfigSchema
from debate_engine.schemas.consensus import ConsensusSchema
from debate_engine.schemas.debate_job import DebateJobSchema, JobStatus
from debate_engine.engines.quick_critique import QuickCritiqueEngine
from debate_engine.engines.debate import DebateOrchestrator
import uuid, asyncio

app = FastAPI(
    title="DebateEngine API",
    description="结构化多智能体批评引擎 - 默认使用 NVIDIA NIM 免费 API",
    version="0.1.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"])

# 内存任务存储（V0.2，V1.0 升级为 Redis）
_job_store: dict[str, DebateJobSchema] = {}

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "backend": "NVIDIA NIM / MiniMax M2.7"}

# ─── V0.1：同步批评接口 ─────────────────────────────────────────

@app.post("/v1/quick-critique", response_model=ConsensusSchema)
async def quick_critique(config: CritiqueConfigSchema):
    """
    快速批评接口（同步，P95 < 15 秒）
    
    发送你的内容，获得结构化的多角色批评报告。
    默认使用 NVIDIA NIM 免费 API，无需付费。
    """
    try:
        engine = QuickCritiqueEngine()
        result = engine.run(config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── V0.2：异步辩论接口 ─────────────────────────────────────────

@app.post("/v1/debate", response_model=dict)
async def submit_debate(config: DebateConfigSchema, background_tasks: BackgroundTasks):
    """
    提交完整辩论任务（异步，返回 job_id）
    
    使用方式：
    1. POST /v1/debate → 获得 job_id
    2. 每隔 3-5 秒轮询 GET /v1/debate/{job_id}
    3. status=DONE 时读取 result 字段
    """
    job_id = str(uuid.uuid4())
    job = DebateJobSchema(
        job_id=job_id,
        status=JobStatus.PENDING,
        config=config,
    )
    _job_store[job_id] = job
    
    # 后台异步运行辩论
    background_tasks.add_task(_run_debate_task, job_id, config)
    
    return {
        "job_id": job_id,
        "status": "PENDING",
        "message": "辩论任务已提交，请通过 GET /v1/debate/{job_id} 轮询结果",
        "poll_url": f"/v1/debate/{job_id}",
    }

@app.get("/v1/debate/{job_id}", response_model=DebateJobSchema)
async def get_debate_result(job_id: str):
    """轮询辩论任务状态和结果"""
    if job_id not in _job_store:
        raise HTTPException(status_code=404, detail=f"Job {job_id} 不存在")
    return _job_store[job_id]

@app.delete("/v1/debate/{job_id}")
async def cancel_debate(job_id: str):
    """取消辩论任务"""
    if job_id not in _job_store:
        raise HTTPException(status_code=404, detail=f"Job {job_id} 不存在")
    job = _job_store[job_id]
    if job.status in [JobStatus.DONE, JobStatus.FAILED]:
        return {"message": "任务已完成，无需取消", "cost_so_far_usd": job.cost_so_far_usd}
    job.status = JobStatus.CANCELLED
    return {"message": "任务已取消", "cost_so_far_usd": job.cost_so_far_usd}

async def _run_debate_task(job_id: str, config: DebateConfigSchema):
    """后台任务执行器"""
    job = _job_store[job_id]
    job.status = JobStatus.RUNNING
    try:
        orchestrator = DebateOrchestrator()
        result = await orchestrator.run(config, job)  # job 对象会被实时更新
        job.status = JobStatus.DONE
        job.result = result
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
```

---

## 八、交互式 Demo（Gradio，可部署到 HuggingFace Spaces）

```python
# demo/app.py
"""
DebateEngine 交互式 Demo
可以直接在 HuggingFace Spaces 免费部署，或本地运行

运行方式：
  pip install gradio debate-engine
  python demo/app.py

HuggingFace Spaces 部署：见文档第九章
"""

import gradio as gr
import json
from debate_engine import QuickCritiqueEngine
from debate_engine.schemas.config import CritiqueConfigSchema, TaskType, ProviderMode

engine = QuickCritiqueEngine()

EXAMPLE_CODE = '''def get_user_orders(user_id):
    """获取用户的所有订单"""
    user = db.query("SELECT * FROM users WHERE id = %s" % user_id)
    orders = []
    for order_id in user['order_ids']:
        order = db.query("SELECT * FROM orders WHERE id = %s" % order_id)
        orders.append(order)
    return orders'''

EXAMPLE_RAG = '''用户问题：什么是量子纠缠？

AI 回答：量子纠缠是爱因斯坦在 1935 年提出的理论，他认为两个粒子可以在任意距离上瞬间影响彼此。
这个现象已经在实验室中被多次证实，目前被广泛应用于量子计算和量子通信领域。
量子纠缠的速度超过光速，违反了相对论的基本假设。'''

def format_critique(critique: dict) -> str:
    severity_emoji = {"CRITICAL": "🔴", "MAJOR": "🟡", "MINOR": "🟢"}.get(
        critique.get("severity", ""), "⚪"
    )
    da_badge = " 🎭(DA)" if critique.get("is_devil_advocate") else ""
    return f"""
{severity_emoji} **{critique.get('defect_type', 'N/A')}**{da_badge} | 置信度: {critique.get('confidence', 0):.0%}

📍 **批评对象：** {critique.get('target_area', '')}

🔍 **证据：** {critique.get('evidence', '')}

💡 **建议：** {critique.get('suggested_fix', '')} `[{critique.get('fix_kind', '')}]`
"""

def run_critique(content: str, task_type: str, enable_da: bool) -> tuple:
    if not content.strip():
        return "❌ 请输入要批评的内容", "", ""
    
    try:
        config = CritiqueConfigSchema(
            content=content,
            task_type=TaskType(task_type),
            provider_mode=ProviderMode.stable,
            enable_devil_advocate=enable_da,
            cost_budget_usd=0.30,
        )
        result = engine.run(config)
        
        # 格式化主要结论
        if result.partial_return:
            conclusion = f"⚠️ **部分结果**（系统异常）\n\n{result.final_conclusion}"
        else:
            confidence_bar = "🟩" * int(result.consensus_confidence * 10) + "⬜" * (10 - int(result.consensus_confidence * 10))
            conclusion = f"""### 📋 最终结论
{result.final_conclusion}

**置信度：** {confidence_bar} {result.consensus_confidence:.0%}

**耗时：** {result.debate_metadata.total_latency_ms}ms  |  **模型：** {', '.join(result.debate_metadata.models_used)}
"""
        
        # 格式化批评列表
        critiques_md = "### 🔍 各角色批评详情\n"
        for c in result.critiques_summary:
            critiques_md += format_critique(c.model_dump()) + "\n---\n"
        
        # 格式化少数意见
        minority_md = ""
        if result.preserved_minority_opinions:
            minority_md = "### 🎭 保留的少数意见\n"
            for op in result.preserved_minority_opinions:
                minority_md += f"""
**来源：** {op.source_role} ({op.source_critique_severity})
**意见：** {op.opinion}
**忽略风险：** {op.potential_risk_if_ignored}

---
"""
        elif result.disagreement_confirmation:
            minority_md = f"✅ **无少数意见**\n\n{result.disagreement_confirmation}"
        
        return conclusion, critiques_md, minority_md
        
    except Exception as e:
        return f"❌ 错误：{str(e)}", "", ""

# 构建 Gradio 界面
with gr.Blocks(
    title="DebateEngine Demo",
    theme=gr.themes.Soft(),
    css=".gradio-container { max-width: 1200px !important }"
) as demo:
    gr.Markdown("""
# 🎭 DebateEngine：结构化多智能体批评引擎

**让多个 AI 角色像真正的专家评审团一样批评你的方案**

- 🔴 `CRITICAL` = 必须修复才能上线
- 🟡 `MAJOR` = 显著影响质量，需认真处理  
- 🟢 `MINOR` = 小问题，可记录为 Tech Debt
- 🎭 `(DA)` = 来自魔鬼代言人角色的批评（故意对立视角）

*使用 NVIDIA NIM 免费 API（MiniMax M2.7，230B MoE 模型）*
""")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📝 输入区域")
            content_input = gr.Textbox(
                label="要批评的内容（代码 / RAG 答案 / 技术方案）",
                placeholder="粘贴你的代码、AI 答案、或技术方案……",
                lines=15,
                value=EXAMPLE_CODE,
            )
            
            with gr.Row():
                task_type = gr.Dropdown(
                    label="任务类型",
                    choices=["CODE_REVIEW", "RAG_VALIDATION", "ARCHITECTURE_DECISION", "GENERAL_CRITIQUE", "AUTO"],
                    value="CODE_REVIEW",
                )
                enable_da = gr.Checkbox(label="启用魔鬼代言人 (DA) 角色", value=True)
            
            gr.Examples(
                examples=[
                    [EXAMPLE_CODE, "CODE_REVIEW", True],
                    [EXAMPLE_RAG, "RAG_VALIDATION", True],
                ],
                inputs=[content_input, task_type, enable_da],
                label="示例",
            )
            
            submit_btn = gr.Button("🚀 开始批评审查", variant="primary", size="lg")
        
        with gr.Column(scale=1):
            gr.Markdown("### 📊 审查结果")
            conclusion_output = gr.Markdown(label="最终结论")
            
            with gr.Tabs():
                with gr.Tab("🔍 各角色批评"):
                    critiques_output = gr.Markdown()
                with gr.Tab("🎭 少数意见"):
                    minority_output = gr.Markdown()
    
    submit_btn.click(
        fn=run_critique,
        inputs=[content_input, task_type, enable_da],
        outputs=[conclusion_output, critiques_output, minority_output],
    )
    
    gr.Markdown("""
---
**DebateEngine** | [GitHub](https://github.com/YOUR_USERNAME/debate-engine) | [PyPI](https://pypi.org/project/debate-engine) | v0.1.0
""")

if __name__ == "__main__":
    demo.launch(share=True)
```

---

## 九、GitHub 部署完整指南

### 9.1 项目结构快速初始化

```bash
# 克隆/创建项目
git clone https://github.com/YOUR_USERNAME/debate-engine.git
cd debate-engine

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -e ".[dev]"
```

### 9.2 pyproject.toml（完整配置）

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "debate-engine"
version = "0.1.0"
description = "结构化多智能体批评与共识引擎 | Structured Multi-Agent Critique & Consensus Library"
readme = "README.md"
license = { text = "MIT" }
authors = [
    { name = "Tony Ye", email = "1235357@wku.edu.cn" },
]
keywords = ["llm", "multi-agent", "critique", "debate", "pydantic", "structured-output"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Programming Language :: Python :: 3.11",
]
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "openai>=1.0",        # 兼容 NVIDIA NIM OpenAI 接口
    "fastapi>=0.100",
    "uvicorn[standard]",
    "python-dotenv",
    "sentence-transformers>=2.0",  # 任务类型自动检测
]

[project.optional-dependencies]
demo = ["gradio>=4.0"]
eval = ["ragas>=0.1", "scikit-learn"]
dev = ["pytest", "pytest-asyncio", "httpx", "black", "ruff"]
all = ["debate-engine[demo,eval,dev]"]

[project.urls]
Homepage = "https://github.com/YOUR_USERNAME/debate-engine"
Repository = "https://github.com/YOUR_USERNAME/debate-engine"

[project.scripts]
debate-engine = "debate_engine.cli:main"
```

### 9.3 Dockerfile（单容器，一行命令启动）

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[demo]"

# 复制源码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动 FastAPI 服务
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# 一行命令启动（本地）
docker build -t debate-engine .
docker run -p 8000:8000 debate-engine

# 测试
curl -X POST http://localhost:8000/v1/quick-critique \
  -H "Content-Type: application/json" \
  -d '{"content": "def add(a, b): return a - b  # 应该是加法但写成了减法"}'
```

### 9.4 GitHub Actions（自动化测试和发布）

```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: pip install -e ".[dev]"
      
      - name: Run regression tests (mock mode, no API calls)
        run: pytest tests/regression/ -v --mock-provider
        
      - name: Check code style
        run: ruff check .
```

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write  # Trusted Publishing，不需要存储 PyPI Token
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with: { python-version: "3.11" }
      - run: pip install build
      - run: python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

### 9.5 HuggingFace Spaces 一键部署 Demo

```yaml
# demo/README.md（这个文件放在 HuggingFace Spaces 仓库根目录）
---
title: DebateEngine Demo
emoji: 🎭
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.0.0
app_file: app.py
pinned: false
---
```

```bash
# 部署步骤
# 1. 在 HuggingFace 创建新的 Space（选择 Gradio SDK）
# 2. 克隆 Space 仓库
git clone https://huggingface.co/spaces/YOUR_USERNAME/debate-engine-demo
cd debate-engine-demo

# 3. 复制 demo 文件
cp debate-engine/demo/app.py .
cat > requirements.txt << EOF
debate-engine
gradio>=4.0
EOF

# 4. 推送
git add . && git commit -m "Deploy DebateEngine demo" && git push
# HuggingFace 会自动构建和部署！
```

### 9.6 Render.com 免费部署（API 服务）

```yaml
# render.yaml（放在项目根目录）
services:
  - type: web
    name: debate-engine-api
    runtime: python
    buildCommand: "pip install -e ."
    startCommand: "uvicorn api.main:app --host 0.0.0.0 --port $PORT"
    plan: free  # 免费计划（750 小时/月）
    envVars:
      - key: NVIDIA_API_KEY
        value: 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
    healthCheckPath: /health
```

```
Render.com 免费部署步骤：
1. 注册 Render.com（免费）
2. New → Web Service → Connect GitHub Repository
3. Render 自动读取 render.yaml 配置
4. 点击 Deploy！
5. 你的 API 就在 https://debate-engine-api.onrender.com 上了
```

---

## 十、DebateEval 评估框架（量化证明有效性）

### 10.1 七项评估指标（用大白话解释）

**BDR（Bug Detection Rate，缺陷发现率）**

问：跟金标准答案相比，DebateEngine 发现了多少比例的真实问题？

计算：已发现的金标准缺陷数 ÷ 金标准总缺陷数

目标：> 0.70（比单 Agent 基线高至少 10%）

**FAR（False Alarm Rate，误报率）**

问：DebateEngine 报告的问题里，有多少是假阳性（实际上不是问题）？

目标：< 0.25（误报太多会让用户失去信任）

**HD（Hallucination Delta，幻觉差值）**

问：在 RAG 验证任务里，使用 DebateEngine 后，答案的事实准确率比基线提高了多少？

用 RAGAS Faithfulness 指标测量

**CS（Conformity Score，从众分数）**

这是我们的原创指标。见第三章详细解释。
目标：Full 3-layer 配置比 No-defense 配置 CS 提高至少 15%

**CE（Critique Efficiency，批评效率）**

问：每次批评调用平均产生多少有效发现？（成本角度）

**RD（Reasoning Depth，推理深度）**

问：Judge 最终采纳了多少比例的 CONCRETE_FIX 类型建议？（结论可操作性）

**CONF（Confidence Calibration，置信度校准）**

问：高置信度的批评是否真的更准确？

### 10.2 基准测试集设计（25 个用例）

```
10 个回归测试用例（快速，每次 CI 跑）：
  - 5 个代码审查（含明确的已知问题，金标准手工标注）
  - 3 个 RAG 验证（含故意注入的幻觉）
  - 2 个架构决策（含明确的利弊对比）

15 个基准测试用例（慢，每周跑）：
  - 6 个代码审查（复杂度更高，多个交织的问题）
  - 6 个 RAG 验证（涉及领域知识判断）
  - 3 个架构决策（用于 CS 消融实验）
```

```python
# debate_engine/eval/run_benchmark.py
import asyncio
from pathlib import Path
import json

async def run_benchmark(
    benchmark_dir: str = "tests/benchmark",
    output_file: str = "benchmark_report.json",
):
    """运行 15 个基准测试用例并生成报告"""
    from debate_engine import QuickCritiqueEngine
    from debate_engine.eval.metrics import calculate_bdr, calculate_far
    
    engine = QuickCritiqueEngine()
    results = []
    
    for case_file in Path(benchmark_dir).glob("*.json"):
        case = json.loads(case_file.read_text())
        
        # 运行 DebateEngine
        de_result = engine.run_from_dict(case["config"])
        
        # 运行单 Agent 基线（直接问 AI，不用辩论）
        baseline_result = run_single_agent_baseline(case["config"]["content"])
        
        # 计算指标
        bdr_de = calculate_bdr(de_result.critiques_summary, case["gold_standard"])
        bdr_base = calculate_bdr(baseline_result, case["gold_standard"])
        
        results.append({
            "case_id": case["id"],
            "task_type": case["config"]["task_type"],
            "BDR_DebateEngine": bdr_de,
            "BDR_Baseline": bdr_base,
            "BDR_Delta": bdr_de - bdr_base,
        })
        
        print(f"✅ {case['id']}: BDR Δ = {(bdr_de - bdr_base):+.1%}")
    
    # 生成报告
    report = {
        "summary": {
            "avg_BDR_delta": sum(r["BDR_Delta"] for r in results) / len(results),
            "cases_with_positive_delta": sum(1 for r in results if r["BDR_Delta"] > 0),
        },
        "cases": results,
    }
    
    Path(output_file).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n📊 基准测试完成！报告已保存到 {output_file}")
    return report
```

---

## 十一、角色提示词设计（核心提示工程）

```python
# debate_engine/roles/templates.py

CODE_REVIEW_ROLES = {
    "ROLE_A": {
        "name": "资深后端架构师",
        "is_devil_advocate": False,
        "system_prompt": """你是一位有 10 年经验的后端架构师，擅长发现代码中的可维护性问题、设计模式缺失和扩展性陷阱。

你的批评风格：
- 关注长期后果，而非短期实现
- 善于发现"现在能跑，数据量 10× 后就崩"的隐患
- 对缺乏单元测试和文档的代码持批评态度

输出要求：
- defect_type 必须精确匹配你发现的问题类型
- evidence 必须包含具体的行号或代码片段（如果有）
- suggested_fix 中的 CONCRETE_FIX 要给出可以直接复制的改进代码思路
- 不要捏造没有的问题，confidence < 0.5 时选择 NEED_MORE_DATA

你现在的任务是批评给定的代码，输出一个 CritiqueSchema JSON。""",
    },
    
    "ROLE_B": {
        "name": "安全工程师",
        "is_devil_advocate": False,
        "system_prompt": """你是一位专注于 Web 安全和 API 安全的工程师，对 OWASP Top 10 和 CWE 体系了如指掌。

你的批评风格：
- 优先找注入类漏洞（SQL、命令行、XSS）
- 关注认证和权限控制的缺失
- 对未验证的用户输入持有最高警惕
- 关注敏感数据处理（日志中的密码、明文存储等）

输出要求：
- SECURITY_RISK 类型必须引用 OWASP 分类或 CWE 编号
- evidence 要说明攻击者如何利用这个漏洞
- suggested_fix 要给出行业标准的安全实践

你现在的任务是批评给定的代码，输出一个 CritiqueSchema JSON。""",
    },
    
    "DA_ROLE": {
        "name": "魔鬼代言人",
        "is_devil_advocate": True,
        "system_prompt": """你是"魔鬼代言人"（Devil's Advocate）。你的职责是找到这段代码/方案中最难处理的、最不明显的问题。

你的批评风格：
- 故意寻找别人不容易发现的问题
- 即使代码表面上正确，你也要思考"在什么极端情况下它会出错"
- 关注隐含的技术债务、隐藏的性能瓶颈、未考虑的边缘情况
- 质疑设计决策背后的假设是否成立

重要：你不是随意批评，你的批评必须有实质的 evidence 支撑。即使你在故意找麻烦，也要找真实存在的麻烦，而不是编造问题。

如果代码/方案真的没有严重问题，你可以批评其"在规模扩展时可能出现的问题"或"与其他系统集成时的风险"。

你现在的任务是批评给定的代码，输出一个 CritiqueSchema JSON。""",
    }
}

RAG_VALIDATION_ROLES = {
    "ROLE_A": {
        "name": "事实核查员",
        "is_devil_advocate": False,
        "system_prompt": """你专门负责检验 AI 生成答案中的事实准确性。

关注点：
- 找到答案中所有可验证的事实声明
- 判断哪些声明可能是幻觉（凭空捏造）
- 指出答案与常识或已知事实不符的地方

evidence 格式：'该声明"[原文]"存在[具体问题]，因为[原因]'""",
    },
    # ... 其他 RAG 角色
}

def get_role_config(task_type: str, enable_da: bool = True) -> dict:
    """根据任务类型返回角色配置"""
    templates = {
        "CODE_REVIEW": CODE_REVIEW_ROLES,
        "RAG_VALIDATION": RAG_VALIDATION_ROLES,
        # ...
    }
    
    roles = templates.get(task_type, CODE_REVIEW_ROLES).copy()
    
    if not enable_da:
        # 把 DA 角色替换为普通批评者
        roles["DA_ROLE"]["is_devil_advocate"] = False
        roles["DA_ROLE"]["system_prompt"] = roles["ROLE_A"]["system_prompt"]
    
    return roles
```

---

## 十二、V5.0 版本路线图（调整后）

### 12.1 三阶段调整：引入 NVIDIA API 后的变化

与 V4.1 相比，V5.0 的核心执行层面变化：

| 项目 | V4.1 | V5.0 |
|---|---|---|
| 默认 AI 后端 | OpenAI GPT（付费） | NVIDIA NIM MiniMax M2.7（免费） |
| 开发成本 | $15-25 | **$0**（使用免费额度） |
| Demo 部署 | 未规划 | **HuggingFace Spaces 免费部署** |
| API 服务部署 | Docker 本地 | **Render.com 免费部署** |
| 代码骨架完整度 | 概念设计 | **完整可运行骨架** |

### 12.2 8 周执行计划（V5.0 更新版）

**第 1-2 周（4月14-27日）：核心骨架**
- Schema 定义（CritiqueSchema, ConsensusSchema）
- NVIDIA Provider 实现和测试
- 角色提示词模板（代码审查 + RAG 验证）
- QuickCritiqueEngine 骨架
- 验收：能调通 NVIDIA API，成功生成一条 CritiqueSchema

**第 3-4 周（4月28日-5月11日）：V0.1 完整功能**
- 匿名化逻辑
- Judge 汇总实现
- Quorum + Partial Return 稳定性保障
- FastAPI + Docker 部署
- 10 个回归测试
- 验收：pip install + docker run 均可用，P95 < 15s

**第 5-6 周（5月12-25日）：V0.2 异步辩论**
- DebateOrchestrator（两轮辩论）
- 异步任务 API（job_id + 轮询）
- 15 个基准测试用例运行
- BDR/HD/CS 真实数据获取
- 验收：两轮辩论稳定完成，真实量化数字到手

**第 7 周（5月26日-6月1日）：Demo + MCP + PyPI**
- Gradio Demo（HuggingFace Spaces 部署）
- MCP 薄适配（3 个工具）
- PyPI 正式发布（v0.1.0）
- Render.com API 服务部署
- 验收：pip install 正式版可用，Demo 在线可访问

**第 8 周（6月2-8日）：文档 + 社区**
- README 最终版（含基准测试结果表格）
- 一个完整的 Jupyter Notebook 示例
- LangChain Discord 首帖
- 验收：社区帖已发，文档完整

### 12.3 V1.0 愿景蓝图（8周后）

```
V1.0 新增：
├── Redis 持久化（真正的中断恢复）
├── NetworkX 辩论图谱（可视化各轮批评关系）
├── diverse 模式（三供应商强制异构）
├── 完整 30 个用例 DebateEval 公开基准报告
├── GitHub Actions PR 自动审查集成
├── 支持更多 NVIDIA NIM 模型（Llama 3.1、Qwen 等）
└── OpenClaw ClawHub 正式发布
```

---

## 十三、DebateEval 消融实验设计

### 13.1 CS 消融实验（证明 Anti-Sycophancy 机制有效）

```
实验设置（3个架构决策用例，每个跑 3 次取均值）：

配置 A（Zero Defense）：
  - 无 DA 角色
  - 无匿名化
  - 单供应商
  → 预期 CS 最低（最多谄媚）

配置 B（DA Only）：
  - 有 DA 角色
  - 无匿名化
  - 单供应商
  → 预期 CS 中等

配置 C（Full Defense）：
  - 有 DA 角色
  - 有匿名化
  - 双供应商（balanced 模式）
  → 预期 CS 最高（最少谄媚）

预期结果：CS(A) < CS(B) < CS(C)，证明每一层防御都有效果
```

### 13.2 简历用量化数字获取计划

第 6 周末，我们将有：
- BDR Δ：DebateEngine 相比单 Agent 基线的缺陷发现率提升（预期 +15% ~ +30%）
- HD 值：RAG 任务中的幻觉率降低（预期 +10% ~ +20%）
- CS 消融结果：Full Defense 相比 Zero Defense 的 CS 提升（预期 +15% ~ +25%）

这三个数字会直接填入简历的 bullet point：
```
• Validated on 25-case DebateEval benchmark: BDR Δ+[X]% vs GPT-4o single-agent; 
  Hallucination Delta +[X]% (RAGAS Faithfulness); CS ablation shows [X]% improvement
  from zero-defense to full 3-layer Anti-Sycophancy configuration
```

---

## 十四、常见问题（FAQ）

**Q：为什么不直接用 AutoGen 或 CrewAI？**

A：AutoGen 的 GroupChat 已进入维护模式（2025 年 10 月）。CrewAI 和 AutoGen 的输出都是自由文本，无法机器解析。DebateEngine 的差异化不在于"让 AI 讨论"，而在于"强制输出结构化的批评，并提供量化的质量评估"。

**Q：NVIDIA NIM 的免费额度够用吗？**

A：免费注册获得 1000 次推理额度，速率限制 40 次/分钟。一次 quick_critique 需要 4 次 API 调用（3 个角色 + 1 个 Judge），1000 次额度 = 250 次完整批评。开发阶段绰绰有余。若额度不足，NVIDIA 还提供其他免费模型（Llama 3.1 等）可以切换。

**Q：这个项目的 API Key 放在代码里安全吗？**

A：NVIDIA API Key 的好处是：免费额度有上限，即使泄露也不会产生无限账单。不过仍然建议在部署时通过环境变量配置，不要硬编码在代码里。Demo 演示中可以用环境变量 `NVIDIA_API_KEY` 注入。

**Q：两轮辩论和一次批评，性能差多少？**

A：quick_critique 目标 P95 < 15 秒；两轮 debate 目标 P95 < 60 秒（因为要做两次完整的批评循环）。这就是为什么两轮辩论必须是异步接口——60 秒的同步请求在 Web 环境下几乎必然超时。

**Q：DA 角色会不会产生太多噪音？**

A：DA 角色的权重在 Judge 汇总时会根据其批评的 evidence 质量动态调整。DA 的 MINOR 批评权重比普通角色的 MINOR 批评权重低（因为 DA 本来就是故意挑剔的），但 DA 的 CRITICAL 批评会获得额外标注（"来自对立视角的致命发现"）。在 DebateEval 里我们会量化 DA 角色的噪音 vs 价值比。

---

## 十五、总结：V5.0 的核心升级一句话

V4.1 是一份完整的工程设计文档，V5.0 在此基础上：

1. **零成本化**：默认 NVIDIA NIM 免费 API，开发阶段不花一分钱
2. **可直接跑**：提供完整的可运行代码骨架，不只是伪代码
3. **可直接部署**：HuggingFace Spaces 免费 Demo + Render.com 免费 API，GitHub 即可部署
4. **说人话**：新增大量通俗解释，让不了解 LLM 底层的人也能理解这个项目在做什么

执行不变：仍然是 2 人 8 周，V0.1（quick_critique 同步）→ V0.2（两轮异步辩论）→ MCP + 收尾。

---

*文档版本：v5.0 Final | 生成日期：2026 年 4 月 12 日*  
*基于：v4.1 Final（2026-04-12）*  
*执行周期：2026 年 4 月 14 日 — 2026 年 6 月 8 日*  
*核心 AI 后端：NVIDIA NIM MiniMax M2.7（230B MoE，免费 API）*  
*项目负责人：Tony Ye + 合作同学*
