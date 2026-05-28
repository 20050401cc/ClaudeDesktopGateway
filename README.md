# Claude Desktop Gateway

> 本地代理网关，让 Claude Desktop 通过 MiMo API 运行

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org)

---

## 功能

- 本地 HTTP 代理，接收 Claude Desktop 的 API 请求
- 自动转发到 MiMo（小米）兼容 API
- 支持 `mimo-v2.5-pro` 和 `mimo-v2.5` 两个模型
- 推理模式（thinking block）自动处理
- 零依赖，纯 Python 标准库实现

## 快速开始

### 1. 配置 API Key

在 `~/.claude/settings.json` 中添加：

```json
{
  "api_key": "your-mimo-api-key"
}
```

或设置环境变量：

```bash
export CLAUDE_GATEWAY_API_KEY=your-mimo-api-key
```

### 2. 启动网关

```bash
python claude_desktop_gateway.py --port 8082
```

或使用 PowerShell 脚本：

```powershell
.\start-gateway.ps1
```

### 3. 配置 Claude Desktop

将 Claude Desktop 的 API Base URL 指向 `http://localhost:8082`

## 参数

```
--port PORT        监听端口（默认 8082）
--upstream URL     上游 API 地址（默认 MiMo 官方）
```

## 工作原理

```
Claude Desktop → localhost:8082 → MiMo API
                  (Gateway)        (上游)
```

Gateway 做的事情：
1. 接收 Anthropic 格式的 `/v1/messages` 请求
2. 转换为 MiMo 兼容格式
3. 转发到上游 API
4. 流式返回响应

## 为什么需要这个？

Claude Desktop 原生只支持 Anthropic API。通过 Gateway 代理，可以：

- 使用小米 MiMo 的 Token 额度
- 享受 MiMo-V2.5-Pro 的推理能力
- 在 Claude Desktop 界面中使用国产模型

## License

MIT
