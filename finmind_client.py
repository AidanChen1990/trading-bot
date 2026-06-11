import requests
from datetime import datetime, timedelta
from config import FINMIND_API_KEY, FINMIND_BASE_URL


# FinMind 加密貨幣幣種對應表（FinMind 使用的 dataset 名稱）
CRYPTO_DATASET = "CryptoPrice"

# TradingView 幣種代號 → FinMind 對應
SYMBOL_MAP = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "SOLUSDT": "SOL",
    "BNBUSDT": "BNB",
    "XRPUSDT": "XRP",
    "DOGEUSDT": "DOGE",
    "ADAUSDT": "ADA",
    "AVAXUSDT": "AVAX",
    "DOTUSDT": "DOT",
    "MATICUSDT": "MATIC",
}


def _get_crypto_symbol(tv_symbol: str) -> str:
    """將 TradingView 幣種代號轉換為 FinMind 格式"""
    # 去掉 PERP、USDT 等後綴，取得基礎幣種
    base = tv_symbol.upper().replace("PERP", "").replace("USDT", "").replace(".P", "")
    return SYMBOL_MAP.get(tv_symbol.upper(), base)


def get_recent_prices(tv_symbol: str, days: int = 30) -> dict:
    """
    取得幣種近期價格資料
    回傳: 包含近期收盤價列表、均價、波動率等資訊
    """
    fm_symbol = _get_crypto_symbol(tv_symbol)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        resp = requests.get(
            f"{FINMIND_BASE_URL}/data",
            params={
                "dataset": CRYPTO_DATASET,
                "data_id": fm_symbol,
                "start_date": start_date,
                "end_date": end_date,
                "token": FINMIND_API_KEY,
            },
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        records = data.get("data", [])
        if not records:
            return {"error": f"無法取得 {fm_symbol} 的價格資料"}

        closes = [float(r["close"]) for r in records if "close" in r]
        if not closes:
            return {"error": "價格資料格式異常"}

        # 計算統計資料
        avg_price = sum(closes) / len(closes)
        max_price = max(closes)
        min_price = min(closes)
        latest_price = closes[-1]

        # 計算近期波動率（標準差 / 均價）
        variance = sum((p - avg_price) ** 2 for p in closes) / len(closes)
        std_dev = variance ** 0.5
        volatility_pct = (std_dev / avg_price) * 100

        # 近期趨勢（最近7天 vs 前7天均價）
        recent_7 = closes[-7:] if len(closes) >= 7 else closes
        prev_7 = closes[-14:-7] if len(closes) >= 14 else closes[:len(closes)//2]
        trend = "上升" if (sum(recent_7)/len(recent_7)) > (sum(prev_7)/len(prev_7)) else "下降"

        return {
            "symbol": fm_symbol,
            "latest_price": latest_price,
            "avg_price_30d": round(avg_price, 4),
            "max_price_30d": max_price,
            "min_price_30d": min_price,
            "volatility_pct_30d": round(volatility_pct, 2),
            "recent_trend_7d": trend,
            "price_vs_avg": round(((latest_price - avg_price) / avg_price) * 100, 2),
            "data_points": len(closes),
        }

    except Exception as e:
        print(f"[FinMind] 取得 {tv_symbol} 資料失敗: {e}")
        return {"error": str(e)}


def get_btc_market_context() -> dict:
    """取得 BTC 大盤環境（供 Claude 判斷整體市場）"""
    return get_recent_prices("BTCUSDT", days=30)
