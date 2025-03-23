#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mcp.server.fastmcp import FastMCP
import requests
from datetime import datetime, timedelta
import os
import pickle
import time
import gzip
import base64
from io import BytesIO
import warnings
import json

# 定义缓存文件路径
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "crypto_cache.pkl")


class CryptoCache:
    """缓存管理器, 用于缓存API响应以减少请求次数"""

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
            缓存的数据, 如果缓存不存在或已过期则返回None
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


# Coinglass API功能
# 禁用SSL警告
warnings.filterwarnings(
    "ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning
)


def yt(encrypted_text, key):
    """解密Coinglass API返回的数据

    Args:
        encrypted_text: 加密文本
        key: 解密密钥

    Returns:
        解密后的文本
    """
    if encrypted_text is None:
        return None

    def decrypt_aes(encrypted_text, key):
        # 创建AES解密器 (ECB模式)
        cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)

        # 解密
        try:
            # 解密base64数据
            encrypted_bytes = base64.b64decode(encrypted_text)
            decrypted_bytes = cipher.decrypt(encrypted_bytes)

            # 移除PKCS7填充
            padding_len = decrypted_bytes[-1]
            if padding_len > 16 or padding_len < 1:  # 检查填充长度是否合理
                raise ValueError("不正确的填充")

            # 检查所有填充字节是否一致
            for i in range(1, padding_len + 1):
                if decrypted_bytes[-i] != padding_len:
                    raise ValueError("填充验证失败")

            decrypted_bytes = decrypted_bytes[:-padding_len]

            # 检查是否是gzip格式 (1f8b开头)
            if (
                len(decrypted_bytes) > 2
                and decrypted_bytes[0] == 0x1F
                and decrypted_bytes[1] == 0x8B
            ):
                return decompress_gzip(decrypted_bytes)
            else:
                # 如果不是压缩格式，直接返回解密结果
                return decrypted_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            raise Exception(f"解密失败: {str(e)}")

    def decompress_gzip(byte_array):
        try:
            with BytesIO(byte_array) as f:
                with gzip.GzipFile(fileobj=f, mode="rb") as g:
                    decompressed_data = g.read()
            return decompressed_data.decode("utf-8")
        except Exception as e:
            raise Exception(f"gzip解压缩失败: {str(e)}")

    decrypted_text = decrypt_aes(encrypted_text, key)

    # 移除首尾的双引号（如果存在）
    if decrypted_text and isinstance(decrypted_text, str):
        if decrypted_text[0] == '"':
            decrypted_text = decrypted_text[1:]
        if decrypted_text[-1] == '"':
            decrypted_text = decrypted_text[:-1]

    return decrypted_text


def calculate_time_range(granularity="1h", lookback_count=100):
    """计算时间范围，根据K线粒度动态计算startTime和endTime

    Args:
        granularity: K线粒度，如1m、5m、1h、4h、1d、1w等
        lookback_count: 需要获取的K线数量

    Returns:
        tuple: (startTime, endTime) 时间戳(毫秒)
    """
    now = datetime.now()
    end_time = int(now.timestamp() * 1000)  # 毫秒时间戳

    # 解析粒度
    if granularity == "1w":
        seconds_per_unit = 7 * 24 * 60 * 60
    elif granularity.endswith("d"):
        seconds_per_unit = int(granularity[:-1]) * 24 * 60 * 60
    elif granularity.endswith("h"):
        seconds_per_unit = int(granularity[:-1]) * 60 * 60
    elif granularity.endswith("m"):
        seconds_per_unit = int(granularity[:-1]) * 60
    else:
        # 默认为1小时
        seconds_per_unit = 60 * 60

    # 计算开始时间
    start_time = end_time - (seconds_per_unit * lookback_count * 1000)

    return start_time, end_time


def normalize_granularity(granularity):
    """标准化K线粒度格式

    Args:
        granularity: K线粒度，如1m、5m、1h、4h、1d、1w等

    Returns:
        str: 标准化后的K线粒度
    """
    granularity = granularity.lower()

    # 对于周线，API使用1w格式
    if granularity == "1w":
        return granularity

    # 对于其他粒度，API使用反转的格式（如h1而非1h）
    return granularity[::-1]


