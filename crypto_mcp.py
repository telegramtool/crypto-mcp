#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mcp.server.fastmcp import FastMCP
from typing import Any
import httpx
import requests
import json
import time
from datetime import datetime, timedelta
import os
import pickle
import sys

# 定义缓存文件路径
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "crypto_cache.pkl")


class CryptoCache:
    """缓存管理器，用于缓存API响应以减少请求次数"""

    def __init__(self, cache_duration=30):  # 默认缓存30分钟
        """初始化缓存管理器

        Args:
            cache_duration: 缓存有效期（分钟）
        """
        self.cache = {}
        self.cache_duration = cache_duration
        self._load_cache()

    def _load_cache(self):
        """从文件加载缓存"""
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)

        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "rb") as f:
                    self.cache = pickle.load(f)
            except (pickle.PickleError, EOFError):
                self.cache = {}

    def _save_cache(self):
        """将缓存保存到文件"""
        try:
            with open(CACHE_FILE, "wb") as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            print(f"缓存保存失败: {e}")

    def get(self, key):
        """获取缓存数据

        Args:
            key: 缓存键名

        Returns:
            缓存的数据，如果缓存不存在或已过期则返回None
        """
        if key in self.cache:
            timestamp, data = self.cache[key]
            if datetime.now() - timestamp < timedelta(minutes=self.cache_duration):
                return data
        return None

    def set(self, key, data):
        """设置缓存数据

        Args:
            key: 缓存键名
            data: 要缓存的数据
        """
        self.cache[key] = (datetime.now(), data)
        self._save_cache()


