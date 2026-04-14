# DebateEngine CI 修复 - 产品需求文档

## Overview
- **Summary**: 修复 GitHub Actions CI 工作流中的测试失败问题，包括 CLI 命令参数不匹配、API 端点 401 错误和 500 错误，确保部署流程能够成功执行。
- **Purpose**: 解决 CI/CD 流程中的测试失败问题，确保代码能够正常部署到 Render 平台。
- **Target Users**: 开发团队和 CI/CD 系统。

## Goals
- 修复 CLI 命令的 `--version` 和 `critique` 子命令功能
- 解决 API 端点的 401 未授权错误
- 解决 API 端点的 500 内部服务器错误
- 确保所有测试能够通过

## Non-Goals (Out of Scope)
- 不修改 `/v1/health` 端点返回的版本值
- 不进行大规模的代码重构
- 不添加新的功能

## Background & Context
- 项目使用 GitHub Actions 进行 CI/CD
- 部署到 Render 平台
- 测试失败导致部署流程中断
- 主要问题集中在 CLI 命令和 API 端点

## Functional Requirements
- **FR-1**: CLI 命令支持 `--version` 选项
- **FR-2**: CLI 命令支持 `critique` 子命令
- **FR-3**: API 端点能够正确处理请求，返回 200 状态码
- **FR-4**: API 端点能够兼容同步和异步测试模拟

## Non-Functional Requirements
- **NFR-1**: 测试执行时间不超过 10 秒
- **NFR-2**: 修复后的代码保持与现有 API 接口兼容
- **NFR-3**: 修复过程中不引入新的依赖

## Constraints
- **Technical**: Python 3.11+, FastAPI, pytest
- **Business**: 修复必须在现有代码基础上进行，不进行大规模重构
- **Dependencies**: 现有项目依赖

## Assumptions
- 项目已经正确配置了必要的环境变量
- 测试环境能够访问必要的 API 密钥

## Acceptance Criteria

### AC-1: CLI 版本命令正常工作
- **Given**: 用户执行 `debate-engine --version` 命令
- **When**: 命令被执行
- **Then**: 显示版本信息，退出码为 0
- **Verification**: `programmatic`

### AC-2: CLI 批评命令正常工作
- **Given**: 用户执行 `debate-engine critique` 命令
- **When**: 命令被执行
- **Then**: 执行批评操作并显示结果，退出码为 0
- **Verification**: `programmatic`

### AC-3: API 端点返回 200 状态码
- **Given**: 发送请求到 API 端点
- **When**: 请求被处理
- **Then**: 返回 200 状态码和正确的响应
- **Verification**: `programmatic`

### AC-4: 所有测试通过
- **Given**: 运行 pytest 测试
- **When**: 测试执行完成
- **Then**: 所有测试通过，无失败
- **Verification**: `programmatic`

## Open Questions
- [ ] 无
