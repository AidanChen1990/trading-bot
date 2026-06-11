from flask import Flask, request, jsonify
from dotenv import load_dotenv
import traceback

load_dotenv()

from config import WEBHOOK_SECRET
from finmind_client import get_recent_prices, get_btc_market_context
from claude_evaluator import evaluate_signal
from pionex_client import open_long, open_short, get_open_positions
import line_notifier

app = Flask(__name__)

# 簡單的持倉追蹤（記憶體內，重啟會清空）
# 生產環境建議改用 Redis 或資料庫
open_longs: set = set()   # 目前持有多單的幣種
open_shorts: set = set()  # 目前持有空單的幣種


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    接收 TradingView Alert Webhook

    期望的 JSON 格式：
    {
        "secret": "your_secret",
        "symbol": "BTCUSDT",
        "direction": "LONG",        // LONG 或 SHORT
        "action": "OPEN",           // OPEN 或 CLOSE
        "timeframe": "1h",
        "price": "65000",
        "qqe_value": "52.3",        // QQE 快線數值（可選）
        "vegas_position": "above"   // above 或 below（可選）
    }
    """
    global open_longs, open_shorts

    # 1. 驗證請求
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "無效的 JSON"}), 400

    if not data:
        return jsonify({"error": "空請求"}), 400

    # 驗證 secret
    if data.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "認證失敗"}), 401

    # 2. 解析訊號
    symbol = data.get("symbol", "").upper().replace("/", "").replace(":", "")
    direction = data.get("direction", "").upper()
    action = data.get("action", "OPEN").upper()
    timeframe = data.get("timeframe", "未知")
    price = data.get("price", "未知")

    if not symbol or direction not in ["LONG", "SHORT"]:
        return jsonify({"error": "symbol 或 direction 格式錯誤"}), 400

    signal = {
        "symbol": symbol,
        "direction": direction,
        "action": action,
        "timeframe": timeframe,
        "price": price,
        "qqe_value": data.get("qqe_value", "未提供"),
        "vegas_position": data.get("vegas_position", "未提供"),
        "strategy": "Vegas + QQE",
    }

    print(f"[Webhook] 收到訊號: {symbol} {direction} {action} @ {price}")

    # 3. 處理平倉指令（不需要 Claude 評估）
    if action == "CLOSE":
        return _handle_close(signal)

    # 4. 通知收到訊號
    line_notifier.notify_signal_received(signal)

    # 5. 風控：同一幣種同方向已有持倉，必須先平倉才能再入單
    if direction == "LONG" and symbol in open_longs:
        msg = f"[風控] {symbol} 多單已有持倉，等待平倉後才可再入單"
        print(msg)
        line_notifier.send_message(f"\n⚠️ 風控攔截\n{msg}")
        return jsonify({"status": "rejected", "reason": "該幣種多單已有持倉"}), 200

    if direction == "SHORT" and symbol in open_shorts:
        msg = f"[風控] {symbol} 空單已有持倉，等待平倉後才可再入單"
        print(msg)
        line_notifier.send_message(f"\n⚠️ 風控攔截\n{msg}")
        return jsonify({"status": "rejected", "reason": "該幣種空單已有持倉"}), 200

    # 6. 取得市場資料（供 Claude 評估用）
    try:
        market_data = get_recent_prices(symbol)
        btc_context = get_btc_market_context()
    except Exception as e:
        print(f"[FinMind] 取得資料失敗: {e}")
        market_data = {"error": str(e)}
        btc_context = {"error": str(e)}

    # 7. Claude 二次評估
    try:
        evaluation = evaluate_signal(signal, market_data, btc_context)
    except Exception as e:
        error_msg = f"Claude 評估異常: {traceback.format_exc()}"
        print(error_msg)
        line_notifier.notify_error(error_msg)
        return jsonify({"status": "error", "reason": str(e)}), 500

    # 8. 根據評估結果決定是否下單
    if not evaluation["approved"]:
        line_notifier.notify_rejected(signal, evaluation)
        return jsonify({
            "status": "rejected",
            "confidence": evaluation["confidence"],
            "reason": evaluation["reason"],
        }), 200

    # 9. 執行下單
    try:
        if direction == "LONG":
            order_result = open_long(symbol)
            if order_result["success"]:
                open_longs.add(symbol)
        else:
            order_result = open_short(symbol)
            if order_result["success"]:
                open_shorts.add(symbol)

        line_notifier.notify_approved(signal, evaluation, order_result)

        return jsonify({
            "status": "approved" if order_result["success"] else "order_failed",
            "confidence": evaluation["confidence"],
            "reason": evaluation["reason"],
            "order": order_result,
        }), 200

    except Exception as e:
        error_msg = f"下單異常: {traceback.format_exc()}"
        print(error_msg)
        line_notifier.notify_error(error_msg)
        return jsonify({"status": "error", "reason": str(e)}), 500


def _handle_close(signal: dict):
    """處理平倉指令"""
    global open_longs, open_shorts
    symbol = signal["symbol"]
    direction = signal["direction"]

    # 這裡可以加入 Pionex 平倉 API 呼叫
    # 目前先記錄並通知
    if direction == "LONG":
        open_longs.discard(symbol)
    else:
        open_shorts.discard(symbol)

    msg = f"\n🔒 平倉指令\n幣種: {symbol}\n方向: {direction}\n（請手動確認 Pionex 平倉）"
    line_notifier.send_message(msg)

    return jsonify({"status": "close_notified", "symbol": symbol}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
