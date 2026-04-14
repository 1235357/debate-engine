# E501 行过长错误修复计划

## 概述
修复 DebateEngine 项目中的所有 E501（行过长）错误，总共40个问题。

## 文件清单及错误数量

1. **src/debate_engine/eval/benchmark.py**: 33个E501错误
2. **src/debate_engine/eval/metrics.py**: 6个E501错误
3. **tests/test_provider.py**: 1个E501错误

## 修复策略

对于所有过长的字符串，使用括号和字符串连接将它们拆分成多行，保持代码功能和可读性不变。

### 具体修复方法示例：

**benchmark.py:**
- 拆分 `description` 和 `reference_answer` 字符串
- 使用括号包裹字符串，使用相邻字符串连接

**metrics.py:**
- 拆分 MetricResult 的 description 中的 f-strings
- 将长 f-string 拆分为多个部分

**test_provider.py:**
- 拆分 test_valid_json 中的 JSON 字符串

## 执行步骤

1. 修复 src/debate_engine/eval/benchmark.py 中的所有长行
2. 修复 src/debate_engine/eval/metrics.py 中的所有长行
3. 修复 tests/test_provider.py 中的长行
4. 运行 ruff 验证所有 E501 错误已修复
