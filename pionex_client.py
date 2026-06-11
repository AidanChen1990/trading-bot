import hmac
import hashlib
import time
import uuid
import requests
from config import (
    PIONEX_API_KEY, PIONEX_SECRET_KEY, PIONEX_BASE_URL,
    LONG_LEVERAGE, SHORT_LEVERAGE, MAX_ORDER_SIZE_USDT
)


def _sign(params: dict, secret: str) -> str:
    """產生 Pionex HMAC-SHA256 簽名"""
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hmac.new(secret.encode(), sorted_params.encode(), hashlib.sha256).hexdigest()


def _headers(params: dict) -> dict:
    signature = _sign(params, PIONEX_SECRET_KEY)
    return {
        "PIONEX-KEY": PIONEX_API_KEY,
        "PIONEX-SIGNATURE": signature,
        "Content-Type": "application/json",
    }


def get_open_positions() -> list:
    """取得目前所有持倉"""
    timestamp = str(int(time.time() * 1000))
    params = {
        "timestamp": timestamp,
    }
    headers = _headers(params)
    try:
        resp = requests.get(
            f"{PIONEX_BASE_URL}/api/v1/account/balances",
            params=params,
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("balances", [])
    except Exception as e:
        print(f"[Pionex] 取得持倉失敗: {e}")
        return []


def place_order(
    symbol: str,
    side: str,          # "BUY" 或 "SELL"
    direction: str,     # "LONG" 或 "SHORT"
    size_usdt: float = None,
) -> dict:
    """
    下合約單
    symbol: 例如 "BTC_USDT"
    side: "BUY"(開倉/加倉) 或 "SELL"(平倉)
    direction: "LONG" 或 "SHORT"
    """
    if size_usdt is None:
        size_usdt = MAX_ORDER_SIZE_USDT

    leverage = LONG_LEVERAGE if direction == "LONG" else SHORT_LEVERAGE
    timestamp = str(int(time.time() * 1000))
    client_order_id = str(uuid.uuid4()).replace("-", "")[:20]

    # Pionex 合約下單參數
    order_params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "size": str(size_usdt),
        "leverage": str(leverage),
        "clientOrderId": client_order_id,
        "timestamp": timestamp,
    }

    params_with_ts = {**order_params}
    headers = _headers(params_with_ts)

    try:
        resp = requests.post(
            f"{PIONEX_BASE_URL}/api/v1/trade/order",
            json=order_params,
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        result = resp.json()
        print(f"[Pionex] 下單成功: {symbol} {direction} {side} ${size_usdt}")
        return {"success": True, "data": result}
    except Exception as e:
        print(f"[Pionex] 下單失敗: {e}")
        return {"success": False, "error": str(e)}


def open_long(symbol: str, size_usdt: float = None) -> dict:
    """開多單"""
    return place_order(symbol, "BUY", "LONG", size_usdt)


def open_short(symbol: str, size_usdt: float = None) -> dict:
    """開空單"""
    return place_order(symbol, "SELL", "SHORT", size_usdt)


def close_long(symbol: str, size_usdt: float = None) -> dict:
    """平多單"""
    return place_order(symbol, "SELL", "LONG", size_usdt)


def close_short(symbol: str, size_usdt: float = None) -> dict:
    """平空單"""
    return place_order(symbol, "BUY", "SHORT", size_usdt)
