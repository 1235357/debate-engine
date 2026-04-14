# DebateEngine CI 修复 - 实现计划

## [x] 任务 1: 修复 cli.py 文件
- **Priority**: P0
- **Depends On**: None
- **Description**:
  - 添加 `--version` 选项
  - 添加 `critique` 子命令
  - 修改 `_run_critique` 函数，使用 `CritiqueConfigSchema` 和 `asyncio.run`
- **Acceptance Criteria Addressed**: AC-1, AC-2
- **Test Requirements**:
  - `programmatic` TR-1.1: 执行 `debate-engine --version` 命令，验证显示版本信息
  - `programmatic` TR-1.2: 执行 `debate-engine critique` 命令，验证能够执行并显示结果
- **Notes**: 确保导入必要的模块，包括 `asyncio`、`__version__`、`QuickCritiqueEngine`、`CritiqueConfigSchema` 和 `TaskType`

## [x] 任务 2: 修复 server.py 文件
- **Priority**: P0
- **Depends On**: None
- **Description**:
  - 添加 `_maybe_await` 函数，兼容同步和异步测试模拟
  - 修改 API 端点，使用 `_maybe_await` 函数
  - 修改 `_validate_api_key` 函数，只在显式启用 API 密钥认证时进行验证
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `programmatic` TR-2.1: 发送请求到 API 端点，验证返回 200 状态码
  - `programmatic` TR-2.2: 运行 API 测试，验证所有测试通过
- **Notes**: 确保不修改 `/v1/health` 端点返回的版本值

## [x] 任务 3: 修复 tests/test_api.py 文件
- **Priority**: P1
- **Depends On**: 任务 2
- **Description**:
  - 将测试中的 `Mock` 改为 `AsyncMock`，确保测试使用异步模拟
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-3.1: 运行 `tests/test_api.py` 测试，验证所有测试通过
- **Notes**: 保持测试结构不变，只修改模拟对象类型

## [x] 任务 4: 修复 tests/test_cli.py 文件
- **Priority**: P1
- **Depends On**: 任务 1
- **Description**:
  - 修改测试方法，使用直接调用 `main()` 而不是 `subprocess`
  - 使用 `AsyncMock` 模拟 `QuickCritiqueEngine.critique` 方法
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-4.1: 运行 `tests/test_cli.py` 测试，验证所有测试通过
- **Notes**: 使用 `capsys` 捕获输出，使用 `pytest.raises(SystemExit)` 捕获退出

## [x] 任务 5: 验证修复结果
- **Priority**: P2
- **Depends On**: 任务 1, 任务 2, 任务 3, 任务 4
- **Description**:
  - 运行所有测试，验证修复是否成功
  - 提交更改，触发 CI 工作流
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-5.1: 运行 `pytest` 命令，验证所有测试通过
  - `programmatic` TR-5.2: 检查 CI 工作流状态，验证部署成功
- **Notes**: 确保提交所有修改的文件
