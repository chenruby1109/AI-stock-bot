"""
bot_task.py — GitHub Actions 執行入口
根據當前台灣時間決定執行哪種報告
"""
import os
import sys
import requests
from datetime import datetime, timezone, timedelta

# ── 台灣時間 ──
TW = timezone(timedelta(hours=8))
now = datetime.now(TW)
hour = now.hour
minute = now.minute
weekday = now.weekday()  # 0=週一 ... 4=週五

TG_TOKEN  = os.environ.get("TG_TOKEN","")
TG_CHAT_ID= os.environ.get("TG_CHAT_ID","")
GIST_ID   = os.environ.get("GIST_ID","")
# GitHub Actions 的 GITHUB_TOKEN 是內建的，用 GITHUB_TOKEN_GIST 避免衝突
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN_GIST", os.environ.get("GITHUB_TOKEN",""))
GROQ_KEY  = os.environ.get("GROQ_API_KEY","")

# 覆蓋環境變數給 gist_db 使用
os.environ["GITHUB_TOKEN"] = GITHUB_TOKEN
os.environ["GIST_ID"]      = GIST_ID

print(f"[{now.strftime('%Y-%m-%d %H:%M')} TW] 執行 bot_task | weekday={weekday}")

def send_tg(msg: str, chat_id: str = "") -> bool:
    cid = chat_id or TG_CHAT_ID
    if not TG_TOKEN or not cid:
        print("❌ TG_TOKEN 或 CHAT_ID 未設定")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": cid, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
        ok = r.status_code == 200
        print(f"TG {'✅' if ok else '❌'} → chat_id={cid}")
        return ok
    except Exception as e:
        print(f"TG 錯誤: {e}")
        return False


# ────────────────────────────────────────
# 載入 gist_db 取得用戶資料
# ────────────────────────────────────────
try:
    import gist_db as db
    users = db.get_all_users()
    print(f"✅ gist_db 連線，{len(users)} 位用戶")
except Exception as e:
    print(f"❌ gist_db 載入失敗: {e}")
    users = {}


def get_watchlist_with_prices(codes: list) -> list:
    """取得觀察名單的現價"""
    import yfinance as yf
    result = []
    for code in codes:
        for sfx in [".TW", ".TWO"]:
            try:
                df = yf.Ticker(code + sfx).history(period="2d")
                if not df.empty:
                    close = float(df["Close"].iloc[-1])
                    prev  = float(df["Close"].iloc[-2]) if len(df) > 1 else close
                    pct   = (close - prev) / prev * 100
                    result.append({"code": code, "close": close, "pct": pct})
                    break
            except:
                continue
    return result


def _sop_check_simple(code: str) -> dict:
    """簡化版 SOP 檢查"""
    import yfinance as yf
    import numpy as np
    try:
        for sfx in [".TW", ".TWO"]:
            df = yf.Ticker(code + sfx).history(period="3mo")
            if df.empty: continue
            # KD
            h9 = df["High"].rolling(9).max()
            l9 = df["Low"].rolling(9).min()
            rsv = ((df["Close"] - l9) / (h9 - l9) * 100).fillna(50)
            k, d = [50.0], [50.0]
            for v in rsv:
                k.append(k[-1]*2/3 + v/3)
                d.append(d[-1]*2/3 + k[-1]/3)
            K = k[-1]; D = d[-1]; pK = k[-2]
            # MACD
            e12 = df["Close"].ewm(span=12,adjust=False).mean()
            e26 = df["Close"].ewm(span=26,adjust=False).mean()
            dif = e12 - e26
            sig = dif.ewm(span=9,adjust=False).mean()
            hist = float((dif - sig).iloc[-1])
            # SAR
            from scipy.signal import argrelextrema
            close = float(df["Close"].iloc[-1])
            sar_val = float(df["Low"].iloc[-5:].min()) * 0.98
            cond_kd   = K > D
            cond_macd = hist > 0
            cond_sar  = close > sar_val
            return {
                "code": code, "close": close,
                "K": K, "D": D, "hist": hist,
                "cond_kd": cond_kd, "cond_macd": cond_macd, "cond_sar": cond_sar,
                "hard_pass": cond_kd and cond_macd and cond_sar,
                "signal": "BUY" if (cond_kd and cond_macd and cond_sar) else "WATCH"
            }
    except Exception as e:
        print(f"SOP check {code} 錯誤: {e}")
    return {"code": code, "close": 0, "hard_pass": False, "signal": "ERR"}


