"""
AI-stock-bot — Streamlit V3.0
深色金融主題 | 完整目標價分析 | 快取修正 | GROQ 狀態提示
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import gist_db as db

try:
    import ai_report
    AI_READY = True
except Exception:
    AI_READY = False

# ─────────────────────────────────────────
st.set_page_config(page_title="AI Stock Bot", page_icon="📈", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0e1a;
    color: #e2e8f0;
}
.stApp { background: #0a0e1a; }
.main .block-container { padding: 1.5rem 2rem; }

/* ── 登入頁 ── */
.login-card {
    background: linear-gradient(145deg,#131929,#1a2236);
    border: 1px solid #2d3a52;
    border-radius: 20px;
    padding: 48px 40px;
    box-shadow: 0 24px 64px rgba(0,0,0,0.6);
}
.login-logo { font-size:40px; text-align:center; margin-bottom:6px; }
.login-title { font-size:26px; font-weight:700; text-align:center; color:#f8fafc; }
.login-sub { text-align:center; color:#64748b; font-size:14px; margin-bottom:28px; }

/* ── 側邊欄 ── */
[data-testid="stSidebar"] {
    background: #0d1220 !important;
    border-right: 1px solid #1e2a3a;
}
[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: #1e2a3a;
    color: #94a3b8;
    border: 1px solid #2d3a52;
    border-radius: 8px;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid #1e2a3a;
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #64748b;
    font-size: 14px;
    font-weight: 500;
    padding: 12px 20px;
    border-bottom: 2px solid transparent;
}
.stTabs [aria-selected="true"] {
    color: #38bdf8 !important;
    border-bottom: 2px solid #38bdf8 !important;
    background: transparent !important;
}

/* ── 卡片 ── */
.card {
    background: linear-gradient(145deg,#131929,#1a2236);
    border: 1px solid #1e2a3a;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
}
.card-sm {
    background: #131929;
    border: 1px solid #1e2a3a;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
}

/* ── 價格顯示 ── */
.price-up   { color:#22d3ee; font-weight:800; font-size:32px; letter-spacing:-1px; }
.price-down { color:#f87171; font-weight:800; font-size:32px; letter-spacing:-1px; }
.price-flat { color:#94a3b8; font-weight:800; font-size:32px; letter-spacing:-1px; }
.pct-up   { color:#4ade80; font-size:15px; font-weight:600; }
.pct-down { color:#f87171; font-size:15px; font-weight:600; }

/* ── SOP 橫幅 ── */
@keyframes glow-buy  { 0%,100%{box-shadow:0 0 0 rgba(34,197,94,0)} 50%{box-shadow:0 0 28px 4px rgba(34,197,94,0.35)} }
@keyframes glow-sell { 0%,100%{box-shadow:0 0 0 rgba(239,68,68,0)}  50%{box-shadow:0 0 28px 4px rgba(239,68,68,0.35)} }
.sop-buy {
    background: linear-gradient(135deg,#052e16,#14532d,#166534);
    border: 1px solid #22c55e;
    border-radius: 14px; padding: 22px 28px; margin: 14px 0;
    animation: glow-buy 2.4s ease-in-out infinite; color:#fff;
}
.sop-sell {
    background: linear-gradient(135deg,#2d0000,#450a0a,#560d0d);
    border: 1px solid #ef4444;
    border-radius: 14px; padding: 22px 28px; margin: 14px 0;
    animation: glow-sell 2.4s ease-in-out infinite; color:#fff;
}
.sop-title { font-size:20px; font-weight:800; letter-spacing:.5px; }
.sop-sub   { font-size:13px; margin-top:8px; line-height:2; color:#d1fae5; }
.sop-sell .sop-sub { color:#fee2e2; }
.watch-b {
    background:#0d1220; border:1px dashed #2d3a52;
    border-radius:12px; padding:16px 20px; margin:10px 0;
    font-size:14px; color:#64748b;
}

/* ── 條件 ── */
.pass { color:#4ade80; font-weight:600; }
.fail { color:#f87171; font-weight:600; }
.hint { color:#fb923c; font-weight:600; }
.cond-row { font-size:14px; line-height:2.2; }

/* ── 波浪 chip ── */
.wchip {
    display:inline-block; font-size:12px; font-weight:700;
    padding:3px 12px; border-radius:20px; margin-right:6px;
    font-family:'DM Mono',monospace;
}
.wbull { background:#052e16; color:#4ade80; border:1px solid #16a34a; }
.wbear { background:#2d0000; color:#f87171; border:1px solid #dc2626; }
.wneut { background:#1c1100; color:#fbbf24; border:1px solid #d97706; }

/* ── Metric override ── */
[data-testid="stMetric"] {
    background: #131929;
    border: 1px solid #1e2a3a;
    border-radius: 12px;
    padding: 14px 18px;
}
[data-testid="stMetricLabel"] { color:#64748b !important; font-size:12px !important; }
[data-testid="stMetricValue"] { color:#f8fafc !important; font-size:22px !important; font-weight:700 !important; }
[data-testid="stMetricDelta"] { font-size:12px !important; }

/* ── 按鈕 ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg,#0ea5e9,#6366f1) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    padding: 10px 20px !important;
    transition: opacity .2s !important;
}
.stButton > button[kind="primary"]:hover { opacity:.88 !important; }
.stButton > button[kind="secondary"] {
    background: #131929 !important; color:#94a3b8 !important;
    border: 1px solid #2d3a52 !important; border-radius:10px !important;
}

/* ── 目標價進度條 ── */
.tgt-card {
    background: linear-gradient(135deg,#0c1628,#111827);
    border: 1px solid #1e3a5f;
    border-radius: 16px; padding: 22px 26px; margin-bottom: 14px;
    position: relative; overflow: hidden;
}
.tgt-card::before {
    content:''; position:absolute; top:0; left:0;
    width:4px; height:100%;
    background: linear-gradient(180deg,#0ea5e9,#6366f1);
}
.tgt-reached::before { background: linear-gradient(180deg,#22c55e,#16a34a); }
.tgt-close::before   { background: linear-gradient(180deg,#f59e0b,#d97706); }

.tgt-name   { font-size:17px; font-weight:700; color:#f8fafc; }
.tgt-code   { font-size:12px; color:#64748b; margin-left:8px; }
.tgt-price  { font-size:28px; font-weight:800; color:#38bdf8; letter-spacing:-1px; }
.tgt-status { font-size:13px; font-weight:600; margin-top:4px; }
.tgt-progress-bg {
    background:#1e2a3a; border-radius:99px; height:8px; margin:14px 0;
    overflow:hidden;
}
.tgt-progress-fill {
    height:100%; border-radius:99px;
    background: linear-gradient(90deg,#0ea5e9,#6366f1);
    transition: width .6s ease;
}
.tgt-progress-fill.reached { background: linear-gradient(90deg,#22c55e,#4ade80); }
.tgt-progress-fill.close   { background: linear-gradient(90deg,#f59e0b,#fbbf24); }

/* ── 報告書 ── */
.report-wrap {
    background:#0d1220; border:1px solid #1e2a3a;
    border-radius:14px; padding:28px 32px; margin-top:16px;
    line-height:1.8;
}
.report-wrap h2 { color:#38bdf8; font-size:20px; border-bottom:1px solid #1e2a3a; padding-bottom:10px; }
.report-wrap h3 { color:#94a3b8; font-size:15px; margin-top:20px; margin-bottom:6px; }
.report-wrap strong { color:#e2e8f0; }
.report-wrap p { color:#94a3b8; font-size:14px; }
.report-wrap li { color:#94a3b8; font-size:14px; margin-bottom:4px; }

/* ── 新聞卡 ── */
.news-bull { color:#4ade80; font-size:12px; font-weight:700;
    background:#052e16; padding:2px 8px; border-radius:4px; }
.news-bear { color:#f87171; font-size:12px; font-weight:700;
    background:#2d0000; padding:2px 8px; border-radius:4px; }
.news-neut { color:#94a3b8; font-size:12px; font-weight:700;
    background:#1e2a3a; padding:2px 8px; border-radius:4px; }
.news-title { color:#cbd5e1; font-size:14px; }
.news-meta  { color:#475569; font-size:12px; }

/* ── 用戶 badge ── */
.badge-admin { background:#1e3a5f; color:#38bdf8; font-size:11px;
    padding:2px 8px; border-radius:6px; font-weight:700; }
.badge-user  { background:#1e1640; color:#a78bfa; font-size:11px;
    padding:2px 8px; border-radius:6px; font-weight:700; }

/* ── input override ── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: #131929 !important;
    border: 1px solid #2d3a52 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
.stSelectbox > div > div {
    background: #131929 !important;
    border: 1px solid #2d3a52 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}

/* ── 分隔線 ── */
hr { border-color: #1e2a3a !important; }

/* ── line chart ── */
[data-testid="stVegaLiteChart"] canvas { border-radius:10px; }

/* ── info/warning override ── */
.stAlert { border-radius:10px !important; }
</style>
""", unsafe_allow_html=True)

