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

### 安装 via Smithery [推荐]

要安装 Crypto MCP for Claude Desktop 自动通过 [Smithery](https://clis.smithery.ai/server/@telegramtool/crypto_mcp), 执行以下命令:

```bash
npx -y @smithery/cli install @telegramtool/crypto_mcp --client claude
```
[内含多种安装方式](https://clis.smithery.ai/server/@telegramtool/crypto_mcp)

![内含多种安装方式](https://github.com/user-attachments/assets/cf999272-9f40-42fd-a764-32302578248a)


### 手动安装

克隆仓库并安装依赖：

```bash
git clone https://github.com/telegramtool/crypto_mcp.git
cd crypto_mcp
pip install -r requirements.txt
```

## 使用方法


### 在Cursor中配置

将以下配置添加到`~/.cursor/mcp.json`文件中：

PIP安装:
```json
{
    "mcpServers": {
        "crypto_mcp": {
            "command": "uv",
            "args": [
                "run",
                "-m",
                "crypto_mcp"]
        }
    }
}
```
Smithery安装:
```json
{
  "mcpServers": {
    "crypto_mcp": {
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "@smithery/cli@latest",
        "run",
        "@telegramtool/crypto_mcp",
        "--config",
        "{}"
      ]
    }
  }
}
```

## 工具

### CoinGecko和Bitget API工具
* `get_coin_price` - 获取指定虚拟币的当前价格
* `get_trending_coins` - 获取当前热门虚拟币列表
* `get_coin_detail` - 获取虚拟币的详细信息
* `get_global_market_data` - 获取全球加密货币市场数据
* `search_coins` - 搜索虚拟币
* `get_common_coins_prices` - 获取常见虚拟币的价格信息
* `get_k_line_data` - 获取虚拟币的K线数据

### Coinglass API工具
* `coinglass_get_coin_info` - 获取虚拟币的合约市场信息
* `coinglass_get_kline_data` - 获取虚拟币合约的K线数据
* `coinglass_get_position_info` - 获取虚拟币合约的持仓信息
* `coinglass_get_trade_volume` - 获取虚拟币合约的成交量信息
* `coinglass_get_trade_amount` - 获取虚拟币的成交额信息
* `coinglass_get_exchange_position` - 获取虚拟币在各交易所的持仓分布

## 资源

* [CoinGecko API](https://www.coingecko.com/en/api)
* [Bitget API](https://bitgetlimited.github.io/apidoc/en/spot)
* [Coinglass](https://www.coinglass.com/)

## 许可证

此项目采用MIT许可证。
