import os

# === Pionex API ===
PIONEX_API_KEY = os.getenv("PIONEX_API_KEY", "")
PIONEX_SECRET_KEY = os.getenv("PIONEX_SECRET_KEY", "")
PIONEX_BASE_URL = "https://api.pionex.com"

# === Claude API ===
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-opus-4-8"

# === FinMind API ===
FINMIND_API_KEY = os.getenv("FINMIND_API_KEY", "")
FINMIND_BASE_URL = "https://api.finmindtrade.com/api/v4"

# === Telegram ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# === Webhook 安全驗證 ===
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your_secret_here")

# === 風控設定 ===
# 單筆下單金額 (USDT)
MAX_ORDER_SIZE_USDT = float(os.getenv("MAX_ORDER_SIZE_USDT", "10"))
# 槓桿倍數（多空統一 x10）
LONG_LEVERAGE = int(os.getenv("LONG_LEVERAGE", "10"))
SHORT_LEVERAGE = int(os.getenv("SHORT_LEVERAGE", "10"))
# 同一幣種同方向只允許一筆持倉，必須平倉後才能再入單
ONE_POSITION_PER_SYMBOL = True