# ────────────────────────────────────────
# 各時段報告
# ────────────────────────────────────────

def report_open():
    """09:30 開盤掃描"""
    print("執行 report_open (09:30)")
    lines = [f"🌅 <b>開盤掃描</b> {now.strftime('%m/%d')} 09:30\n━━━━━━━━━━━"]

    for uname, uinfo in users.items():
        chat_id = uinfo.get("telegram_chat_id","")
        if not chat_id: continue
        codes = uinfo.get("watchlist",[])
        if not codes: continue

        msg_lines = [f"🌅 <b>開盤掃描</b>｜{uinfo.get('display_name',uname)}\n"]
        prices = get_watchlist_with_prices(codes)
        for p in prices:
            icon = "🔺" if p["pct"] > 0 else "💚" if p["pct"] < 0 else "➖"
            msg_lines.append(f"{icon} <b>{p['code']}</b>  {p['close']:.2f}  ({p['pct']:+.2f}%)")

        msg_lines.append(f"\n<i>⏰ {now.strftime('%H:%M')} | AI Stock Bot</i>")
        send_tg("\n".join(msg_lines), chat_id)

    # 全局推播
    send_tg(f"🌅 開盤掃描完成 {now.strftime('%H:%M')}")


def report_mid():
    """10:20 / 12:00 盤中"""
    print(f"執行 report_mid ({hour:02d}:{minute:02d})")
    for uname, uinfo in users.items():
        chat_id = uinfo.get("telegram_chat_id","")
        if not chat_id: continue
        codes = uinfo.get("watchlist",[])
        if not codes: continue

        msg_lines = [f"🔔 <b>盤中SOP掃描</b> {now.strftime('%H:%M')}｜{uinfo.get('display_name',uname)}\n"]
        triggered = []
        for code in codes[:8]:
            sop = _sop_check_simple(code)
            if sop["signal"] == "BUY":
                triggered.append(
                    f"🚀 <b>{code}</b> SOP觸發！"
                    f"  K={sop['K']:.1f} MACD={'🔴' if sop['hist']>0 else '🟢'}"
                )
            else:
                met = sum([sop.get("cond_kd",False), sop.get("cond_macd",False), sop.get("cond_sar",False)])
                msg_lines.append(f"👀 {code}  {met}/3  {sop['close']:.2f}")

        if triggered:
            msg_lines.insert(1, "\n".join(triggered) + "\n")

        msg_lines.append(f"\n<i>⏰ {now.strftime('%H:%M')} | AI Stock Bot</i>")
        send_tg("\n".join(msg_lines), chat_id)


def report_close():
    """13:36 收盤確認"""
    print("執行 report_close (13:36)")
    for uname, uinfo in users.items():
        chat_id = uinfo.get("telegram_chat_id","")
        if not chat_id: continue
        codes = uinfo.get("watchlist",[])
        if not codes: continue

        msg_lines = [f"🌇 <b>收盤確認</b> {now.strftime('%m/%d')}｜{uinfo.get('display_name',uname)}\n"]
        prices = get_watchlist_with_prices(codes)
        for p in prices:
            icon = "🔺" if p["pct"] > 1 else "💚" if p["pct"] < -1 else "➖"
            sop  = _sop_check_simple(p["code"])
            met  = sum([sop.get("cond_kd",False), sop.get("cond_macd",False), sop.get("cond_sar",False)])
            star = "⭐" if sop["signal"]=="BUY" else ""
            msg_lines.append(
                f"{icon} <b>{p['code']}</b>  {p['close']:.2f}  ({p['pct']:+.2f}%)  {star}SOP:{met}/3"
            )

        # 目標價達成檢查
        targets = db.get_user_all_targets(uname)
        reached = []
        for code, entry in targets.items():
            tgt = entry.get("target_price", 0)
            for p in prices:
                if p["code"] == code and p["close"] >= tgt:
                    reached.append(f"🎯 {code} 已達目標價 {tgt:.2f}！現價 {p['close']:.2f}")

        if reached:
            msg_lines.append("\n" + "\n".join(reached))

        msg_lines.append(f"\n<i>⏰ {now.strftime('%H:%M')} | AI Stock Bot</i>")
        send_tg("\n".join(msg_lines), chat_id)


