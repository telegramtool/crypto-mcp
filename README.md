# Crypto MCP

![License](https://img.shields.io/badge/license-MIT-blue.svg)

这是一个基于Model Context Protocol (MCP)的加密货币价格查询服务器。它提供了各种工具来获取虚拟币价格、市场趋势、详细信息和K线数据。

## 目录

* [安装](#安装)
* [使用方法](#使用方法)
* [工具](#工具)
* [资源](#资源)
* [许可证](#许可证)

## 安装

### 通过pip安装

```bash
pip install crypto_mcp
```

### 手动安装

克隆仓库并安装依赖：

```bash
git clone https://github.com/telegramtool/crypto_mcp.git
cd crypto_mcp
pip install -r requirements.txt
```

## 使用方法

### 直接运行

安装后，可以直接使用以下命令运行MCP服务器：

```bash
crypto_mcp
```

### 在Claude桌面应用中配置

将以下配置添加到Claude桌面客户端的配置文件中：

```json
{
  "mcpServers": {
    "crypto": {
      "command": "crypto_mcp",
      "args": [],
      "env": {}
    }
  }
}
```

### 在Cursor中配置

将以下配置添加到`~/.cursor/mcp.json`文件中：

```json
{
  "mcpServers": {
    "crypto": {
      "command": "crypto_mcp",
      "args": [],
      "env": {}
    }
  }
}
```

### 在Windsurf中配置

将以下配置添加到`./codeium/windsurf/model_config.json`文件中：

```json
{
  "mcpServers": {
    "crypto-price": {
      "command": "crypto_mcp",
      "args": [],
      "env": {}
    }
  }
}
```

## 工具

* `get_coin_price` - 获取指定虚拟币的当前价格
* `get_trending_coins` - 获取当前热门虚拟币列表
* `get_coin_detail` - 获取虚拟币的详细信息
* `get_global_market_data` - 获取全球加密货币市场数据
* `search_coins` - 搜索虚拟币
* `get_common_coins_prices` - 获取常见虚拟币的价格信息
* `get_k_line_data` - 获取虚拟币的K线数据

## 资源

* [CoinGecko API](https://www.coingecko.com/en/api)
* [Bitget API](https://bitgetlimited.github.io/apidoc/en/spot)
* [Model Context Protocol](https://github.com/hyperbrowserai/mcp)

## 许可证

此项目采用MIT许可证。
