# CI 代码风格修复计划

## 当前状态分析

### ✅ 已完成的修复
- `schemas/` 目录下的所有文件已经修复完成：
  - `consensus.py` - Optional → | None 已修复，导入已排序
  - `critique.py` - Optional → | None 已修复，导入已排序
  - `job.py` - Optional → | None 已修复，导入已排序
  - `config.py` - Optional → | None 已修复，导入已排序
  - `enums.py` - 导入已排序
  - `proposal.py` - 文件末尾换行已修复

### 🔍 剩余问题
通过 `ruff check .` 显示只有 **41 个错误**，主要都是 **E501 (Line too long)** 问题

## 修复计划

### 1. 运行自动修复
- 使用 `ruff check . --fix` 尝试自动修复
- 使用 `ruff format .` 格式化所有代码

### 2. 手动修复剩余的长行问题

#### 2.1 `src/debate_engine/eval/benchmark.py` (约 37 个长行)
- 将所有超过 100 字符的长字符串拆分成多行
- 主要是 BenchmarkCase 中的 description 和 reference_answer 字段

#### 2.2 `src/debate_engine/eval/metrics.py` (约 3 个长行)
- 修复 f-string 格式化字符串
- 主要是 MetricResult 的 description 字段

#### 2.3 `tests/test_provider.py` (1 个长行)
- 拆分长 JSON 字符串

### 3. 验证修复
- 再次运行 `ruff check .` 确认无错误
- 运行测试确保功能正常
- 提交并推送修复

## 文件清单

### 需要修改的文件
1. `src/debate_engine/eval/benchmark.py`
2. `src/debate_engine/eval/metrics.py`
3. `tests/test_provider.py`

### 不需要修改的文件
- 所有 `schemas/` 目录下的文件（已修复）
- 其他大部分文件（已修复）

## 风险评估
- 低风险：主要是代码格式化和字符串换行
- 不影响功能逻辑
