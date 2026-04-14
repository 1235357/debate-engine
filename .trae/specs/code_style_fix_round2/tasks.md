# DebateEngine 代码风格修复（第二轮）- 实现计划

## [x] 任务 1：安装开发依赖
- **优先级**：P0
- **依赖**：无
- **描述**：
  - 执行 `pip install -e ".[dev]"` 安装开发依赖
- **验收标准**：AC-1
- **测试要求**：
  - `programmatic` TR-1.1：执行 `ruff --version` 验证 Ruff 已安装
- **说明**：确保项目安装了所有开发依赖，包括 Ruff 工具

## [x] 任务 2：自动修复 Ruff 错误
- **优先级**：P0
- **依赖**：任务 1
- **描述**：
  - 执行 `ruff check . --fix` 自动修复可修复的代码风格问题
- **验收标准**：AC-1
- **测试要求**：
  - `programmatic` TR-2.1：执行 `ruff check .` 验证自动修复后错误数量减少
- **说明**：Ruff 的 `--fix` 选项可以自动修复许多常见的代码风格问题

## [x] 任务 3：格式化代码
- **优先级**：P0
- **依赖**：任务 2
- **描述**：
  - 执行 `ruff format .` 格式化代码
- **验收标准**：AC-1
- **测试要求**：
  - `programmatic` TR-3.1：执行 `ruff format --check .` 验证代码已正确格式化
- **说明**：使用 Ruff 的格式化功能确保代码风格一致

## [x] 任务 4：手动修复剩余 Ruff 错误
- **优先级**：P0
- **依赖**：任务 3
- **描述**：
  - 执行 `ruff check .` 查看剩余的代码风格错误
  - 手动修复这些错误，重点关注以下文件：
    - job.py：修复 Optional 类型注解、import 分组、文件末尾缺换行
    - proposal.py：修复 import 分组、文件末尾缺换行
    - config.py：修复多行语句、import 分组、超长行
    - test_config_fix.py：修复未使用变量、import 分组
    - test_readme_example.py：修复未使用变量、import 分组
- **验收标准**：AC-1
- **测试要求**：
  - `programmatic` TR-4.1：执行 `ruff check .` 验证所有错误已修复
- **说明**：手动修复自动工具无法解决的代码风格问题

## [x] 任务 5：验证新文件提交
- **优先级**：P0
- **依赖**：任务 4
- **描述**：
  - 执行 `git add src/debate_engine/api/key_manager.py` 添加新文件
  - 执行 `git commit -m "Add APIKeyManager module to fix circular import issue"` 提交新文件
- **验收标准**：AC-4
- **测试要求**：
  - `programmatic` TR-5.1：执行 `git status` 验证新文件已提交
  - `programmatic` TR-5.2：执行 `git log` 验证提交记录
- **说明**：确保新添加的 key_manager.py 文件正确提交到仓库

## [x] 任务 6：验证功能完整性
- **优先级**：P1
- **依赖**：任务 5
- **描述**：
  - 执行 `pytest -q` 运行所有测试用例
  - 确保所有测试用例通过
- **验收标准**：AC-3
- **测试要求**：
  - `programmatic` TR-6.1：执行 `pytest -q` 验证所有测试用例通过
- **说明**：确保代码风格修复不会影响代码的功能

## [x] 任务 7：验证 CI 流程通过
- **优先级**：P1
- **依赖**：任务 6
- **描述**：
  - 执行 `git push` 推送代码
  - 验证 GitHub Actions CI 流程成功通过
- **验收标准**：AC-2
- **测试要求**：
  - `programmatic` TR-7.1：查看 GitHub Actions 流程状态，确认成功通过
- **说明**：最终验证代码风格修复是否解决了 CI 失败问题