# ── Session ──
if "user" not in st.session_state:
    st.session_state.user = None

def logout():
    st.session_state.user = None
    st.rerun()

# ════════════════════════════════════════
# 登入頁
# ════════════════════════════════════════
if st.session_state.user is None:
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class='login-card'>
            <div class='login-logo'>📈</div>
            <div class='login-title'>AI Stock Bot</div>
            <div class='login-sub'>Professional Trading Intelligence Platform</div>
        </div>
        """, unsafe_allow_html=True)
        with st.container():
            uname = st.text_input("帳號", placeholder="輸入帳號", key="li_u")
            upw   = st.text_input("密碼", type="password", placeholder="輸入密碼", key="li_p")
            if st.button("🔐 登入", type="primary", use_container_width=True):
                u = db.login(uname, upw)
                if u:
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("❌ 帳號或密碼錯誤")
            st.caption("預設帳號：ruby / admin1234")
    st.stop()

# ════════════════════════════════════════
# 已登入
# ════════════════════════════════════════
user     = st.session_state.user
is_admin = user.get("role") == "admin"

# ── 檢查 GROQ Key ──
try:
    groq_key = st.secrets.get("GROQ_API_KEY", "")
except Exception:
    groq_key = ""

with st.sidebar:
    st.markdown(f"""
    <div style='padding:12px 0 6px'>
        <div style='font-size:16px;font-weight:700;color:#f8fafc'>👤 {user['display_name']}</div>
        <div style='font-size:12px;color:#64748b;margin-top:3px'>
            {'<span class="badge-admin">👑 管理員</span>' if is_admin else '<span class="badge-user">👤 用戶</span>'}
            &nbsp; @{user['username']}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    if groq_key:
        st.success("✅ Groq AI 已連線")
    else:
        st.error("❌ 未設定 GROQ_API_KEY")
        st.caption("至 groq.com 免費取得 → 填入 Streamlit Secrets")

    st.markdown("---")
    st.subheader("📲 Telegram")
    tg_token = st.text_input("Bot Token", type="password", placeholder="BotFather token", key="sb_tok")
    tg_chat  = st.text_input("Chat ID", value=user.get("telegram_chat_id",""), placeholder="你的 Chat ID", key="sb_chat")
    if st.button("💾 儲存 Chat ID", use_container_width=True):
        db.update_telegram(user["username"], tg_chat)
        st.session_state.user["telegram_chat_id"] = tg_chat
        st.success("✅ 已儲存")
    st.markdown("---")
    if st.button("🚪 登出", use_container_width=True):
        logout()

# ── Tabs ──
_tabs = ["📊 個股分析", "🎯 目標價", "📋 觀察名單", "⚙️ 帳號設定"]
if is_admin: _tabs.append("👑 用戶管理")
tabs    = st.tabs(_tabs)
tab_ana = tabs[0]; tab_tgt = tabs[1]; tab_wl  = tabs[2]
tab_acc = tabs[3]; tab_admin = tabs[4] if is_admin else None

# ════════════════════════════════════════
# 工具函數
# ════════════════════════════════════════
@st.cache_data(ttl=1800)
def fetch_stock(symbol):
    clean = symbol.strip().replace(".TW","").replace(".TWO","")
    for sfx in [".TW", ".TWO"]:
        try:
            t  = yf.Ticker(clean + sfx)
            df = t.history(period="2y")
            if df.empty: df = t.history(period="max")
            if not df.empty:
                return df, t.history(period="1mo",interval="60m"), \
                       t.history(period="1mo",interval="30m"), clean
        except: continue
    return None, None, None, clean

@st.cache_data(ttl=3600)
def fetch_name(symbol):
    try:
        r   = requests.get("https://histock.tw/stock/rank.aspx?p=all",
                           headers={"User-Agent":"Mozilla/5.0"}, timeout=5)
        dfs = pd.read_html(r.text); df = dfs[0]
        cc  = [c for c in df.columns if "代號" in str(c)][0]
        cn  = [c for c in df.columns if "股票" in str(c) or "名稱" in str(c)][0]
        for _, row in df.iterrows():
            code = "".join(c for c in str(row[cc]) if c.isdigit())
            if code == symbol: return str(row[cn])
    except: pass
    return symbol

