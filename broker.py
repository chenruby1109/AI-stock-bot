"""
broker.py — 主力券商進出資料模組
資料來源：台灣證交所 (TWSE) / 證券商當日進出
"""
import requests
import pandas as pd
from datetime import datetime, timedelta

def get_broker_data(code: str) -> dict:
    """
    取得個股當日主力券商進出
    回傳 {
        "buy_brokers":  [{"name", "buy", "sell", "net"}],
        "sell_brokers": [...],
        "net_total":    int,
        "date":         str,
        "error":        None or str
    }
    """
    try:
        today = datetime.now().strftime("%Y%m%d")
        # 嘗試今天，若無資料退一天
        for delta in [0, 1, 2, 3]:
            d = (datetime.now() - timedelta(days=delta)).strftime("%Y%m%d")
            url = f"https://www.twse.com.tw/pcversion/zh/fund/T86?response=json&date={d}&stockNo={code}"
            r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
            if r.status_code != 200: continue
            data = r.json()
            if data.get("stat") == "OK" and data.get("data"):
                break
        else:
            return {"error": "無法取得主力資料（非交易日或代號錯誤）"}

        rows = data["data"]
        date_str = data.get("date", d)

        brokers = []
        for row in rows:
            # row: [券商代號, 券商名稱, 買進張數, 賣出張數, 差異張數]
            try:
                name = str(row[1]).strip()
                buy  = int(str(row[2]).replace(",",""))
                sell = int(str(row[3]).replace(",",""))
                net  = int(str(row[4]).replace(",",""))
                brokers.append({"name":name,"buy":buy,"sell":sell,"net":net})
            except: continue

        # 按淨買超排序
        brokers.sort(key=lambda x: x["net"], reverse=True)
        buy_top  = [b for b in brokers if b["net"] > 0][:10]
        sell_top = [b for b in brokers if b["net"] < 0][-10:][::-1]
        net_total = sum(b["net"] for b in brokers)

        return {
            "buy_brokers":  buy_top,
            "sell_brokers": sell_top,
            "net_total":    net_total,
            "date":         date_str,
            "all_brokers":  brokers,
            "error":        None
        }
    except Exception as e:
        return {"error": f"取得資料失敗：{e}"}


def get_institutional(code: str) -> dict:
    """
    三大法人買賣超
    回傳 {foreign, trust, dealer, total, date, error}
    """
    try:
        for delta in [0,1,2,3]:
            d = (datetime.now() - timedelta(days=delta)).strftime("%Y%m%d")
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={d}&stockNo={code}"
            r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
            if r.status_code != 200: continue
            data = r.json()
            if data.get("stat") == "OK": break
        else:
            return {"error": "無法取得三大法人資料"}

        # 另一個 API：三大法人
        url2 = f"https://www.twse.com.tw/fund/MI_QFIIS?response=json&date={d}&stockNo={code}"
        r2 = requests.get(url2, headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
        if r2.status_code == 200:
            d2 = r2.json()
            if d2.get("stat") == "OK" and d2.get("data"):
                row = d2["data"][0]
                def to_int(s):
                    try: return int(str(s).replace(",","").replace(" ",""))
                    except: return 0
                return {
                    "foreign": to_int(row[4]) if len(row)>4 else 0,  # 外資
                    "trust":   to_int(row[7]) if len(row)>7 else 0,  # 投信
                    "dealer":  to_int(row[10]) if len(row)>10 else 0, # 自營
                    "date":    d,
                    "error":   None
                }
        return {"error": "三大法人資料格式異常"}
    except Exception as e:
        return {"error": str(e)}