def report_evening():
    """18:40 盤後深度報告（用 Groq 生成）"""
    print("執行 report_evening (18:40)")
    import yfinance as yf

    for uname, uinfo in users.items():
        chat_id = uinfo.get("telegram_chat_id","")
        if not chat_id: continue
        codes = uinfo.get("watchlist",[])
        if not codes: continue

        display = uinfo.get("display_name", uname)

        # 先送一個開頭訊息
        send_tg(
            f"🌙 <b>盤後深度報告</b>｜{display}\n"
            f"📅 {now.strftime('%Y-%m-%d')}\n"
            f"正在分析 {len(codes)} 支觀察股票...",
            chat_id
        )

        for code in codes[:3]:  # 每人最多3支，避免超時
            try:
                # 基本技術指標
                sop = _sop_check_simple(code)
                tgt_entry = db.get_user_target(uname, code)
                tgt_str = f"\n🎯 目標價：{tgt_entry['target_price']:.2f}" if tgt_entry else ""

                prices = get_watchlist_with_prices([code])
                price_info = prices[0] if prices else {"close":0,"pct":0}

                # Groq 生成摘要（如果有 key）
                ai_summary = ""
                if GROQ_KEY:
                    try:
                        prompt = (
                            f"台股 {code} 今日收盤 {price_info['close']:.2f}（{price_info['pct']:+.2f}%）。"
                                    f"請用2-3句話給出明日操作建議，繁體中文，直接說重點。"
                        )
                        r = requests.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                            json={"model":"llama-3.3-70b-versatile","max_tokens":200,"temperature":0.3,
                                  "messages":[{"role":"user","content":prompt}]},
                            timeout=30
                        )
                        if r.status_code == 200:
                            ai_summary = "\n\n🤖 " + r.json()["choices"][0]["message"]["content"]
                    except: pass

                icon = "🔺" if price_info["pct"]>0 else "💚" if price_info["pct"]<0 else "➖"
                sop_icon = "🚀" if sop["hard_pass"] else "👀"
                met = sum([sop.get(k,False) for k in ["cond_kd","cond_macd","cond_sar"]])

                msg = (
                    f"━━━━━━━━━━━━━━━\n"
                    f"{icon} <b>{code}</b>  {price_info['close']:.2f}  ({price_info['pct']:+.2f}%)\n"
                    f"KD {sop['K']:.1f}/{sop['D']:.1f}  |  MACD {'🔴紅柱' if sop['hist']>0 else '🟢綠柱'}\n"
                    f"{sop_icon} SOP：{met}/3達標"
                    f"{tgt_str}"
                    f"{ai_summary}\n"
                )
                send_tg(msg, chat_id)

            except Exception as e:
                print(f"深度報告 {code} 錯誤: {e}")


# ────────────────────────────────────────
# 判斷時間執行對應任務
# ────────────────────────────────────────
if __name__ == "__main__":
    if weekday > 4:
        print("週末，不執行")
        sys.exit(0)

    task = None

    # 允許 ±3 分鐘誤差
    time_str = f"{hour:02d}{minute:02d}"

    if   "0927" <= time_str <= "0933": task = "open"
    elif "1017" <= time_str <= "1023": task = "mid"
    elif "1157" <= time_str <= "1203": task = "mid"
    elif "1333" <= time_str <= "1339": task = "close"
    elif "1837" <= time_str <= "1843": task = "evening"
    else:
        # 手動觸發或測試時，從命令列參數決定
        if len(sys.argv) > 1:
            task = sys.argv[1]
        else:
            print(f"時間 {time_str} 不在任何排程區間，測試執行 evening")
            task = "evening"

    print(f"執行任務：{task}")

    if   task == "open":    report_open()
    elif task == "mid":     report_mid()
    elif task == "close":   report_close()
    elif task == "evening": report_evening()
    else:
        print(f"未知任務：{task}")

    print("✅ 完成")
