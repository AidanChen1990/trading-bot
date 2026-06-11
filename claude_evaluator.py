import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


LONG_SYSTEM_PROMPT = """你是一位專業的加密貨幣交易風險評估員，專門負責審查「做多」訊號。

你的職責：
1. 根據提供的市場資料與訊號資訊，判斷這筆多單是否值得執行
2. 評估風險，保護資金安全

你的評估標準（多單）：
- Vegas Channel：價格是否確實在通道上方？通道是否向上延伸？
- QQE 訊號強度：快線穿越慢線的幅度是否足夠？
- 多時框共振：若有多個時框訊號，是否方向一致？
- 大盤環境：BTC 整體趨勢是否支持做多？
- 波動率：目前波動是否異常（過高波動風險較大）
- 價格位置：目前價格是否明顯偏離均價（過度追高風險）

輸出格式（必須嚴格遵守）：
DECISION: APPROVE 或 REJECT
CONFIDENCE: 1-10（10最有信心）
REASON: 簡短說明理由（繁體中文，2-3句話）
"""

SHORT_SYSTEM_PROMPT = """你是一位專業的加密貨幣交易風險評估員，專門負責審查「做空」訊號。

你的職責：
1. 根據提供的市場資料與訊號資訊，判斷這筆空單是否值得執行
2. 空單風險更高，評估標準應比多單更嚴格

你的評估標準（空單）：
- Vegas Channel：價格是否確實跌破通道下方？通道是否向下延伸？
- QQE 訊號強度：死叉是否明確？動能是否持續向下？
- 多時框共振：需要至少2個時框方向一致才考慮核准
- 大盤環境：BTC 是否也在下跌趨勢？還是只有該幣種弱勢？
- 波動率：加密貨幣空單在高波動期間極危險，需特別謹慎
- 資金費率考量：如果多頭資金費率為正值，空單成本高

輸出格式（必須嚴格遵守）：
DECISION: APPROVE 或 REJECT
CONFIDENCE: 1-10（10最有信心）
REASON: 簡短說明理由（繁體中文，2-3句話）
"""


def _build_user_message(signal: dict, market_data: dict, btc_context: dict) -> str:
    """組裝送給 Claude 的評估訊息"""
    symbol = signal.get("symbol", "未知")
    direction = signal.get("direction", "未知")
    timeframe = signal.get("timeframe", "未知")
    strategy = signal.get("strategy", "Vegas + QQE")
    price = signal.get("price", "未知")
    qqe_value = signal.get("qqe_value", "未知")
    vegas_position = signal.get("vegas_position", "未知")  # above/below

    market_info = ""
    if "error" not in market_data:
        market_info = f"""
目標幣種市場資料（近30天）：
- 最新價格: {market_data.get('latest_price', '未知')}
- 30日均價: {market_data.get('avg_price_30d', '未知')}
- 30日波動率: {market_data.get('volatility_pct_30d', '未知')}%
- 近7日趨勢: {market_data.get('recent_trend_7d', '未知')}
- 價格偏離均價: {market_data.get('price_vs_avg', '未知')}%
"""

    btc_info = ""
    if "error" not in btc_context:
        btc_info = f"""
BTC 大盤環境：
- BTC 最新價格: {btc_context.get('latest_price', '未知')}
- BTC 近7日趨勢: {btc_context.get('recent_trend_7d', '未知')}
- BTC 30日波動率: {btc_context.get('volatility_pct_30d', '未知')}%
- BTC 偏離均價: {btc_context.get('price_vs_avg', '未知')}%
"""

    message = f"""請評估以下交易訊號：

=== 訊號資訊 ===
幣種: {symbol}
方向: {direction}
時間框架: {timeframe}
策略: {strategy}
當前價格: {price}
Vegas 通道位置: {vegas_position}（above=價格在通道上方, below=下方）
QQE 數值: {qqe_value}

{market_info}
{btc_info}

請根據以上資料給出你的評估。"""

    return message


def evaluate_signal(signal: dict, market_data: dict, btc_context: dict) -> dict:
    """
    讓 Claude 評估交易訊號
    回傳: {"approved": bool, "confidence": int, "reason": str}
    """
    direction = signal.get("direction", "LONG").upper()
    system_prompt = LONG_SYSTEM_PROMPT if direction == "LONG" else SHORT_SYSTEM_PROMPT
    user_message = _build_user_message(signal, market_data, btc_context)

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        content = response.content[0].text.strip()
        print(f"[Claude] 評估回應:\n{content}")

        # 解析回應
        lines = content.split("\n")
        decision = "REJECT"
        confidence = 5
        reason = "無法解析評估結果"

        for line in lines:
            if line.startswith("DECISION:"):
                decision = line.replace("DECISION:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = int(line.replace("CONFIDENCE:", "").strip())
                except:
                    confidence = 5
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()

        return {
            "approved": decision == "APPROVE",
            "confidence": confidence,
            "reason": reason,
            "raw_response": content,
        }

    except Exception as e:
        print(f"[Claude] 評估失敗: {e}")
        return {
            "approved": False,
            "confidence": 0,
            "reason": f"Claude 評估服務異常: {str(e)}",
            "raw_response": "",
        }