class CoinglassService:
    """Coinglass API服务类"""

    def __init__(self):
        self.cache = CryptoCache(cache_duration=15)  # 使用15分钟缓存时间

    def get_coinglass_data(self, url):
        """获取Coinglass API数据

        Args:
            url: API URL

        Returns:
            解密后的API数据
        """
        cache_key = f"coinglass_{url}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        headers = {
            "language": "zh",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua": '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            "sec-ch-ua-mobile": "?0",
            "encryption": "true",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "accept": "application/json",
            "cache-ts": str(int(time.time() * 1000)),
            "origin": "https://www.coinglass.com",
            "sec-fetch-site": "same-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://www.coinglass.com/",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "priority": "u=1, i",
        }

        try:
            # 禁用SSL证书验证
            response = requests.get(url, headers=headers, verify=False)

            # 检查HTTP响应状态
            if response.status_code != 200:
                print(f"API请求失败，状态码: {response.status_code}")
                return None

            response_json = response.json()
            if not response_json.get("success", False):
                print(f"API返回错误: {response_json}")
                return None

            user_header = response.headers.get("user")
            if user_header is None:
                print("响应头中没有找到'user'字段")
                return response_json.get("data")

            data = yt(
                response_json.get("data"),
                yt(user_header, "Y29pbmdsYXNzL2Fw"),
            )
            # 尝试解析返回的数据
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    print(f"无法解析API返回的数据为JSON")

            # 缓存结果
            self.cache.set(cache_key, data)
            return data
        except Exception as e:
            print(f"请求或解析过程中出错: {e}")
            return None

    def get_symbol_info(self, symbol):
        """获取币种基本信息，返回pair和exName

        Args:
            symbol: 币种符号，如BTC、ETH

        Returns:
            tuple: (pair, exName, 成交额)
        """
        symbol_upper = symbol.upper()
        list_url = f"https://fapi.coinglass.com/api/select/coins/tickers?keyword={symbol_upper}&exName=&type=Futures"
        data = self.get_coinglass_data(list_url)
        if not data or len(data) == 0:
            return None, None, None

        pair = None
        exName = None
        成交额 = None

        if "instrument" in data[0]:
            pair = data[0]["instrument"]["instrumentId"]
            exName = data[0]["instrument"]["exName"]

        if "volUsd" in data[0]:
            成交额 = data[0]["volUsd"]

        return pair, exName, 成交额

    def get_coin_info(self, symbol):
        """获取此币种信息

        Args:
            symbol: 交易币对, 例如 BTC, ETH

        Returns:
            币种详细信息
        """
        pair, exName, _ = self.get_symbol_info(symbol)

        if not pair or not exName:
            return None

        url = f"https://fapi.coinglass.com/api/ticker?pair={pair}&exName={exName}&type=Futures"
        return self.get_coinglass_data(url)

    def get_kline_data(self, symbol, granularity="1h", lookback_count=100):
        """获取K线数据

        Args:
            symbol: 交易币对, 例如 BTC, ETH
            granularity: K线粒度, 默认1h
            lookback_count: 需要获取的K线数量，默认100条

        Returns:
            K线数据数组
        """
        pair, exName, _ = self.get_symbol_info(symbol)

        if not pair or not exName:
            return None

        start_time, end_time = calculate_time_range(granularity, lookback_count)
        api_granularity = normalize_granularity(granularity)

        url = f"https://fapi.coinglass.com/api/v2/kline?symbol={exName}_{pair}%23kline&interval={api_granularity}&endTime={end_time}&startTime={start_time}&minLimit=false"
        return self.get_coinglass_data(url)

    def get_position_info(self, symbol, granularity="1h", lookback_count=100):
        """获取持仓信息

        Args:
            symbol: 交易币对, 例如 BTC, ETH
            granularity: K线粒度, 默认1h
            lookback_count: 需要获取的K线数量，默认100条

        Returns:
            持仓信息数据数组
        """
        pair, exName, _ = self.get_symbol_info(symbol)

        if not pair or not exName:
            return None

        start_time, end_time = calculate_time_range(granularity, lookback_count)
        api_granularity = normalize_granularity(granularity)

        url = f"https://fapi.coinglass.com/api/v2/kline?symbol={exName}_{pair}%23coin%23oi_kline&interval={api_granularity}&endTime={end_time}&startTime={start_time}&minLimit=false"
        return self.get_coinglass_data(url)

    def get_trade_volume(self, symbol, granularity="1h", lookback_count=100):
        """获取成交量[买入卖出的交易币数量]

        Args:
            symbol: 交易币对, 例如 BTC, ETH
            granularity: K线粒度, 默认1h
            lookback_count: 需要获取的K线数量，默认100条

        Returns:
            成交量数据数组
        """
        pair, exName, _ = self.get_symbol_info(symbol)
        if not pair or not exName:
            return None

        start_time, end_time = calculate_time_range(granularity, lookback_count)
        api_granularity = normalize_granularity(granularity)

        url = f"https://fapi.coinglass.com/api/v2/kline?symbol={exName}_{pair}%23buy_sell_qty_kline&interval={api_granularity}&endTime={end_time}&startTime={start_time}&minLimit=false"
        return self.get_coinglass_data(url)

    def get_trade_amount(self, symbol, granularity="1h", lookback_count=100):
        """获取成交额[买入卖出的美金]

        Args:
            symbol: 交易币对, 例如 BTC, ETH
            granularity: K线粒度, 默认1h
            lookback_count: 需要获取的K线数量，默认100条

        Returns:
            成交额数据数组
        """
        symbol_upper = symbol.upper()
        api_granularity = normalize_granularity(granularity)

        # 这个接口不需要pair和exName
        url = f"https://capi.coinglass.com/api/v2/kline?diff=false&minLimit=false&limit={lookback_count}&interval={api_granularity}&symbol=ALL%23{symbol_upper}%23aggregated_spot_buy_sell_usd"
        return self.get_coinglass_data(url)

    def get_exchange_position(self, symbol):
        """获取持仓量[各交易所]

        Args:
            symbol: 交易币对, 例如 BTC, ETH

        Returns:
            各交易所持仓量数据
        """
        symbol_upper = symbol.upper()

        # 这个接口不需要pair和exName
        url = (
            f"https://capi.coinglass.com/api/openInterest/ex/info?symbol={symbol_upper}"
        )
        return self.get_coinglass_data(url)

    def format_kline_data(self, data):
        """格式化K线数据

        Args:
            data: K线数据

        Returns:
            格式化后的K线数据
        """
        if not data:
            return "未能获取K线数据"

        result = "K线数据:\n"
        result += "时间\t\t开盘价\t\t最高价\t\t最低价\t\t收盘价\t\t成交量\n"
        result += "-" * 80 + "\n"

        for item in data:
            time_str = datetime.fromtimestamp(item[0] / 1000).strftime("%Y-%m-%d %H:%M")
            result += f"{time_str}\t{item[1]}\t\t{item[2]}\t\t{item[3]}\t\t{item[4]}\t\t{item[5]}\n"

        return result

    def format_position_info(self, data):
        """格式化持仓信息

        Args:
            data: 持仓信息数据

        Returns:
            格式化后的持仓信息
        """
        if not data:
            return "未能获取持仓信息"

        result = "持仓信息:\n"
        result += "时间\t\t开盘持仓\t最高持仓\t最低持仓\t收盘持仓\n"
        result += "-" * 80 + "\n"

        for item in data:
            time_str = datetime.fromtimestamp(item[0] / 1000).strftime("%Y-%m-%d %H:%M")
            result += f"{time_str}\t{item[1]}\t\t{item[2]}\t\t{item[3]}\t\t{item[4]}\n"

        return result

    def format_trade_volume(self, data):
        """格式化成交量信息

        Args:
            data: 成交量数据

        Returns:
            格式化后的成交量信息
        """
        if not data:
            return "未能获取成交量信息"

        result = "成交量信息:\n"
        result += "时间\t\t买入数量\t卖出数量\n"
        result += "-" * 60 + "\n"

        for item in data:
            time_str = datetime.fromtimestamp(item[0] / 1000).strftime("%Y-%m-%d %H:%M")
            result += f"{time_str}\t{item[1]}\t\t{item[2]}\n"

        return result

    def format_trade_amount(self, data):
        """格式化成交额信息

        Args:
            data: 成交额数据

        Returns:
            格式化后的成交额信息
        """
        if not data:
            return "未能获取成交额信息"

        result = "成交额信息(美元):\n"
        result += "时间\t\t买入金额\t卖出金额\n"
        result += "-" * 60 + "\n"

        for item in data:
            time_str = datetime.fromtimestamp(item[0] / 1000).strftime("%Y-%m-%d %H:%M")
            result += f"{time_str}\t{item[1]}\t\t{item[2]}\n"

        return result

    def format_exchange_position(self, data):
        """格式化交易所持仓信息

        Args:
            data: 交易所持仓数据

        Returns:
            格式化后的交易所持仓信息
        """
        if not data:
            return "未能获取交易所持仓信息"

        result = "各交易所持仓信息:\n"
        result += "交易所\t\t持仓量\t\t持仓比例\n"
        result += "-" * 60 + "\n"

        for item in data:
            result += (
                f"{item['exchangeName']}\t\t{item['oi']}\t\t{item['oiPercent']}%\n"
            )

        return result


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
        self.coinglass_service = CoinglassService()  # 添加Coinglass服务

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
            # 对于K线数据, 我们直接请求Bitget API, 不使用缓存的_make_request方法
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
            # 如果请求失败, 尝试从缓存获取
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
            result += f"\n... 仅显示前20条数据, 共 {len(data)} 条 ...\n"

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
        currency: 货币单位 (默认为人民币cny, 也可以是usd等)

    Returns:
        包含价格信息的字符串
    """
    currencies = [c.strip() for c in currency.split(",") if c.strip()]
    if not currencies:
        currencies = ["cny"]

    try:
        price_data = crypto_service.get_price(coin_id, currencies)

        if not price_data or coin_id not in price_data:
            return f"未找到关于 {coin_id} 的价格信息, 请检查ID是否正确"

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
            return f"未找到关于 {coin_id} 的详细信息, 请检查ID是否正确"

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
        limit: 返回结果数量上限, 默认10

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
        symbol: 交易币对, 例如 BTCUSDT, ETHUSDT
        granularity: K线粒度, 默认1h (可选: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 12h, 1d, 1w等)
        limit: 返回数据条数, 默认100, 最大1000
        k_line_type: K线类型, 默认MARKET (可选: MARKET, MARK, INDEX)

    Returns:
        数组格式如下: index[0] 是时间戳, 如 1742652000 代表时间:2025-3-22 22:00:00; index[1] 是开盘价; index[2] 是最高价; index[3] 是最低价; index[4] 是收盘价, 最新一个收盘价可能还在持续更新; index[5] 是交易币成交量；
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


# Coinglass API工具
@mcp.tool()
async def coinglass_get_coin_info(symbol: str) -> str:
    """获取虚拟币的合约市场信息 (Coinglass API)

    Args:
        symbol: 币种符号，例如BTC、ETH

    Returns:
        包含币种在合约市场的详细信息
    """
    try:
        data = crypto_service.coinglass_service.get_coin_info(symbol)
        if not data:
            return f"未找到关于 {symbol} 的合约市场信息，请检查符号是否正确"

        # 格式化输出
        result = f"{symbol.upper()} 合约市场信息:\n"
        result += "=" * 50 + "\n"

        if isinstance(data, dict):
            for key, value in data.items():
                result += f"{key}: {value}\n"
        elif isinstance(data, list) and data:
            item = data[0]
            if isinstance(item, dict):
                for key, value in item.items():
                    result += f"{key}: {value}\n"
            else:
                result += f"{data}\n"
        else:
            result += f"{data}\n"

        return result
    except Exception as e:
        return f"获取合约市场信息时出错: {str(e)}"


@mcp.tool()
async def coinglass_get_kline_data(
    symbol: str, granularity: str = "1h", lookback_count: int = 100
) -> str:
    """获取虚拟币合约的K线数据 (Coinglass API)

    Args:
        symbol: 币种符号，例如BTC、ETH
        granularity: K线粒度，默认1h (可选: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 12h, 24h, 1d, 1w等)
        lookback_count: 需要获取的K线数量，默认100条

    Returns:
        包含K线数据的格式化信息
    """
    try:
        data = crypto_service.coinglass_service.get_kline_data(
            symbol, granularity, lookback_count
        )
        if not data:
            return f"未找到关于 {symbol} 的K线数据，请检查符号是否正确"

        # 格式化结果
        formatted_data = crypto_service.coinglass_service.format_kline_data(data)
        return formatted_data
    except Exception as e:
        return f"获取K线数据时出错: {str(e)}"


@mcp.tool()
async def coinglass_get_position_info(
    symbol: str, granularity: str = "1h", lookback_count: int = 100
) -> str:
    """获取虚拟币合约的持仓信息 (Coinglass API)

    Args:
        symbol: 币种符号，例如BTC、ETH
        granularity: K线粒度，默认1h (可选: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 12h, 24h, 1d, 1w等)
        lookback_count: 需要获取的K线数量，默认100条

    Returns:
        包含持仓信息的格式化数据
    """
    try:
        data = crypto_service.coinglass_service.get_position_info(
            symbol, granularity, lookback_count
        )
        if not data:
            return f"未找到关于 {symbol} 的持仓信息，请检查符号是否正确"

        # 格式化结果
        formatted_data = crypto_service.coinglass_service.format_position_info(data)
        return formatted_data
    except Exception as e:
        return f"获取持仓信息时出错: {str(e)}"


@mcp.tool()
async def coinglass_get_trade_volume(
    symbol: str, granularity: str = "1h", lookback_count: int = 100
) -> str:
    """获取虚拟币合约的成交量信息 (Coinglass API)

    Args:
        symbol: 币种符号，例如BTC、ETH
        granularity: K线粒度，默认1h (可选: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 12h, 24h, 1d, 1w等)
        lookback_count: 需要获取的K线数量，默认100条

    Returns:
        包含成交量信息的格式化数据
    """
    try:
        data = crypto_service.coinglass_service.get_trade_volume(
            symbol, granularity, lookback_count
        )
        if not data:
            return f"未找到关于 {symbol} 的成交量信息，请检查符号是否正确"

        # 格式化结果
        formatted_data = crypto_service.coinglass_service.format_trade_volume(data)
        return formatted_data
    except Exception as e:
        return f"获取成交量信息时出错: {str(e)}"


@mcp.tool()
async def coinglass_get_trade_amount(
    symbol: str, granularity: str = "1h", lookback_count: int = 100
) -> str:
    """获取虚拟币的成交额信息 (Coinglass API)

    Args:
        symbol: 币种符号，例如BTC、ETH
        granularity: K线粒度，默认1h (可选: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 12h, 24h, 1d, 1w等)
        lookback_count: 需要获取的K线数量，默认100条

    Returns:
        包含成交额信息的格式化数据
    """
    try:
        data = crypto_service.coinglass_service.get_trade_amount(
            symbol, granularity, lookback_count
        )
        if not data:
            return f"未找到关于 {symbol} 的成交额信息，请检查符号是否正确"

        # 格式化结果
        formatted_data = crypto_service.coinglass_service.format_trade_amount(data)
        return formatted_data
    except Exception as e:
        return f"获取成交额信息时出错: {str(e)}"


@mcp.tool()
async def coinglass_get_exchange_position(symbol: str) -> str:
    """获取虚拟币在各交易所的持仓分布 (Coinglass API)

    Args:
        symbol: 币种符号，例如BTC、ETH

    Returns:
        包含各交易所持仓分布的格式化信息
    """
    try:
        data = crypto_service.coinglass_service.get_exchange_position(symbol)
        if not data:
            return f"未找到关于 {symbol} 的交易所持仓分布信息，请检查符号是否正确"

        # 格式化结果
        formatted_data = crypto_service.coinglass_service.format_exchange_position(data)
        return formatted_data
    except Exception as e:
        return f"获取交易所持仓分布信息时出错: {str(e)}"


if __name__ == "__main__":
    # 启动服务器, 使用标准输入/输出作为通信方式
    mcp.run(transport="stdio")
