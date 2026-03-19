"""
AI-stock-bot — Telegram 雲端哨兵
Version: 1.0.0
SOP 三線硬觸發：KD金叉/多頭 + MACD翻紅 + SAR多方
軟提示：波浪 3-3/3-5/3浪/5浪 + 量比 ≥ 1.5
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import os
from datetime import datetime, timedelta

# ─────────────────────────────────────────
# ⚙️  設定區 (優先讀環境變數，方便雲端部署)
# ─────────────────────────────────────────
TG_TOKEN  = os.environ.get("TG_TOKEN",   "你的_BOT_TOKEN")
TG_CHAT   = os.environ.get("TG_CHAT_ID", "你的_CHAT_ID")

# 監控名單  { 代號: 名稱 }
WATCH_LIST = {
    "2454": "聯發科",
    "2324": "仁寶",
    "4927": "泰鼎-KY",
    "8299": "群聯",
    "3017": "奇鋐",
    "6805": "富世達",
    "3661": "世芯-KY",
    "6770": "力積電",
}

# 冷卻時間 (秒)
SOP_COOLDOWN    = 4 * 3600   # SOP 訊號同一股 4 小時內不重複
SIGNAL_COOLDOWN = 1 * 3600   # 一般訊號 1 小時

# ─────────────────────────────────────────
# 工具：Telegram
# ─────────────────────────────────────────
def tg_send(msg: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=8
        )
    except Exception as e:
        print(f"[TG ERROR] {e}")

# ─────────────────────────────────────────
# 工具：資料取得
# ─────────────────────────────────────────
def get_df(code: str, period="1y", interval="1d") -> pd.DataFrame | None:
    for sfx in [".TW", ".TWO"]:
        try:
            df = yf.Ticker(code + sfx).history(period=period, interval=interval)
            if not df.empty: return df
        except: pass
    return None

# ─────────────────────────────────────────
# 指標計算
# ─────────────────────────────────────────
def _sar(high, low, af0=0.02, af_max=0.2):
    n   = len(high)
    sar = np.zeros(n); trend = np.ones(n)
    ep  = np.zeros(n); af    = np.full(n, af0)
    sar[0]=low[0]; ep[0]=high[0]
    for i in range(1, n):
        sar[i] = sar[i-1] + af[i-1]*(ep[i-1]-sar[i-1])
        if trend[i-1] == 1:
            if low[i] < sar[i]:
                trend[i]=-1; sar[i]=ep[i-1]; ep[i]=low[i]; af[i]=af0
            else:
                trend[i]=1
                if high[i]>ep[i-1]: ep[i]=high[i]; af[i]=min(af[i-1]+af0,af_max)
                else: ep[i]=ep[i-1]; af[i]=af[i-1]
                sar[i]=min(sar[i], low[i-1])
                if i>1: sar[i]=min(sar[i], low[i-2])
        else:
            if high[i] > sar[i]:
                trend[i]=1; sar[i]=ep[i-1]; ep[i]=high[i]; af[i]=af0
            else:
                trend[i]=-1
                if low[i]<ep[i-1]: ep[i]=low[i]; af[i]=min(af[i-1]+af0,af_max)
                else: ep[i]=ep[i-1]; af[i]=af[i-1]
                sar[i]=max(sar[i], high[i-1])
                if i>1: sar[i]=max(sar[i], high[i-2])
    return sar

def add_ind(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
    n = len(df)

    df["SAR"] = _sar(df["High"].values, df["Low"].values) if n>5 else np.nan

    for p in [5, 10, 20, 60]:
        df[f"MA{p}"] = df["Close"].rolling(p).mean() if n>=p else np.nan

    h9  = df["High"].rolling(9).max()
    l9  = df["Low"].rolling(9).min()
    rsv = ((df["Close"]-l9)/(h9-l9)*100).fillna(50)
    k,d = [50.0],[50.0]
    for v in rsv:
        k.append(k[-1]*2/3+v/3); d.append(d[-1]*2/3+k[-1]/3)
    df["K"]=k[1:]; df["D"]=d[1:]

    e12=df["Close"].ewm(span=12,adjust=False).mean()
    e26=df["Close"].ewm(span=26,adjust=False).mean()
    df["DIF"]      =e12-e26
    df["MACD_SIG"] =df["DIF"].ewm(span=9,adjust=False).mean()
    df["MACD_HIST"]=df["DIF"]-df["MACD_SIG"]

    df["TR"]     =np.maximum(df["High"]-df["Low"],np.abs(df["High"]-df["Close"].shift(1)))
    df["ATR"]    =df["TR"].rolling(14).mean()
    df["VOL_MA5"]=df["Volume"].rolling(5).mean()
    return df

# ─────────────────────────────────────────
# 波浪識別
# ─────────────────────────────────────────
def wave_label(df: pd.DataFrame) -> str:
    if df is None or len(df) < 15: return "N/A"
    c   = df["Close"].iloc[-1]
    m20 = df["MA20"].iloc[-1] if not pd.isna(df["MA20"].iloc[-1]) else c
    m60 = df["MA60"].iloc[-1] if "MA60" in df.columns and not pd.isna(df["MA60"].iloc[-1]) else c
    k   = df["K"].iloc[-1]; pk=df["K"].iloc[-2]
    h   = df["MACD_HIST"].iloc[-1]; ph=df["MACD_HIST"].iloc[-2]
    if c >= m60:
        if c > m20:
            if h>0 and h>ph: return "3-5" if k>80 else "3-3"
            if h>0:          return "3-a"
            return "3-1"
        else:
            if k<20: return "4-c"
            if k<pk: return "4-a"
            return "4-b"
    else:
        if c<m20: return "C-5" if k<20 else "C-3"
        return "B-c" if k>80 else "B-a"

# ─────────────────────────────────────────
# ★  核心 SOP 判斷
# ─────────────────────────────────────────
def sop_check(df: pd.DataFrame) -> dict:
    """
    回傳 dict：
      signal   : "BUY" / "SELL" / None
      hard_pass: bool  (三線全達)
      cond_*   : 各條件 bool
      *_label  : 文字說明
      vol_ratio: float
      wave     : str
    """
    empty = {"signal":None,"hard_pass":False}
    if df is None or len(df)<30: return empty

    t=df.iloc[-1]; p=df.iloc[-2]

    # 硬條件
    kd_cross = (p["K"]<p["D"]) and (t["K"]>t["D"])
    kd_bull  = t["K"]>t["D"]
    cond_kd  = kd_bull or kd_cross
    kd_lbl   = "今日金叉✨" if kd_cross else ("多頭排列" if kd_bull else "空方排列")

    cond_macd = t["MACD_HIST"]>0
    macd_flip = p["MACD_HIST"]<=0 and t["MACD_HIST"]>0
    macd_lbl  = "今日翻紅🔴" if macd_flip else ("紅柱延伸" if cond_macd else "綠柱整理")

    cond_sar = float(t["Close"]) > float(t["SAR"])
    sar_lbl  = "多方支撐↑" if cond_sar else "空方壓力↓"

    hard_pass = cond_kd and cond_macd and cond_sar

    # 軟條件
    vol_ma5   = t["VOL_MA5"] if t["VOL_MA5"]>0 else 1
    vol_ratio = round(float(t["Volume"])/float(vol_ma5),1)
    cond_vol  = vol_ratio>=1.5

    wave = wave_label(df)
    wave_hint_map = {
        "3-3":"🌊 3-3 主升急漲（波浪加分）",
        "3-5":"🏔️ 3-5 噴出末段（波浪加分，注意高點）",
        "3-1":"🌱 3-1 初升啟動（波浪提示）",
        "4-c":"🪤 4-c 修正末端（波浪提示）",
    }
    wave_hint = wave_hint_map.get(wave)

    # 訊號決定
    signal = None
    if hard_pass:
        signal = "SELL" if wave in ("3-5","B-c","C-3") else "BUY"

    return {
        "signal":    signal,
        "hard_pass": hard_pass,
        "cond_kd":   cond_kd,   "kd_lbl":   kd_lbl,
        "cond_macd": cond_macd, "macd_lbl": macd_lbl,
        "cond_sar":  cond_sar,  "sar_lbl":  sar_lbl,
        "cond_vol":  cond_vol,  "vol_ratio":vol_ratio,
        "wave":      wave,      "wave_hint":wave_hint,
    }

# ─────────────────────────────────────────
# 組 Telegram 訊息
# ─────────────────────────────────────────
def build_sop_msg(signal: str, code: str, name: str,
                  df: pd.DataFrame, sop: dict) -> str:
    t = df.iloc[-1]; p = df.iloc[-2]
    pct  = (t["Close"]-p["Close"])/p["Close"]*100
    icon = "🔺" if pct>0 else "💚" if pct<0 else "➖"
    atr  = float(t["ATR"]) if not pd.isna(t["ATR"]) else float(t["Close"])*0.02

    ma5  = float(t["MA5"])  if not pd.isna(t.get("MA5",  np.nan)) else float(t["Close"])
    ma20 = float(t["MA20"]) if not pd.isna(t.get("MA20", np.nan)) else float(t["Close"])
    fib_236 = df["High"].iloc[-120:].max() - (df["High"].iloc[-120:].max()-df["Low"].iloc[-120:].min())*0.236
    fib_618 = df["High"].iloc[-120:].max() - (df["High"].iloc[-120:].max()-df["Low"].iloc[-120:].min())*0.618
    buy_agg = max(ma5,  fib_236)
    buy_con = max(ma20, fib_236)
    stop    = max(float(t["Close"]) - atr*2, fib_618)

    emoji  = "🚀" if signal=="BUY" else "⚠️"
    action = "BUY — SOP 三線觸發！進場！" if signal=="BUY" else "SELL — 高檔出場訊號！"

    price_blk = (
        f"🦁 激進買點：<b>{buy_agg:.2f}</b>\n"
        f"🐢 保守買點：<b>{buy_con:.2f}</b>\n"
        f"🛑 建議停損：<b>{stop:.2f}</b>"
    ) if signal=="BUY" else (
        f"⚡ 建議出場：<b>{t['Close']:.2f}</b> 附近\n"
        f"🛑 停損：<b>{stop:.2f}</b>"
    )

    # 軟提示
    soft = ""
    if sop["cond_vol"]:  soft += f"\n💡 量比 <b>{sop['vol_ratio']}x</b> ≥ 1.5（加分提示）"
    if sop["wave_hint"]: soft += f"\n{sop['wave_hint']}"

    return (
        f"{emoji} <b>AI Stock Bot — SOP 訊號</b> {emoji}\n\n"
        f"<b>{name}（{code}）</b> {icon} {t['Close']:.2f}（{pct:+.2f}%）\n"
        f"📊 量比：{sop['vol_ratio']}x ｜ 🌊 日線：{sop['wave']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>{action}</b>\n"
        f"✅ KD：{sop['kd_lbl']}\n"
        f"✅ MACD：{sop['macd_lbl']}\n"
        f"✅ SAR：{sop['sar_lbl']}"
        f"{soft}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{price_blk}\n\n"
        f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>"
    )

# ─────────────────────────────────────────
# 一般訊號偵測 (盤中快報)
# ─────────────────────────────────────────
def basic_signals(df: pd.DataFrame) -> list[str]:
    if df is None or len(df)<10: return []
    t=df.iloc[-1]; p=df.iloc[-2]; sigs=[]
    # 出量突破
    if t["Volume"]>t["VOL_MA5"]*1.5 and t["Close"]>p["Close"]*1.02:
        sigs.append("🚀 <b>出量突破</b>（量增+2%）")
    # KD 金叉
    if p["K"]<p["D"] and t["K"]>t["D"] and t["K"]<80:
        sigs.append("✅ <b>KD 今日金叉</b>")
    # MACD 翻紅
    if p["MACD_HIST"]<=0 and t["MACD_HIST"]>0:
        sigs.append("🔴 <b>MACD 今日翻紅</b>")
    # 咕嚕咕嚕
    if t["K"]<40 and t["K"]>p["K"] and t["K"]>t["D"]:
        sigs.append("💧 <b>底部咕嚕咕嚕</b>（低檔KD轉上）")
    # 連買
    recent = df.iloc[-10:]
    streak = 0
    for x in reversed(((recent["Close"]>=recent["Open"]) | (recent["Close"]>recent["Close"].shift(1))).values):
        if x: streak+=1
        else: break
    if 3<=streak<=10:
        sigs.append(f"🛡️ <b>主力連買 {streak} 天</b>")
    return sigs

# ─────────────────────────────────────────
# 定時報告
# ─────────────────────────────────────────
SCHEDULE = {
    "09:30": "open",
    "10:20": "mid",
    "12:00": "mid",
    "13:36": "close",
    "18:40": "evening",
}

def report_open():
    lines = ["🌅 <b>09:30 開盤掃描</b>\n"]
    for code,name in WATCH_LIST.items():
        df = get_df(code); df = add_ind(df)
        if df is None: continue
        t=df.iloc[-1]; p=df.iloc[-2]
        pct=(t["Close"]-p["Close"])/p["Close"]*100
        icon="🔺" if pct>0 else "💚" if pct<0 else "➖"
        vol_r=round(t["Volume"]/t["VOL_MA5"],1) if t["VOL_MA5"]>0 else 0
        sigs = basic_signals(df)
        sop  = sop_check(df)
        sop_txt=""
        if sop["hard_pass"]: sop_txt=" ⚡<b>三線已達！</b>"
        lines.append(
            f"<b>{name}({code})</b> {icon}{t['Close']:.2f}({pct:+.2f}%) 量比{vol_r}x{sop_txt}\n"
            + (f"  {'｜'.join(sigs)}\n" if sigs else "  觀察中\n")
        )
    tg_send("\n".join(lines))

def report_mid(label: str):
    lines = [f"🔔 <b>{label} 盤中戰略</b>\n"]
    for code,name in WATCH_LIST.items():
        df=get_df(code); df=add_ind(df)
        if df is None: continue
        t=df.iloc[-1]; p=df.iloc[-2]
        pct=(t["Close"]-p["Close"])/p["Close"]*100
        icon="🔺" if pct>0 else "💚" if pct<0 else "➖"
        sop  = sop_check(df)
        sigs = basic_signals(df)
        # SOP 狀態
        hard_n = sum([sop["cond_kd"],sop["cond_macd"],sop["cond_sar"]])
        sop_line = ""
        if sop["signal"]=="BUY":   sop_line="🚀 <b>SOP BUY 觸發！</b>"
        elif sop["signal"]=="SELL":sop_line="⚠️ <b>SOP SELL 觸發！</b>"
        else:                       sop_line=f"👀 SOP 觀察中（{hard_n}/3 硬條件）"
        # 軟提示
        hints=""
        if sop["cond_vol"]:  hints+=f" 💡量比{sop['vol_ratio']}x"
        if sop["wave_hint"]: hints+=f" 🌊{sop['wave']}"
        lines.append(
            f"<b>{name}({code})</b> {icon}{t['Close']:.2f}({pct:+.2f}%)\n"
            f"  {sop_line}{hints}\n"
            + (f"  {'｜'.join(sigs)}\n" if sigs else "")
        )
    tg_send("\n".join(lines))

def report_close():
    lines = ["🌇 <b>13:36 收盤確認</b>\n"]
    for code,name in WATCH_LIST.items():
        df=get_df(code); df=add_ind(df)
        if df is None: continue
        t=df.iloc[-1]; p=df.iloc[-2]
        pct=(t["Close"]-p["Close"])/p["Close"]*100
        icon="🔺" if pct>0 else "💚" if pct<0 else "➖"
        atr=float(t["ATR"]) if not pd.isna(t["ATR"]) else float(t["Close"])*0.02
        ma20=float(t["MA20"]) if not pd.isna(t.get("MA20",np.nan)) else float(t["Close"])
        stop=float(t["Close"])-atr*2
        lines.append(
            f"<b>{name}({code})</b> <b>{icon}{t['Close']:.2f}({pct:+.2f}%)</b>\n"
            f"  🎯 明日低接參考：{ma20:.2f}｜🛑 停損：{stop:.2f}\n"
        )
    tg_send("\n".join(lines))

def report_evening():
    lines = ["🌙 <b>18:40 盤後AI總結</b>\n"]
    for code,name in WATCH_LIST.items():
        df=get_df(code); df=add_ind(df)
        if df is None: continue
        t=df.iloc[-1]; p=df.iloc[-2]
        pct=(t["Close"]-p["Close"])/p["Close"]*100
        icon="🔺" if pct>0 else "💚" if pct<0 else "➖"
        # 籌碼推估
        v_up   = t["Volume"]>t["VOL_MA5"] and t["Close"]>p["Close"]
        v_down = t["Volume"]>t["VOL_MA5"] and t["Close"]<p["Close"]
        chip   = "量增價漲 (主力進場)" if v_up else "出貨跡象⚠️" if v_down else "量縮整理"
        sop    = sop_check(df)
        # 綜合建議
        score  = sum([sop["cond_kd"],sop["cond_macd"],sop["cond_sar"],
                      sop["cond_vol"],sop["cond_wave"] if "cond_wave" in sop else False])
        advice = "🔥 積極操作" if score>=4 else "✅ 拉回留意" if score>=2 else "⚠️ 觀望"
        lines.append(
            f"<b>{name}({code})</b> {icon}{t['Close']:.2f}({pct:+.2f}%)\n"
            f"  🛡️ 籌碼：{chip}\n"
            f"  💡 AI：{advice}（硬條件達 {sum([sop['cond_kd'],sop['cond_macd'],sop['cond_sar']])}/3）\n"
        )
    tg_send("\n".join(lines))

# ─────────────────────────────────────────
# 主迴圈
# ─────────────────────────────────────────
def run():
    print("🤖 AI Stock Bot V1.0 啟動...")
    tg_send(
        "🤖 <b>AI Stock Bot V1.0 上線！</b>\n\n"
        "SOP 三線觸發：KD金叉/多頭 + MACD翻紅 + SAR多方\n"
        "軟提示：波浪 3-3/3-5/3浪/5浪 ＋ 量比≥1.5\n\n"
        f"監控：{' / '.join(WATCH_LIST.values())}"
    )

    sent_schedule : dict[str,bool] = {t:False for t in SCHEDULE}
    sop_history   : dict[str, datetime] = {}   # code → 上次 SOP 推播時間
    sig_history   : dict[str, datetime] = {}   # code → 上次一般訊號時間

    while True:
        now   = datetime.utcnow() + timedelta(hours=8)
        hm    = now.strftime("%H:%M")
        wday  = now.weekday()                    # 0=Mon

        is_workday    = wday <= 4
        is_active     = is_workday and  8 <= now.hour <= 19
        is_trading    = is_workday and (
            now.hour == 9 or
            (9 < now.hour < 13) or
            (now.hour == 13 and now.minute <= 30)
        )

        # 休市
        if not is_active:
            print(f"\r💤 {hm} 休市", end="")
            if hm == "00:00":
                for k in sent_schedule: sent_schedule[k]=False
            time.sleep(60); continue

        print(f"\r🔄 {hm} {'交易中' if is_trading else '盤後'}", end="")

        # ── 定時報告 ──
        if hm in SCHEDULE and not sent_schedule[hm]:
            rtype = SCHEDULE[hm]
            print(f"\n⏰ {hm} 定時報告 ({rtype})")
            if   rtype == "open":    report_open()
            elif rtype == "mid":     report_mid(hm)
            elif rtype == "close":   report_close()
            elif rtype == "evening": report_evening()
            sent_schedule[hm] = True

        # 每日 08:00 重置旗標
        if hm == "08:00":
            for k in sent_schedule: sent_schedule[k]=False

        # ── 即時 SOP 掃描 (交易時段) ──
        if is_trading:
            for code, name in WATCH_LIST.items():
                try:
                    # SOP 冷卻判斷
                    last_sop = sop_history.get(code)
                    sop_ok   = (not last_sop or
                                (now - last_sop).seconds >= SOP_COOLDOWN)

                    if sop_ok:
                        df  = get_df(code)
                        if df is None: continue
                        df  = add_ind(df)
                        sop = sop_check(df)

                        if sop["signal"] in ("BUY","SELL"):
                            msg = build_sop_msg(sop["signal"], code, name, df, sop)
                            tg_send(msg)
                            sop_history[code] = now
                            print(f"\n🚨 {hm} SOP {sop['signal']} → {name}({code})")
                            continue   # 已推 SOP，跳過一般訊號

                    # 一般訊號冷卻
                    last_sig = sig_history.get(code)
                    sig_ok   = (not last_sig or
                                (now - last_sig).seconds >= SIGNAL_COOLDOWN)
                    if not sig_ok: continue

                    df   = get_df(code)
                    if df is None: continue
                    df   = add_ind(df)
                    sigs = basic_signals(df)

                    if sigs:
                        t   = df.iloc[-1]; p = df.iloc[-2]
                        pct = (t["Close"]-p["Close"])/p["Close"]*100
                        icon= "🔺" if pct>0 else "💚" if pct<0 else "➖"
                        msg = (
                            f"🚨 <b>盤中訊號快報</b>\n\n"
                            f"<b>{name}（{code}）</b> {icon}{t['Close']:.2f}（{pct:+.2f}%）\n"
                            + "\n".join(sigs) +
                            f"\n<i>⏰ {hm}</i>"
                        )
                        tg_send(msg)
                        sig_history[code] = now
                except Exception as e:
                    pass  # 靜默忽略單支失敗

        time.sleep(30)

if __name__ == "__main__":
    run()