def _sar(high, low, af0=0.02, af_max=0.2):
    n=len(high); sar=np.zeros(n); trend=np.ones(n)
    ep=np.zeros(n); af=np.full(n,af0); sar[0]=low[0]; ep[0]=high[0]
    for i in range(1,n):
        sar[i]=sar[i-1]+af[i-1]*(ep[i-1]-sar[i-1])
        if trend[i-1]==1:
            if low[i]<sar[i]: trend[i]=-1;sar[i]=ep[i-1];ep[i]=low[i];af[i]=af0
            else:
                trend[i]=1
                if high[i]>ep[i-1]: ep[i]=high[i];af[i]=min(af[i-1]+af0,af_max)
                else: ep[i]=ep[i-1];af[i]=af[i-1]
                sar[i]=min(sar[i],low[i-1])
                if i>1: sar[i]=min(sar[i],low[i-2])
        else:
            if high[i]>sar[i]: trend[i]=1;sar[i]=ep[i-1];ep[i]=high[i];af[i]=af0
            else:
                trend[i]=-1
                if low[i]<ep[i-1]: ep[i]=low[i];af[i]=min(af[i-1]+af0,af_max)
                else: ep[i]=ep[i-1];af[i]=af[i-1]
                sar[i]=max(sar[i],high[i-1])
                if i>1: sar[i]=max(sar[i],high[i-2])
    return sar

def add_ind(df):
    if df is None or df.empty: return df
    n=len(df)
    df["SAR"]=_sar(df["High"].values,df["Low"].values) if n>5 else np.nan
    for p in [5,10,20,60,120]:
        df[f"MA{p}"]=df["Close"].rolling(p).mean() if n>=p else np.nan
    h9=df["High"].rolling(9).max(); l9=df["Low"].rolling(9).min()
    rsv=((df["Close"]-l9)/(h9-l9)*100).fillna(50)
    k,d=[50.0],[50.0]
    for v in rsv: k.append(k[-1]*2/3+v/3); d.append(d[-1]*2/3+k[-1]/3)
    df["K"]=k[1:]; df["D"]=d[1:]
    e12=df["Close"].ewm(span=12,adjust=False).mean()
    e26=df["Close"].ewm(span=26,adjust=False).mean()
    df["DIF"]=e12-e26; df["MACD_SIG"]=df["DIF"].ewm(span=9,adjust=False).mean()
    df["MACD_HIST"]=df["DIF"]-df["MACD_SIG"]
    df["TR"]=np.maximum(df["High"]-df["Low"],np.abs(df["High"]-df["Close"].shift(1)))
    df["ATR"]=df["TR"].rolling(14).mean()
    df["VOL_MA5"]=df["Volume"].rolling(5).mean()
    df["BB_MID"]=df["Close"].rolling(20).mean()
    std=df["Close"].rolling(20).std()
    df["BB_UP"]=df["BB_MID"]+2*std; df["BB_LO"]=df["BB_MID"]-2*std
    df["BB_PCT"]=(df["Close"]-df["BB_LO"])/(df["BB_UP"]-df["BB_LO"])
    return df

def wave_label(df):
    if df is None or len(df)<15: return "N/A"
    c=df["Close"].iloc[-1]
    m20=df["MA20"].iloc[-1] if not pd.isna(df["MA20"].iloc[-1]) else c
    m60=df["MA60"].iloc[-1] if not pd.isna(df["MA60"].iloc[-1]) else c
    k=df["K"].iloc[-1]; pk=df["K"].iloc[-2]
    h=df["MACD_HIST"].iloc[-1]; ph=df["MACD_HIST"].iloc[-2]
    if c>=m60:
        if c>m20:
            if h>0 and h>ph: return "3-5" if k>80 else "3-3"
            if h>0: return "3-a"
            return "3-1"
        else:
            if k<20: return "4-c"
            if k<pk: return "4-a"
            return "4-b"
    else:
        if c<m20: return "C-5" if k<20 else "C-3"
        return "B-c" if k>80 else "B-a"

def sop_check(df):
    empty={"signal":None,"hard_pass":False,"cond_kd":False,"kd_label":"N/A",
           "cond_macd":False,"macd_label":"N/A","cond_sar":False,"sar_label":"N/A",
           "cond_vol":False,"vol_ratio":0,"wave_label":"N/A","wave_hint":None}
    if df is None or len(df)<30: return empty
    t=df.iloc[-1]; p=df.iloc[-2]
    kd_cross=(p["K"]<p["D"]) and (t["K"]>t["D"])
    kd_bull=t["K"]>t["D"]
    cond_kd=kd_bull or kd_cross
    kd_label="今日金叉✨" if kd_cross else ("多頭排列" if kd_bull else "空方排列")
    cond_macd=t["MACD_HIST"]>0
    macd_label="今日翻紅" if (p["MACD_HIST"]<=0 and t["MACD_HIST"]>0) else \
               ("紅柱延伸" if cond_macd else "綠柱整理")
    cond_sar=float(t["Close"])>float(t["SAR"])
    sar_label="多方支撐" if cond_sar else "空方壓力"
    hard_pass=cond_kd and cond_macd and cond_sar
    vma=t["VOL_MA5"] if t["VOL_MA5"]>0 else 1
    vol_ratio=round(float(t["Volume"])/float(vma),1)
    cond_vol=vol_ratio>=1.5
    wlabel=wave_label(df)
    wave_hint={"3-3":"🌊 3-3主升急漲","3-5":"🏔️ 3-5噴出末段",
               "3-1":"🌱 3-1初升啟動","4-c":"🪤 4-c修正末端"}.get(wlabel)
    signal=None
    if hard_pass: signal="SELL" if wlabel in ("3-5","B-c","C-3") else "BUY"
    return {"signal":signal,"hard_pass":hard_pass,
            "cond_kd":cond_kd,"kd_label":kd_label,
            "cond_macd":cond_macd,"macd_label":macd_label,
            "cond_sar":cond_sar,"sar_label":sar_label,
            "cond_vol":cond_vol,"vol_ratio":vol_ratio,
            "wave_label":wlabel,"wave_hint":wave_hint}

def fibonacci(df):
    w=min(len(df),120); hi=df["High"].iloc[-w:].max(); lo=df["Low"].iloc[-w:].min(); d=hi-lo
    return {"0.236":hi-d*0.236,"0.382":hi-d*0.382,"0.500":hi-d*0.5,"0.618":hi-d*0.618,
            "high":hi,"low":lo}

def push_tg(token,chat_id,signal,name,code,price,sop,buy_agg,buy_con,stop):
    if not token or not chat_id: return False
    e="🚀" if signal=="BUY" else "⚠️"
    a="BUY — SOP三線觸發！" if signal=="BUY" else "SELL — 高檔出場！"
    pl=(f"🦁 激進:<b>{buy_agg:.2f}</b> 🐢 保守:<b>{buy_con:.2f}</b> 🛑 停損:<b>{stop:.2f}</b>"
        if signal=="BUY" else f"⚡ 出場:<b>{price:.2f}</b> 🛑 停損:<b>{stop:.2f}</b>")
    soft=("" if not sop["cond_vol"] else f"\n💡量比{sop['vol_ratio']}x≥1.5")+\
         ("" if not sop["wave_hint"] else f"\n{sop['wave_hint']}")
    msg=(f"{e}<b>AI Stock Bot SOP</b>{e}\n<b>{name}（{code}）</b> 💰{price:.2f}\n"
         f"━━━━━━━━━━━\n<b>{a}</b>\n✅KD:{sop['kd_label']}\n"
         f"✅MACD:{sop['macd_label']}\n✅SAR:{sop['sar_label']}{soft}\n"
         f"━━━━━━━━━━━\n{pl}\n<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>")
    try:
        r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id":chat_id,"text":msg,"parse_mode":"HTML"},timeout=8)
        return r.status_code==200
    except: return False