class AdvancedCryptoPriceService:
    """增强版虚拟币价格查询服务"""

    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.bitget_url = "https://api.bitget.com/api/v2"
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        self.cache = CryptoCache()

    def _make_request(self, endpoint, params=None, cache_key=None):
        """发送API请求并处理缓存逻辑

        Args:
            endpoint: API端点
            params: 请求参数
            cache_key: 缓存键名

        Returns:
            API响应数据
        """
        # 尝试从缓存获取数据
        if cache_key:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        # 发送请求
        try:
            response = requests.get(
                f"{self.base_url}{endpoint}", headers=self.headers, params=params
            )
            response.raise_for_status()
            data = response.json()

            # 存入缓存
            if cache_key:
                self.cache.set(cache_key, data)

            return data
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None

    def get_price(self, coin_ids, currencies=["cny", "usd"]):
        """获取指定虚拟币的当前价格

        Args:
            coin_ids: 虚拟币ID字符串或列表 (如 'bitcoin', 'ethereum' 等)
            currencies: 货币单位列表 (默认为CNY和USD)

        Returns:
            dict: 包含价格信息的字典
        """
        endpoint = "/simple/price"

        # 确保coin_ids是字符串
        if isinstance(coin_ids, list):
            coin_ids = ",".join(coin_ids)

        # 确保currencies是字符串
        if isinstance(currencies, list):
            currencies = ",".join(currencies)

        params = {
            "ids": coin_ids,
            "vs_currencies": currencies,
            "include_market_cap": "true",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
            "include_last_updated_at": "true",
        }

        cache_key = f"price_{coin_ids}_{currencies}"
        return self._make_request(endpoint, params, cache_key)

    def get_coin_detail(self, coin_id):
        """获取虚拟币的详细信息

        Args:
            coin_id: 虚拟币ID (如 'bitcoin')

        Returns:
            dict: 包含详细信息的字典
        """
        endpoint = f"/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "true",
            "market_data": "true",
            "community_data": "true",
            "developer_data": "true",
        }

        cache_key = f"detail_{coin_id}"
        return self._make_request(endpoint, params, cache_key)

    def get_coin_market_chart(self, coin_id, currency="cny", days=7):
        """获取虚拟币的历史价格数据

        Args:
            coin_id: 虚拟币ID
            currency: 货币单位
            days: 数据天数 (1/7/14/30/90/180/365/max)

        Returns:
            dict: 包含历史价格、市值和交易量的字典
        """
        endpoint = f"/coins/{coin_id}/market_chart"
        params = {"vs_currency": currency, "days": days}

        cache_key = f"chart_{coin_id}_{currency}_{days}"
        return self._make_request(endpoint, params, cache_key)

    def get_trending_coins(self):
        """获取当前热门虚拟币列表"""
        endpoint = "/search/trending"
        cache_key = "trending"
        return self._make_request(endpoint, cache_key=cache_key)

    def get_coin_list(self):
        """获取所有支持的虚拟币列表"""
        endpoint = "/coins/list"
        cache_key = "coinlist"
        return self._make_request(endpoint, cache_key=cache_key)

    def get_global_data(self):
        """获取全球加密货币市场数据"""
        endpoint = "/global"
        cache_key = "global"
        return self._make_request(endpoint, cache_key=cache_key)

    def get_candle_data(
        self,
        symbol,
        granularity="1h",
        start_time=None,
        end_time=None,
        k_line_type="MARKET",
        limit=100,
    ):
        """获取K线数据

        Args:
            symbol: 交易币对
            product_type: 产品类型 (USDT-FUTURES, COIN-FUTURES等)
            granularity: k线粒度 (1m, 5m, 15m, 1H等)
            start_time: 开始时间 (可选)
            end_time: 结束时间 (可选)
            k_line_type: k线类型 (MARKET, MARK, INDEX)
            limit: 返回数量限制 (默认100, 最大1000)

        Returns:
            dict: K线数据
        """
        endpoint = "/mix/market/candles"

        params = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "granularity": granularity,
            "kLineType": k_line_type,
            "limit": str(limit),
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        cache_key = f"candle_{symbol}_{granularity}_{limit}"

        try:
            # 对于K线数据，我们直接请求Bitget API，不使用缓存的_make_request方法
            response = requests.get(
                f"{self.bitget_url}{endpoint}", headers=self.headers, params=params
            )
            response.raise_for_status()
            data = response.json()

            # 只有成功获取数据时才缓存
            if data.get("code") == "00000" and "data" in data:
                self.cache.set(cache_key, data)

            return data
        except requests.exceptions.RequestException as e:
            # 如果请求失败，尝试从缓存获取
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data
            print(f"请求K线数据错误: {e}")
            return None

    def format_candle_data(self, candle_data, granularity):
        """格式化K线数据

        Args:
            candle_data: API返回的K线数据
            granularity: k线粒度

        Returns:
            str: 格式化后的K线数据
        """
        if (
            not candle_data
            or candle_data.get("code") != "00000"
            or "data" not in candle_data
            or not candle_data["data"]
        ):
            return "未能获取K线数据或数据为空"

        data = candle_data["data"]
        result = f"\nK线数据 (粒度: {granularity}):\n"
        result += "=" * 50 + "\n"
        result += f"{'时间':<20} {'开盘价':<12} {'最高价':<12} {'最低价':<12} {'收盘价':<12} {'成交量':<12}\n"
        result += "-" * 80 + "\n"

        # 遍历K线数据
        for candle in data[:20]:  # 限制显示前20条以避免输出过长
            time_str = datetime.fromtimestamp(int(candle[0]) / 1000).strftime(
                "%Y-%m-%d %H:%M"
            )
            open_price = candle[1]
            high_price = candle[2]
            low_price = candle[3]
            close_price = candle[4]
            volume = candle[5]

            result += f"{time_str:<20} {open_price:<12} {high_price:<12} {low_price:<12} {close_price:<12} {volume:<12}\n"

        if len(data) > 20:
            result += f"\n... 仅显示前20条数据，共 {len(data)} 条 ...\n"

        return result

    def format_price_info(self, price_data, coin_id, currencies=["cny", "usd"]):
        """格式化价格信息以便于显示

        Args:
            price_data: API返回的价格数据
            coin_id: 虚拟币ID
            currencies: 货币单位列表

        Returns:
            str: 格式化后的价格信息
        """
        if not price_data or coin_id not in price_data:
            return f"未能获取 {coin_id} 的价格信息"

        coin_data = price_data[coin_id]
        result = f"\n{coin_id.upper()} 价格信息:\n"
        result += "=" * 40 + "\n"

        # 循环显示不同货币的价格
        for currency in currencies:
            if isinstance(currency, list):
                currency = currency[0]  # 确保currency是字符串

            price = coin_data.get(currency)
            market_cap = coin_data.get(f"{currency}_market_cap")
            vol_24h = coin_data.get(f"{currency}_24h_vol")
            change_24h = coin_data.get(f"{currency}_24h_change")

            if price:
                result += f"\n{currency.upper()} 价格信息:\n"
                result += "-" * 30 + "\n"
                result += f"当前价格: {price:,.2f} {currency.upper()}\n"

                if market_cap:
                    result += f"市值: {market_cap:,.2f} {currency.upper()}\n"

                if vol_24h:
                    result += f"24小时交易量: {vol_24h:,.2f} {currency.upper()}\n"

                if change_24h:
                    change_emoji = "🔺" if change_24h > 0 else "🔻"
                    result += f"24小时变化: {change_emoji} {change_24h:.2f}%\n"

        # 最后更新时间
        last_updated = coin_data.get("last_updated_at")
        if last_updated:
            last_updated_str = datetime.fromtimestamp(last_updated).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            result += f"\n最后更新时间: {last_updated_str}\n"

        return result

    def format_detailed_info(self, coin_detail):
        """格式化详细信息以便于显示

        Args:
            coin_detail: API返回的详细数据

        Returns:
            str: 格式化后的详细信息
        """
        if not coin_detail:
            return "未能获取详细信息"

        result = (
            f"\n{coin_detail['name']} ({coin_detail['symbol'].upper()}) 详细信息:\n"
        )
        result += "=" * 50 + "\n"

        # 基本信息
        result += "\n基本信息:\n"
        result += "-" * 30 + "\n"
        result += f"名称: {coin_detail['name']}\n"
        result += f"符号: {coin_detail['symbol'].upper()}\n"
        result += f"当前排名: #{coin_detail.get('market_cap_rank', 'N/A')}\n"

        if "hashing_algorithm" in coin_detail and coin_detail["hashing_algorithm"]:
            result += f"哈希算法: {coin_detail['hashing_algorithm']}\n"

        # 描述
        if (
            "description" in coin_detail
            and "zh" in coin_detail["description"]
            and coin_detail["description"]["zh"]
        ):
            description = coin_detail["description"]["zh"]
            # 截取描述的前150个字符
            short_desc = (
                description[:150] + "..." if len(description) > 150 else description
            )
            result += f"简介: {short_desc}\n"

        # 市场数据
        if "market_data" in coin_detail:
            market_data = coin_detail["market_data"]
            result += "\n市场数据:\n"
            result += "-" * 30 + "\n"

            # 当前价格 (CNY和USD)
            if "current_price" in market_data:
                prices = market_data["current_price"]
                if "cny" in prices:
                    result += f"当前价格 (CNY): ¥{prices['cny']:,.2f}\n"
                if "usd" in prices:
                    result += f"当前价格 (USD): ${prices['usd']:,.2f}\n"

            # 价格变化
            if "price_change_percentage_24h" in market_data:
                change_24h = market_data["price_change_percentage_24h"]
                change_emoji = "🔺" if change_24h > 0 else "🔻"
                result += f"24小时价格变化: {change_emoji} {change_24h:.2f}%\n"

            # 市值
            if "market_cap" in market_data and "cny" in market_data["market_cap"]:
                result += f"市值 (CNY): ¥{market_data['market_cap']['cny']:,.2f}\n"

            # 交易量
            if "total_volume" in market_data and "cny" in market_data["total_volume"]:
                result += (
                    f"24小时交易量 (CNY): ¥{market_data['total_volume']['cny']:,.2f}\n"
                )

            # 流通量
            if (
                "circulating_supply" in market_data
                and market_data["circulating_supply"]
            ):
                result += f"流通量: {market_data['circulating_supply']:,.0f} {coin_detail['symbol'].upper()}\n"

            # 总供应量
            if "total_supply" in market_data and market_data["total_supply"]:
                result += f"总供应量: {market_data['total_supply']:,.0f} {coin_detail['symbol'].upper()}\n"

            # 最高价历史
            if "ath" in market_data and "cny" in market_data["ath"]:
                result += f"历史最高价 (CNY): ¥{market_data['ath']['cny']:,.2f}\n"
                if "ath_date" in market_data and "cny" in market_data["ath_date"]:
                    ath_date = datetime.fromisoformat(
                        market_data["ath_date"]["cny"].replace("Z", "+00:00")
                    )
                    result += f"历史最高价日期: {ath_date.strftime('%Y-%m-%d')}\n"

            # 距离最高价的跌幅
            if (
                "ath_change_percentage" in market_data
                and "cny" in market_data["ath_change_percentage"]
            ):
                result += f"距离历史最高价: {market_data['ath_change_percentage']['cny']:.2f}%\n"

        # 链接信息
        if "links" in coin_detail:
            links = coin_detail["links"]
            result += "\n相关链接:\n"
            result += "-" * 30 + "\n"

            if "homepage" in links and links["homepage"] and links["homepage"][0]:
                result += f"官网: {links['homepage'][0]}\n"

            if (
                "blockchain_site" in links
                and links["blockchain_site"]
                and links["blockchain_site"][0]
            ):
                result += f"区块浏览器: {links['blockchain_site'][0]}\n"

            if (
                "official_forum_url" in links
                and links["official_forum_url"]
                and links["official_forum_url"][0]
            ):
                result += f"官方论坛: {links['official_forum_url'][0]}\n"

            if "subreddit_url" in links and links["subreddit_url"]:
                result += f"Reddit: {links['subreddit_url']}\n"

            if (
                "repos_url" in links
                and "github" in links["repos_url"]
                and links["repos_url"]["github"]
                and links["repos_url"]["github"][0]
            ):
                result += f"GitHub: {links['repos_url']['github'][0]}\n"

        return result

    def format_trending_coins(self, trending_data):
        """格式化热门虚拟币信息

        Args:
            trending_data: API返回的热门币种数据

        Returns:
            str: 格式化后的热门币种信息
        """
        if not trending_data or "coins" not in trending_data:
            return "未能获取热门虚拟币信息"

        result = "\n当前热门虚拟币 (全球搜索量最高):\n"
        result += "=" * 50 + "\n"

        for i, coin in enumerate(trending_data["coins"], 1):
            item = coin["item"]
            result += f"{i}. {item['name']} ({item['symbol']})\n"
            result += f"   ID: {item['id']}\n"
            result += f"   市值排名: #{item['market_cap_rank']}\n"
            if "price_btc" in item:
                result += f"   BTC价格: {item['price_btc']:.8f} BTC\n"
            result += "\n"

        return result

    def format_global_data(self, global_data):
        """格式化全球加密货币市场数据

        Args:
            global_data: API返回的全球市场数据

        Returns:
            str: 格式化后的全球市场数据
        """
        if not global_data or "data" not in global_data:
            return "未能获取全球市场数据"

        data = global_data["data"]
        result = "\n全球加密货币市场数据:\n"
        result += "=" * 50 + "\n"

        # 活跃加密货币和交易所数量
        result += f"活跃虚拟币: {data.get('active_cryptocurrencies', 'N/A')}\n"
        result += f"活跃交易所: {data.get('active_exchanges', 'N/A')}\n"

        # 总市值
        if "total_market_cap" in data and "usd" in data["total_market_cap"]:
            result += f"总市值 (USD): ${data['total_market_cap']['usd']:,.0f}\n"
            if "cny" in data["total_market_cap"]:
                result += f"总市值 (CNY): ¥{data['total_market_cap']['cny']:,.0f}\n"

        # 24小时交易量
        if "total_volume" in data and "usd" in data["total_volume"]:
            result += f"24小时总交易量 (USD): ${data['total_volume']['usd']:,.0f}\n"

        # 比特币占比
        if "market_cap_percentage" in data and "btc" in data["market_cap_percentage"]:
            result += f"比特币市值占比: {data['market_cap_percentage']['btc']:.2f}%\n"

        # 以太坊占比
        if "market_cap_percentage" in data and "eth" in data["market_cap_percentage"]:
            result += f"以太坊市值占比: {data['market_cap_percentage']['eth']:.2f}%\n"

        # 市场趋势
        if "market_cap_change_percentage_24h_usd" in data:
            change = data["market_cap_change_percentage_24h_usd"]
            change_emoji = "🔺" if change > 0 else "🔻"
            result += f"24小时市值变化: {change_emoji} {change:.2f}%\n"

        # 更新时间
        if "updated_at" in data:
            updated_at = datetime.fromtimestamp(data["updated_at"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            result += f"\n数据更新时间: {updated_at}\n"

        return result


def get_common_coins():
    """返回常见虚拟币列表"""
    return [
        {"id": "bitcoin", "name": "比特币", "symbol": "BTC"},
        {"id": "ethereum", "name": "以太坊", "symbol": "ETH"},
        {"id": "tether", "name": "泰达币", "symbol": "USDT"},
        {"id": "binancecoin", "name": "币安币", "symbol": "BNB"},
        {"id": "ripple", "name": "瑞波币", "symbol": "XRP"},
        {"id": "cardano", "name": "卡尔达诺", "symbol": "ADA"},
        {"id": "dogecoin", "name": "狗狗币", "symbol": "DOGE"},
        {"id": "solana", "name": "索拉纳", "symbol": "SOL"},
        {"id": "polkadot", "name": "波卡", "symbol": "DOT"},
        {"id": "litecoin", "name": "莱特币", "symbol": "LTC"},
    ]


# 初始化FastMCP服务器
mcp = FastMCP("crypto-price")

# 初始化服务
crypto_service = AdvancedCryptoPriceService()


@mcp.tool()
async def get_coin_price(coin_id: str, currency: str = "cny") -> str:
    """获取指定虚拟币的当前价格

    Args:
        coin_id: 虚拟币的ID (例如 bitcoin, ethereum, dogecoin)
        currency: 货币单位 (默认为人民币cny，也可以是usd等)

    Returns:
        包含价格信息的字符串
    """
    currencies = [c.strip() for c in currency.split(",") if c.strip()]
    if not currencies:
        currencies = ["cny"]

    try:
        price_data = crypto_service.get_price(coin_id, currencies)

        if not price_data or coin_id not in price_data:
            return f"未找到关于 {coin_id} 的价格信息，请检查ID是否正确"

        result = crypto_service.format_price_info(price_data, coin_id, currencies)
        return result
    except Exception as e:
        return f"获取价格信息时出错: {str(e)}"


@mcp.tool()
async def get_trending_coins() -> str:
    """获取当前热门虚拟币列表

    Returns:
        包含热门虚拟币信息的字符串
    """
    try:
        trending_data = crypto_service.get_trending_coins()

        if not trending_data:
            return "无法获取热门虚拟币数据"

        result = crypto_service.format_trending_coins(trending_data)
        return result
    except Exception as e:
        return f"获取热门虚拟币时出错: {str(e)}"


@mcp.tool()
async def get_coin_detail(coin_id: str) -> str:
    """获取虚拟币的详细信息

    Args:
        coin_id: 虚拟币的ID (例如 bitcoin, ethereum)

    Returns:
        包含详细信息的字符串
    """
    try:
        coin_detail = crypto_service.get_coin_detail(coin_id)

        if not coin_detail:
            return f"未找到关于 {coin_id} 的详细信息，请检查ID是否正确"

        result = crypto_service.format_detailed_info(coin_detail)
        return result
    except Exception as e:
        return f"获取详细信息时出错: {str(e)}"


@mcp.tool()
async def get_global_market_data() -> str:
    """获取全球加密货币市场数据

    Returns:
        包含市场数据的字符串
    """
    try:
        global_data = crypto_service.get_global_data()

        if not global_data:
            return "无法获取全球市场数据"

        result = crypto_service.format_global_data(global_data)
        return result
    except Exception as e:
        return f"获取市场数据时出错: {str(e)}"


@mcp.tool()
async def search_coins(query: str, limit: int = 10) -> str:
    """搜索虚拟币

    Args:
        query: 搜索关键词
        limit: 返回结果数量上限，默认10

    Returns:
        包含搜索结果的字符串
    """
    try:
        all_coins = crypto_service.get_coin_list()

        if not all_coins:
            return "无法获取虚拟币列表"

        # 搜索匹配的币种
        results = [
            coin
            for coin in all_coins
            if query.lower() in coin["name"].lower()
            or query.lower() in coin["symbol"].lower()
            or query.lower() in coin["id"].lower()
        ]

        # 限制返回结果数量
        results = results[:limit]

        if not results:
            return f"未找到与 '{query}' 相关的虚拟币"

        # 格式化结果
        result = f"找到 {len(results)} 个与 '{query}' 相关的虚拟币:\n\n"
        for i, coin in enumerate(results, 1):
            result += f"{i}. {coin['name']} ({coin['symbol'].upper()})\n"
            result += f"   ID: {coin['id']}\n\n"

        return result
    except Exception as e:
        return f"搜索时出错: {str(e)}"


@mcp.tool()
async def get_common_coins_prices() -> str:
    """获取常见虚拟币的价格信息

    Returns:
        包含常见虚拟币价格的字符串
    """
    try:
        common_list = get_common_coins()
        coin_ids = [coin["id"] for coin in common_list]
        price_data = crypto_service.get_price(coin_ids, ["cny", "usd"])

        if not price_data:
            return "无法获取价格数据"

        # 格式化结果
        result = "常见虚拟币价格一览:\n\n"

        for coin in common_list:
            coin_id = coin["id"]
            if coin_id in price_data:
                data = price_data[coin_id]

                result += f"{coin['name']} ({coin['symbol'].upper()}):\n"

                cny_price = data.get("cny", "N/A")
                if cny_price != "N/A":
                    result += f"  CNY: ¥{cny_price:,.2f}\n"

                usd_price = data.get("usd", "N/A")
                if usd_price != "N/A":
                    result += f"  USD: ${usd_price:,.2f}\n"

                change_24h = data.get("cny_24h_change", "N/A")
                if change_24h != "N/A":
                    change_emoji = "🔺" if change_24h > 0 else "🔻"
                    result += f"  24h变化: {change_emoji} {change_24h:.2f}%\n"

                result += "\n"

        return result
    except Exception as e:
        return f"获取常见币种价格出错: {str(e)}"


@mcp.tool()
async def get_k_line_data(
    symbol: str,
    granularity: str = "1h",
    limit: int = 100,
    k_line_type: str = "MARKET",
) -> str:
    """获取虚拟币的K线数据

    Args:
        symbol: 交易币对，例如 BTCUSDT, ETHUSDT
        granularity: K线粒度，默认1h (可选: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 12h, 1d, 1w等)
        limit: 返回数据条数，默认100，最大1000
        k_line_type: K线类型，默认MARKET (可选: MARKET, MARK, INDEX)

    Returns:
        包含K线数据的字符串
    """
    try:
        candle_data = crypto_service.get_candle_data(
            symbol=symbol,
            granularity=granularity,
            k_line_type=k_line_type,
            limit=limit,
        )

        if not candle_data or candle_data.get("code") != "00000":
            error_msg = (
                candle_data.get("msg", "未知错误") if candle_data else "获取数据失败"
            )
            return f"获取K线数据失败: {error_msg}"

        result = crypto_service.format_candle_data(candle_data, granularity)
        return result
    except Exception as e:
        return f"获取K线数据时出错: {str(e)}"


if __name__ == "__main__":
    # 启动服务器，使用标准输入/输出作为通信方式
    mcp.run(transport="stdio")
