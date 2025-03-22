# 虚拟币价格查询 MCP 服务

这是一个使用 MCP (Model Context Protocol) 协议的虚拟币价格查询服务，允许 Claude 等大语言模型通过对话界面查询虚拟币价格和市场数据。

## 项目特点

- 🔍 **实时加密货币数据查询**: 获取最新的虚拟币价格、趋势和市场数据
- 🤖 **AI助手工具集成**: 与Claude等支持MCP的AI助手无缝集成
- 🛠️ **多种部署方式**: 支持直接运行、Docker容器化、Linux systemd服务和Windows服务
- 📊 **丰富的数据功能**: 提供价格查询、趋势分析、详细信息等多种功能

## 可用工具列表

此MCP服务提供以下工具:

| 工具名称 | 描述 | 参数 |
|---------|------|------|
| get_coin_price | 获取指定虚拟币的当前价格 | coin_id, currency="cny" |
| get_trending_coins | 获取当前热门虚拟币列表 | 无 |
| get_coin_detail | 获取虚拟币的详细信息 | coin_id |
| get_global_market_data | 获取全球加密货币市场数据 | 无 |
| search_coins | 搜索虚拟币 | query, limit=10 |
| get_common_coins_prices | 获取常见虚拟币的价格信息 | 无 |

## 快速开始

### 前提条件

- Python 3.6+
- 网络连接（用于访问CoinGecko API）

### 安装

```bash
# 克隆仓库
git clone https://github.com/telegramtool/crypto_mcp.git
cd crypto_mcp

# 安装依赖
pip install -r requirements_api.txt
pip install "mcp[cli]>=0.4.0"
```

### 运行服务

```bash
# 直接运行
python web_mcp_server.py
```

服务将在 http://localhost:8080 启动

## 部署指南

详细的部署指南可以在以下文件中找到:

- [MCP服务部署指南](MCP_DEPLOYMENT.md) - 包含所有部署方法的详细说明
- [Claude集成指南](CLAUDE_INTEGRATION.md) - 如何将服务与Claude桌面版集成

## 示例用法

在Claude中可以尝试以下提示:

1. "查询比特币的当前价格"
2. "告诉我今天最热门的加密货币"
3. "以太坊详细信息是什么?"
4. "全球加密货币市场现状如何?"
5. "搜索与'dog'相关的加密货币"

## 项目结构

```
crypto-price-mcp/
├── api/                      # API服务核心代码
├── Dockerfile.mcp            # MCP服务的Docker配置
├── docker-compose.mcp.yml    # Docker-compose配置
├── web_mcp_server.py         # MCP Web服务主程序
├── run_mcp_server.py         # MCP CLI服务程序
├── advanced_crypto_service.py # 高级加密货币服务
├── requirements_api.txt      # API依赖列表
├── crypto-mcp.service        # Linux systemd服务配置
├── crypto-mcp-windows.xml    # Windows服务配置
├── install_windows_service.bat # Windows服务安装脚本
├── MCP_DEPLOYMENT.md         # 部署文档
├── CLAUDE_INTEGRATION.md     # Claude集成文档
└── README.md                 # 项目说明
```

## 服务状态确认

检查服务是否正常运行:

```bash
# 健康检查
curl http://localhost:8080/healthz

# 查看工具列表
curl http://localhost:8080/tools
```

## 许可协议

本项目采用 MIT 许可证

## 致谢

- 感谢 [CoinGecko API](https://www.coingecko.com/en/api) 提供数据支持
- 感谢 [Anthropic](https://www.anthropic.com/) 提供 MCP 协议规范 