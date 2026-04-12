# DebateEngine

> **结构化多智能体对抗批评引擎**

## 项目简介

DebateEngine 是一个 pip 可安装的 Python 生产库，通过 Pydantic v2 结构化 Schema 将多智能体批评的输出从自由文本升级为**机器可解析、CI/CD 可集成、可量化评估**的结构化对象，填补了学术多智能体辩论研究与工业界 AI Code Review 工具之间的工程空白。

## 核心价值

1. **结构化输出**：Pydantic v2 Schema 定义，机器可解析，CI/CD 可集成
2. **对抗性批评**：多角色、Devil's Advocate、匿名化处理
3. **量化评估**：Conformity Score 等 7 项指标
4. **成本可控**：NVIDIA NIM 免费 API 集成
5. **生态集成**：OpenClaw、LangGraph、GitHub Actions

## 快速开始

### 安装

```bash
pip install debate-engine
```

### 使用 CLI

```bash
debate-engine --content "def vulnerable_function(user_input):\n    query = f\"SELECT * FROM users WHERE username = '{user_input}'\"\n    return execute_query(query)" --task-type CODE_REVIEW
```

### 使用 API

```bash
# 启动服务器
debate-engine-server

# 发送请求
curl -X POST http://localhost:8000/v1/quick-critique \
  -H "Content-Type: application/json" \
  -d '{"content": "def vulnerable_function(user_input):\n    query = f\"SELECT * FROM users WHERE username = '{user_input}'\"\n    return execute_query(query)", "task_type": "CODE_REVIEW"}'
```

### 使用 MCP Server

```bash
# 启动 MCP 服务器
debate-engine-mcp

# 在 OpenClaw 中使用
@debate-critique
请审查这段代码：

def vulnerable_function(user_input):
    query = f"SELECT * FROM users WHERE username = '{user_input}'"
    return execute_query(query)
```

## 技术栈

- **核心语言**：Python >= 3.11
- **结构化输出**：Pydantic v2
- **LLM 抽象**：LiteLLM
- **API 框架**：FastAPI
- **服务器**：Uvicorn
- **测试**：pytest

## 项目结构

```
src/
└── debate_engine/
    ├── schemas/         # Pydantic 模型
    ├── orchestration/   # 核心逻辑
    ├── providers/       # LLM 供应商
    ├── api/             # REST API
    ├── mcp_server/      # MCP Server
    ├── output/          # 输出格式
    └── cli.py           # 命令行工具
```

## 落地场景

1. **代码审查质量门控**：在 GitHub Actions 中集成，自动阻止严重问题的合并
2. **OpenClaw 技能升级**：将 OpenClaw 的批评输出从自由文本升级为结构化 Schema
3. **RAG 幻觉检测**：多角色对抗检测 RAG 答案的幻觉
4. **LangGraph 评估节点**：作为 LangGraph 工作流中的质量检查点

## 许可证

MIT License
