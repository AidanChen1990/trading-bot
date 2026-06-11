import requests
from config import LINE_NOTIFY_TOKEN

LINE_NOTIFY_URL = "https://notify-api.line.me/api/notify"


def send_message(message: str) -> bool:
    """發送 LINE Notify 訊息"""
    if not LINE_NOTIFY_TOKEN:
        print("[LINE] 未設定 LINE_NOTIFY_TOKEN，跳過通知")
        return False

    try:
        resp = requests.post(
            LINE_NOTIFY_URL,
            headers={"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"},
            data={"message": message},
            timeout=10
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[LINE] 通知發送失敗: {e}")
        return False


def notify_signal_received(signal: dict) -> None:
    """收到 TradingView 訊號時通知"""
    symbol = signal.get("symbol", "未知")
    direction = signal.get("direction", "未知")
    timeframe = signal.get("timeframe", "未知")
    price = signal.get("price", "未知")

    emoji = "📈" if direction == "LONG" else "📉"
    msg = (
        f"\n{emoji} 收到交易訊號\n"
        f"幣種: {symbol}\n"
        f"方向: {direction}\n"
        f"時框: {timeframe}\n"
        f"價格: {price}\n"
        f"⏳ Claude 評估中..."
    )
    send_message(msg)


def notify_approved(signal: dict, evaluation: dict, order_result: dict) -> None:
    """Claude 核准並下單成功時通知"""
    symbol = signal.get("symbol", "未知")
    direction = signal.get("direction", "未知")
    price = signal.get("price", "未知")
    confidence = evaluation.get("confidence", 0)
    reason = evaluation.get("reason", "")

    emoji = "✅📈" if direction == "LONG" else "✅📉"
    success = order_result.get("success", False)
    order_status = "下單成功 🎯" if success else f"下單失敗 ❌ {order_result.get('error', '')}"

    msg = (
        f"\n{emoji} Claude 核准 - {direction}\n"
        f"幣種: {symbol}\n"
        f"價格: {price}\n"
        f"信心度: {confidence}/10\n"
        f"理由: {reason}\n"
        f"狀態: {order_status}"
    )
    send_message(msg)


def notify_rejected(signal: dict, evaluation: dict) -> None:
    """Claude 拒絕訊號時通知"""
    symbol = signal.get("symbol", "未知")
    direction = signal.get("direction", "未知")
    price = signal.get("price", "未知")
    confidence = evaluation.get("confidence", 0)
    reason = evaluation.get("reason", "")

    emoji = "🚫📈" if direction == "LONG" else "🚫📉"
    msg = (
        f"\n{emoji} Claude 拒絕 - {direction}\n"
        f"幣種: {symbol}\n"
        f"價格: {price}\n"
        f"信心度: {confidence}/10\n"
        f"拒絕理由: {reason}"
    )
    send_message(msg)


def notify_error(error_msg: str) -> None:
    """系統錯誤通知"""
    msg = f"\n⚠️ 系統錯誤\n{error_msg}"
    send_message(msg)