def wchip(lbl):
    c="wbull" if lbl.startswith(("3","4")) else "wbear" if lbl.startswith(("C","B")) else "wneut"
    return f"<span class='wchip {c}'>{lbl}</span>"

def _v(row,key,fb=np.nan):
    v=row.get(key,fb); return fb if pd.isna(v) else v

def get_quick_price(code):
    """快速取得現價"""
    for sfx in [".TW",".TWO"]:
        try:
            df=yf.Ticker(code+sfx).history(period="5d")
            if not df.empty: return float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2])
        except: pass
    return None, None

# ════════════════════════════════════════
# TAB 1：個股分析
# ════════════════════════════════════════
with tab_ana:
    c1,c2,c3=st.columns([3,1,2])
    with c1: si=st.text_input("","2330",placeholder="輸入股票代號，如 2330",
                               label_visibility="collapsed",key="ana_in")
    with c2: run_btn=st.button("🚀 分析",type="primary",use_container_width=True)
    with c3: add_wl=st.button("➕ 加入觀察名單",use_container_width=True,key="ana_wl")

    if add_wl and si:
        cc2=si.strip().replace(".TW","").replace(".TWO","")
        nm2=fetch_name(cc2)
        db.add_to_watchlist(user["username"],cc2,nm2)
        st.success(f"✅ {nm2}（{cc2}）已加入觀察名單")

    if run_btn:
        cc=si.strip().replace(".TW","").replace(".TWO","")
        with st.spinner(f"正在載入 {cc} 所有數據..."):
            df_d,df_60,df_30,cc=fetch_stock(cc)
            nm=fetch_name(cc)
        if df_d is None or len(df_d)<10:
            st.error("❌ 找不到資料，請確認代號")
            st.stop()

        df_d=add_ind(df_d)
        df_60=add_ind(df_60) if df_60 is not None and not df_60.empty else None
        df_30=add_ind(df_30) if df_30 is not None and not df_30.empty else None

        t=df_d.iloc[-1]; p=df_d.iloc[-2]
        sop=sop_check(df_d); fib=fibonacci(df_d)
        atr=_v(t,"ATR",t["Close"]*0.02)
        w_d=wave_label(df_d)
        w_60=wave_label(df_60) if df_60 is not None else "N/A"
        w_30=wave_label(df_30) if df_30 is not None else "N/A"
        ma5=_v(t,"MA5",fib["0.236"]); ma20=_v(t,"MA20",fib["0.382"])
        buy_agg=max(ma5,fib["0.236"]); buy_con=max(ma20,fib["0.382"])
        stop=max(t["Close"]-atr*2,fib["0.618"])
        vma5=t["VOL_MA5"] if t["VOL_MA5"]>0 else 1
        vol_r=round(t["Volume"]/vma5,1)
        diff=t["Close"]-p["Close"]; dp=diff/p["Close"]*100
        pcls="price-up" if diff>0 else "price-down" if diff<0 else "price-flat"
        pct_cls="pct-up" if diff>0 else "pct-down"
        ps="+" if diff>0 else ""

        # ── 標題 ──
        st.markdown(f"""
        <div style='margin-bottom:20px'>
            <span style='font-size:13px;color:#64748b;letter-spacing:1px;text-transform:uppercase'>股票代號 {cc}</span>
            <div style='display:flex;align-items:baseline;gap:16px;margin-top:4px'>
                <span style='font-size:26px;font-weight:800;color:#f8fafc'>{nm}</span>
                <span class='{pcls}'>{t['Close']:.2f}</span>
                <span class='{pct_cls}'>{ps}{diff:.2f} ({ps}{dp:.2f}%)</span>
            </div>
            <div style='color:#64748b;font-size:13px;margin-top:4px'>
                成交量 {int(t['Volume']/1000):,} 張 &nbsp;·&nbsp; 量比 {vol_r}x &nbsp;·&nbsp;
                波浪 {wchip(w_d)}{wchip(w_60)}{wchip(w_30)}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 目標價顯示
        my_tgt=db.get_user_target(user["username"],cc)
        if my_tgt:
            tc=db.check_target_reached(t["Close"],my_tgt["target_price"])
            gap_pct=tc["gap_pct"]
            prog=min(100,max(0,100-gap_pct)) if gap_pct>0 else 100
            color="reached" if gap_pct<=0 else "close" if gap_pct<=5 else ""
            st.markdown(f"""
            <div class='tgt-card {color}'>
                <span style='font-size:12px;color:#64748b;letter-spacing:1px'>🎯 你的目標價</span>
                <div style='display:flex;align-items:center;gap:20px;margin-top:6px'>
                    <span class='tgt-price'>{my_tgt['target_price']:.2f}</span>
                    <span class='tgt-status' style='color:{"#4ade80" if gap_pct<=0 else "#fbbf24" if gap_pct<=5 else "#38bdf8"}'>{tc['status']}</span>
                </div>
                <div class='tgt-progress-bg'>
                    <div class='tgt-progress-fill {color}' style='width:{prog}%'></div>
                </div>
                <span style='font-size:12px;color:#64748b'>{tc['desc']}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin:0'></div>", unsafe_allow_html=True)

        # ── SOP ──
        signal=sop["signal"]
        if signal in ("BUY","SELL"):
            css="sop-buy" if signal=="BUY" else "sop-sell"
            atxt="🚀 BUY — SOP 三線全達，最佳進場！" if signal=="BUY" else "⚠️ SELL — 高檔出場訊號！"
            hints=""
            if sop["cond_vol"]:  hints+=f"<span>💡 量比{vol_r}x（≥1.5加分）</span> &nbsp;"
            if sop["wave_hint"]: hints+=f"<span>{sop['wave_hint']}</span>"
            phtml=(f"🦁 激進 <b>{buy_agg:.2f}</b> &nbsp;｜&nbsp; 🐢 保守 <b>{buy_con:.2f}</b> &nbsp;｜&nbsp; 🛑 停損 <b>{stop:.2f}</b>"
                   if signal=="BUY"
                   else f"⚡ 建議出場 <b>{t['Close']:.2f}</b> &nbsp;｜&nbsp; 🛑 停損 <b>{stop:.2f}</b>")
            st.markdown(f"""<div class='{css}'>
                <div class='sop-title'>{atxt}</div>
                <div class='sop-sub'>✅ KD：{sop['kd_label']} &nbsp;&nbsp; ✅ MACD：{sop['macd_label']} &nbsp;&nbsp; ✅ SAR：{sop['sar_label']}</div>
                {f'<div style="margin-top:8px;font-size:13px;color:#fef3c7">{hints}</div>' if hints else ''}
                <div style='margin-top:14px;font-size:15px;font-weight:600'>{phtml}</div>
            </div>""", unsafe_allow_html=True)
            _,_,tg_col=st.columns(3)
            with tg_col:
                if st.button("📲 推播到 Telegram",type="primary",use_container_width=True):
                    ok=push_tg(tg_token,tg_chat,signal,nm,cc,t["Close"],sop,buy_agg,buy_con,stop)
                    st.success("✅ 推播成功！") if ok else st.warning("⚠️ 請先填入 Token / Chat ID")
        else:
            hc=sum([sop["cond_kd"],sop["cond_macd"],sop["cond_sar"]])
            items="".join([f"<div class='cond-row'><span class='{'pass' if ok else 'fail'}'>{'✅' if ok else '❌'} {lb}</span></div>"
                           for ok,lb in [(sop["cond_kd"],f"KD：{sop['kd_label']}"),
                                         (sop["cond_macd"],f"MACD：{sop['macd_label']}"),
                                         (sop["cond_sar"],f"SAR：{sop['sar_label']}")]])
            vol_txt=(f"<span class='hint'>💡 量比{vol_r}x ≥1.5 ✔</span>"
                     if sop["cond_vol"] else f"<span style='color:#475569'>💡 量比{vol_r}x（未達1.5）</span>")
            wave_txt=(f"<span class='hint'>{sop['wave_hint']} ✔</span>"
                      if sop["wave_hint"] else f"<span style='color:#475569'>🌊 {w_d}（非提示範圍）</span>")
            st.markdown(f"""<div class='watch-b'>
                <span style='color:#94a3b8;font-weight:600'>👀 SOP 觀察中</span>
                <span style='color:#475569;font-size:13px;margin-left:8px'>硬條件 {hc}/3 達標</span>
                <div style='margin-top:10px'>{items}</div>
                <div style='margin-top:10px;font-size:13px'>{vol_txt} &nbsp; {wave_txt}</div>
            </div>""", unsafe_allow_html=True)

        # ── 指標區 ──
        st.markdown("---")
        c_w1,c_w2,c_w3=st.columns(3)
        c_w1.info(f"📅 日線波浪\n\n## {w_d}")
        c_w2.warning(f"⏰ 60分鐘\n\n## {w_60}")
        c_w3.error(f"⚡ 30分鐘\n\n## {w_30}")

        cd=df_d[["Close","MA5","MA20","MA60"]].iloc[-60:].dropna()
        if not cd.empty:
            st.markdown("#### 📈 近60日 K線走勢 + 均線")
            st.line_chart(cd,color=["#38bdf8","#f97316","#4ade80","#a78bfa"])
            st.caption("藍:收盤 ｜ 橙:5MA ｜ 綠:20MA ｜ 紫:60MA")

        ic1,ic2=st.columns(2)
        with ic1:
            st.markdown("#### 📐 費波那契支撐壓力")
            prc=t["Close"]
            for ratio,key in [("0.236","0.236"),("0.382","0.382"),("0.500","0.500"),("0.618","0.618")]:
                lvl=fib[key]; ok=prc>lvl
                color="#4ade80" if ok else "#f87171"
                icon="✅" if ok else "⚠️"
                st.markdown(f"""<div class='card-sm'>
                    <span style='color:#64748b;font-size:12px'>{ratio}</span>
                    <span style='float:right;font-weight:700;color:{color}'>{icon} {lvl:.2f}</span>
                </div>""", unsafe_allow_html=True)
        with ic2:
            st.markdown("#### 🎯 布林通道")
            bb=_v(t,"BB_PCT",0.5)
            bm="衝出上軌（賣訊）" if bb>1 else "跌破下軌（買訊）" if bb<0 else "區間震盪"
            bb_color="#f87171" if bb>1 else "#4ade80" if bb<0 else "#38bdf8"
            st.markdown(f"""<div class='card-sm' style='text-align:center'>
                <div style='font-size:13px;color:#64748b'>布林通道位置</div>
                <div style='font-size:20px;font-weight:700;color:{bb_color};margin:8px 0'>{bm}</div>
                <div style='background:#1e2a3a;border-radius:99px;height:10px;overflow:hidden'>
                    <div style='height:100%;width:{min(max(bb*100,0),100):.0f}%;background:linear-gradient(90deg,#4ade80,#f97316,#f87171);border-radius:99px'></div>
                </div>
                <div style='font-size:12px;color:#475569;margin-top:6px'>{bb*100:.0f}% 位置（0%=下軌 100%=上軌）</div>
            </div>""", unsafe_allow_html=True)
            st.markdown(f"""<div class='card-sm'>
                <div style='display:flex;justify-content:space-between;font-size:13px'>
                    <span style='color:#64748b'>KD</span><span style='color:#e2e8f0'>K={t['K']:.1f} D={t['D']:.1f} → {sop['kd_label']}</span>
                </div>
            </div>""", unsafe_allow_html=True)
            st.markdown(f"""<div class='card-sm'>
                <div style='display:flex;justify-content:space-between;font-size:13px'>
                    <span style='color:#64748b'>MACD Hist</span><span style='color:#e2e8f0'>{t['MACD_HIST']:+.4f} → {sop['macd_label']}</span>
                </div>
            </div>""", unsafe_allow_html=True)
            st.markdown(f"""<div class='card-sm'>
                <div style='display:flex;justify-content:space-between;font-size:13px'>
                    <span style='color:#64748b'>SAR</span><span style='color:#e2e8f0'>{float(t["SAR"]):.2f} → {sop['sar_label']}</span>
                </div>
            </div>""", unsafe_allow_html=True)

        # ── 目標價預估 ──
        st.markdown("---")
        st.markdown("#### 🎯 AI 目標價預估")
        tc1,tc2,tc3=st.columns(3)
        for col,mult,lb,color in [(tc1,1.05,"短線 +5%","#22d3ee"),(tc2,1.10,"波段 +10%","#a78bfa"),(tc3,1.20,"長線 +20%","#4ade80")]:
            tp=t["Close"]*mult; days=max(5,int((tp-t["Close"])/max(atr*0.4,0.01)*2.5))
            col.markdown(f"""<div class='card-sm' style='text-align:center;border-color:#2d3a52'>
                <div style='font-size:12px;color:#64748b'>{lb}</div>
                <div style='font-size:24px;font-weight:800;color:{color};margin:6px 0'>{tp:.2f}</div>
                <div style='font-size:12px;color:#475569'>約 {days} 個交易日</div>
            </div>""", unsafe_allow_html=True)

        # ── AI 報告書 ──
        st.markdown("---")
        st.markdown("## 🤖 AI 深度個股分析報告書")
        st.caption(f"整合技術面・基本面・波浪理論・美股連動・最新新聞 ｜ Groq Llama 3.3 70B 免費生成")

        if not AI_READY:
            st.warning("⚠️ `ai_report.py` 尚未上傳到 GitHub repo，請先上傳")
        elif not groq_key:
            st.markdown("""
            <div class='card' style='border-color:#d97706;background:#1c1100'>
                <div style='font-size:16px;font-weight:700;color:#fbbf24'>⚠️ 需要設定 Groq API Key 才能生成報告</div>
                <div style='color:#92400e;font-size:14px;margin-top:8px'>
                    1. 前往 <b>console.groq.com</b> 免費註冊<br>
                    2. 左側 API Keys → Create API Key<br>
                    3. 複製 gsk_xxx 開頭的 Key<br>
                    4. Streamlit Cloud → Settings → Secrets → 加入：<br>
                    <code style='background:#1e2a3a;padding:4px 8px;border-radius:4px;color:#38bdf8'>GROQ_API_KEY = "gsk_你的key"</code>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            if st.button("📋 生成完整分析報告書（免費）",type="primary",use_container_width=True,key="gen_report"):
                tgt_entry    = db.get_user_target(user["username"],cc)
                my_tgt_price = tgt_entry["target_price"] if tgt_entry else None
                with st.spinner("🤖 AI 正在分析所有數據，生成完整報告書...（30-60 秒）"):
                    result=ai_report.generate_full_report(cc,nm,my_tgt_price)
                if result.get("error"):
                    st.error(result["error"])
                else:
                    fund=result["fundamental"]; us=result["us_market"]; news_list=result["news"]
                    # 摘要卡片
                    mc1,mc2,mc3,mc4=st.columns(4)
                    mc1.metric("SOP訊號",   result["sop"].get("signal","N/A"))
                    mc2.metric("波浪位置",   result["wave_title"].split()[0] if result["wave_title"] else "N/A")
                    pe_val=fund.get("pe")
                    mc3.metric("本益比P/E",  f"{pe_val:.1f}" if pe_val else "N/A")
                    mc4.metric("法人目標價",  str(fund.get("target_mean","N/A")))
                    # 新聞
                    if news_list:
                        st.markdown("#### 📰 最新相關新聞")
                        for n_item in news_list[:5]:
                            badge_cls=("news-bull" if "利多" in n_item["sentiment"]
                                       else "news-bear" if "利空" in n_item["sentiment"]
                                       else "news-neut")
                            st.markdown(f"""<div class='card-sm' style='display:flex;align-items:center;gap:12px'>
                                <span class='{badge_cls}'>{n_item['sentiment'].split()[0]}</span>
                                <span class='news-title'><a href='{n_item["link"]}' target='_blank' style='color:#cbd5e1;text-decoration:none'>{n_item['title']}</a></span>
                                <span class='news-meta' style='margin-left:auto;white-space:nowrap'>{n_item['pub']}</span>
                            </div>""", unsafe_allow_html=True)
                    # 美股
                    if us:
                        st.markdown("#### 🌏 美股即時連動")
                        us_cols=st.columns(len(us))
                        for idx,(tk,uv) in enumerate(us.items()):
                            icon="🔺" if uv["pct"]>0 else "💚"
                            us_cols[idx].metric(uv["name"],f"{uv['price']}",f"{icon}{uv['pct']:+.2f}%")
                    # 完整報告
                    st.markdown(f"""<div class='report-wrap'>{result['report_md']}</div>""",
                                unsafe_allow_html=True)

        st.caption(f"更新：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ AI Stock Bot V3.0")

# ════════════════════════════════════════
# TAB 2：目標價（重新設計，含詳細分析）
# ════════════════════════════════════════
with tab_tgt:
    st.markdown("### 🎯 目標價投資計畫")
    st.caption("設定你的目標價，系統每日自動追蹤進度並發送詳細達標分析")

    # 新增目標價
    with st.container(border=True):
        st.markdown("#### ➕ 新增 / 更新目標價")
        t1c,t2c,t3c,t4c=st.columns([2,1.5,2,1])
        with t1c: tc_code  = st.text_input("股票代號",placeholder="如 2330",key="tc",label_visibility="collapsed")
        with t2c: tc_price = st.number_input("目標價格",min_value=0.01,step=0.5,format="%.2f",key="tp",label_visibility="collapsed")
        with t3c: tc_note  = st.text_input("投資備註",placeholder="如：法說會前布局",key="tn",label_visibility="collapsed")
        with t4c: tc_btn   = st.button("💾 儲存",type="primary",use_container_width=True,key="ts")
    if tc_btn and tc_code:
        code_in=tc_code.strip().replace(".TW","").replace(".TWO","")
        ok=db.set_target(user["username"],user["display_name"],code_in,tc_price,tc_note)
        if ok:
            st.success(f"✅ 已設定 {code_in} 目標價 {tc_price:.2f}")
            st.rerun()
        else:
            st.error("儲存失敗")

    st.markdown("---")
    my_tgts=db.get_user_all_targets(user["username"])

    if not my_tgts:
        st.markdown("""
        <div class='card' style='text-align:center;padding:40px'>
            <div style='font-size:40px'>🎯</div>
            <div style='font-size:18px;font-weight:700;color:#f8fafc;margin:12px 0'>尚無目標價</div>
            <div style='color:#64748b;font-size:14px'>設定目標價後，系統會每天追蹤進度<br>並在達標前發送詳細的達標條件分析報告</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"#### 📌 追蹤中：{len(my_tgts)} 支股票")
        for code,entry in my_tgts.items():
            nm_t=fetch_name(code)
            price_now,price_prev=get_quick_price(code)

            if price_now:
                gap      = entry["target_price"] - price_now
                gap_pct  = gap / price_now * 100
                reached  = price_now >= entry["target_price"]
                close    = 0 < gap_pct <= 5
                prog     = min(100, max(0, price_now / entry["target_price"] * 100))
                day_pct  = (price_now - price_prev) / price_prev * 100 if price_prev else 0
                # 估算天數
                try:
                    df_tmp,_,_,_=fetch_stock(code)
                    df_tmp=add_ind(df_tmp)
                    atr_tmp=float(df_tmp["ATR"].iloc[-1]) if df_tmp is not None else price_now*0.02
                    est_days=max(5,int(gap/max(atr_tmp*0.4,0.01)*2.0)) if gap>0 else 0
                except: est_days=0
                card_cls="reached" if reached else "close" if close else ""
                status_color="#4ade80" if reached else "#fbbf24" if close else "#38bdf8"
                status_txt="✅ 已達目標！" if reached else f"🔥 即將達標！差 {gap_pct:.1f}%" if close else f"📈 推進中 {gap_pct:.1f}% 待突破"
            else:
                prog=50; card_cls=""; status_color="#64748b"; status_txt="無法取得現價"
                gap_pct=0; reached=False; close=False; est_days=0; day_pct=0

            with st.expander(f"{'✅' if reached else '🔥' if close else '📌'} {nm_t}（{code}） — 目標 {entry['target_price']:.2f}", expanded=True):
                col_l,col_r=st.columns([2,1])
                with col_l:
                    st.markdown(f"""
                    <div class='tgt-card {card_cls}'>
                        <div style='display:flex;justify-content:space-between;align-items:flex-start'>
                            <div>
                                <span class='tgt-name'>{nm_t}</span>
                                <span class='tgt-code'>{code}</span>
                            </div>
                            <div style='text-align:right'>
                                <div style='font-size:11px;color:#64748b'>現價</div>
                                <div style='font-size:20px;font-weight:800;color:#f8fafc'>{price_now:.2f if price_now else 'N/A'}</div>
                                <div style='font-size:12px;color:{"#4ade80" if day_pct>0 else "#f87171"}'>{f"+{day_pct:.2f}%" if day_pct>0 else f"{day_pct:.2f}%"}</div>
                            </div>
                        </div>
                        <div style='margin-top:16px'>
                            <div style='display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-bottom:6px'>
                                <span>進度</span>
                                <span style='font-weight:700;color:{status_color}'>{status_txt}</span>
                            </div>
                            <div class='tgt-progress-bg'>
                                <div class='tgt-progress-fill {card_cls}' style='width:{prog:.0f}%'></div>
                            </div>
                            <div style='display:flex;justify-content:space-between;font-size:11px;color:#475569;margin-top:4px'>
                                <span>現價 {price_now:.2f if price_now else '-'}</span>
                                <span>{prog:.0f}%</span>
                                <span>目標 {entry['target_price']:.2f}</span>
                            </div>
                        </div>
                        {f'<div style="margin-top:12px;font-size:12px;color:#64748b;background:#0a0e1a;padding:8px 12px;border-radius:8px">📝 {entry["note"]}</div>' if entry.get("note") else ''}
                        <div style='margin-top:10px;font-size:11px;color:#475569'>設定於 {entry.get("updated_at","—")}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_r:
                    st.markdown("**📊 關鍵數字**")
                    if price_now:
                        st.metric("目標價", f"{entry['target_price']:.2f}")
                        st.metric("現價",   f"{price_now:.2f}",   f"{'+' if day_pct>0 else ''}{day_pct:.2f}%")
                        st.metric("差距",   f"{abs(gap):.2f} 元",  f"{abs(gap_pct):.1f}%")
                        if est_days > 0:
                            eta = (datetime.now() + timedelta(days=est_days)).strftime("%m/%d")
                            st.metric("預估達標", f"~{est_days}天", f"約 {eta}")
                    if st.button("🗑️ 刪除",key=f"dt_{code}",use_container_width=True):
                        db.delete_target(user["username"],code)
                        st.success("已刪除"); st.rerun()

                # 達標條件分析
                if not reached and price_now:
                    st.markdown("**🔍 達標條件分析**")
                    try:
                        df_tmp,_,_,_=fetch_stock(code)
                        if df_tmp is not None:
                            df_tmp=add_ind(df_tmp); t_tmp=df_tmp.iloc[-1]
                            hi=df_tmp["High"].iloc[-120:].max(); lo=df_tmp["Low"].iloc[-120:].min(); d_=hi-lo
                            conds=[
                                (float(t_tmp["Close"])>float(t_tmp.get("MA60",t_tmp["Close"])), f"站上季線 {t_tmp.get('MA60',0):.2f}"),
                                (float(t_tmp["MACD_HIST"])>0, "MACD 翻紅，動能轉正"),
                                (float(t_tmp["K"])>float(t_tmp["D"]), "KD 多頭排列"),
                                (float(t_tmp["Volume"])>float(t_tmp["VOL_MA5"])*1.2, "成交量放大，主力進場"),
                                (float(t_tmp["Close"])>float(t_tmp["SAR"]), "突破 SAR 停損線"),
                            ]
                            met=sum(1 for ok,_ in conds if ok)
                            st.markdown(f"<div style='font-size:13px;color:#64748b;margin-bottom:8px'>已達成 {met}/{len(conds)} 個條件</div>", unsafe_allow_html=True)
                            for ok_c,txt in conds:
                                icon="✅" if ok_c else "❌"
                                color="#4ade80" if ok_c else "#f87171"
                                st.markdown(f"<div class='card-sm'><span style='color:{color}'>{icon}</span> <span style='font-size:13px;color:#94a3b8'>{txt}</span></div>", unsafe_allow_html=True)
                            # 途中壓力
                            resistances=[]
                            for r,lbl in [(hi-d_*0.236,"費波0.236"),(hi-d_*0.382,"費波0.382"),
                                          (float(t_tmp.get("MA20",0)),"20日均線"),(float(t_tmp.get("MA60",0)),"60日均線")]:
                                if price_now < r < entry["target_price"] and r>0:
                                    resistances.append(f"{lbl} {r:.2f}")
                            if resistances:
                                st.markdown(f"""<div class='card-sm' style='border-color:#d97706'>
                                    <span style='font-size:12px;color:#fbbf24'>🚧 途中壓力位：</span>
                                    <span style='font-size:13px;color:#94a3b8'>{' → '.join(resistances)}</span>
                                </div>""", unsafe_allow_html=True)
                    except: pass

    # 管理員總覽
    if is_admin:
        st.markdown("---")
        with st.expander("👑 管理員：全用戶目標價總覽"):
            all_tgts=db.get_all_targets_admin()
            if not all_tgts:
                st.info("尚無任何用戶設定目標價")
            else:
                for code,entries in all_tgts.items():
                    nm_t=fetch_name(code)
                    st.markdown(f"**{nm_t}（{code}）— {len(entries)} 人設定**")
                    for e in entries:
                        dot="🔵" if e["username"]==user["username"] else "⚪"
                        st.markdown(f"{dot} **{e['display_name']}** 目標 {e['target_price']:.2f}｜{e.get('note','—')}｜{e.get('updated_at','—')}")
                    st.divider()

# ════════════════════════════════════════
# TAB 3：觀察名單
# ════════════════════════════════════════
with tab_wl:
    st.markdown("### 📋 我的觀察名單")
    with st.container(border=True):
        a1,a2,a3=st.columns([2,2,1])
        with a1: nc=st.text_input("代號",placeholder="如 2330",key="wl_c",label_visibility="collapsed")
        with a2: nn=st.text_input("名稱（空白自動查詢）",placeholder="如 台積電",key="wl_n",label_visibility="collapsed")
        with a3: ab=st.button("➕ 新增",type="primary",use_container_width=True,key="wl_ab")
    if ab and nc:
        code_in=nc.strip().replace(".TW","").replace(".TWO","")
        nm_in=nn.strip() or fetch_name(code_in)
        db.add_to_watchlist(user["username"],code_in,nm_in)
        st.success(f"✅ 已新增 {nm_in}（{code_in}）"); st.rerun()

    st.markdown("---")
    my_codes=db.get_user_watchlist_codes(user["username"])
    st.markdown(f"#### 追蹤中：{len(my_codes)} 支")
    if not my_codes:
        st.markdown("""
        <div class='card' style='text-align:center;padding:32px'>
            <div style='font-size:36px'>📋</div>
            <div style='color:#f8fafc;font-weight:700;margin:10px 0'>尚無追蹤股票</div>
            <div style='color:#64748b;font-size:14px'>新增股票後，Cloud Bot 每天自動推送個人報告到你的 Telegram</div>
        </div>""", unsafe_allow_html=True)
    else:
        wl_map=db.get_global_watchlist()
        for code in my_codes:
            nm_w=wl_map.get(code,code)
            my_tgt_e=db.get_user_target(user["username"],code)
            tgt_txt=f"🎯 {my_tgt_e['target_price']:.2f}" if my_tgt_e else "未設定目標價"
            price_n,_=get_quick_price(code)
            price_txt=f"{price_n:.2f}" if price_n else "—"
            cl1,cl2,cl3,cl4,cl5=st.columns([1,2,1.5,2,1])
            cl1.markdown(f"<span style='font-family:DM Mono;font-weight:700;color:#38bdf8'>{code}</span>",unsafe_allow_html=True)
            cl2.write(nm_w)
            cl3.write(price_txt)
            cl4.caption(tgt_txt)
            with cl5:
                if st.button("🗑️",key=f"rwl_{code}",use_container_width=True):
                    db.remove_from_watchlist(user["username"],code)
                    st.success(f"已移除 {code}"); st.rerun()

    st.markdown("---")
    st.markdown("""
    #### 📅 每日自動推播時間表
    | 時間 | 內容 |
    |------|------|
    | 09:30 | 🌅 開盤掃描 + 量能偵測 |
    | 10:20 / 12:00 | 🔔 盤中 SOP 狀態 |
    | 13:36 | 🌇 收盤確認 + 明日建議 |
    | 18:40 | 🌙 **個人深度報告**（波浪＋多因子＋目標價＋美股＋新聞）|
    | 即時 | ⚡ SOP 三線觸發立即推播（冷卻 4 小時）|
    """)

# ════════════════════════════════════════
# TAB 4：帳號設定
# ════════════════════════════════════════
with tab_acc:
    st.markdown("### ⚙️ 帳號設定")
    col_l,col_r=st.columns(2)
    with col_l:
        with st.container(border=True):
            st.markdown("#### 🔑 修改密碼")
            op  = st.text_input("舊密碼",type="password",key="op")
            np1 = st.text_input("新密碼",type="password",key="np1")
            np2 = st.text_input("確認新密碼",type="password",key="np2")
            if st.button("更新密碼",type="primary"):
                if np1!=np2: st.error("❌ 兩次密碼不一致")
                else:
                    ok,msg=db.change_password(user["username"],op,np1)
                    st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")
    with col_r:
        with st.container(border=True):
            st.markdown("#### 📲 Telegram Chat ID")
            st.caption("設定後 Cloud Bot 每天自動推送個人報告")
            cur_id=user.get("telegram_chat_id","")
            new_id=st.text_input("Chat ID",value=cur_id,placeholder="從 @userinfobot 取得")
            if st.button("💾 儲存",type="primary",key="save_tg_acc"):
                db.update_telegram(user["username"],new_id)
                st.session_state.user["telegram_chat_id"]=new_id
                st.success("✅ 已儲存！")
    st.markdown("---")
    st.markdown("#### ℹ️ 帳號資訊")
    info=db.get_user(user["username"])
    ca,cb,cc_=st.columns(3)
    ca.metric("帳號",    user["username"])
    cb.metric("角色",    "管理員 👑" if is_admin else "一般用戶")
    cc_.metric("建立時間", info.get("created_at","—") if info else "—")

# ════════════════════════════════════════
# TAB 5：用戶管理（管理員）
# ════════════════════════════════════════
if is_admin and tab_admin:
    with tab_admin:
        st.markdown("### 👑 用戶管理")
        with st.container(border=True):
            st.markdown("#### ➕ 新增用戶")
            u1,u2,u3,u4,u5=st.columns([2,2,2,1.5,1])
            with u1: nu  = st.text_input("帳號",  placeholder="英文小寫",key="nu", label_visibility="collapsed")
            with u2: npw = st.text_input("密碼",  type="password",placeholder="至少4碼",key="npw",label_visibility="collapsed")
            with u3: nd  = st.text_input("顯示名稱",placeholder="如：小明",key="nd", label_visibility="collapsed")
            with u4: nr  = st.selectbox("角色",["user","admin"],key="nr",label_visibility="collapsed")
            with u5: nb  = st.button("➕",type="primary",use_container_width=True,key="nb")
            if nb:
                ok,msg=db.create_user(nu,npw,nd,nr)
                st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}"); st.rerun()
        st.markdown("---")
        all_users=db.get_all_users()
        st.markdown(f"#### 👥 用戶列表（{len(all_users)} 人）")
        for uname,uinfo in all_users.items():
            rbadge=("<span class='badge-admin'>👑 管理員</span>" if uinfo.get("role")=="admin"
                    else "<span class='badge-user'>👤 用戶</span>")
            tg_s="✅" if uinfo.get("telegram_chat_id") else "❌"
            wl_n=len(uinfo.get("watchlist",[])); tgt_n=len(db.get_user_all_targets(uname))
            with st.container(border=True):
                r1,r2,r3,r4=st.columns([3,2,2,1])
                with r1:
                    st.markdown(f"**{uinfo.get('display_name',uname)}** (@{uname}) {rbadge}",unsafe_allow_html=True)
                    st.caption(f"建立：{uinfo.get('created_at','—')}")
                with r2:
                    st.write(f"TG：{tg_s} ｜ 觀察：{wl_n}支 ｜ 目標：{tgt_n}支")
                with r3:
                    rpw=st.text_input("重設密碼",type="password",placeholder="新密碼",
                                      key=f"rpw_{uname}",label_visibility="collapsed")
                    if st.button("🔑 重設",key=f"rset_{uname}",use_container_width=True):
                        ok,msg=db.admin_reset_password(uname,rpw)
                        st.success(msg) if ok else st.error(msg)
                with r4:
                    if uname!=user["username"]:
                        if st.button("🗑️",key=f"du_{uname}",use_container_width=True):
                            ok,msg=db.delete_user(uname)
                            st.success(msg) if ok else st.error(msg); st.rerun()
                    else: st.caption("（自己）")
