"""
AI-stock-bot — cloud_bot.py  v1.1
從 watchlist.json 讀取監控清單，不刪除永久存在。
每日自動推播時間表 + SOP 三線即時訊號。
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import os
from datetime import datetime, timedelta
from watchlist import to_simple_dict

# ─────────────────────────────────────────
# ⚙️  設定區
# ─────────────────────────────────────────
TG_TOKEN = os.environ.get("TG_TOKEN",   "你的_BOT_TOKEN")
TG_CHAT  = os.environ.get("TG_CHAT_ID", "你的_CHAT_ID")

SOP_COOLDOWN = 4 * 3600   # SOP 同一股 4 小時不重複
SIG_COOLDOWN = 1 * 3600   # 一般訊號 1 小時不重複


# ─────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────
def tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=8
        )
    except Exception as e:
        print(f"[TG] {e}")


# ─────────────────────────────────────────
# 資料 & 指標
# ─────────────────────────────────────────
def get_df(code, period="1y", interval="1d"):
    for sfx in [".TW", ".TWO"]:
        try:
            df = yf.Ticker(code + sfx).history(period=period, interval=interval)
            if not df.empty:
                return df
        except:
            pass
    return None


def _sar(hi, lo, a=0.02, am=0.2):
    n = len(hi); sar = np.zeros(n); tr = np.ones(n)
    ep = np.zeros(n); af = np.full(n, a)
    sar[0] = lo[0]; ep[0] = hi[0]
    for i in range(1, n):
        sar[i] = sar[i-1] + af[i-1] * (ep[i-1] - sar[i-1])
        if tr[i-1] == 1:
            if lo[i] < sar[i]:
                tr[i] = -1; sar[i] = ep[i-1]; ep[i] = lo[i]; af[i] = a
            else:
                tr[i] = 1
                if hi[i] > ep[i-1]: ep[i] = hi[i]; af[i] = min(af[i-1]+a, am)
                else: ep[i] = ep[i-1]; af[i] = af[i-1]
                sar[i] = min(sar[i], lo[i-1])
                if i > 1: sar[i] = min(sar[i], lo[i-2])
        else:
            if hi[i] > sar[i]:
                tr[i] = 1; sar[i] = ep[i-1]; ep[i] = hi[i]; af[i] = a
            else:
                tr[i] = -1
                if lo[i] < ep[i-1]: ep[i] = lo[i]; af[i] = min(af[i-1]+a, am)
                else: ep[i] = ep[i-1]; af[i] = af[i-1]
                sar[i] = max(sar[i], lo[i-1])
                if i > 1: sar[i] = max(sar[i], lo[i-2])
    return sar


def add_ind(df):
    if df is None or df.empty:
        return df
    n = len(df)
    df["SAR"] = _sar(df["High"].values, df["Low"].values) if n > 5 else np.nan
    for p in [5, 10, 20, 60]:
        df[f"MA{p}"] = df["Close"].rolling(p).mean() if n >= p else np.nan
    h9 = df["High"].rolling(9).max(); l9 = df["Low"].rolling(9).min()
    rsv = ((df["Close"] - l9) / (h9 - l9) * 100).fillna(50)
    k, d = [50.0], [50.0]
    for v in rsv:
        k.append(k[-1]*2/3 + v/3); d.append(d[-1]*2/3 + k[-1]/3)
    df["K"] = k[1:]; df["D"] = d[1:]
    e12 = df["Close"].ewm(span=12, adjust=False).mean()
    e26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["DIF"] = e12 - e26
    df["MACD_SIG"] = df["DIF"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["DIF"] - df["MACD_SIG"]
    df["TR"] = np.maximum(df["High"]-df["Low"],
                          np.abs(df["High"]-df["Close"].shift(1)))
    df["ATR"] = df["TR"].rolling(14).mean()
    df["VOL_MA5"] = df["Volume"].rolling(5).mean()
    return df


def wave(df):
    if df is None or len(df) < 15:
        return "N/A"
    c = df["Close"].iloc[-1]
    m20 = df["MA20"].iloc[-1] if not pd.isna(df["MA20"].iloc[-1]) else c
    m60_raw = df["MA60"].iloc[-1] if "MA60" in df.columns else np.nan
    m60 = m60_raw if not pd.isna(m60_raw) else c
    k = df["K"].iloc[-1]; pk = df["K"].iloc[-2]
    h = df["MACD_HIST"].iloc[-1]; ph = df["MACD_HIST"].iloc[-2]
    if c >= m60:
        if c > m20:
            if h > 0 and h > ph: return "3-5" if k > 80 else "3-3"
            if h > 0: return "3-a"
            return "3-1"
        else:
            if k < 20: return "4-c"
            if k < pk: return "4-a"
            return "4-b"
    else:
        if c < m20: return "C-5" if k < 20 else "C-3"
        return "B-c" if k > 80 else "B-a"


_WHINTS = {
    "3-3": "🌊 3-3 主升急漲（波浪加分）",
    "3-5": "🏔️ 3-5 噴出末段（波浪加分，注意高點）",
    "3-1": "🌱 3-1 初升啟動",
    "4-c": "🪤 4-c 修正末端",
}


# ─────────────────────────────────────────
# ★ SOP 判斷（三線硬觸發）
# ─────────────────────────────────────────
def sop_check(df):
    if df is None or len(df) < 30:
        return {"signal": None, "hard_pass": False}
    t = df.iloc[-1]; p = df.iloc[-2]
    kx = (p["K"] < p["D"]) and (t["K"] > t["D"])
    kb = t["K"] > t["D"]; ck = kb or kx
    kl = "今日金叉✨" if kx else ("多頭排列" if kb else "空方排列")
    cm = t["MACD_HIST"] > 0
    ml = ("今日翻紅🔴" if (p["MACD_HIST"] <= 0 and t["MACD_HIST"] > 0)
          else ("紅柱延伸" if cm else "綠柱整理"))
    cs = float(t["Close"]) > float(t["SAR"])
    sl = "多方支撐↑" if cs else "空方壓力↓"
    hp = ck and cm and cs
    vm = t["VOL_MA5"] if t["VOL_MA5"] > 0 else 1
    vr = round(float(t["Volume"]) / float(vm), 1)
    cv = vr >= 1.5
    wl = wave(df); cw = wl in ("3-3", "3-5", "3-1", "4-c")
    sig = None
    if hp:
        sig = "SELL" if wl in ("3-5", "B-c", "C-3") else "BUY"
    return {"signal": sig, "hard_pass": hp,
            "cond_kd": ck, "kd_lbl": kl,
            "cond_macd": cm, "macd_lbl": ml,
            "cond_sar": cs, "sar_lbl": sl,
            "cond_vol": cv, "vol_ratio": vr,
            "cond_wave": cw, "wave_lbl": wl,
            "wave_hint": _WHINTS.get(wl)}


def sop_msg(sig, code, name, df, s):
    t = df.iloc[-1]; p = df.iloc[-2]
    pct = (t["Close"] - p["Close"]) / p["Close"] * 100
    icon = "🔺" if pct > 0 else "💚" if pct < 0 else "➖"
    atr = float(t["ATR"]) if not pd.isna(t["ATR"]) else float(t["Close"]) * .02
    ma5  = float(t["MA5"])  if not pd.isna(t.get("MA5",  np.nan)) else float(t["Close"])
    ma20 = float(t["MA20"]) if not pd.isna(t.get("MA20", np.nan)) else float(t["Close"])
    hi = df["High"].iloc[-120:].max(); lo = df["Low"].iloc[-120:].min(); d = hi - lo
    ba = max(ma5,  hi - d * .236)
    bc = max(ma20, hi - d * .382)
    st_ = max(float(t["Close"]) - atr * 2, hi - d * .618)
    soft = ""
    if s["cond_vol"]:  soft += f"\n💡 量比 <b>{s['vol_ratio']}x</b>（≥1.5 加分）"
    if s["wave_hint"]: soft += f"\n{s['wave_hint']}"
    pl = (f"🦁 激進：<b>{ba:.2f}</b>  🐢 保守：<b>{bc:.2f}</b>  🛑 停損：<b>{st_:.2f}</b>"
          if sig == "BUY" else
          f"⚡ 出場：<b>{t['Close']:.2f}</b>  🛑 停損：<b>{st_:.2f}</b>")
    return (
        f"{'🚀' if sig=='BUY' else '⚠️'} <b>AI Stock Bot — SOP {sig}</b> {'🚀' if sig=='BUY' else '⚠️'}\n\n"
        f"<b>{name}（{code}）</b> {icon} {t['Close']:.2f}（{pct:+.2f}%）\n"
        f"📊 量比：{s['vol_ratio']}x ｜ 🌊 {s['wave_lbl']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ KD：{s['kd_lbl']}\n"
        f"✅ MACD：{s['macd_lbl']}\n"
        f"✅ SAR：{s['sar_lbl']}"
        f"{soft}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{pl}\n"
        f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>"
    )


# ─────────────────────────────────────────
# 一般訊號
# ─────────────────────────────────────────
def basic_sigs(df):
    if df is None or len(df) < 10:
        return []
    t = df.iloc[-1]; p = df.iloc[-2]; sigs = []
    if t["Volume"] > t["VOL_MA5"] * 1.5 and t["Close"] > p["Close"] * 1.02:
        sigs.append("🚀 <b>出量突破</b>")
    if (p["K"] < p["D"]) and (t["K"] > t["D"]) and t["K"] < 80:
        sigs.append("✅ <b>KD 金叉</b>")
    if p["MACD_HIST"] <= 0 and t["MACD_HIST"] > 0:
        sigs.append("🔴 <b>MACD 翻紅</b>")
    if t["K"] < 40 and t["K"] > p["K"] and t["K"] > t["D"]:
        sigs.append("💧 <b>底部咕嚕咕嚕</b>")
    streak = 0
    col = ((df["Close"] >= df["Open"]) | (df["Close"] > df["Close"].shift(1))).iloc[-10:]
    for x in reversed(col.values):
        if x: streak += 1
        else: break
    if 3 <= streak <= 10:
        sigs.append(f"🛡️ <b>連買 {streak} 天</b>")
    return sigs


# ─────────────────────────────────────────
# 定時報告
# ─────────────────────────────────────────
def _rows(watch, mode, label=""):
    lines = []
    for code, name in watch.items():
        try:
            df = get_df(code); df = add_ind(df)
            if df is None: continue
            t = df.iloc[-1]; p = df.iloc[-2]
            pct = (t["Close"] - p["Close"]) / p["Close"] * 100
            icon = "🔺" if pct > 0 else "💚" if pct < 0 else "➖"
            vm = t["VOL_MA5"] if t["VOL_MA5"] > 0 else 1
            vr = round(float(t["Volume"]) / float(vm), 1)
            row = f"<b>{name}（{code}）</b> {icon} {t['Close']:.2f}（{pct:+.2f}%）\n"

            if mode == "brief":
                s  = sop_check(df)
                hn = sum([s["cond_kd"], s["cond_macd"], s["cond_sar"]])
                tag = ""
                if s["signal"] == "BUY":   tag = " 🚀<b>SOP BUY</b>"
                elif s["signal"] == "SELL": tag = " ⚠️<b>SOP SELL</b>"
                else:                       tag = f" SOP {hn}/3"
                soft = ""
                if s["cond_vol"]:  soft += " 💡量比"
                if s["wave_hint"]: soft += f" 🌊{s['wave_lbl']}"
                row += f"  {tag}{soft} ｜ 量比：{vr}x\n"

            elif mode == "open":
                s    = sop_check(df)
                sigs = basic_sigs(df)
                hn   = sum([s["cond_kd"], s["cond_macd"], s["cond_sar"]])
                row += f"  📊 量比：{vr}x ｜ 波浪：{s['wave_lbl']} ｜ SOP：{hn}/3"
                if s["signal"]: row += f" ⚡<b>{s['signal']}</b>"
                row += "\n"
                if sigs: row += "  " + "｜".join(sigs) + "\n"

            elif mode == "mid":
                s    = sop_check(df)
                sigs = basic_sigs(df)
                hn   = sum([s["cond_kd"], s["cond_macd"], s["cond_sar"]])
                atr  = float(t["ATR"]) if not pd.isna(t["ATR"]) else float(t["Close"]) * .02
                ma5  = float(t["MA5"])  if not pd.isna(t.get("MA5",  np.nan)) else float(t["Close"])
                ma20 = float(t["MA20"]) if not pd.isna(t.get("MA20", np.nan)) else float(t["Close"])
                hi = df["High"].iloc[-120:].max(); lo = df["Low"].iloc[-120:].min(); d = hi - lo
                ba = max(ma5, hi-d*.236); bc = max(ma20, hi-d*.382)
                row += f"  🛒 激進{ba:.2f}｜保守{bc:.2f}｜量比{vr}x ｜ SOP：{hn}/3"
                if s["signal"]: row += f" ⚡<b>{s['signal']}</b>"
                if s["cond_vol"]:  row += " 💡量比"
                if s["wave_hint"]: row += f" 🌊{s['wave_lbl']}"
                row += "\n"
                if sigs: row += "  " + "｜".join(sigs) + "\n"

            elif mode == "close":
                atr  = float(t["ATR"]) if not pd.isna(t["ATR"]) else float(t["Close"]) * .02
                ma20 = float(t["MA20"]) if not pd.isna(t.get("MA20", np.nan)) else float(t["Close"])
                stop = float(t["Close"]) - atr * 2
                row += f"  🎯 明日低接：{ma20:.2f} ｜ 🛑 停損：{stop:.2f}\n"

            elif mode == "evening":
                v_up   = t["Volume"] > t["VOL_MA5"] and t["Close"] > p["Close"]
                v_down = t["Volume"] > t["VOL_MA5"] and t["Close"] < p["Close"]
                chip   = "量增價漲（主力進場）" if v_up else "出貨跡象⚠️" if v_down else "量縮整理"
                s      = sop_check(df)
                hn     = sum([s["cond_kd"], s["cond_macd"], s["cond_sar"]])
                score  = hn + int(s["cond_vol"]) + int(s["cond_wave"])
                advice = "🔥 積極操作" if score >= 4 else "✅ 拉回留意" if score >= 2 else "⚠️ 觀望"
                row += f"  🛡️ {chip} ｜ 🌊{wave(df)} ｜ SOP：{hn}/3\n"
                row += f"  💡 AI：{advice}\n"

            lines.append(row + "─────────────────")
        except:
            pass
    return "\n".join(lines)


SCHEDULE = {
    "08:30": "brief",    # 每日晨報（自選股總覽）
    "09:30": "open",     # 開盤掃描
    "10:20": "mid",      # 盤中戰略
    "12:00": "mid",      # 盤中戰略
    "13:36": "close",    # 收盤確認
    "18:40": "evening",  # 盤後AI總結
}

HEADERS = {
    "brief":   "☀️ <b>每日晨報 — 自選股總覽</b>",
    "open":    "🌅 <b>09:30 開盤掃描</b>",
    "mid":     "🔔 <b>{label} 盤中戰略</b>",
    "close":   "🌇 <b>13:36 收盤確認</b>",
    "evening": "🌙 <b>18:40 盤後AI總結</b>",
}


# ─────────────────────────────────────────
# 主迴圈
# ─────────────────────────────────────────
def run():
    print("🤖 AI Stock Bot V1.1 啟動...")
    watch = to_simple_dict()
    tg(
        "🤖 <b>AI Stock Bot V1.1 上線！</b>\n\n"
        "✅ 自選股從 watchlist.json 讀取（每 10 分鐘同步）\n"
        "📅 時間表：08:30 晨報 / 09:30 / 10:20 / 12:00 / 13:36 / 18:40\n"
        "SOP：KD + MACD + SAR 三線全達觸發\n\n"
        f"監控 <b>{len(watch)}</b> 支：" +
        " / ".join(list(watch.values())[:6]) +
        (" ..." if len(watch) > 6 else "")
    )

    sent    = {t: False for t in SCHEDULE}
    sop_h   = {}
    sig_h   = {}
    last_rl = datetime.utcnow()

    while True:
        now   = datetime.utcnow() + timedelta(hours=8)
        hm    = now.strftime("%H:%M")
        wday  = now.weekday()

        is_work    = wday <= 4
        is_active  = is_work and  8 <= now.hour <= 19
        is_trading = is_work and (
            now.hour == 9 or
            (9 < now.hour < 13) or
            (now.hour == 13 and now.minute <= 30)
        )

        if not is_active:
            print(f"\r💤 {hm}", end="")
            if hm == "00:00":
                for k in sent: sent[k] = False
            time.sleep(60)
            continue

        # ── 每 10 分鐘重新載入自選股 ──
        if (datetime.utcnow() - last_rl).seconds >= 600:
            watch   = to_simple_dict()
            last_rl = datetime.utcnow()
            print(f"\n🔄 {hm} 重載自選股，共 {len(watch)} 支")

        print(f"\r{'📈' if is_trading else '🕐'} {hm} "
              f"{'交易中' if is_trading else '盤後'} [{len(watch)}支]", end="")

        # ── 定時報告 ──
        if hm in SCHEDULE and not sent[hm]:
            rt  = SCHEDULE[hm]
            hdr = HEADERS[rt].replace("{label}", hm)
            body = _rows(watch, rt, hm)
            tg(f"{hdr}（共 {len(watch)} 支）\n\n{body}\n\n"
               f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>")
            sent[hm] = True
            print(f"\n⏰ {hm} 推播 {rt}")

        if hm == "08:00":
            for k in sent: sent[k] = False

        # ── 即時 SOP 掃描（交易時段）──
        if is_trading:
            for code, name in watch.items():
                try:
                    # SOP 冷卻
                    ls = sop_h.get(code)
                    sop_ok = not ls or (now - ls).seconds >= SOP_COOLDOWN
                    if sop_ok:
                        df = get_df(code); df = add_ind(df)
                        if df is None: continue
                        s = sop_check(df)
                        if s["signal"] in ("BUY", "SELL"):
                            tg(sop_msg(s["signal"], code, name, df, s))
                            sop_h[code] = now
                            print(f"\n🚨 {hm} SOP {s['signal']} → {name}({code})")
                            continue

                    # 一般訊號冷卻
                    lg = sig_h.get(code)
                    if lg and (now - lg).seconds < SIG_COOLDOWN:
                        continue
                    df = get_df(code); df = add_ind(df)
                    if df is None: continue
                    sigs = basic_sigs(df)
                    if sigs:
                        t2 = df.iloc[-1]; p2 = df.iloc[-2]
                        pct = (t2["Close"] - p2["Close"]) / p2["Close"] * 100
                        icon = "🔺" if pct > 0 else "💚"
                        tg(f"🚨 <b>盤中訊號</b>\n\n"
                           f"<b>{name}（{code}）</b> {icon}{t2['Close']:.2f}（{pct:+.2f}%）\n"
                           + "\n".join(sigs) +
                           f"\n<i>⏰{hm}</i>")
                        sig_h[code] = now
                except:
                    pass

        time.sleep(30)


if __name__ == "__main__":
    run()
