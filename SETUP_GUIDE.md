# 自動交易機器人設定指南

## 系統架構

```
TradingView Alert → Railway 伺服器 → Claude 評估 → Pionex 下單 → LINE 通知
```

---

## 步驟一：取得所需 API Key

### 1. Pionex API Key
1. 登入 Pionex → 右上角頭像 → API 管理
2. 建立新 API，勾選「交易」權限
3. 記錄 `API Key` 和 `Secret Key`

### 2. Anthropic (Claude) API Key
1. 前往 https://console.anthropic.com
2. API Keys → Create Key
3. 記錄 Key（只顯示一次）

### 3. FinMind API Key
1. 登入 FinMind → 個人設定 → API Token
2. 複製你的 Token

### 4. LINE Notify Token
1. 前往 https://notify-bot.line.me/my/
2. 「發行權杖」→ 選擇要接收通知的群組或個人
3. 複製 Token

---

## 步驟二：部署到 Railway

1. 前往 https://railway.app → 用 GitHub 登入
2. New Project → Deploy from GitHub Repo
3. 上傳本專案到你的 GitHub
4. Railway 會自動偵測並部署

### 設定環境變數
在 Railway 專案設定 → Variables，加入以下變數：

```
PIONEX_API_KEY=你的 Pionex API Key
PIONEX_SECRET_KEY=你的 Pionex Secret Key
ANTHROPIC_API_KEY=你的 Claude API Key
FINMIND_API_KEY=你的 FinMind Token
LINE_NOTIFY_TOKEN=你的 LINE Notify Token
WEBHOOK_SECRET=自訂一個密碼（例如 my_secret_2024）
MAX_ORDER_SIZE_USDT=100
LONG_LEVERAGE=3
SHORT_LEVERAGE=2
MAX_LONG_POSITIONS=3
MAX_SHORT_POSITIONS=2
```

### 取得 Webhook URL
部署成功後，Railway 會給你一個網址，格式如：
```
https://your-project.up.railway.app
```

你的 Webhook URL 就是：
```
https://your-project.up.railway.app/webhook
```

---

## 步驟三：TradingView 設定

### Pine Script Alert 設定

在你的 Vegas + QQE 策略裡，加入 alert 邏輯：

```pine
// 多單訊號
longCondition = ta.crossover(qqe_fast, qqe_slow) and close > vegas_upper
if longCondition
    alert('{"secret":"你的WEBHOOK_SECRET","symbol":"' + syminfo.ticker + '","direction":"LONG","action":"OPEN","timeframe":"' + timeframe.period + '","price":"' + str.tostring(close) + '","vegas_position":"above"}', alert.freq_once_per_bar)

// 空單訊號
shortCondition = ta.crossunder(qqe_fast, qqe_slow) and close < vegas_lower
if shortCondition
    alert('{"secret":"你的WEBHOOK_SECRET","symbol":"' + syminfo.ticker + '","direction":"SHORT","action":"OPEN","timeframe":"' + timeframe.period + '","price":"' + str.tostring(close) + '","vegas_position":"below"}', alert.freq_once_per_bar)
```

### Alert 設定方式
1. 在圖表上點「Alert」（鬧鐘圖示）
2. Condition：選你的策略
3. **Webhook URL**：貼上你的 Railway URL
4. Message：貼上上面的 JSON 格式

---

## Webhook JSON 格式說明

```json
{
    "secret": "你設定的 WEBHOOK_SECRET",
    "symbol": "BTCUSDT",
    "direction": "LONG",
    "action": "OPEN",
    "timeframe": "1h",
    "price": "65000",
    "qqe_value": "52.3",
    "vegas_position": "above"
}
```

| 欄位 | 說明 | 必填 |
|------|------|------|
| secret | 驗證密碼，防止偽造請求 | ✅ |
| symbol | 幣種，例如 BTCUSDT | ✅ |
| direction | LONG 或 SHORT | ✅ |
| action | OPEN（開倉）或 CLOSE（平倉） | ✅ |
| timeframe | 時間框架，例如 1h, 4h, 1d | ✅ |
| price | 當前價格 | ✅ |
| qqe_value | QQE 指標數值 | 選填 |
| vegas_position | above 或 below | 選填 |

---

## 流程說明

1. TradingView 觸發訊號 → 發送 Webhook
2. 伺服器驗證 secret，解析訊號
3. 風控檢查（持倉數量上限）
4. LINE 通知「收到訊號，評估中」
5. FinMind 取得市場資料
6. **Claude 二次評估**（多空分離評估邏輯）
7. 若 Claude **核准** → Pionex 下單 → LINE 通知結果
8. 若 Claude **拒絕** → LINE 通知拒絕理由，不下單

---

## 注意事項

- TradingView Webhook 功能需要 **Pro 以上方案**
- 首次部署建議先設定小金額（`MAX_ORDER_SIZE_USDT=10`）測試
- 伺服器重啟後持倉追蹤記憶體會清空，生產環境建議升級為資料庫儲存
- Pionex API 合約下單文件：https://pionex-doc.gitbook.io/apidocs
