"""
AI-stock-bot — Streamlit 分析主程式
Version: 1.0.0
SOP 定義：KD金叉/多頭 + MACD翻紅 + SAR多方 (三線全達 → 觸發)
軟提示：波浪 3-3/3-5/3浪/5浪 + 量比 ≥ 1.5
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

# ─────────────────────────────────────────
# 頁面設定
# ─────────────────────────────────────────
st.set_page_config(page_title="AI Stock Bot", page_icon="🤖", layout="wide")

st.markdown("""
<style>
/* ── 全域字體 ── */
body { font-family: 'Segoe UI', sans-serif; }

/* ── SOP 觸發橫幅 ── */
@keyframes glow {
    0%,100% { box-shadow: 0 0 6px #00c853; }
    50%      { box-shadow: 0 0 22px 6px #00c853; }
}
.sop-banner-buy {
    background: linear-gradient(135deg,#003300,#004d00,#006600);
    border: 2px solid #00c853;
    border-radius: 12px;
    padding: 22px 28px;
    margin: 14px 0;
    animation: glow 2s ease-in-out infinite;
    color: #fff;
}
@keyframes glow-sell {
    0%,100% { box-shadow: 0 0 6px #ff1744; }
    50%      { box-shadow: 0 0 22px 6px #ff1744; }
}
.sop-banner-sell {
    background: linear-gradient(135deg,#330000,#4d0000,#660000);
    border: 2px solid #ff1744;
    border-radius: 12px;
    padding: 22px 28px;
    margin: 14px 0;
    animation: glow-sell 2s ease-in-out infinite;
    color: #fff;
}
.sop-title  { font-size: 24px; font-weight: 900; letter-spacing: 1px; }
.sop-sub    { font-size: 15px; margin-top: 8px; line-height: 1.9; }
.sop-hint   {
    background: rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 10px 14px;
    margin-top: 12px;
    font-size: 14px;
    color: #ffe082;
}

/* ── 觀察橫幅 ── */
.watch-banner {
    background: #f9f9f9;
    border: 2px dashed #bbb;
    border-radius: 10px;
    padding: 14px 20px;
    margin: 10px 0;
    font-size: 14px;
    color: #444;
}

/* ── 區塊卡片 ── */
.card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 14px;
}
.card-title { font-size: 17px; font-weight: 700; margin-bottom: 10px; color: #1a237e; }

/* ── 條件列表 ── */
.cond-row { font-size: 15px; line-height: 2; }
.pass  { color: #2e7d32; font-weight: 600; }
.fail  { color: #c62828; font-weight: 600; }
.hint  { color: #e65100; font-weight: 600; }

/* ── 波段標籤 ── */
.wave-chip {
    display: inline-block;
    font-size: 13px;
    font-weight: bold;
    padding: 2px 10px;
    border-radius: 20px;
    margin-right: 6px;
}
.wave-bull { background: #e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7; }
.wave-bear { background: #ffebee; color: #c62828; border: 1px solid #ef9a9a; }
.wave-neut { background: #fff3e0; color: #e65100; border: 1px solid #ffcc80; }

/* ── 股價大字 ── */
.price-up   { color: #d32f2f; font-weight: 800; font-size: 28px; }
.price-down { color: #388e3c; font-weight: 800; font-size: 28px; }
.price-flat { color: #555;    font-weight: 800; font-size: 28px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 側邊欄
# ─────────────────────────────────────────
with st.sidebar:
    st.image("https://raw.githubusercontent.com/primer/octicons/main/icons/graph-24.svg", width=36)
    st.title("🤖 AI Stock Bot")
    st.caption("V1.0  |  SOP 三線觸發版")

    st.markdown("---")
    stock_input = st.text_input("📌 輸入股票代號", value="2330", placeholder="如 2330, 2454")
    run_btn = st.button("🚀 開始分析", type="primary", use_container_width=True)

    st.markdown("---")
    st.subheader("📲 Telegram 推播")
    tg_token = st.text_input("Bot Token", type="password", placeholder="從 BotFather 取得")
    tg_chat  = st.text_input("Chat ID",   placeholder="你的頻道或個人 ID")

    st.markdown("---")
    st.caption("SOP 條件說明：")
    st.markdown("""
- ✅ **必達 (硬觸發)**
  - KD 金叉 / 多頭排列
  - MACD Hist 翻紅
  - SAR 多方支撐
- 💡 **加分提示 (軟條件)**
  - 波浪：3-3 / 3-5 / 3浪 / 5浪
  - 量比 ≥ 1.5
""")

# ─────────────────────────────────────────
# ① 資料取得
# ─────────────────────────────────────────
@st.cache_data(ttl=1800)
def fetch_stock(symbol: str):
    """取得日線、60分、30分 K 線及 ticker 物件"""
    clean = symbol.strip().replace(".TW","").replace(".TWO","")
    for suffix in [".TW", ".TWO"]:
        t = yf.Ticker(clean + suffix)
        try:
            df = t.history(period="2y")
            if df.empty: df = t.history(period="max")
            if not df.empty:
                df60 = t.history(period="1mo", interval="60m")
                df30 = t.history(period="1mo", interval="30m")
                return df, df60, df30, t, clean
        except:
            continue
    return None, None, None, None, clean

@st.cache_data(ttl=3600)
def fetch_name(symbol: str) -> str:
    try:
        r   = requests.get("https://histock.tw/stock/rank.aspx?p=all",
                           headers={"User-Agent":"Mozilla/5.0"}, timeout=5)
        dfs = pd.read_html(r.text)
        df  = dfs[0]
        cc  = [c for c in df.columns if "代號" in str(c)][0]
        cn  = [c for c in df.columns if "股票" in str(c) or "名稱" in str(c)][0]
        for _, row in df.iterrows():
            code = "".join(c for c in str(row[cc]) if c.isdigit())
            if code == symbol: return str(row[cn])
    except: pass
    return symbol

# ─────────────────────────────────────────
# ② 技術指標
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

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
    n = len(df)

    # SAR
    df["SAR"] = _sar(df["High"].values, df["Low"].values) if n > 5 else np.nan

    # 均線
    for p in [5, 10, 20, 60, 120]:
        df[f"MA{p}"] = df["Close"].rolling(p).mean() if n >= p else np.nan

    # KD (9,3,3)
    h9 = df["High"].rolling(9).max()
    l9 = df["Low"].rolling(9).min()
    rsv = ((df["Close"] - l9) / (h9 - l9) * 100).fillna(50)
    k, d = [50.0], [50.0]
    for v in rsv:
        k.append(k[-1]*2/3 + v/3)
        d.append(d[-1]*2/3 + k[-1]/3)
    df["K"] = k[1:]; df["D"] = d[1:]

    # MACD (12,26,9)
    e12 = df["Close"].ewm(span=12, adjust=False).mean()
    e26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["DIF"]       = e12 - e26
    df["MACD_SIG"]  = df["DIF"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["DIF"] - df["MACD_SIG"]

    # ATR
    df["TR"]  = np.maximum(df["High"]-df["Low"],
                np.abs(df["High"]-df["Close"].shift(1)))
    df["ATR"] = df["TR"].rolling(14).mean()

    # 布林
    df["BB_MID"] = df["Close"].rolling(20).mean()
    std          = df["Close"].rolling(20).std()
    df["BB_UP"]  = df["BB_MID"] + 2*std
    df["BB_LO"]  = df["BB_MID"] - 2*std
    df["BB_PCT"] = (df["Close"] - df["BB_LO"]) / (df["BB_UP"] - df["BB_LO"])

    # 量均
    df["VOL_MA5"] = df["Volume"].rolling(5).mean()

    return df

# ─────────────────────────────────────────
# ③ 波浪識別
# ─────────────────────────────────────────
_BULL_WAVES = {"3-1","3-3","3-5","4-a","4-b","4-c"}
_BEAR_WAVES = {"C-3","C-5","B-a","B-c"}
_HINT_WAVES = {"3-3","3-5"}          # 軟提示波浪 (加入 3浪/5浪 概念)

def wave_label(df: pd.DataFrame) -> str:
    if df is None or len(df) < 15: return "N/A"
    c   = df["Close"].iloc[-1]
    m20 = df["MA20"].iloc[-1]  if not pd.isna(df["MA20"].iloc[-1])  else c
    m60 = df["MA60"].iloc[-1]  if not pd.isna(df["MA60"].iloc[-1])  else c
    k   = df["K"].iloc[-1];  pk = df["K"].iloc[-2]
    h   = df["MACD_HIST"].iloc[-1]; ph = df["MACD_HIST"].iloc[-2]

    if c >= m60:                          # 多頭大趨勢
        if c > m20:
            if h > 0 and h > ph: return "3-5" if k > 80 else "3-3"
            if h > 0:            return "3-a"
            return "3-1"
        else:
            if k < 20:   return "4-c"
            if k < pk:   return "4-a"
            return "4-b"
    else:                                 # 空頭大趨勢
        if c < m20:
            return "C-5" if k < 20 else "C-3"
        return "B-c" if k > 80 else "B-a"

def wave_hint(label: str) -> str | None:
    """波浪軟提示文字，None 代表無提示"""
    hints = {
        "3-3": "🌊 3-3 主升急漲，波浪共振加分！",
        "3-5": "🏔️ 3-5 噴出末段，注意高點，波浪加分！",
        "3-1": "🌱 3-1 初升啟動，潛力波浪提示",
        "4-c": "🪤 4-c 修正末端，底部波浪提示",
    }
    return hints.get(label)

# ─────────────────────────────────────────
# ④ 費波那契
# ─────────────────────────────────────────
def fibonacci(df: pd.DataFrame) -> dict:
    w    = min(len(df), 120)
    hi   = df["High"].iloc[-w:].max()
    lo   = df["Low"].iloc[-w:].min()
    diff = hi - lo
    return {
        "high": hi, "low": lo,
        "0.236": hi - diff*0.236,
        "0.382": hi - diff*0.382,
        "0.500": hi - diff*0.500,
        "0.618": hi - diff*0.618,
    }

# ─────────────────────────────────────────
# ⑤ 核心 SOP 判斷
# ─────────────────────────────────────────
def sop_check(df: pd.DataFrame) -> dict:
    """
    回傳 SOP 各條件狀態與最終訊號。
    hard_pass = True  → 三線全達，發出 BUY / SELL
    soft hints → 波浪 & 量比 提示
    """
    if df is None or len(df) < 30:
        return {"signal": None}

    t = df.iloc[-1]; p = df.iloc[-2]

    # ── 硬條件 ──
    kd_cross = (p["K"] < p["D"]) and (t["K"] > t["D"])
    kd_bull  = t["K"] > t["D"]
    cond_kd  = kd_bull or kd_cross
    kd_label = "今日金叉 ✨" if kd_cross else ("多頭排列" if kd_bull else "空方排列")

    cond_macd  = t["MACD_HIST"] > 0
    macd_label = "今日翻紅 🔴" if (p["MACD_HIST"]<=0 and t["MACD_HIST"]>0) else \
                 ("紅柱延伸"   if cond_macd else "綠柱整理")

    cond_sar  = t["Close"] > t["SAR"]
    sar_label = "多方支撐 ↑" if cond_sar else "空方壓力 ↓"

    hard_pass = cond_kd and cond_macd and cond_sar

    # ── 軟條件 ──
    vol_ma5   = t["VOL_MA5"] if t["VOL_MA5"] > 0 else 1
    vol_ratio = round(t["Volume"] / vol_ma5, 1)
    cond_vol  = vol_ratio >= 1.5

    # 波浪 (日線)
    wlabel    = wave_label(df)
    cond_wave = wlabel in ("3-3","3-5","3-1","4-c")  # 3浪/5浪系列

    # ── 訊號邏輯 ──
    signal = None
    if hard_pass:
        # 高檔出場判斷：SAR 多但波浪已進 3-5 或 B-c
        if wlabel in ("3-5","B-c","C-3"):
            signal = "SELL"
        else:
            signal = "BUY"

    return {
        "signal":      signal,
        "hard_pass":   hard_pass,
        "cond_kd":     cond_kd,   "kd_label":   kd_label,
        "cond_macd":   cond_macd, "macd_label": macd_label,
        "cond_sar":    cond_sar,  "sar_label":  sar_label,
        "cond_vol":    cond_vol,  "vol_ratio":  vol_ratio,
        "cond_wave":   cond_wave, "wave_label": wlabel,
        "wave_hint":   wave_hint(wlabel),
    }

# ─────────────────────────────────────────
# ⑥ Telegram 推播
# ─────────────────────────────────────────
def push_telegram(token: str, chat_id: str, signal: str, name: str, code: str,
                  price: float, sop: dict, buy_agg: float, buy_con: float, stop: float) -> bool:
    if not token or not chat_id or "填" in token: return False
    emoji  = "🚀" if signal == "BUY" else "⚠️"
    action = "BUY — SOP 三線觸發！" if signal == "BUY" else "SELL — 高檔出場訊號！"
    price_lines = (f"🦁 激進買點：<b>{buy_agg:.2f}</b>\n"
                   f"🐢 保守買點：<b>{buy_con:.2f}</b>\n"
                   f"🛑 建議停損：<b>{stop:.2f}</b>") if signal=="BUY" else \
                  f"⚡ 建議出場：<b>{price:.2f}</b> 附近\n🛑 停損：<b>{stop:.2f}</b>"

    soft_lines = ""
    if sop["cond_vol"]:  soft_lines += f"\n💡 量比 {sop['vol_ratio']}x ≥ 1.5 (加分)"
    if sop["wave_hint"]: soft_lines += f"\n{sop['wave_hint']}"

    msg = (f"{emoji} <b>AI Stock Bot — SOP 訊號</b> {emoji}\n\n"
           f"<b>{name}（{code}）</b>\n"
           f"💰 現價：{price:.2f}\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"<b>{action}</b>\n"
           f"✅ KD：{sop['kd_label']}\n"
           f"✅ MACD：{sop['macd_label']}\n"
           f"✅ SAR：{sop['sar_label']}\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"{price_lines}"
           f"{soft_lines}\n\n"
           f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>")
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=8
        )
        return r.status_code == 200
    except:
        return False

# ─────────────────────────────────────────
# ⑦ 主顯示邏輯
# ─────────────────────────────────────────
def _v(row, key, fallback=np.nan):
    v = row.get(key, fallback)
    return fallback if pd.isna(v) else v

def wave_chip_html(label: str) -> str:
    cls = "wave-bull" if label.startswith(("3","4")) else \
          "wave-bear" if label.startswith(("C","B")) else "wave-neut"
    return f"<span class='wave-chip {cls}'>{label}</span>"

if run_btn:
    code_clean = stock_input.strip().replace(".TW","").replace(".TWO","")
    with st.spinner(f"正在載入 {code_clean} 資料..."):
        df_d, df_60, df_30, ticker, code_clean = fetch_stock(code_clean)
        name = fetch_name(code_clean)

    if df_d is None or len(df_d) < 10:
        st.error(f"❌ 找不到 {code_clean} 資料，請確認代號是否正確。")
        st.stop()

    # 計算指標
    df_d  = add_indicators(df_d)
    df_60 = add_indicators(df_60) if df_60 is not None and not df_60.empty else None
    df_30 = add_indicators(df_30) if df_30 is not None and not df_30.empty else None

    t = df_d.iloc[-1]; p = df_d.iloc[-2]

    # 計算各值
    sop  = sop_check(df_d)
    fib  = fibonacci(df_d)
    atr  = _v(t, "ATR", t["Close"]*0.02)

    w_d  = wave_label(df_d)
    w_60 = wave_label(df_60) if df_60 is not None else "N/A"
    w_30 = wave_label(df_30) if df_30 is not None else "N/A"

    ma5  = _v(t, "MA5",  fib["0.236"])
    ma20 = _v(t, "MA20", fib["0.382"])
    buy_agg = max(ma5,  fib["0.236"])
    buy_con = max(ma20, fib["0.382"])
    stop    = max(t["Close"] - atr*2, fib["0.618"])

    vol_ma5   = t["VOL_MA5"] if t["VOL_MA5"] > 0 else 1
    vol_ratio = round(t["Volume"] / vol_ma5, 1)

    diff     = t["Close"] - p["Close"]
    diff_pct = diff / p["Close"] * 100
    p_cls    = "price-up" if diff > 0 else "price-down" if diff < 0 else "price-flat"
    p_sign   = "+" if diff > 0 else ""

    # ── 標題區 ──
    st.markdown(f"## 📊 {name}（{code_clean}）")
    c1, c2, c3 = st.columns([2,2,3])
    c1.markdown(f"<span class='{p_cls}'>{t['Close']:.2f}</span>", unsafe_allow_html=True)
    c1.caption(f"{p_sign}{diff:.2f}（{p_sign}{diff_pct:.2f}%）")
    c2.metric("成交量", f"{int(t['Volume']/1000)} 張", f"量比 {vol_ratio}x")
    c3.markdown(
        f"波浪結構：{wave_chip_html(w_d)}{wave_chip_html(w_60)}{wave_chip_html(w_30)}",
        unsafe_allow_html=True
    )

    st.markdown("---")

    # ════════════════════════════════════════
    # SOP 訊號區塊
    # ════════════════════════════════════════
    signal = sop["signal"]

    if signal in ("BUY", "SELL"):
        css_cls = "sop-banner-buy" if signal == "BUY" else "sop-banner-sell"
        action_txt = "🚀 BUY — SOP 三線全達，最佳進場！" if signal=="BUY" \
               else "⚠️ SELL — 高檔出場訊號觸發！"

        # 軟提示 HTML
        hints_html = ""
        if sop["cond_vol"]:
            hints_html += f"<div>💡 <b>量比 {vol_ratio}x</b>（≥ 1.5 加分提示）</div>"
        if sop["wave_hint"]:
            hints_html += f"<div>{sop['wave_hint']}</div>"

        price_html = (
            f"<b>🦁 激進買點：{buy_agg:.2f}</b> ｜ "
            f"<b>🐢 保守買點：{buy_con:.2f}</b> ｜ "
            f"<b>🛑 建議停損：{stop:.2f}</b>"
        ) if signal=="BUY" else (
            f"<b>⚡ 建議出場：{t['Close']:.2f} 附近分批出場</b> ｜ "
            f"<b>🛑 停損：{stop:.2f}</b>"
        )

        st.markdown(f"""
        <div class='{css_cls}'>
            <div class='sop-title'>{action_txt}</div>
            <div class='sop-sub'>
                ✅ KD：{sop['kd_label']} &nbsp;｜&nbsp;
                ✅ MACD：{sop['macd_label']} &nbsp;｜&nbsp;
                ✅ SAR：{sop['sar_label']}
            </div>
            {'<div class="sop-hint">' + hints_html + '</div>' if hints_html else ''}
            <div style='margin-top:14px; font-size:15px'>{price_html}</div>
        </div>
        """, unsafe_allow_html=True)

        # Telegram 推播按鈕
        if st.button("📲 推播到 Telegram", type="primary"):
            ok = push_telegram(tg_token, tg_chat, signal, name, code_clean,
                               t["Close"], sop, buy_agg, buy_con, stop)
            st.success("✅ 已推播！") if ok else st.warning("⚠️ 請先在側邊欄填入 Token / Chat ID")

    else:
        # 未觸發 → 顯示條件進度
        hard_count = sum([sop["cond_kd"], sop["cond_macd"], sop["cond_sar"]])
        rows_html  = "".join([
            f"<div class='cond-row'>"
            f"<span class='{'pass' if ok else 'fail'}'>{'✅' if ok else '❌'} {label}</span>"
            f"</div>"
            for ok, label in [
                (sop["cond_kd"],   f"KD：{sop['kd_label']}"),
                (sop["cond_macd"], f"MACD：{sop['macd_label']}"),
                (sop["cond_sar"],  f"SAR：{sop['sar_label']}"),
            ]
        ])
        # 軟提示
        soft_html = ""
        if sop["cond_vol"]:
            soft_html += f"<div class='cond-row'><span class='hint'>💡 量比 {vol_ratio}x ≥ 1.5（軟提示達標 ✔）</span></div>"
        else:
            soft_html += f"<div class='cond-row'><span style='color:#888'>💡 量比 {vol_ratio}x（未達 1.5）</span></div>"
        if sop["wave_hint"]:
            soft_html += f"<div class='cond-row'><span class='hint'>{sop['wave_hint']}（軟提示達標 ✔）</span></div>"
        else:
            soft_html += f"<div class='cond-row'><span style='color:#888'>🌊 波浪 {w_d}（非 3-3/3-5/3浪 提示範圍）</span></div>"

        st.markdown(f"""
        <div class='watch-banner'>
            👀 <b>SOP 觀察中</b>（硬條件 {hard_count}/3 達標，尚未觸發）
            <div style='margin-top:10px'>{rows_html}</div>
            <hr style='border:none;border-top:1px dashed #ccc;margin:10px 0'>
            <b style='font-size:13px;color:#888'>軟提示（加分項）：</b>
            {soft_html}
        </div>
        """, unsafe_allow_html=True)

    # ════════════════════════════════════════
    # 波浪結構 + 均線圖
    # ════════════════════════════════════════
    st.markdown("---")
    col_w1, col_w2, col_w3 = st.columns(3)
    col_w1.info(f"📅 日線\n\n### {w_d}")
    col_w2.warning(f"⏰ 60分K\n\n### {w_60}")
    col_w3.error(f"⚡ 30分K\n\n### {w_30}")

    # 均線圖（近 60 日）
    chart_data = df_d[["Close","MA5","MA20","MA60"]].iloc[-60:].dropna()
    if not chart_data.empty:
        st.markdown("#### 📈 近 60 日股價 + 均線")
        st.line_chart(chart_data, color=["#000000","#e53935","#43a047","#1e88e5"])
        st.caption("黑:收盤 ｜ 紅:5MA ｜ 綠:20MA ｜ 藍:60MA")

    # ════════════════════════════════════════
    # 費波那契 + 布林
    # ════════════════════════════════════════
    st.markdown("---")
    fc, bc = st.columns(2)
    with fc:
        st.markdown("#### 📐 費波那契回檔")
        price = t["Close"]
        for ratio, key in [("0.236","0.236"),("0.382","0.382"),("0.500","0.500"),("0.618","0.618")]:
            lvl = fib[key]
            tag = "✅ 守住" if price > lvl else "⚠️ 跌破"
            st.write(f"**{ratio}**：{lvl:.2f} — {tag}")

    with bc:
        st.markdown("#### 🎯 布林通道位置")
        bb_pct = _v(t, "BB_PCT", 0.5)
        bb_msg = "衝出上軌（賣訊）" if bb_pct > 1 else "跌破下軌（買訊）" if bb_pct < 0 else "區間震盪"
        st.metric("布林位置", bb_msg)
        st.progress(float(np.clip(bb_pct, 0, 1)))
        st.caption(f"目前在通道 {bb_pct*100:.1f}% 位置（0%=下軌，100%=上軌）")

    # ════════════════════════════════════════
    # 目標價
    # ════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 🎯 目標價預估")
    t1, t2, t3 = st.columns(3)
    reality = 2.5
    for col, mult, label in [(t1,1.05,"短線 +5%"),(t2,1.10,"波段 +10%"),(t3,1.20,"長線 +20%")]:
        tp    = t["Close"] * mult
        dist  = tp - t["Close"]
        days  = max(5, int(dist / (atr*0.4) * reality))
        col.metric(label, f"{tp:.2f}", f"約 {days} 天")

    st.markdown("---")
    st.caption(f"資料更新：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ AI Stock Bot V1.0")
