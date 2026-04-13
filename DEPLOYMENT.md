# DebateEngine 部署指南

## 概述

本指南将帮助你在 Render（免费托管服务）上部署 DebateEngine API，并将其连接到 GitHub Pages 上的前端。

## 核心功能增强

### 多 API 密钥支持
- **轮询机制**：使用 Round-Robin 算法在多个 API 密钥间自动切换
- **负载均衡**：自动分配请求，避免单个密钥超限
- **故障转移**：自动检测失效密钥并切换到可用密钥
- **冷却机制**：失效密钥在 60 秒后自动恢复
- **统计监控**：实时追踪每个密钥的使用情况

### 支持的环境变量
- `NVIDIA_API_KEY`：主密钥（必需）
- `NVIDIA_API_KEY_1` 到 `NVIDIA_API_KEY_10`：备用密钥（可选，最多 10 个）

## 部署步骤

### 1. 在 Render 上部署 API

#### 步骤 1：注册 Render 账号
- 访问 https://render.com
- 使用 GitHub 账号登录

#### 步骤 2：从 GitHub 仓库部署
1. 点击 "New +" 按钮，选择 "Web Service"
2. 选择你的 `1235357/debate-engine` 仓库
3. 选择 `main` 分支

#### 步骤 3：配置部署设置
- **Name**: `debate-engine-api`
- **Language**: `Python 3`
- **Region**: 选择离你最近的区域（推荐 Singapore）
- **Build Command**: `pip install -e .`
- **Start Command**: `python api_server.py`
- **Instance Type**: 选择 `Free`

#### 步骤 4：添加环境变量（重要！）
在 "Environment Variables" 部分添加你的 API 密钥：

**单个密钥配置（最少）**：
- **Key**: `NVIDIA_API_KEY`
- **Value**: 输入你的 NVIDIA API 密钥

**多个密钥配置（推荐）**：
- **Key**: `NVIDIA_API_KEY`
- **Value**: 输入你的第一个 NVIDIA API 密钥

然后点击 "Add Environment Variable" 继续添加：
- **Key**: `NVIDIA_API_KEY_1`
- **Value**: 输入你的第二个 NVIDIA API 密钥

继续添加直到所有密钥都配置好（最多支持 11 个：NVIDIA_API_KEY + NVIDIA_API_KEY_1 到 _10）

**注意**：所有密钥的 "sync" 选项都不要勾选

#### 步骤 5：高级配置（可选）
- **Health Check Path**: `/health`
- **Auto-Deploy**: 保持 `On Commit`（自动部署）

#### 步骤 6：部署
点击 "Deploy web service"，等待部署完成（通常需要 1-3 分钟）

#### 步骤 7：获取 API 地址
部署完成后，你会看到一个 URL，类似：
`https://debate-engine-api.onrender.com`

### 2. 配置前端

#### 更新前端 API 地址
编辑 `demo/index.html` 文件，找到 API_URL 配置：

```javascript
// 将这一行：
const API_URL = '';

// 修改为你的 Render API 地址，例如：
const API_URL = 'https://debate-engine-api.onrender.com';
```

#### 提交并推送更改
```bash
git add demo/index.html
git commit -m "Update API URL to Render deployment"
git push origin main
```

### 3. GitHub Pages 会自动更新

GitHub Actions 会自动将更改部署到 GitHub Pages。

## 监控和调试

### 检查 API 状态
访问健康检查端点：
```
https://debate-engine-api.onrender.com/health
```

你会看到类似这样的响应：
```json
{
  "status": "healthy",
  "model": "minimaxai/minimax-m2.7",
  "api_keys": {
    "total_keys": 3,
    "active_keys": 3,
    "key_details": {
      "key_0": {
        "success_count": 42,
        "failure_count": 0,
        "is_active": true
      },
      "key_1": {
        "success_count": 38,
        "failure_count": 1,
        "is_active": true
      },
      "key_2": {
        "success_count": 40,
        "failure_count": 0,
        "is_active": true
      }
    }
  }
}
```

### API 密钥统计
访问统计端点获取详细使用情况：
```
https://debate-engine-api.onrender.com/api/stats
```

## 工作原理

### APIKeyManager 类
这是多密钥管理的核心组件，提供：

1. **Round-Robin 轮询**：按顺序循环使用每个密钥
2. **智能故障检测**：自动检测失败的 API 调用
3. **自动恢复**：失效密钥在冷却期后自动重新激活
4. **线程安全**：使用锁机制确保并发安全
5. **统计追踪**：记录每个密钥的成功/失败次数

### 故障转移流程
1. 请求到达 → 获取下一个密钥
2. 调用成功 → 记录成功统计
3. 调用失败 → 标记密钥为失效，尝试下一个密钥
4. 冷却期（60秒）后 → 密钥自动恢复可用

## 文件说明

### `api_server.py`（v0.2.0 增强版）
FastAPI 后端服务器，包含：
- **APIKeyManager**：多密钥管理器
- 负载均衡和故障转移
- 流式响应支持
- CORS 配置
- 健康检查和统计端点
- 自动重试机制

### `render.yaml`
Render 的配置文件，包含：
- 服务类型和名称
- 构建和启动命令
- 免费套餐配置
- 11 个 API 密钥环境变量配置

### `.github/workflows/deploy-api.yml`
GitHub Actions 工作流，包含：
- NVIDIA API 连接测试
- 项目依赖安装
- 测试运行

## 测试部署

### 1. 测试 API
访问你的 Render API 地址的健康检查端点：
```
https://debate-engine-api.onrender.com/health
```

### 2. 测试前端
访问 GitHub Pages 地址：
```
https://1235357.github.io/debate-engine/
```

## 注意事项

### 免费套餐限制
- Render 免费套餐在 15 分钟无活动后会休眠
- 首次请求可能需要 30-60 秒唤醒
- 每月有 750 小时的免费运行时间

### NVIDIA API 密钥安全
- 不要将 API 密钥提交到代码仓库
- 使用 Render 的环境变量管理
- 定期轮换 API 密钥
- 可以使用多个密钥分散负载和降低风险

### CORS 配置
当前 API 配置允许所有来源（`*`），生产环境中应该限制为你的 GitHub Pages 域名。

### 多密钥最佳实践
1. 使用至少 2-3 个密钥以获得更好的可靠性
2. 监控 `/api/stats` 端点了解使用情况
3. 及时补充失效或耗尽配额的密钥
4. 所有密钥应使用相同的 API 端点和模型

## 故障排除

### API 无法连接
1. 检查 Render 服务是否正在运行
2. 确认至少一个 NVIDIA_API_KEY 已正确设置
3. 查看 Render 的日志
4. 访问 `/health` 端点检查状态

### 前端显示错误
1. 检查浏览器控制台的错误信息
2. 确认 API_URL 配置正确
3. 检查 CORS 配置
4. 确认 API 服务已完全启动（可能需要 1-2 分钟）

### 所有密钥都失败
1. 检查你的 NVIDIA API 密钥是否有效
2. 确认密钥没有超出配额
3. 检查网络连接
4. 查看 Render 日志获取详细错误信息

## 下一步

部署完成后，你可以：
1. 自定义前端界面
2. 添加更多 API 端点
3. 配置自定义域名
4. 设置监控和告警
5. 添加更多 API 密钥扩展容量
6. 使用 `/api/stats` 监控密钥使用情况
