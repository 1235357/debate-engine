# GitHub Actions Workflows

本目录包含 DebateEngine 项目的 GitHub Actions 工作流配置。

## 工作流概览

### 1. `ci.yml` - 持续集成
**触发条件**: push 或 PR 到 main 分支

**功能**:
- Python 3.11 和 3.12 测试
- 代码格式化检查 (ruff)
- 类型检查 (mypy)
- 单元测试 (pytest)
- 自动发布到 PyPI (仅在标签时)

### 2. `deploy-demo.yml` - GitHub Pages 部署
**触发条件**: push 或 PR 到 main 分支

**功能**:
- 自动构建和部署 demo 页面
- 使用 GitHub Pages 托管
- 部署地址: https://1235357.github.io/debate-engine/

### 3. `deploy-api.yml` - API 测试
**触发条件**: push 或 PR 到 main 分支

**功能**:
- 安装项目依赖
- 运行测试
- 测试 NVIDIA API 连接
- 验证 API 密钥配置

### 4. `debate-review.yml` - PR 代码审查
**触发条件**: PR 打开、同步或重新打开

**功能**:
- 自动分析 PR 变更的代码文件
- 使用 DebateEngine 多智能体系统进行审查
- 生成结构化的批评报告
- 发布 SARIF 结果到 GitHub Security 标签
- 发现 CRITICAL 问题时阻止合并

## 配置需求

### Secrets
需要在仓库 Settings > Secrets 中配置以下密钥:

- `NVIDIA_API_KEY`: NVIDIA API 密钥 (用于 deploy-api.yml)
- `GOOGLE_API_KEY`: Google AI Studio API 密钥 (用于 debate-review.yml)
- `GROQ_API_KEY`: Groq API 密钥 (用于 debate-review.yml, 可选)
- `PYPI_API_TOKEN`: PyPI API 令牌 (用于 ci.yml 发布, 可选)

## 环境变量

### NVIDIA API 多密钥支持
项目支持最多 11 个 NVIDIA API 密钥以实现负载均衡和故障转移:

- `NVIDIA_API_KEY`: 主密钥 (必需)
- `NVIDIA_API_KEY_1` 到 `NVIDIA_API_KEY_10`: 备用密钥 (可选)

在 Render 或其他托管平台上配置这些环境变量即可启用多密钥功能。

## Render 部署

项目使用 Render 免费托管 API 服务:

1. 在 render.com 创建 Web Service
2. 连接到 GitHub 仓库
3. 配置环境变量 (至少一个 NVIDIA_API_KEY)
4. 部署!

Render 会自动从 main 分支部署更新。

## 故障排除

### GitHub Pages 部署失败
- 检查 `.github/workflows/deploy-demo.yml` 权限配置
- 确认仓库 Settings > Pages 已正确配置

### API 测试失败
- 确认 `NVIDIA_API_KEY` Secret 已正确设置
- 检查 API 密钥是否有效且未超限

### PR 审查不工作
- 确认 `GOOGLE_API_KEY` 和可选的 `GROQ_API_KEY` 已设置
- 检查 PR 是否包含支持的文件类型 (.py, .js, .ts, .java, .go, .rs)

## 更多信息

详见项目根目录的 [DEPLOYMENT.md](../../DEPLOYMENT.md) 文档获取完整部署指南。
