"""
broker.py V3 — 主力券商分點進出 + 三大法人
修正：
  1. T86 券商名稱含分點（如「凱基台北」→ 格式化為「凱基-台北」）
  2. 三大法人改用 TWT38U endpoint（最準確的個股三大法人 API）
  3. 所有數值除以 1000 換算為張數
"""
import requests
import re
from datetime import datetime, timedelta

HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# ── 主要券商名稱對照（讓分點名稱更易讀）──
BROKER_SHORT = {
    "富邦": "富邦", "凱基": "凱基", "元大": "元大", "國泰": "國泰",
    "永豐金": "永豐金", "群益": "群益", "玉山": "玉山", "兆豐": "兆豐",
    "台新": "台新", "中信": "中信", "第一金": "第一金", "合庫": "合庫",
    "統一": "統一", "華南永昌": "華南", "摩根大通": "摩根", "美林": "美林",
    "瑞士信貸": "瑞信", "高盛": "高盛", "花旗環球": "花旗", "麥格理": "麥格理",
    "德意志": "德銀", "巴克萊": "巴克萊", "野村": "野村", "匯豐": "匯豐",
}

def _fmt_broker(raw_name: str) -> str:
    """
    格式化券商分點名稱
    TWSE T86 回傳格式通常是 「凱基台北」→ 改為 「凱基-台北」
    外資通常是「美林」「摩根大通」等
    """
    raw = str(raw_name).strip()
    if not raw:
        return raw
    # 常見外資直接回傳
    for k in ["摩根大通","美林","高盛","花旗環球","瑞士信貸","德意志","巴克萊","野村","匯豐","麥格理"]:
        if k in raw:
            return raw
    # 台灣本土券商：嘗試加入分隔符
    for main, short in BROKER_SHORT.items():
        if raw.startswith(main) and len(raw) > len(main):
            branch = raw[len(main):]
            return f"{short}-{branch}"
    # 找不到對應就直接回傳
    return raw


def _recent_dates(n=7):
    """回傳最近 n 個可能是交易日的日期（跳過週末）"""
    dates = []
    d = datetime.now()
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return dates


def _to_lots(s) -> int:
    """股數字串 → 張數（÷1000）"""
    try:
        return int(str(s).replace(",","").replace(" ","").replace("+","")) // 1000
    except:
        return 0


# ──────────────────────────────────────────
# 主力券商分點進出（T86）
# ──────────────────────────────────────────
def get_broker_data(code: str) -> dict:
    """
    T86 API：個股券商進出明細
    fields: [券商代號, 券商名稱(含分點), 買進股數, 賣出股數, 差異股數]
    """
    for d in _recent_dates():
        for url_tmpl in [
            f"https://www.twse.com.tw/fund/T86?response=json&date={d}&stockNo={code}",
            f"https://www.twse.com.tw/pcversion/zh/fund/T86?response=json&date={d}&stockNo={code}",
        ]:
            try:
                r = requests.get(url_tmpl, headers=HDR, timeout=12)
                if r.status_code != 200:
                    continue
                j = r.json()
                if j.get("stat") != "OK" or not j.get("data"):
                    continue

                brokers = []
                for row in j["data"]:
                    if len(row) < 5:
                        continue
                    name = _fmt_broker(row[1])
                    buy  = _to_lots(row[2])
                    sell = _to_lots(row[3])
                    net  = buy - sell   # 自行計算，避免原始差異欄位解析錯誤
                    brokers.append({"name": name, "buy": buy, "sell": sell, "net": net})

                if not brokers:
                    continue

                brokers.sort(key=lambda x: x["net"], reverse=True)
                return {
                    "error":       None,
                    "date":        d,
                    "net_total":   sum(b["net"] for b in brokers),
                    "buy_brokers": [b for b in brokers if b["net"] > 0][:10],
                    "sell_brokers":[b for b in brokers if b["net"] < 0][-10:][::-1],
                }
            except Exception:
                continue

    return {
        "error":       f"查無 {code} 主力資料（非交易日或為上櫃股票）",
        "buy_brokers": [], "sell_brokers": [], "net_total": 0,
    }


# ──────────────────────────────────────────
# 三大法人個股買賣超（TWT38U → 最準確）
# ──────────────────────────────────────────
def get_institutional(code: str) -> dict:
    """
    TWT38U：三大法人個股買賣超
    fields: [日期, 股票代號, 股票名稱,
             外資買進股數, 外資賣出股數, 外資買賣超股數,
             投信買進股數, 投信賣出股數, 投信買賣超股數,
             自營商買進股數(自行), 自營商賣出股數(自行), 自營商買賣超股數(自行),
             自營商買進股數(避險), 自營商賣出股數(避險), 自營商買賣超股數(避險),
             三大法人買賣超股數]
    買賣超欄位: 外資[5] 投信[8] 自營[11+14合計] 合計[15]
    """
    for d in _recent_dates():
        try:
            url = (f"https://www.twse.com.tw/fund/TWT38U"
                   f"?response=json&date={d}&stockNo={code}")
            r = requests.get(url, headers=HDR, timeout=12)
            if r.status_code != 200:
                continue
            j = r.json()
            if j.get("stat") != "OK" or not j.get("data"):
                continue

            row = j["data"][0]
            if len(row) < 10:
                continue

            # TWT38U 欄位索引（從0開始）
            # [0]=日期 [1]=代號 [2]=名稱
            # [3]=外資買進 [4]=外資賣出 [5]=外資買賣超
            # [6]=投信買進 [7]=投信賣出 [8]=投信買賣超
            # [9]=自營買進(自行) [10]=自營賣出(自行) [11]=自營買賣超(自行)
            # [12]=自營買進(避險) [13]=自營賣出(避險) [14]=自營買賣超(避險)
            # [15]=三大合計

            foreign = _to_lots(row[5])  if len(row) > 5  else 0
            trust   = _to_lots(row[8])  if len(row) > 8  else 0
            dealer1 = _to_lots(row[11]) if len(row) > 11 else 0
            dealer2 = _to_lots(row[14]) if len(row) > 14 else 0
            dealer  = dealer1 + dealer2
            total   = _to_lots(row[15]) if len(row) > 15 else (foreign+trust+dealer)

            return {
                "error":   None,
                "date":    d,
                "foreign": foreign,
                "trust":   trust,
                "dealer":  dealer,
                "total":   total,
            }
        except Exception:
            continue

    # fallback：舊版 MI_QFIIS endpoint
    for d in _recent_dates():
        try:
            url = (f"https://www.twse.com.tw/fund/MI_QFIIS"
                   f"?response=json&date={d}&stockNo={code}")
            r = requests.get(url, headers=HDR, timeout=12)
            if r.status_code != 200: continue
            j = r.json()
            if j.get("stat") != "OK" or not j.get("data"): continue
            row = j["data"][0]
            # MI_QFIIS 欄位：[日期, ...買進, 賣出, 差異...]
            # 外資差異通常在 index 4，投信在 7，自營在 10
            foreign = _to_lots(row[4])  if len(row) > 4  else 0
            trust   = _to_lots(row[7])  if len(row) > 7  else 0
            dealer  = _to_lots(row[10]) if len(row) > 10 else 0
            return {
                "error": None, "date": d,
                "foreign": foreign, "trust": trust,
                "dealer": dealer, "total": foreign+trust+dealer,
            }
        except Exception:
            continue

    return {"error": "三大法人資料暫無", "foreign": 0, "trust": 0, "dealer": 0, "total": 0}
