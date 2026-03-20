"""
broker.py — 主力券商進出資料
資料來源：TWSE 公開資訊觀測站
"""
import requests
import json
from datetime import datetime, timedelta

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def _try_dates(build_url, days=5):
    """嘗試最近幾個交易日，回傳第一個有效的 (data, date_str)"""
    for delta in range(days):
        d = (datetime.now() - timedelta(days=delta)).strftime("%Y%m%d")
        try:
            r = requests.get(build_url(d), headers=HEADERS, timeout=10)
            if r.status_code != 200 or not r.text.strip():
                continue
            data = r.json()
            if data.get("stat") == "OK" and data.get("data"):
                return data, d
        except Exception:
            continue
    return None, None

def get_broker_data(code: str) -> dict:
    """主力券商買賣超 Top 10"""
    def url(d): return f"https://www.twse.com.tw/fund/T86?response=json&date={d}&stockNo={code}"
    data, d = _try_dates(url)
    if not data:
        # 嘗試上市股票另一個 endpoint
        def url2(d): return f"https://www.twse.com.tw/pcversion/zh/fund/T86?response=json&date={d}&stockNo={code}"
        data, d = _try_dates(url2)
    if not data:
        return {"error": f"⚠️ 主力資料暫無（非交易日或代號 {code} 為上櫃股票）", "buy_brokers":[], "sell_brokers":[], "net_total":0}

    brokers = []
    for row in data["data"]:
        try:
            def _n(s): return int(str(s).replace(",","").replace(" ","") or "0")
            brokers.append({"name": str(row[1]).strip(),
                            "buy":  _n(row[2]), "sell": _n(row[3]), "net": _n(row[4])})
        except: continue

    brokers.sort(key=lambda x: x["net"], reverse=True)
    return {
        "error":        None,
        "date":         d,
        "net_total":    sum(b["net"] for b in brokers),
        "buy_brokers":  [b for b in brokers if b["net"] > 0][:10],
        "sell_brokers": [b for b in brokers if b["net"] < 0][-10:][::-1],
    }

def get_institutional(code: str) -> dict:
    """三大法人買賣超"""
    def url(d): return f"https://www.twse.com.tw/fund/MI_QFIIS?response=json&date={d}&stockNo={code}"
    data, d = _try_dates(url)
    if not data:
        return {"error": "三大法人資料暫無"}
    try:
        row = data["data"][0]
        def _n(s):
            try: return int(str(s).replace(",","").replace(" ","").lstrip("+") or "0")
            except: return 0
        # 欄位：外資買進、外資賣出、外資差異、投信買、投信賣、投信差異、自營買、自營賣、自營差異
        # 不同 API 版本欄位數不同，安全取值
        foreign = _n(row[4]) if len(row) > 4 else 0
        trust   = _n(row[7]) if len(row) > 7 else 0
        dealer  = _n(row[10]) if len(row) > 10 else 0
        total   = foreign + trust + dealer
        return {"error": None, "foreign": foreign, "trust": trust, "dealer": dealer, "total": total, "date": d}
    except Exception as e:
        return {"error": str(e)}
