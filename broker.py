"""
broker.py V4 — 主力券商分點 + 三大法人
T86 API 欄位（依 TWSE 官方文件）：
  fields[0] = 券商代號
  fields[1] = 券商名稱（含分點，如「凱基台北」）
  fields[2] = 買進股數
  fields[3] = 賣出股數
  fields[4] = 差異股數（買-賣，可能為負）

三大法人 TWT38U 欄位：
  [0]=日期 [1]=代號 [2]=名稱
  [3]=外資買進 [4]=外資賣出 [5]=外資買賣超
  [6]=投信買進 [7]=投信賣出 [8]=投信買賣超
  [9]=自營買進 [10]=自營賣出 [11]=自營買賣超(自行)
  [12]=自營買進(避險) [13]=自營賣出(避險) [14]=自營買賣超(避險)
  [15]=三大法人合計
"""
import requests
from datetime import datetime, timedelta

HDR = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.twse.com.tw/",
}

# 主要券商名稱 → 格式化分點
BROKER_MAIN = [
    "富邦","凱基","元大","國泰","永豐金","群益","玉山","兆豐","台新","中信",
    "第一金","合庫","統一","台銀","陽信","三商","臺灣企銀","遠東","宏遠",
    "摩根大通","美林","高盛","花旗環球","瑞士信貸","德意志","巴克萊",
    "野村","匯豐","麥格理","大和","瑞銀","法國興業","里昂","渣打",
]

def _fmt_broker(raw: str) -> str:
    """凱基台北 → 凱基-台北"""
    raw = str(raw).strip()
    for main in BROKER_MAIN:
        if raw.startswith(main) and len(raw) > len(main):
            branch = raw[len(main):]
            # 避免重複加-
            if not branch.startswith("-"):
                return f"{main}-{branch}"
    return raw

def _to_lots(s) -> int:
    """股數字串 → 張數（÷1000，去掉逗號與空格）"""
    try:
        v = str(s).replace(",","").replace(" ","").replace("+","").strip()
        if not v or v in ["-","—","N/A"]: return 0
        return int(float(v)) // 1000
    except:
        return 0

def _recent_dates(n=8):
    """最近 n 個平日日期"""
    dates, d = [], datetime.now()
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return dates


# ══════════════════════════════════════
# 主力券商分點（T86）
# ══════════════════════════════════════
def get_broker_data(code: str) -> dict:
    clean = code.strip().replace(".TW","").replace(".TWO","")

    for date_str in _recent_dates():
        urls = [
            f"https://www.twse.com.tw/fund/T86?response=json&date={date_str}&stockNo={clean}",
            f"https://www.twse.com.tw/pcversion/zh/fund/T86?response=json&date={date_str}&stockNo={clean}",
        ]
        for url in urls:
            try:
                r = requests.get(url, headers=HDR, timeout=15)
                if r.status_code != 200:
                    continue

                j = r.json()
                # 確認 API 成功 + 有資料
                if j.get("stat") != "OK":
                    continue
                rows = j.get("data") or []
                if not rows:
                    continue

                # 驗證第一行確實是券商格式（欄位數至少5個）
                if len(rows[0]) < 5:
                    continue

                # 印出前兩行給 debug（只在開發時保留）
                # print("T86 sample row:", rows[0])

                brokers = []
                for row in rows:
                    if len(row) < 5:
                        continue
                    broker_name = _fmt_broker(row[1])   # 欄位1 = 券商名稱含分點
                    buy  = _to_lots(row[2])              # 欄位2 = 買進股數
                    sell = _to_lots(row[3])              # 欄位3 = 賣出股數
                    net  = buy - sell                    # 自行計算淨買超（張）
                    brokers.append({
                        "name": broker_name,
                        "buy":  buy,
                        "sell": sell,
                        "net":  net,
                    })

                if not brokers:
                    continue

                brokers.sort(key=lambda x: x["net"], reverse=True)
                buy_list  = [b for b in brokers if b["net"] > 0][:10]
                sell_list = [b for b in brokers if b["net"] < 0]

                return {
                    "error":        None,
                    "date":         date_str,
                    "net_total":    sum(b["net"] for b in brokers),
                    "buy_brokers":  buy_list,
                    "sell_brokers": list(reversed(sell_list))[:10],  # 賣超最多的10家
                }
            except Exception as e:
                continue

    return {
        "error":       f"⚠️ 查無 {clean} 券商資料（可能為上櫃股票或非交易日）",
        "buy_brokers": [],
        "sell_brokers":[],
        "net_total":   0,
    }


# ══════════════════════════════════════
# 三大法人（TWT38U + MI_QFIIS fallback）
# ══════════════════════════════════════
def get_institutional(code: str) -> dict:
    clean = code.strip().replace(".TW","").replace(".TWO","")

    # 方法1：TWT38U（最準確）
    for date_str in _recent_dates():
        try:
            url = (f"https://www.twse.com.tw/fund/TWT38U"
                   f"?response=json&date={date_str}&stockNo={clean}")
            r = requests.get(url, headers=HDR, timeout=15)
            if r.status_code != 200:
                continue
            j = r.json()
            if j.get("stat") != "OK" or not j.get("data"):
                continue
            row = j["data"][0]
            if len(row) < 10:
                continue

            # 欄位5=外資買賣超, 8=投信買賣超, 11=自營(自行), 14=自營(避險)
            foreign = _to_lots(row[5])  if len(row) > 5  else 0
            trust   = _to_lots(row[8])  if len(row) > 8  else 0
            d_self  = _to_lots(row[11]) if len(row) > 11 else 0
            d_hedge = _to_lots(row[14]) if len(row) > 14 else 0
            dealer  = d_self + d_hedge
            total   = _to_lots(row[15]) if len(row) > 15 else foreign+trust+dealer

            if foreign == 0 and trust == 0 and dealer == 0:
                continue  # 全部為0代表當日沒有資料，試下一天

            return {
                "error":   None,
                "date":    date_str,
                "foreign": foreign,
                "trust":   trust,
                "dealer":  dealer,
                "total":   total,
                "source":  "TWT38U",
            }
        except Exception:
            continue

    # 方法2：MI_QFIIS fallback
    for date_str in _recent_dates():
        try:
            url = (f"https://www.twse.com.tw/fund/MI_QFIIS"
                   f"?response=json&date={date_str}&stockNo={clean}")
            r = requests.get(url, headers=HDR, timeout=15)
            if r.status_code != 200: continue
            j = r.json()
            if j.get("stat") != "OK" or not j.get("data"): continue
            row = j["data"][0]
            if len(row) < 8: continue

            # MI_QFIIS 買賣超通常在 index 4, 7, 10
            foreign = _to_lots(row[4]) if len(row) > 4 else 0
            trust   = _to_lots(row[7]) if len(row) > 7 else 0
            dealer  = _to_lots(row[10])if len(row) > 10 else 0

            if foreign == 0 and trust == 0 and dealer == 0:
                continue

            return {
                "error":   None,
                "date":    date_str,
                "foreign": foreign,
                "trust":   trust,
                "dealer":  dealer,
                "total":   foreign+trust+dealer,
                "source":  "MI_QFIIS",
            }
        except Exception:
            continue

    return {
        "error":   "三大法人資料暫無",
        "foreign": 0, "trust": 0, "dealer": 0, "total": 0,
    }
