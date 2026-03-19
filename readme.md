# 🤖 AI Stock Bot

台股技術分析機器人，支援 Streamlit 視覺化分析頁面 + Telegram 雲端哨兵自動推播。

---

## SOP 訊號邏輯

### ✅ 硬觸發（三線全達才發訊號）
| 條件 | 說明 |
|------|------|
| KD 金叉 / 多頭排列 | K > D 或今日黃金交叉 |
| MACD 翻紅 | MACD Hist > 0 |
| SAR 多方支撐 | 收盤 > SAR 值 |

### 💡 軟提示（加分顯示，不影響觸發）
| 提示 | 說明 |
|------|------|
| 波浪 3-3 / 3-5 / 3浪 / 5浪 | 主升或噴出浪，顯示波浪加分提示 |
| 量比 ≥ 1.5 | 放量，顯示量能加分提示 |

---

## 檔案說明

```
AI-stock-bot/
├── app.py           # Streamlit 分析頁面
├── cloud_bot.py     # Telegram 雲端哨兵
└── requirements.txt # 套件需求
```

---

## 快速開始

### 1. 安裝套件
```bash
pip install -r requirements.txt
```

### 2. 啟動 Streamlit 分析頁面
```bash
streamlit run app.py
```
在側邊欄輸入股票代號（如 `2330`），即可分析。  
填入 Telegram Token / Chat ID 後可手動推播訊號。

### 3. 啟動雲端哨兵
```bash
# 設定環境變數（或直接修改 cloud_bot.py 設定區）
export TG_TOKEN="你的 Bot Token"
export TG_CHAT_ID="你的 Chat ID"

python cloud_bot.py
```

---

## 雲端部署（推薦）

### Render / Railway / Fly.io
1. 設定環境變數 `TG_TOKEN` 與 `TG_CHAT_ID`
2. Start Command：`python cloud_bot.py`

### GitHub Actions（定時觸發）
可搭配 `.github/workflows/` 設定每日排程。

---

## 定時推播時間表

| 時間  | 內容 |
|-------|------|
| 09:30 | 開盤掃描（早盤量比 + 訊號） |
| 10:20 | 盤中戰略（SOP 狀態 + 建議） |
| 12:00 | 盤中戰略（SOP 狀態 + 建議） |
| 13:36 | 收盤確認（收盤價 + 明日佈局） |
| 18:40 | 盤後 AI 總結（籌碼 + 綜合建議） |
| 即時  | SOP 三線觸發立即推播（冷卻 4 小時） |

---

## 監控名單設定

修改 `cloud_bot.py` 中的 `WATCH_LIST`：

```python
WATCH_LIST = {
    "2330": "台積電",
    "2454": "聯發科",
    # 加入更多...
}
```
