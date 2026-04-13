# DebateEngine 部署指南

## 概述

本指南将帮助你在 Render（免费托管服务）上部署 DebateEngine API，并将其连接到 GitHub Pages 上的前端。

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
- **Region**: 选择离你最近的区域
- **Runtime**: `Python`
- **Build Command**: `pip install -e .`
- **Start Command**: `python api_server.py`
- **Plan**: 选择 `Free`

#### 步骤 4：添加环境变量
在 "Environment" 部分添加：
- **Key**: `NVIDIA_API_KEY`
- **Value**: 你的 NVIDIA API 密钥（不要勾选 "Add to environment variable group"）

#### 步骤 5：部署
点击 "Create Web Service"，等待部署完成（通常需要 1-3 分钟）

#### 步骤 6：获取 API 地址
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

## 文件说明

### `render.yaml`
Render 的配置文件，包含：
- 服务类型和名称
- 构建和启动命令
- 免费套餐配置
- 环境变量配置

### `api_server.py`
FastAPI 后端服务器，包含：
- NVIDIA API 集成
- 流式响应支持
- CORS 配置
- 健康检查端点

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

你应该会看到：
```json
{"status": "healthy", "model": "minimaxai/minimax-m2.7"}
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

### CORS 配置
当前 API 配置允许所有来源（`*`），生产环境中应该限制为你的 GitHub Pages 域名。

## 故障排除

### API 无法连接
1. 检查 Render 服务是否正在运行
2. 确认 NVIDIA_API_KEY 已正确设置
3. 查看 Render 的日志

### 前端显示错误
1. 检查浏览器控制台的错误信息
2. 确认 API_URL 配置正确
3. 检查 CORS 配置

## 下一步

部署完成后，你可以：
1. 自定义前端界面
2. 添加更多 API 端点
3. 配置自定义域名
4. 设置监控和告警
