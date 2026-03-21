"""
broker.py ── 版本標記 V5_BROKER_FIX
主力券商分點進出（T86）+ 三大法人（TWT38U）
"""
import requests
from datetime import datetime, timedelta

VERSION = "V5_BROKER_FIX"

HDR = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.twse.com.tw/zh/trading/fund/T86.html",
}

# 券商名稱主體（用來加入「-」分點）
_MAINS = [
    "富邦","凱基","元大","國泰","永豐金","群益","玉山","兆豐","台新","中信",
    "第一金","合庫","統一","台銀","陽信","遠東","宏遠","日盛","大昌","大展",
    "摩根大通","美林","高盛","花旗環球","瑞士信貸","德意志","巴克萊",
    "野村","匯豐","麥格理","大和","瑞銀","法國興業","里昂","渣打","法巴",
    "港商高盛","港商美林","港商摩根","港商野村","港商瑞銀",
]

def _clean(code: str) -> str:
    return code.strip().replace(".TW","").replace(".TWO","")

def _lots(s) -> int:
    try:
        return int(str(s).replace(",","").replace(" ","").replace("+","").replace("−","-")) // 1000
    except:
        return 0

def _dates(n=10):
    dates, d = [], datetime.now()
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return dates

def _fmt(raw: str) -> str:
    """元大板橋 → 元大-板橋"""
    s = str(raw).strip()
    for m in _MAINS:
        if s.startswith(m) and len(s) > len(m) and not s[len(m)] == "-":
            return f"{m}-{s[len(m):]}"
    return s


# ═══════════════════════════════════════════
# T86：主力券商分點進出
# TWSE 回傳欄位順序（依官方）：
#   [0] 券商代號   [1] 券商名稱(含分點)
#   [2] 買進股數   [3] 賣出股數   [4] 差異股數
# ═══════════════════════════════════════════
def get_broker_data(code: str) -> dict:
    c = _clean(code)
    for dt in _dates():
        url = f"https://www.twse.com.tw/fund/T86?response=json&date={dt}&stockNo={c}"
        try:
            resp = requests.get(url, headers=HDR, timeout=15)
            if resp.status_code != 200:
                continue
            j = resp.json()
            if j.get("stat") != "OK":
                continue
            rows = j.get("data") or []
            if not rows:
                continue

            # ── 關鍵驗證：T86 row[0] 是 4 碼數字券商代號 ──
            # 若 row[0] 不像券商代號，跳過此次結果
            first = rows[0]
            if len(first) < 5:
                continue
            broker_code = str(first[0]).strip()
            if not (broker_code.isdigit() and len(broker_code) == 4):
                # 不是券商代號格式，這批資料不對
                continue

            brokers = []
            for row in rows:
                if len(row) < 5:
                    continue
                name = _fmt(str(row[1]).strip())     # row[1] = 券商名稱含分點
                buy  = _lots(row[2])                  # row[2] = 買進股數
                sell = _lots(row[3])                  # row[3] = 賣出股數
                net  = buy - sell                     # 自行計算淨買超
                brokers.append({"name": name, "buy": buy, "sell": sell, "net": net})

            if not brokers:
                continue

            brokers.sort(key=lambda x: x["net"], reverse=True)
            return {
                "error":        None,
                "version":      VERSION,
                "date":         dt,
                "net_total":    sum(b["net"] for b in brokers),
                "buy_brokers":  [b for b in brokers if b["net"] > 0][:10],
                "sell_brokers": [b for b in brokers if b["net"] < 0][-10:][::-1],
            }
        except Exception:
            continue

    # 上櫃股票（OTC）嘗試
    for dt in _dates():
        url = f"https://www.tpex.org.tw/web/stock/fund/broker_trading/brokerBS_result.php?l=zh-tw&se=EW&d={dt[:4]}/{dt[4:6]}/{dt[6:]}&stkno={c}&o=json"
        try:
            resp = requests.get(url, headers=HDR, timeout=12)
            j = resp.json()
            rows = j.get("aaData") or []
            if not rows:
                continue
            brokers = []
            for row in rows:
                if len(row) < 5: continue
                name = _fmt(str(row[1]).strip())
                buy  = _lots(row[2])
                sell = _lots(row[3])
                net  = buy - sell
                brokers.append({"name": name, "buy": buy, "sell": sell, "net": net})
            if not brokers: continue
            brokers.sort(key=lambda x: x["net"], reverse=True)
            return {
                "error": None, "version": VERSION, "date": dt,
                "net_total": sum(b["net"] for b in brokers),
                "buy_brokers":  [b for b in brokers if b["net"] > 0][:10],
                "sell_brokers": [b for b in brokers if b["net"] < 0][-10:][::-1],
            }
        except Exception:
            continue

    return {
        "error": f"⚠️ 查無 {c} 券商資料（非交易日、上櫃資料或代號錯誤）",
        "version": VERSION,
        "buy_brokers": [], "sell_brokers": [], "net_total": 0,
    }


# ═══════════════════════════════════════════
# 三大法人（TWT38U）
# 欄位：[0]日期 [1]代號 [2]名稱
#   [3]外資買 [4]外資賣 [5]外資超 ← 用這個
#   [6]投信買 [7]投信賣 [8]投信超 ← 用這個
#   [9]自營買(自) [10]自營賣(自) [11]自營超(自) ← 用這個
#   [12]自營買(避) [13]自營賣(避) [14]自營超(避) ← 用這個
#   [15]三大合計 ← 用這個
# ═══════════════════════════════════════════
def get_institutional(code: str) -> dict:
    c = _clean(code)

    for dt in _dates():
        try:
            url = f"https://www.twse.com.tw/fund/TWT38U?response=json&date={dt}&stockNo={c}"
            resp = requests.get(url, headers=HDR, timeout=15)
            if resp.status_code != 200: continue
            j = resp.json()
            if j.get("stat") != "OK" or not j.get("data"): continue
            row = j["data"][0]
            if len(row) < 10: continue

            foreign = _lots(row[5])  if len(row) > 5  else 0
            trust   = _lots(row[8])  if len(row) > 8  else 0
            d_self  = _lots(row[11]) if len(row) > 11 else 0
            d_hedge = _lots(row[14]) if len(row) > 14 else 0
            dealer  = d_self + d_hedge
            total   = _lots(row[15]) if len(row) > 15 else foreign + trust + dealer

            # 全為0可能是沒交易，試下一天
            if foreign == 0 and trust == 0 and dealer == 0:
                continue

            return {
                "error": None, "date": dt,
                "foreign": foreign, "trust": trust,
                "dealer": dealer, "total": total,
            }
        except Exception:
            continue

    # fallback
    for dt in _dates():
        try:
            url = f"https://www.twse.com.tw/fund/MI_QFIIS?response=json&date={dt}&stockNo={c}"
            resp = requests.get(url, headers=HDR, timeout=12)
            if resp.status_code != 200: continue
            j = resp.json()
            if j.get("stat") != "OK" or not j.get("data"): continue
            row = j["data"][0]
            if len(row) < 8: continue
            foreign = _lots(row[4]) if len(row) > 4 else 0
            trust   = _lots(row[7]) if len(row) > 7 else 0
            dealer  = _lots(row[10])if len(row) > 10 else 0
            if foreign == 0 and trust == 0 and dealer == 0: continue
            return {
                "error": None, "date": dt,
                "foreign": foreign, "trust": trust,
                "dealer": dealer, "total": foreign+trust+dealer,
            }
        except Exception:
            continue

    return {"error": "三大法人資料暫無", "foreign": 0, "trust": 0, "dealer": 0, "total": 0}
