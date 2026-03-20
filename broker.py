"""
broker.py — 主力券商進出 + 三大法人
資料來源：台灣證交所 TWSE 公開 API
"""
import requests
from datetime import datetime, timedelta

HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

def _recent_dates(n=6):
    """回傳最近 n 個日期字串（跳過週末）"""
    dates = []
    d = datetime.now()
    while len(dates) < n:
        if d.weekday() < 5:          # 週一~五
            dates.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return dates

# ─────────────────────────────────────────
# 主力券商進出（T86）
# 欄位：[券商代號, 券商名稱, 買進股數, 賣出股數, 差異股數]
# 注意：股數 ÷ 1000 = 張數
# ─────────────────────────────────────────
def get_broker_data(code: str) -> dict:
    for d in _recent_dates():
        try:
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={d}&stockNo={code}"
            r = requests.get(url, headers=HDR, timeout=10)
            if r.status_code != 200: continue
            j = r.json()
            if j.get("stat") != "OK" or not j.get("data"): continue

            def to_lots(s):
                """股數字串 → 張數（÷1000，去逗號）"""
                try:
                    return int(str(s).replace(",", "").replace(" ", "")) // 1000
                except:
                    return 0

            brokers = []
            for row in j["data"]:
                if len(row) < 5: continue
                name = str(row[1]).strip()
                buy  = to_lots(row[2])
                sell = to_lots(row[3])
                net  = buy - sell          # 自己算差異，避免欄位解析錯誤
                brokers.append({"name": name, "buy": buy, "sell": sell, "net": net})

            if not brokers: continue
            brokers.sort(key=lambda x: x["net"], reverse=True)
            return {
                "error":        None,
                "date":         d,
                "net_total":    sum(b["net"] for b in brokers),
                "buy_brokers":  [b for b in brokers if b["net"] > 0][:10],
                "sell_brokers": [b for b in brokers if b["net"] < 0][-10:][::-1],
            }
        except Exception as e:
            continue

    return {"error": f"查無 {code} 主力資料（非交易日或代號為上櫃）",
            "buy_brokers": [], "sell_brokers": [], "net_total": 0}


# ─────────────────────────────────────────
# 三大法人（個股）
# 使用 TWSE stockcode API
# ─────────────────────────────────────────
def get_institutional(code: str) -> dict:
    """
    三大法人個股買賣超（張數）
    外資/投信/自營商
    """
    for d in _recent_dates():
        try:
            # 使用 TWSE 三大法人個股查詢
            url = (f"https://www.twse.com.tw/fund/TWT38U"
                   f"?response=json&date={d}&stockNo={code}")
            r = requests.get(url, headers=HDR, timeout=10)
            if r.status_code != 200: continue
            j = r.json()
            if j.get("stat") != "OK" or not j.get("data"): continue

            def to_lots(s):
                try:
                    v = int(str(s).replace(",","").replace(" ","").replace("+",""))
                    return v // 1000   # 股 → 張
                except: return 0

            # TWT38U 格式：各法人當日買超股數
            # row[0]=日期, row[1]=股票代號, row[2]=外資買超, row[3]=投信買超, row[4]=自營商買超
            row = j["data"][0]
            if len(row) < 5: continue
            foreign = to_lots(row[2])
            trust   = to_lots(row[3])
            dealer  = to_lots(row[4])
            return {
                "error":   None,
                "date":    d,
                "foreign": foreign,
                "trust":   trust,
                "dealer":  dealer,
                "total":   foreign + trust + dealer,
            }
        except:
            continue

    # fallback：嘗試另一個 endpoint
    for d in _recent_dates():
        try:
            url = (f"https://www.twse.com.tw/fund/MI_QFIIS"
                   f"?response=json&date={d}&stockNo={code}")
            r = requests.get(url, headers=HDR, timeout=10)
            if r.status_code != 200: continue
            j = r.json()
            if j.get("stat") != "OK" or not j.get("data"): continue

            def to_lots2(s):
                try: return int(str(s).replace(",","").replace(" ","")) // 1000
                except: return 0

            row = j["data"][0]
            # MI_QFIIS 欄位：[日期, ..., 外資買超, ..., 投信買超, ..., 自營買超]
            # 找差異欄位（通常是買-賣那欄）
            foreign = to_lots2(row[4])  if len(row) > 4  else 0
            trust   = to_lots2(row[7])  if len(row) > 7  else 0
            dealer  = to_lots2(row[10]) if len(row) > 10 else 0
            return {
                "error":   None,
                "date":    d,
                "foreign": foreign,
                "trust":   trust,
                "dealer":  dealer,
                "total":   foreign + trust + dealer,
            }
        except:
            continue

    return {"error": "三大法人資料暫無", "foreign": 0, "trust": 0, "dealer": 0, "total": 0}
