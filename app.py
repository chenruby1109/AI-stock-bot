"""
AI-stock-bot V3.1 — 鮮明色彩 + 動畫 + session_state 修正
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timedelta
import gist_db as db

try:    import ai_report;  AI_READY = True
except: AI_READY = False
try:    import broker as bk; BROKER_READY = True
except: BROKER_READY = False
try:    import wave_chart as wc; WC_READY = True
except: WC_READY = False
try:    import global_market as gm; GM_READY = True
except: GM_READY = False

# ── API Keys ──
def _secret(key):
    try:    return st.secrets[key]
    except: return os.environ.get(key,"")

st.set_page_config(page_title="AI Stock Bot", page_icon="📈", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

*{ box-sizing:border-box; }
html,body,[class*="css"]{ font-family:'Outfit',sans-serif; background:#060b18; color:#f0f4ff; }
.stApp{ background:#060b18; }
.main .block-container{ padding:1.5rem 2.5rem; max-width:1400px; }

/* ── 背景動畫光暈 ── */
.stApp::before{
    content:''; position:fixed; top:-40%; left:-20%;
    width:700px; height:700px;
    background:radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%);
    animation: drift1 18s ease-in-out infinite; pointer-events:none; z-index:0;
}
.stApp::after{
    content:''; position:fixed; bottom:-30%; right:-10%;
    width:600px; height:600px;
    background:radial-gradient(circle, rgba(14,165,233,0.10) 0%, transparent 70%);
    animation: drift2 22s ease-in-out infinite; pointer-events:none; z-index:0;
}
@keyframes drift1{ 0%,100%{transform:translate(0,0)} 50%{transform:translate(80px,60px)} }
@keyframes drift2{ 0%,100%{transform:translate(0,0)} 50%{transform:translate(-60px,-40px)} }

/* ── SOP 橫幅 ── */
@keyframes pulse-buy  { 0%,100%{box-shadow:0 0 0 0 rgba(34,197,94,0.4)}  60%{box-shadow:0 0 0 18px rgba(34,197,94,0)} }
@keyframes pulse-sell { 0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,0.4)}  60%{box-shadow:0 0 0 18px rgba(239,68,68,0)} }
@keyframes shimmer{ 0%{background-position:-200% 0} 100%{background-position:200% 0} }
@keyframes fadeUp{ from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
@keyframes spin{ to{transform:rotate(360deg)} }

.sop-buy{
    background:linear-gradient(135deg,#022c22 0%,#064e3b 50%,#065f46 100%);
    border:2px solid #10b981; border-radius:18px; padding:24px 30px; margin:16px 0;
    animation:pulse-buy 2.5s ease-in-out infinite, fadeUp .5s ease both;
    position:relative; overflow:hidden;
}
.sop-buy::after{
    content:''; position:absolute; inset:0;
    background:linear-gradient(90deg,transparent,rgba(16,185,129,0.08),transparent);
    background-size:200% 100%;
    animation:shimmer 3s linear infinite;
}
.sop-sell{
    background:linear-gradient(135deg,#2d0a0a 0%,#450a0a 50%,#7f1d1d 100%);
    border:2px solid #ef4444; border-radius:18px; padding:24px 30px; margin:16px 0;
    animation:pulse-sell 2.5s ease-in-out infinite, fadeUp .5s ease both;
}
.sop-title{ font-size:22px; font-weight:900; letter-spacing:.5px; color:#fff; }
.sop-conds{ font-size:14px; margin-top:10px; color:rgba(255,255,255,0.85); line-height:2.2; }
.sop-price{ margin-top:14px; font-size:16px; font-weight:700; color:#fff; }

/* ── 觀察框 ── */
.watch-b{
    background:rgba(255,255,255,0.03); border:1px dashed rgba(255,255,255,0.15);
    border-radius:14px; padding:16px 22px; margin:12px 0; font-size:14px;
    animation:fadeUp .4s ease both;
}

/* ── 卡片 ── */
.card{
    background:rgba(255,255,255,0.04);
    border:1px solid rgba(255,255,255,0.09);
    border-radius:16px; padding:22px; margin-bottom:14px;
    backdrop-filter:blur(10px);
    transition:border-color .25s, transform .25s;
    animation:fadeUp .4s ease both;
}
.card:hover{ border-color:rgba(99,102,241,0.4); transform:translateY(-2px); }
.card-sm{
    background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
    border-radius:10px; padding:11px 16px; margin-bottom:8px;
    transition:border-color .2s;
}
.card-sm:hover{ border-color:rgba(14,165,233,0.35); }

/* ── 目標價卡片 ── */
.tgt-card{
    background:linear-gradient(145deg,rgba(14,165,233,0.08),rgba(99,102,241,0.06));
    border:1px solid rgba(14,165,233,0.25); border-radius:16px; padding:22px 26px;
    margin-bottom:14px; position:relative; overflow:hidden;
    animation:fadeUp .5s ease both;
    transition:border-color .25s, transform .25s;
}
.tgt-card:hover{ border-color:rgba(14,165,233,0.5); transform:translateY(-2px); }
.tgt-card::before{
    content:''; position:absolute; left:0; top:0; width:3px; height:100%;
    background:linear-gradient(180deg,#0ea5e9,#6366f1);
}
.tgt-card.reached{ border-color:rgba(34,197,94,0.4); }
.tgt-card.reached::before{ background:linear-gradient(180deg,#22c55e,#4ade80); }
.tgt-card.close{ border-color:rgba(251,191,36,0.4); }
.tgt-card.close::before{ background:linear-gradient(180deg,#fbbf24,#f59e0b); }

.tgt-progress-bg{
    background:rgba(255,255,255,0.08); border-radius:99px; height:8px;
    margin:14px 0; overflow:hidden;
}
.tgt-progress-fill{
    height:100%; border-radius:99px;
    background:linear-gradient(90deg,#0ea5e9,#6366f1);
    transition:width .8s cubic-bezier(.4,0,.2,1);
}
.tgt-progress-fill.reached{ background:linear-gradient(90deg,#22c55e,#4ade80); }
.tgt-progress-fill.close  { background:linear-gradient(90deg,#f59e0b,#fbbf24); }

/* ── 波浪 chip ── */
.wchip{
    display:inline-block; font-size:12px; font-weight:700;
    padding:3px 12px; border-radius:20px; margin-right:5px;
    font-family:'JetBrains Mono',monospace; letter-spacing:.5px;
    transition:transform .2s;
}
.wchip:hover{ transform:scale(1.08); }
.wbull{ background:rgba(34,197,94,0.15); color:#4ade80; border:1px solid rgba(34,197,94,0.35); }
.wbear{ background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.35); }
.wneut{ background:rgba(251,191,36,0.12); color:#fbbf24; border:1px solid rgba(251,191,36,0.3); }

/* ── 券商列 ── */
.broker-row{
    display:flex; align-items:center; justify-content:space-between;
    background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07);
    border-radius:9px; padding:9px 14px; margin-bottom:6px;
    transition:background .2s; animation:fadeUp .3s ease both;
}
.broker-row:hover{ background:rgba(255,255,255,0.07); }
.broker-name{ font-size:13px; color:#e2e8f0; font-weight:500; }
.broker-buy { color:#4ade80; font-weight:700; font-family:'JetBrains Mono'; font-size:13px; }
.broker-sell{ color:#f87171; font-weight:700; font-family:'JetBrains Mono'; font-size:13px; }

/* ── Metric 覆蓋 ── */
[data-testid="stMetric"]{
    background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.09);
    border-radius:14px; padding:16px 20px; transition:border-color .25s;
    animation:fadeUp .4s ease both;
}
[data-testid="stMetric"]:hover{ border-color:rgba(99,102,241,0.35); }
[data-testid="stMetricLabel"]{ color:#94a3b8 !important; font-size:12px !important; font-weight:600 !important; letter-spacing:.8px !important; text-transform:uppercase !important; }
[data-testid="stMetricValue"]{ color:#f8fafc !important; font-size:24px !important; font-weight:800 !important; }
[data-testid="stMetricDelta"]{ font-size:13px !important; font-weight:600 !important; }

/* ── 按鈕 ── */
.stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#0ea5e9,#6366f1) !important;
    color:#fff !important; border:none !important; border-radius:12px !important;
    font-weight:700 !important; font-size:15px !important;
    padding:10px 22px !important; letter-spacing:.3px !important;
    transition:opacity .2s, transform .15s !important;
    box-shadow:0 4px 20px rgba(99,102,241,0.3) !important;
}
.stButton>button[kind="primary"]:hover{
    opacity:.88 !important; transform:translateY(-1px) !important;
}
.stButton>button[kind="secondary"]{
    background:rgba(255,255,255,0.06) !important; color:#94a3b8 !important;
    border:1px solid rgba(255,255,255,0.12) !important; border-radius:12px !important;
}

/* ── Input ── */
.stTextInput>div>div>input, .stNumberInput>div>div>input{
    background:rgba(255,255,255,0.05) !important;
    border:1px solid rgba(255,255,255,0.12) !important;
    border-radius:10px !important; color:#f0f4ff !important;
}
.stSelectbox>div>div{
    background:rgba(255,255,255,0.05) !important;
    border:1px solid rgba(255,255,255,0.12) !important;
    border-radius:10px !important; color:#f0f4ff !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"]{
    background:#080d1a !important;
    border-right:1px solid rgba(255,255,255,0.07) !important;
}

/* ── Tab ── */
.stTabs [data-baseweb="tab-list"]{ background:transparent; border-bottom:1px solid rgba(255,255,255,0.1); }
.stTabs [data-baseweb="tab"]{ color:#64748b; font-weight:600; padding:12px 18px; }
.stTabs [aria-selected="true"]{ color:#38bdf8 !important; border-bottom:2px solid #38bdf8 !important; }

/* ── 價格 ── */
.price-up   { color:#34d399; font-weight:900; font-size:34px; letter-spacing:-1px; text-shadow:0 0 20px rgba(52,211,153,0.4); }
.price-down { color:#f87171; font-weight:900; font-size:34px; letter-spacing:-1px; text-shadow:0 0 20px rgba(248,113,113,0.4); }
.price-flat { color:#94a3b8; font-weight:900; font-size:34px; letter-spacing:-1px; }
.pct-up   { color:#34d399; font-size:15px; font-weight:700; }
.pct-down { color:#f87171; font-size:15px; font-weight:700; }

/* ── 報告書 ── */
.report-box{
    background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.1);
    border-radius:16px; padding:32px 36px; margin-top:20px;
    animation:fadeUp .5s ease both; line-height:1.9;
}
.report-box h2{ color:#38bdf8; font-size:20px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:10px; }
.report-box h3{ color:#a5b4fc; font-size:16px; margin-top:22px; }
.report-box p, .report-box li{ color:#cbd5e1; font-size:14px; }
.report-box strong{ color:#f0f4ff; }

/* ── badge ── */
.badge-admin{ background:rgba(14,165,233,0.2); color:#38bdf8; font-size:11px; padding:2px 8px; border-radius:5px; font-weight:700; border:1px solid rgba(14,165,233,0.3); }
.badge-user { background:rgba(99,102,241,0.15); color:#a78bfa; font-size:11px; padding:2px 8px; border-radius:5px; font-weight:700; border:1px solid rgba(99,102,241,0.25); }

/* ── 條件列 ── */
.pass{ color:#4ade80; font-weight:700; }
.fail{ color:#f87171; font-weight:700; }
.hint{ color:#fbbf24; font-weight:700; }
.cond-row{ font-size:14px; line-height:2.4; }

/* ── 進度條（Streamlit） ── */
.stProgress>div>div{ background:linear-gradient(90deg,#0ea5e9,#6366f1) !important; border-radius:99px !important; }

hr{ border-color:rgba(255,255,255,0.08) !important; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════
# Session State 初始化
# ════════════════════════════════════════
for k,v in [("user",None),("stock_data",None),("stock_code",""),
            ("stock_name",""),("report_result",None)]:
    if k not in st.session_state: st.session_state[k]=v

def logout():
    st.session_state.user=None; st.rerun()

# ════════════════════════════════════════
# 登入頁
# ════════════════════════════════════════
if st.session_state.user is None:
    _,mid,_=st.columns([1,1.2,1])
    with mid:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center;animation:fadeUp .6s ease both'>
            <div style='font-size:52px;margin-bottom:10px'>📈</div>
            <div style='font-size:30px;font-weight:900;color:#f0f4ff;letter-spacing:-1px'>AI Stock Bot</div>
            <div style='font-size:14px;color:#64748b;margin:8px 0 30px'>Professional Trading Intelligence</div>
        </div>
        """,unsafe_allow_html=True)
        with st.container(border=True):
            uname=st.text_input("帳號",placeholder="輸入帳號",key="li_u")
            upw  =st.text_input("密碼",type="password",placeholder="輸入密碼",key="li_p")
            if st.button("🔐 登入",type="primary",use_container_width=True):
                u=db.login(uname,upw)
                if u: st.session_state.user=u; st.rerun()
                else: st.error("❌ 帳號或密碼錯誤")
            st.caption("預設帳號：ruby / admin1234")
    st.stop()

user=st.session_state.user
is_admin=user.get("role")=="admin"
groq_key=_secret("GROQ_API_KEY")
tg_token_secret=_secret("TG_TOKEN")
tg_chat_secret =_secret("TG_CHAT_ID")

# ─── Telegram 推播（自動 fallback 到 Secrets）───
def send_tg(msg: str, chat_id: str=""):
    tok=tg_token_secret
    cid=chat_id or tg_chat_secret
    if not tok or not cid: return False
    try:
        r=requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                        json={"chat_id":cid,"text":msg,"parse_mode":"HTML"},timeout=8)
        return r.status_code==200
    except: return False

def push_sop(signal,name,code,price,sop,buy_agg,buy_con,stop,chat_id=""):
    e="🚀" if signal=="BUY" else "⚠️"
    a="BUY — SOP三線觸發！" if signal=="BUY" else "SELL — 高檔出場！"
    pl=(f"🦁 激進:<b>{buy_agg:.2f}</b> | 🐢 保守:<b>{buy_con:.2f}</b> | 🛑 停損:<b>{stop:.2f}</b>"
        if signal=="BUY" else f"⚡ 出場:<b>{price:.2f}</b> | 🛑 停損:<b>{stop:.2f}</b>")
    soft=("" if not sop.get("cond_vol") else f"\n💡量比{sop.get('vol_ratio',0)}x≥1.5")+\
         ("" if not sop.get("wave_hint") else f"\n{sop.get('wave_hint','')}")
    msg=(f"{e} <b>AI Stock Bot — SOP訊號</b> {e}\n"
         f"<b>{name}（{code}）</b> 💰{price:.2f}\n"
         f"━━━━━━━━━━━\n<b>{a}</b>\n"
         f"✅KD:{sop.get('kd_label','')}\n✅MACD:{sop.get('macd_label','')}\n✅SAR:{sop.get('sar_label','')}"
         f"{soft}\n━━━━━━━━━━━\n{pl}\n"
         f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>")
    return send_tg(msg, chat_id)

# ════════════════════════════════════════
# 側邊欄
# ════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div style='padding:14px 0 6px;animation:fadeUp .4s ease both'>
        <div style='font-size:17px;font-weight:800;color:#f0f4ff'>{user['display_name']}</div>
        <div style='font-size:12px;color:#64748b;margin-top:4px'>
            {"<span class='badge-admin'>👑 管理員</span>" if is_admin else "<span class='badge-user'>👤 用戶</span>"}
            &nbsp; @{user['username']}
        </div>
    </div>
    """,unsafe_allow_html=True)
    st.markdown("---")
    if groq_key:
        st.markdown("<div style='background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.3);border-radius:10px;padding:10px 14px;font-size:13px;font-weight:700;color:#4ade80'>✅ Groq AI 已連線</div>",unsafe_allow_html=True)
    else:
        st.markdown("<div style='background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.25);border-radius:10px;padding:10px 14px;font-size:13px;color:#f87171'>❌ 未設定 GROQ_API_KEY</div>",unsafe_allow_html=True)
    if tg_token_secret:
        user_cid = user.get("telegram_chat_id","")
        tg_status = "✅ 個人已綁定" if user_cid else "⚠️ 請到帳號設定填入你的 Chat ID"
        tg_color  = "#38bdf8" if user_cid else "#fbbf24"
        tg_bg     = "rgba(14,165,233,0.1)" if user_cid else "rgba(251,191,36,0.08)"
        tg_border = "rgba(14,165,233,0.2)" if user_cid else "rgba(251,191,36,0.2)"
        st.markdown(f"<div style='background:{tg_bg};border:1px solid {tg_border};border-radius:10px;padding:8px 14px;font-size:13px;color:{tg_color};margin-top:8px'>{tg_status}</div>",unsafe_allow_html=True)
    st.markdown("---")
    if st.button("🚪 登出",use_container_width=True): logout()

# ── Tabs ──
_tabs=["📊 個股分析","🎯 目標價","📋 觀察名單","⚙️ 帳號設定"]
if is_admin: _tabs.append("👑 用戶管理")
tabs=st.tabs(_tabs)
tab_ana=tabs[0]; tab_tgt=tabs[1]; tab_wl=tabs[2]; tab_acc=tabs[3]
tab_admin=tabs[4] if is_admin else None

# ════════════════════════════════════════
# 工具函數
# ════════════════════════════════════════
@st.cache_data(ttl=1800)
def fetch_stock(symbol):
    clean=symbol.strip().replace(".TW","").replace(".TWO","")
    for sfx in [".TW",".TWO"]:
        try:
            t=yf.Ticker(clean+sfx)
            df=t.history(period="2y")
            if df.empty: df=t.history(period="max")
            if not df.empty:
                return df, t.history(period="1mo",interval="60m"), \
                           t.history(period="1mo",interval="30m"), clean
        except: continue
    return None,None,None,clean

@st.cache_data(ttl=3600)
def fetch_name(symbol):
    try:
        r=requests.get("https://histock.tw/stock/rank.aspx?p=all",
                       headers={"User-Agent":"Mozilla/5.0"},timeout=5)
        dfs=pd.read_html(r.text); df=dfs[0]
        cc=[c for c in df.columns if "代號" in str(c)][0]
        cn=[c for c in df.columns if "股票" in str(c) or "名稱" in str(c)][0]
        for _,row in df.iterrows():
            code="".join(c for c in str(row[cc]) if c.isdigit())
            if code==symbol: return str(row[cn])
    except: pass
    return symbol

def _sar(hi,lo,af0=0.02,af_max=0.2):
    n=len(hi); s=np.zeros(n); tr=np.ones(n); ep=np.zeros(n); af=np.full(n,af0)
    s[0]=lo[0]; ep[0]=hi[0]
    for i in range(1,n):
        s[i]=s[i-1]+af[i-1]*(ep[i-1]-s[i-1])
        if tr[i-1]==1:
            if lo[i]<s[i]: tr[i]=-1;s[i]=ep[i-1];ep[i]=lo[i];af[i]=af0
            else:
                tr[i]=1
                if hi[i]>ep[i-1]: ep[i]=hi[i];af[i]=min(af[i-1]+af0,af_max)
                else: ep[i]=ep[i-1];af[i]=af[i-1]
                s[i]=min(s[i],lo[i-1])
                if i>1: s[i]=min(s[i],lo[i-2])
        else:
            if hi[i]>s[i]: tr[i]=1;s[i]=ep[i-1];ep[i]=hi[i];af[i]=af0
            else:
                tr[i]=-1
                if lo[i]<ep[i-1]: ep[i]=lo[i];af[i]=min(af[i-1]+af0,af_max)
                else: ep[i]=ep[i-1];af[i]=af[i-1]
                s[i]=max(s[i],lo[i-1])
                if i>1: s[i]=max(s[i],lo[i-2])
    return s

def add_ind(df):
    if df is None or df.empty: return df
    n=len(df)
    df["SAR"]=_sar(df["High"].values,df["Low"].values) if n>5 else np.nan
    for p in [5,10,20,60,120]: df[f"MA{p}"]=df["Close"].rolling(p).mean() if n>=p else np.nan
    h9=df["High"].rolling(9).max(); l9=df["Low"].rolling(9).min()
    rsv=((df["Close"]-l9)/(h9-l9)*100).fillna(50)
    k,d=[50.0],[50.0]
    for v in rsv: k.append(k[-1]*2/3+v/3); d.append(d[-1]*2/3+k[-1]/3)
    df["K"]=k[1:]; df["D"]=d[1:]
    e12=df["Close"].ewm(span=12,adjust=False).mean(); e26=df["Close"].ewm(span=26,adjust=False).mean()
    df["DIF"]=e12-e26; df["MACD_SIG"]=df["DIF"].ewm(span=9,adjust=False).mean(); df["MACD_HIST"]=df["DIF"]-df["MACD_SIG"]
    df["TR"]=np.maximum(df["High"]-df["Low"],np.abs(df["High"]-df["Close"].shift(1)))
    df["ATR"]=df["TR"].rolling(14).mean(); df["VOL_MA5"]=df["Volume"].rolling(5).mean()
    df["BB_MID"]=df["Close"].rolling(20).mean(); std=df["Close"].rolling(20).std()
    df["BB_UP"]=df["BB_MID"]+2*std; df["BB_LO"]=df["BB_MID"]-2*std
    df["BB_PCT"]=(df["Close"]-df["BB_LO"])/(df["BB_UP"]-df["BB_LO"])
    return df

def wave_label(df):
    if df is None or len(df)<15: return "N/A"
    c=df["Close"].iloc[-1]
    m20=df["MA20"].iloc[-1] if not pd.isna(df["MA20"].iloc[-1]) else c
    m60=df["MA60"].iloc[-1] if not pd.isna(df["MA60"].iloc[-1]) else c
    k=df["K"].iloc[-1]; pk=df["K"].iloc[-2]; h=df["MACD_HIST"].iloc[-1]; ph=df["MACD_HIST"].iloc[-2]
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
    kd_cross=(p["K"]<p["D"]) and (t["K"]>t["D"]); kd_bull=t["K"]>t["D"]
    cond_kd=kd_bull or kd_cross
    kd_label="今日金叉 ✨" if kd_cross else ("多頭排列" if kd_bull else "空方排列")
    cond_macd=t["MACD_HIST"]>0
    macd_label="今日翻紅 🔴" if (p["MACD_HIST"]<=0 and t["MACD_HIST"]>0) else ("紅柱延伸" if cond_macd else "綠柱整理")
    cond_sar=float(t["Close"])>float(t["SAR"]); sar_label="多方支撐" if cond_sar else "空方壓力"
    hard_pass=cond_kd and cond_macd and cond_sar
    vma=t["VOL_MA5"] if t["VOL_MA5"]>0 else 1; vol_ratio=round(float(t["Volume"])/float(vma),1)
    cond_vol=vol_ratio>=1.5; wlabel=wave_label(df)
    wave_hint={"3-3":"🌊 3-3主升急漲","3-5":"🏔️ 3-5噴出末段","3-1":"🌱 3-1初升","4-c":"🪤 4-c修正末端"}.get(wlabel)
    signal=None
    if hard_pass: signal="SELL" if wlabel in ("3-5","B-c","C-3") else "BUY"
    return {"signal":signal,"hard_pass":hard_pass,"cond_kd":cond_kd,"kd_label":kd_label,
            "cond_macd":cond_macd,"macd_label":macd_label,"cond_sar":cond_sar,"sar_label":sar_label,
            "cond_vol":cond_vol,"vol_ratio":vol_ratio,"wave_label":wlabel,"wave_hint":wave_hint}

def fibonacci(df):
    w=min(len(df),120); hi=df["High"].iloc[-w:].max(); lo=df["Low"].iloc[-w:].min(); d=hi-lo
    return {"0.236":hi-d*0.236,"0.382":hi-d*0.382,"0.500":hi-d*0.5,"0.618":hi-d*0.618,"high":hi,"low":lo}

def _v(row,key,fb=np.nan):
    v=row.get(key,fb); return fb if pd.isna(v) else v

def wchip(l):
    c="wbull" if l.startswith(("3","4")) else "wbear" if l.startswith(("C","B")) else "wneut"
    return f"<span class='wchip {c}'>{l}</span>"

def get_quick_price(code):
    for sfx in [".TW",".TWO"]:
        try:
            df=yf.Ticker(code+sfx).history(period="5d")
            if not df.empty: return float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2] if len(df)>1 else df["Close"].iloc[-1])
        except: pass
    return None, None

# ════════════════════════════════════════
# TAB 1：個股分析
# ════════════════════════════════════════
with tab_ana:
    _my_codes = db.get_user_watchlist_codes(user["username"])
    _wl_map   = db.get_global_watchlist() if _my_codes else {}

    # 若從觀察名單跳轉過來，預填代號
    _jump = st.session_state.pop("_jump_code","")

    if _my_codes:
        _opts = ["手動輸入..."] + [f"{c}  {_wl_map.get(c,c)}" for c in _my_codes]
        sc1,sc2,sc3 = st.columns([2,2,1])
        with sc1:
            st.markdown("<span style='font-size:12px;color:#64748b;letter-spacing:.5px'>📋 從觀察名單快選</span>",unsafe_allow_html=True)
            wl_sel = st.selectbox("", options=_opts,
                                  label_visibility="collapsed", key="wl_sel")
        with sc2:
            st.markdown("<span style='font-size:12px;color:#64748b;letter-spacing:.5px'>或輸入代號</span>",unsafe_allow_html=True)
            # 從下拉選取時自動填入，跳轉也自動填入
            _pre = ""
            if wl_sel and wl_sel != "手動輸入...":
                _pre = wl_sel.split()[0]
            if _jump:
                _pre = _jump
            si = st.text_input("", value=_pre or "2330",
                               placeholder="如 2330",
                               label_visibility="collapsed", key="ana_in")
        with sc3:
            st.markdown("<span style='font-size:12px;color:#64748b'>&nbsp;</span>",unsafe_allow_html=True)
            run_btn = st.button("🚀 分析", type="primary", use_container_width=True)
    else:
        c1,c2,c3 = st.columns([3,1,1])
        with c1: si=st.text_input("","2330",placeholder="輸入股票代號，如 2330",label_visibility="collapsed",key="ana_in")
        with c2: run_btn=st.button("🚀 分析",type="primary",use_container_width=True)

    add_wl = st.button("➕ 加入觀察名單",use_container_width=False,key="ana_wl")
    # 自動分析：從下拉選單選了非手動 → 直接觸發
    # 只在有代號且不是初始狀態時觸發
    _auto_run = False
    if _my_codes and wl_sel not in ("", "手動輸入...") and si and si != "2330":
        _auto_run = True

    if add_wl and si:
        cc2=si.strip().replace(".TW","").replace(".TWO","")
        nm2=fetch_name(cc2)
        db.add_to_watchlist(user["username"],cc2,nm2)
        st.success(f"✅ {nm2}（{cc2}）已加入觀察名單")

    # 分析按下 → 計算並存入 session_state
    if (run_btn or _auto_run) and si and si.strip():
        cc=si.strip().replace(".TW","").replace(".TWO","")
        with st.spinner(f"載入 {cc} 所有數據..."):
            df_d,df_60,df_30,cc=fetch_stock(cc)
            nm=fetch_name(cc)
        if df_d is None or len(df_d)<10:
            st.error("❌ 找不到資料，請確認代號"); st.stop()
        df_d=add_ind(df_d)
        df_60=add_ind(df_60) if df_60 is not None and not df_60.empty else None
        df_30=add_ind(df_30) if df_30 is not None and not df_30.empty else None
        st.session_state.stock_data=(df_d,df_60,df_30,cc,nm)
        st.session_state.stock_code=cc
        st.session_state.stock_name=nm
        st.session_state.report_result=None  # 清空舊報告

    # 從 session_state 取出資料顯示
    if st.session_state.stock_data is None:
        st.markdown("""
        <div style='text-align:center;padding:60px 20px;animation:fadeUp .6s ease both'>
            <div style='font-size:48px;margin-bottom:16px'>📊</div>
            <div style='font-size:20px;font-weight:700;color:#f0f4ff;margin-bottom:8px'>輸入股票代號開始分析</div>
            <div style='color:#64748b;font-size:14px'>支援上市上櫃股票，輸入4位數字代號後點擊「分析」</div>
        </div>
        """,unsafe_allow_html=True)
    else:
        df_d,df_60,df_30,cc,nm=st.session_state.stock_data
        t=df_d.iloc[-1]; p=df_d.iloc[-2]
        sop=sop_check(df_d); fib=fibonacci(df_d)
        atr=_v(t,"ATR",t["Close"]*0.02)
        w_d=wave_label(df_d); w_60=wave_label(df_60) if df_60 is not None else "N/A"
        w_30=wave_label(df_30) if df_30 is not None else "N/A"
        ma5=_v(t,"MA5",fib["0.236"]); ma20=_v(t,"MA20",fib["0.382"])
        buy_agg=max(ma5,fib["0.236"]); buy_con=max(ma20,fib["0.382"])
        stop=max(t["Close"]-atr*2,fib["0.618"])
        vma5=t["VOL_MA5"] if t["VOL_MA5"]>0 else 1; vol_r=round(t["Volume"]/vma5,1)
        diff=t["Close"]-p["Close"]; dp=diff/p["Close"]*100
        pcls="price-up" if diff>0 else "price-down" if diff<0 else "price-flat"
        pct_cls="pct-up" if diff>0 else "pct-down"
        ps="+" if diff>0 else ""

        # ── 標題 ──
        st.markdown(f"""
        <div style='animation:fadeUp .4s ease both;margin-bottom:22px'>
            <div style='font-size:12px;color:#64748b;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px'>股票代號 {cc}</div>
            <div style='display:flex;align-items:baseline;gap:16px;flex-wrap:wrap'>
                <span style='font-size:28px;font-weight:900;color:#f0f4ff'>{nm}</span>
                <span class='{pcls}'>{t['Close']:.2f}</span>
                <span class='{pct_cls}'>{ps}{diff:.2f}（{ps}{dp:.2f}%）</span>
            </div>
            <div style='color:#64748b;font-size:13px;margin-top:6px'>
                成交量 <span style='color:#94a3b8;font-weight:600'>{int(t['Volume']/1000):,} 張</span>
                &nbsp;·&nbsp; 量比 <span style='color:#94a3b8;font-weight:600'>{vol_r}x</span>
                &nbsp;·&nbsp; {wchip(w_d)}{wchip(w_60)}{wchip(w_30)}
            </div>
        </div>
        """,unsafe_allow_html=True)

        # ── 目標價（第一欄位緊接在行情下方）──
        my_tgt=db.get_user_target(user["username"],cc)
        if my_tgt:
            tc=db.check_target_reached(t["Close"],my_tgt["target_price"])
            gp=tc["gap_pct"]; prog=min(100,max(0,100-gp)) if gp>0 else 100
            cls="reached" if gp<=0 else "close" if gp<=5 else ""
            sc="#4ade80" if gp<=0 else "#fbbf24" if gp<=5 else "#38bdf8"

            # 取得法人目標價
            analyst_target = ""
            try:
                for sfx in [".TW",".TWO"]:
                    _info = yf.Ticker(cc+sfx).info
                    _at = _info.get("targetMeanPrice")
                    if _at:
                        analyst_target = f"法人目標價：{_at:.2f}"
                        break
            except: pass

            st.markdown(f"""
            <div class='tgt-card {cls}'>
                <div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px'>
                    <div>
                        <div style='font-size:11px;color:#64748b;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px'>🎯 你的目標價</div>
                        <div style='display:flex;align-items:center;gap:12px'>
                            <span style='font-size:30px;font-weight:900;color:#38bdf8'>{my_tgt['target_price']:.2f}</span>
                            <span style='font-size:14px;font-weight:700;color:{sc}'>{tc['status']}</span>
                        </div>
                        <div style='font-size:12px;color:#64748b;margin-top:4px'>{tc['desc']}</div>
                    </div>
                    {f'<div style="text-align:right;font-size:12px;color:#94a3b8;padding-top:4px">📊 {analyst_target}</div>' if analyst_target else ''}
                </div>
                <div class='tgt-progress-bg'><div class='tgt-progress-fill {cls}' style='width:{prog:.0f}%'></div></div>
                <div style='display:flex;justify-content:space-between;font-size:11px;color:#475569'>
                    <span>現價 {float(t["Close"]):.2f}</span>
                    <span>{prog:.0f}%</span>
                    <span>目標 {my_tgt['target_price']:.2f}</span>
                </div>
            </div>
            """,unsafe_allow_html=True)
        else:
            # 沒設目標價時顯示法人目標價
            try:
                for sfx in [".TW",".TWO"]:
                    _info = yf.Ticker(cc+sfx).info
                    _at   = _info.get("targetMeanPrice")
                    _ath  = _info.get("targetHighPrice")
                    _atl  = _info.get("targetLowPrice")
                    _anc  = _info.get("numberOfAnalystOpinions",0)
                    if _at:
                        _gap = (_at - float(t["Close"])) / float(t["Close"]) * 100
                        st.markdown(f"""<div class='card-sm'>
                            <span style='font-size:12px;color:#64748b'>📊 法人目標價（{_anc}位分析師）</span>
                            <span style='float:right;font-weight:700;color:#38bdf8'>
                                {_at:.2f}  <span style='font-size:11px;color:{"#4ade80" if _gap>0 else "#f87171"}'>
                                ({_gap:+.1f}%)</span>
                            </span>
                            <div style='font-size:11px;color:#475569;margin-top:4px'>
                                低：{_atl:.2f} ｜ 高：{_ath:.2f}
                            </div>
                        </div>""",unsafe_allow_html=True)
                        break
            except: pass

        st.markdown("---")

        # ── SOP ──
        signal=sop["signal"]
        if signal in ("BUY","SELL"):
            css="sop-buy" if signal=="BUY" else "sop-sell"
            atxt=("🚀 BUY — SOP 三線全達，最佳進場！" if signal=="BUY" else "⚠️ SELL — 高檔出場訊號！")
            hints=""
            if sop["cond_vol"]:  hints+=f"💡 量比{vol_r}x（≥1.5加分）&nbsp;&nbsp;"
            if sop["wave_hint"]: hints+=sop['wave_hint']
            if signal=="BUY":
                phtml=(f"🦁 激進 <b>{buy_agg:.2f}</b> &nbsp;·&nbsp; 🐢 保守 <b>{buy_con:.2f}</b> &nbsp;·&nbsp; 🛑 停損 <b>{stop:.2f}</b>")
            else:
                phtml=(f"⚡ 建議出場 <b>{float(t['Close']):.2f}</b> &nbsp;·&nbsp; 🛑 停損 <b>{stop:.2f}</b>")
            st.markdown(f"""<div class='{css}'>
                <div class='sop-title'>{atxt}</div>
                <div class='sop-conds'>✅ KD：{sop['kd_label']} &nbsp;&nbsp; ✅ MACD：{sop['macd_label']} &nbsp;&nbsp; ✅ SAR：{sop['sar_label']}</div>
                {f'<div style="margin-top:8px;font-size:13px;color:rgba(255,255,255,0.7)">{hints}</div>' if hints else ''}
                <div class='sop-price'>{phtml}</div>
            </div>""",unsafe_allow_html=True)
            _,_,tg_col=st.columns(3)
            with tg_col:
                if st.button("📲 推播到 Telegram",type="primary",use_container_width=True):
                    ok=push_sop(signal,nm,cc,t["Close"],sop,buy_agg,buy_con,stop)
                    st.success("✅ 推播成功！") if ok else st.error("❌ 推播失敗，請確認 TG_TOKEN 已設定")
        else:
            hc=sum([sop["cond_kd"],sop["cond_macd"],sop["cond_sar"]])
            items="".join([f"<div class='cond-row'><span class='{'pass' if ok else 'fail'}'>{'✅' if ok else '❌'} {lb}</span></div>"
                           for ok,lb in [(sop["cond_kd"],f"KD：{sop['kd_label']}"),
                                         (sop["cond_macd"],f"MACD：{sop['macd_label']}"),
                                         (sop["cond_sar"],f"SAR：{sop['sar_label']}")]])
            sh=(f"<span class='hint'>💡 量比{vol_r}x ≥1.5 ✔</span>&nbsp;" if sop["cond_vol"]
                else f"<span style='color:#475569'>💡 量比{vol_r}x（未達1.5）</span>&nbsp;")
            sh+=(f"<span class='hint'>{sop['wave_hint']} ✔</span>" if sop["wave_hint"]
                 else f"<span style='color:#475569'>🌊 {w_d}（非提示範圍）</span>")
            st.markdown(f"""<div class='watch-b'>
                <span style='color:#94a3b8;font-weight:700'>👀 SOP 觀察中</span>
                <span style='color:#475569;font-size:13px;margin-left:10px'>硬條件 {hc}/3 達標</span>
                <div style='margin-top:10px'>{items}</div>
                <div style='margin-top:10px;font-size:13px'>{sh}</div>
            </div>""",unsafe_allow_html=True)

        # ── 波浪 + 圖 ──
        st.markdown("---")
        cw1,cw2,cw3=st.columns(3)
        cw1.info(f"📅 日線波浪\n\n## {w_d}")
        cw2.warning(f"⏰ 60分鐘\n\n## {w_60}")
        cw3.error(f"⚡ 30分鐘\n\n## {w_30}")
        if WC_READY and wc.PLOTLY_OK:
            st.markdown("#### 📊 日K線圖 + 波浪標注")
            _fig = wc.build_kline_chart(df_d, df_60=df_60, wave_label_d=w_d, stock_name=nm, code=cc)
            if _fig:
                st.plotly_chart(_fig, use_container_width=True, config={"displayModeBar":False})
        else:
            _cd = df_d[["Close","MA5","MA20","MA60"]].iloc[-60:].dropna()
            if not _cd.empty:
                st.line_chart(_cd, color=["#38bdf8","#f97316","#4ade80","#a78bfa"])
        if WC_READY:
            _wi = wc.get_wave_info(w_d)
            st.markdown("---")
            st.markdown(f"#### {_wi['emoji']} 波浪劇本分析 — {_wi['label']}")
            st.caption(_wi['desc'])
            for _sc in _wi.get("scenarios", []):
                _sc_c = _sc["color"]
                try: _r,_g,_b=int(_sc_c[1:3],16),int(_sc_c[3:5],16),int(_sc_c[5:7],16); _bg=f"rgba({_r},{_g},{_b},0.07)"
                except: _bg="rgba(255,255,255,0.05)"
                st.markdown(
                    f"<div style='background:{_bg};border-left:3px solid {_sc_c};border-radius:10px;padding:14px 18px;margin-bottom:10px'>"
                    f"<div style='font-size:14px;font-weight:700;color:{_sc_c};margin-bottom:6px'>{_sc['name']}</div>"
                    f"<div style='font-size:13px;color:#cbd5e1;line-height:1.8'>{_sc['desc']}</div>"
                    f"<div style='margin-top:8px;font-size:12px;display:flex;gap:12px;flex-wrap:wrap'>"
                    f"<span style='background:rgba(255,255,255,0.05);padding:4px 10px;border-radius:6px;color:#94a3b8'>"
                    f"✅ {_sc['cond']}</span>"
                    f"<span style='background:rgba(239,68,68,0.08);padding:4px 10px;border-radius:6px;color:#fca5a5'>"
                    f"{_sc['risk']}</span></div></div>",
                    unsafe_allow_html=True
                )

        # ── 費波 + 布林 ──
        st.markdown("---")
        fc,bc=st.columns(2)
        with fc:
            st.markdown("#### 📐 費波那契支撐壓力")
            prc=t["Close"]
            for ratio,key,name_ in [("0.236","0.236","強勢支撐"),("0.382","0.382","初級支撐"),("0.500","0.500","多空分界"),("0.618","0.618","黃金防線")]:
                lvl=fib[key]; ok=prc>lvl
                color="#4ade80" if ok else "#f87171"
                st.markdown(f"""<div class='card-sm'>
                    <span style='color:#64748b;font-size:12px'>{ratio} {name_}</span>
                    <span style='float:right;font-weight:700;color:{color};font-family:JetBrains Mono'>
                        {"✅" if ok else "⚠️"} {lvl:.2f}
                    </span>
                </div>""",unsafe_allow_html=True)
        with bc:
            st.markdown("#### 📊 技術指標")
            bb=_v(t,"BB_PCT",0.5)
            bm="衝出上軌（過熱）" if bb>1 else "跌破下軌（超跌）" if bb<0 else "區間震盪"
            bb_c="#f87171" if bb>1 else "#4ade80" if bb<0 else "#38bdf8"
            for label,val,color in [
                ("KD", f"K={t['K']:.1f} D={t['D']:.1f} → {sop['kd_label']}", "#4ade80" if sop['cond_kd'] else "#f87171"),
                ("MACD", f"{t['MACD_HIST']:+.4f} → {sop['macd_label']}", "#4ade80" if sop['cond_macd'] else "#f87171"),
                ("SAR", f"{float(t['SAR']):.2f} → {sop['sar_label']}", "#4ade80" if sop['cond_sar'] else "#f87171"),
                ("布林位置", f"{bb*100:.0f}% — {bm}", bb_c),
                ("ATR", f"{atr:.2f} 元", "#94a3b8"),
            ]:
                st.markdown(f"""<div class='card-sm'>
                    <span style='color:#64748b;font-size:12px'>{label}</span>
                    <span style='float:right;color:{color};font-size:13px;font-weight:600'>{val}</span>
                </div>""",unsafe_allow_html=True)

        # ── 主力券商 ──
        st.markdown("---")
        st.markdown("#### 🏦 主力券商進出（當日）")
        if not BROKER_READY:
            st.caption("⚠️ broker.py 未上傳")
        else:
            with st.spinner("載入主力資料..."):
                bk_data=bk.get_broker_data(cc)
                inst=bk.get_institutional(cc)
            if bk_data.get("error"):
                st.markdown(f"<div class='card-sm' style='color:#fbbf24'>{bk_data['error']}</div>",unsafe_allow_html=True)
            else:
                net=bk_data["net_total"]
                nc="#4ade80" if net>0 else "#f87171" if net<0 else "#94a3b8"
                ni="🔺" if net>0 else "💚" if net<0 else "➖"
                st.markdown(f"""<div class='card' style='text-align:center;padding:16px'>
                    <div style='font-size:12px;color:#64748b;margin-bottom:4px'>資料日期 {bk_data.get('date','-')} | 全體券商淨買超</div>
                    <div style='font-size:28px;font-weight:900;color:{nc}'>{ni} {abs(net):,} 張</div>
                </div>""",unsafe_allow_html=True)
                if not inst.get("error"):
                    ia,ib,ic=st.columns(3)
                    fv=inst.get('foreign',0); tv=inst.get('trust',0); dv=inst.get('dealer',0)
                    ia.metric("🌐 外資", f"{fv:+,} 張")
                    ib.metric("🏦 投信", f"{tv:+,} 張")
                    ic.metric("🏢 自營", f"{dv:+,} 張")
                ba,sa=st.columns(2)
                with ba:
                    st.markdown("<div style='color:#4ade80;font-weight:700;font-size:14px;margin-bottom:8px'>🔺 主力買超前10</div>",unsafe_allow_html=True)
                    for b in bk_data["buy_brokers"][:8]:
                        st.markdown(f"""<div class='broker-row'>
                            <span class='broker-name'>{b['name']}</span>
                            <span class='broker-buy'>+{b['net']:,}</span>
                        </div>""",unsafe_allow_html=True)
                with sa:
                    st.markdown("<div style='color:#f87171;font-weight:700;font-size:14px;margin-bottom:8px'>💚 主力賣超前10</div>",unsafe_allow_html=True)
                    for b in bk_data["sell_brokers"][:8]:
                        st.markdown(f"""<div class='broker-row'>
                            <span class='broker-name'>{b['name']}</span>
                            <span class='broker-sell'>{b['net']:,}</span>
                        </div>""",unsafe_allow_html=True)

        # ── 目標價預估 ──
        st.markdown("---")
        st.markdown("#### 🎯 AI 目標價預估")
        tc1,tc2,tc3=st.columns(3)
        for col,mult,lb,color in [(tc1,1.05,"短線 +5%","#22d3ee"),(tc2,1.10,"波段 +10%","#a78bfa"),(tc3,1.20,"長線 +20%","#4ade80")]:
            tp=t["Close"]*mult; days=max(5,int((tp-t["Close"])/max(atr*0.4,0.01)*2.5))
            col.markdown(f"""<div class='card' style='text-align:center;padding:18px'>
                <div style='font-size:12px;color:#64748b;letter-spacing:.8px;text-transform:uppercase'>{lb}</div>
                <div style='font-size:28px;font-weight:900;color:{color};margin:8px 0'>{tp:.2f}</div>
                <div style='font-size:12px;color:#64748b'>約 {days} 個交易日</div>
            </div>""",unsafe_allow_html=True)

        st.caption(f"更新：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ AI Stock Bot V3.1")

        # ── 全球市場情報 ──
        st.markdown("---")
        st.markdown("## 🌍 全球市場情報")
        if GM_READY:
            with st.spinner("載入全球市場情報..."):
                gm_data = gm.get_full_global_report(cc)
            ind_info = gm_data["industry_info"]
            st.caption(f"偵測產業：{ind_info.get('name','—')}  ｜  以下顯示相關指數、個股及最新情報")

            # 相關美股 ETF
            etf_data = gm_data["us_etf_data"]
            if etf_data:
                st.markdown("#### 📊 相關美股 ETF")
                ecols = st.columns(min(len(etf_data),4))
                for i,d in enumerate(etf_data):
                    ecols[i%4].metric(d["name"], f"{d['price']}", f"{d['direction']}{d['pct']:+.2f}%")

            # 相關美股個股
            us_stocks = gm_data["us_stock_data"]
            if us_stocks:
                st.markdown("#### 🇺🇸 相關美股個股")
                scols = st.columns(min(len(us_stocks),5))
                for i,d in enumerate(us_stocks):
                    scols[i%5].metric(f"{d['name']}({d['ticker']})", f"{d['price']}", f"{d['direction']}{d['pct']:+.2f}%")

            # 全球相關個股
            global_stocks = gm_data["global_data"]
            if global_stocks:
                st.markdown("#### 🌏 全球相關個股")
                gcols = st.columns(min(len(global_stocks),4))
                for i,d in enumerate(global_stocks):
                    gcols[i%4].metric(f"{d['name']}", f"{d['price']}", f"{d['direction']}{d['pct']:+.2f}%")

            # 產業新聞
            ind_news = gm_data["industry_news"]
            if ind_news:
                st.markdown("#### 📰 相關產業新聞")
                for n in ind_news[:5]:
                    nc1,nc2 = st.columns([1,8])
                    nc1.markdown(n["sentiment"])
                    nc2.markdown(f"[{n['title']}]({n['url']})  `{n['time']}`")

            # Trump 最新言論
            trump_posts = gm_data["trump_posts"]
            src_label = trump_posts[0].get("source","") if trump_posts else ""
            is_ts = "Truth Social" in src_label
            expander_title = (
                "🇺🇸 Trump Truth Social 最新發文" if is_ts
                else "🇺🇸 Trump 最新言論（Google News）"
            )
            with st.expander(expander_title, expanded=True):
                if not is_ts and trump_posts and "⚠️" not in trump_posts[0]["text"]:
                    st.caption("⚠️ Truth Social 暫時無法連線，以下為 Google News 搜尋到的川普相關最新新聞")
                if trump_posts:
                    for p in trump_posts:
                        src_badge = f"<span style='background:rgba(249,115,22,0.2);color:#f97316;font-size:10px;padding:2px 6px;border-radius:4px;margin-right:8px'>{p.get('source','')}</span>" if p.get('source') else ""
                        st.markdown(f"""
                        <div style='background:rgba(255,255,255,0.04);border-left:3px solid #f97316;
                             border-radius:8px;padding:12px 16px;margin-bottom:10px'>
                            <div style='font-size:13px;color:#e2e8f0;line-height:1.7'>{p["text"]}</div>
                            <div style='font-size:11px;color:#64748b;margin-top:6px'>
                                {src_badge}⏰ {p["time"]}
                                {"&nbsp;&nbsp;<a href='" + p["url"] + "' target='_blank' style='color:#38bdf8'>查看原文</a>" if p.get("url") else ""}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.caption("目前無法取得川普相關資料")

        # ── AI 報告書 ──
        st.markdown("---")
        st.markdown("## 🤖 AI 深度個股分析報告書")
        st.caption("整合技術面・基本面・波浪理論・美股連動・最新新聞 ｜ Groq Llama 3.3 70B 免費生成")

        if not AI_READY:
            st.warning("⚠️ `ai_report.py` 尚未上傳到 GitHub")
        elif not groq_key:
            st.markdown("""<div class='card' style='border-color:rgba(251,191,36,0.3)'>
                <div style='font-size:16px;font-weight:700;color:#fbbf24'>⚠️ 需要設定 GROQ_API_KEY</div>
                <div style='color:#94a3b8;font-size:14px;margin-top:8px'>
                    1. 至 <b>console.groq.com</b> 免費註冊<br>
                    2. API Keys → Create API Key → 複製 gsk_xxx<br>
                    3. Streamlit → Settings → Secrets 加入：<br>
                    <code style='color:#38bdf8'>GROQ_API_KEY = "gsk_你的key"</code>
                </div>
            </div>""",unsafe_allow_html=True)
        else:
            if st.button("📋 生成完整分析報告書（免費）",type="primary",use_container_width=True,key="gen_report"):
                tgt_entry=db.get_user_target(user["username"],cc)
                my_tgt_price=tgt_entry["target_price"] if tgt_entry else None
                with st.spinner("🤖 AI 分析中，約 30-60 秒..."):
                    result=ai_report.generate_full_report(cc,nm,my_tgt_price)
                st.session_state.report_result=result

            # 顯示已儲存的報告（按其他按鈕也不會消失）
            if st.session_state.report_result:
                result=st.session_state.report_result
                if result.get("error"):
                    st.error(result["error"])
                else:
                    fund=result["fundamental"]; us=result["us_market"]; news_list=result["news"]
                    mc1,mc2,mc3,mc4=st.columns(4)
                    mc1.metric("SOP訊號",result["sop"].get("signal","N/A"))
                    mc2.metric("波浪位置",result["wave_title"].split()[0] if result["wave_title"] else "N/A")
                    pe_val=fund.get("pe"); mc3.metric("本益比P/E",f"{pe_val:.1f}" if pe_val else "N/A")
                    mc4.metric("法人目標",str(fund.get("target_mean","N/A")))
                    if news_list:
                        st.markdown("#### 📰 最新新聞")
                        for ni in news_list[:5]:
                            badge=("news-bull" if "利多" in ni["sentiment"] else "news-bear" if "利空" in ni["sentiment"] else "news-neut")
                            st.markdown(f"""<div class='broker-row'>
                                <span style='background:rgba(255,255,255,0.06);padding:2px 8px;border-radius:5px;font-size:12px;font-weight:700;
                                color:{"#4ade80" if "利多" in ni["sentiment"] else "#f87171" if "利空" in ni["sentiment"] else "#94a3b8"}'>{ni["sentiment"].split()[0]}</span>
                                <span style='color:#cbd5e1;font-size:13px;margin:0 12px;flex:1'>
                                    <a href='{ni["link"]}' target='_blank' style='color:#cbd5e1;text-decoration:none'>{ni["title"]}</a>
                                </span>
                                <span style='color:#475569;font-size:12px;white-space:nowrap'>{ni["pub"]}</span>
                            </div>""",unsafe_allow_html=True)
                    if us:
                        st.markdown("#### 🌏 美股即時")
                        us_cols=st.columns(len(us))
                        for idx,(tk,uv) in enumerate(us.items()):
                            icon="🔺" if uv["pct"]>0 else "💚"
                            us_cols[idx].metric(uv["name"],f"{uv['price']}",f"{icon}{uv['pct']:+.2f}%")
                    st.markdown(f"<div class='report-box'>{result['report_md']}</div>",unsafe_allow_html=True)

# ════════════════════════════════════════
# TAB 2：目標價
# ════════════════════════════════════════
with tab_tgt:
    st.markdown("### 🎯 目標價投資計畫")
    st.caption("設定目標價後，每次觸發 SOP 訊號時自動推播 Telegram 提醒")

    with st.container(border=True):
        st.markdown("#### ➕ 新增 / 更新目標價")
        t1c,t2c,t3c,t4c=st.columns([2,1.5,2,1])
        with t1c: tc_code =st.text_input("股票代號",placeholder="如 2330",key="tc",label_visibility="collapsed")
        with t2c: tc_price=st.number_input("目標價格",min_value=0.01,step=0.5,format="%.2f",key="tp",label_visibility="collapsed")
        with t3c: tc_note =st.text_input("投資備註",placeholder="如：法說會前布局",key="tn",label_visibility="collapsed")
        with t4c: tc_btn  =st.button("💾 儲存",type="primary",use_container_width=True,key="ts")

    if tc_btn and tc_code:
        code_in=tc_code.strip().replace(".TW","").replace(".TWO","")
        nm_in=fetch_name(code_in)
        ok=db.set_target(user["username"],user["display_name"],code_in,tc_price,tc_note)
        if ok:
            st.success(f"✅ 已設定 {nm_in}（{code_in}）目標價 {tc_price:.2f}")
            # 🔔 推播目標價設定通知
            chat_id=user.get("telegram_chat_id","") or tg_chat_secret
            if chat_id:
                msg=(f"🎯 <b>目標價設定通知</b>\n\n"
                     f"<b>{nm_in}（{code_in}）</b>\n"
                     f"💰 目標價：<b>{tc_price:.2f}</b> 元\n"
                     f"📝 備註：{tc_note or '—'}\n"
                     f"👤 設定者：{user['display_name']}\n"
                     f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>")
                send_tg(msg, chat_id)
            st.rerun()
        else:
            st.error("儲存失敗")

    st.markdown("---")
    my_tgts=db.get_user_all_targets(user["username"])
    st.markdown(f"#### 📌 追蹤中：{len(my_tgts)} 支")
    if not my_tgts:
        st.markdown("""<div class='card' style='text-align:center;padding:40px'>
            <div style='font-size:40px;margin-bottom:12px'>🎯</div>
            <div style='font-size:18px;font-weight:700;color:#f0f4ff;margin-bottom:8px'>尚無目標價</div>
            <div style='color:#64748b;font-size:14px'>設定目標價後每日自動追蹤進度<br>SOP 觸發時自動推播到你的 Telegram</div>
        </div>""",unsafe_allow_html=True)
    else:
        # ── 總覽卡片格 ──
        st.markdown("#### 📊 目標價總覽")
        grid_cols = st.columns(min(len(my_tgts), 3))
        for idx,(code,entry) in enumerate(my_tgts.items()):
            price_g,price_prev_g = get_quick_price(code)
            nm_g = fetch_name(code)
            if price_g:
                gap_g = entry["target_price"] - price_g
                gp_g  = gap_g / price_g * 100
                prog_g = min(100, max(0, price_g / entry["target_price"] * 100))
                reached_g = price_g >= entry["target_price"]
                close_g   = 0 < gp_g <= 5
                sc_g = "#4ade80" if reached_g else "#fbbf24" if close_g else "#38bdf8"
                st_txt = "✅ 已達標" if reached_g else f"🔥 差{gp_g:.1f}%" if close_g else f"📈 {gp_g:.1f}%"
                day_g = (price_g - price_prev_g) / price_prev_g * 100 if price_prev_g else 0
            else:
                prog_g=50; sc_g="#64748b"; st_txt="—"; price_g=0; gp_g=0; day_g=0; reached_g=False; close_g=False
            grid_cols[idx % 3].markdown(f"""
            <div class='tgt-card {"reached" if reached_g else "close" if close_g else ""}' style='padding:16px 18px;cursor:pointer'>
                <div style='font-size:13px;font-weight:700;color:#94a3b8'>{nm_g} <span style='color:#475569;font-size:11px'>{code}</span></div>
                <div style='font-size:22px;font-weight:900;color:#f0f4ff;margin:6px 0'>{f"{price_g:.2f}" if price_g else "—"}</div>
                <div style='font-size:11px;color:{"#4ade80" if day_g>0 else "#f87171"}'>{f"{day_g:+.2f}%" if price_g else ""}</div>
                <div class='tgt-progress-bg' style='margin:10px 0 6px'><div class='tgt-progress-fill {"reached" if reached_g else "close" if close_g else ""}' style='width:{prog_g:.0f}%'></div></div>
                <div style='display:flex;justify-content:space-between;font-size:11px'>
                    <span style='color:#64748b'>目標 {entry["target_price"]:.2f}</span>
                    <span style='color:{sc_g};font-weight:700'>{st_txt}</span>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🔍 詳細分析")
        for code,entry in my_tgts.items():
            nm_t=fetch_name(code)
            price_now,price_prev=get_quick_price(code)
            if price_now:
                gap=entry["target_price"]-price_now; gap_pct=gap/price_now*100
                reached=price_now>=entry["target_price"]; close=0<gap_pct<=5
                prog=min(100,max(0,price_now/entry["target_price"]*100))
                day_pct=(price_now-price_prev)/price_prev*100 if price_prev else 0
                try:
                    df_tmp,_,_,_=fetch_stock(code); df_tmp=add_ind(df_tmp)
                    atr_tmp=float(df_tmp["ATR"].iloc[-1]) if df_tmp is not None else price_now*0.02
                    est_days=max(5,int(gap/max(atr_tmp*0.4,0.01)*2.0)) if gap>0 else 0
                except: est_days=0
                cls="reached" if reached else "close" if close else ""
                sc="#4ade80" if reached else "#fbbf24" if close else "#38bdf8"
                status="✅ 已達目標！" if reached else f"🔥 差 {gap_pct:.1f}%，即將達標！" if close else f"📈 推進中，差 {gap_pct:.1f}%"
                price_str=f"{price_now:.2f}"
            else:
                prog=50; cls=""; sc="#64748b"; status="無法取得現價"
                gap_pct=0; reached=False; close=False; est_days=0; day_pct=0; price_str="N/A"

            with st.expander(f"{'✅' if reached else '🔥' if close else '📌'} {nm_t}（{code}） — 目標 {entry['target_price']:.2f}", expanded=True):
                col_l,col_r=st.columns([3,1])
                with col_l:
                    st.markdown(f"""<div class='tgt-card {cls}'>
                        <div style='display:flex;justify-content:space-between;align-items:flex-start'>
                            <div>
                                <span style='font-size:18px;font-weight:800;color:#f0f4ff'>{nm_t}</span>
                                <span style='font-size:12px;color:#64748b;margin-left:8px'>{code}</span>
                            </div>
                            <div style='text-align:right'>
                                <div style='font-size:11px;color:#64748b'>現價</div>
                                <div style='font-size:22px;font-weight:900;color:#f0f4ff'>{price_str}</div>
                                <div style='font-size:12px;color:{"#4ade80" if day_pct>0 else "#f87171"}'>{f"+{day_pct:.2f}%" if day_pct>0 else f"{day_pct:.2f}%"}</div>
                            </div>
                        </div>
                        <div style='margin-top:16px'>
                            <div style='display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-bottom:6px'>
                                <span>進度</span>
                                <span style='font-weight:700;color:{sc}'>{status}</span>
                            </div>
                            <div class='tgt-progress-bg'><div class='tgt-progress-fill {cls}' style='width:{prog:.0f}%'></div></div>
                            <div style='display:flex;justify-content:space-between;font-size:11px;color:#475569;margin-top:4px'>
                                <span>現價 {price_str}</span><span>{prog:.0f}%</span><span>目標 {entry['target_price']:.2f}</span>
                            </div>
                        </div>
                        {f'<div style="margin-top:10px;font-size:12px;color:#64748b;background:rgba(255,255,255,0.05);padding:8px 12px;border-radius:8px">📝 {entry["note"]}</div>' if entry.get("note") else ''}
                        <div style='margin-top:8px;font-size:11px;color:#475569'>設定於 {entry.get("updated_at","—")}</div>
                    </div>""",unsafe_allow_html=True)

                    # 達標條件
                    if not reached and price_now:
                        st.markdown("**🔍 達標條件分析**")
                        try:
                            df_tmp,_,_,_=fetch_stock(code)
                            if df_tmp is not None:
                                df_tmp=add_ind(df_tmp); t_t=df_tmp.iloc[-1]
                                hi=df_tmp["High"].iloc[-120:].max(); lo=df_tmp["Low"].iloc[-120:].min(); d_=hi-lo
                                conds=[
                                    (float(t_t["Close"])>float(t_t.get("MA60",t_t["Close"])), f"站上季線 {t_t.get('MA60',0):.2f}"),
                                    (float(t_t["MACD_HIST"])>0, "MACD 翻紅，動能轉正"),
                                    (float(t_t["K"])>float(t_t["D"]), "KD 多頭排列"),
                                    (float(t_t["Volume"])>float(t_t["VOL_MA5"])*1.2, "成交量放大，主力進場"),
                                    (float(t_t["Close"])>float(t_t["SAR"]), "突破 SAR 停損線"),
                                ]
                                met=sum(1 for ok_c,_ in conds if ok_c)
                                st.caption(f"已達成 {met}/{len(conds)} 個條件")
                                for ok_c,txt in conds:
                                    c_="pass" if ok_c else "fail"
                                    st.markdown(f"<div class='card-sm'><span class='{c_}'>{'✅' if ok_c else '❌'}</span> <span style='color:#94a3b8;font-size:13px'>{txt}</span></div>",unsafe_allow_html=True)
                                res=[(hi-d_*0.236,"費波0.236"),(hi-d_*0.382,"費波0.382"),(float(t_t.get("MA20",0)),"20日均線"),(float(t_t.get("MA60",0)),"60日均線")]
                                rs=[f"{l} {r:.2f}" for r,l in res if price_now<r<entry["target_price"] and r>0]
                                if rs: st.markdown(f"<div class='card-sm' style='border-color:rgba(251,191,36,0.3)'><span style='color:#fbbf24;font-size:12px'>🚧 途中壓力：</span><span style='color:#94a3b8;font-size:13px'>{' → '.join(rs)}</span></div>",unsafe_allow_html=True)
                        except: pass

                with col_r:
                    if price_now:
                        st.metric("目標價",f"{entry['target_price']:.2f}")
                        st.metric("現價",price_str,f"{'+' if day_pct>0 else ''}{day_pct:.2f}%")
                        st.metric("差距",f"{abs(gap):.2f} 元",f"{abs(gap_pct):.1f}%")
                        if est_days>0:
                            eta=(datetime.now()+timedelta(days=est_days)).strftime("%m/%d")
                            st.metric("預估達標",f"~{est_days}天",f"約 {eta}")
                    if st.button("🗑️ 刪除",key=f"dt_{code}",use_container_width=True):
                        db.delete_target(user["username"],code)
                        st.success("已刪除"); st.rerun()

    if is_admin:
        st.markdown("---")
        with st.expander("👑 管理員：全用戶目標價總覽"):
            all_tgts=db.get_all_targets_admin()
            if not all_tgts: st.info("尚無任何用戶設定目標價")
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
        st.markdown("""<div class='card' style='text-align:center;padding:32px'>
            <div style='font-size:36px'>📋</div>
            <div style='color:#f0f4ff;font-weight:700;margin:10px 0'>尚無追蹤股票</div>
            <div style='color:#64748b;font-size:14px'>Cloud Bot 每天 18:40 自動推送個人深度報告</div>
        </div>""",unsafe_allow_html=True)
    else:
        wl_map=db.get_global_watchlist()
        hd1,hd2,hd3,hd4,hd5=st.columns([1,2,1.5,2,1])
        for h,t_ in zip([hd1,hd2,hd3,hd4,hd5],["代號","名稱","現價","目標價","操作"]):
            h.markdown(f"<span style='font-size:11px;color:#475569;letter-spacing:.8px;text-transform:uppercase'>{t_}</span>",unsafe_allow_html=True)
        for code in my_codes:
            nm_w    = wl_map.get(code, code)
            my_tgt_e= db.get_user_target(user["username"], code)
            tgt_txt = f"🎯 {my_tgt_e['target_price']:.2f}" if my_tgt_e else "—"
            price_n, _ = get_quick_price(code)
            price_txt  = f"{price_n:.2f}" if price_n else "—"
            cl1,cl2,cl3,cl4,cl5,cl6 = st.columns([1,2,1.2,1.8,1.5,1])
            cl1.markdown(f"<span style='font-family:JetBrains Mono;font-weight:700;color:#38bdf8'>{code}</span>",unsafe_allow_html=True)
            cl2.write(nm_w); cl3.write(price_txt); cl4.caption(tgt_txt)
            with cl5:
                if st.button(f"📊 分析", key=f"ana_wl_{code}", use_container_width=True):
                    st.session_state["_jump_code"] = code
                    st.session_state.stock_data = None  # 清除舊資料，強制重新分析
                    st.rerun()
            with cl6:
                if st.button("🗑️", key=f"rwl_{code}", use_container_width=True):
                    db.remove_from_watchlist(user["username"], code)
                    st.success(f"已移除"); st.rerun()

# ════════════════════════════════════════
# TAB 4：帳號設定
# ════════════════════════════════════════
with tab_acc:
    st.markdown("### ⚙️ 帳號設定")
    cl,cr=st.columns(2)
    with cl:
        with st.container(border=True):
            st.markdown("#### 🔑 修改密碼")
            op=st.text_input("舊密碼",type="password",key="op")
            np1=st.text_input("新密碼",type="password",key="np1")
            np2=st.text_input("確認新密碼",type="password",key="np2")
            if st.button("更新密碼",type="primary"):
                if np1!=np2: st.error("❌ 兩次密碼不一致")
                else:
                    ok,msg=db.change_password(user["username"],op,np1)
                    st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")
    with cr:
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
    info=db.get_user(user["username"])
    ca,cb,cc_=st.columns(3)
    ca.metric("帳號",user["username"])
    cb.metric("角色","管理員 👑" if is_admin else "一般用戶")
    cc_.metric("建立時間",info.get("created_at","—") if info else "—")

# ════════════════════════════════════════
# TAB 5：用戶管理（管理員）
# ════════════════════════════════════════
if is_admin and tab_admin:
    with tab_admin:
        st.markdown("### 👑 用戶管理")
        st.caption("所有帳號由管理員手動建立，用戶無法自行註冊")
        with st.container(border=True):
            st.markdown("#### ➕ 建立新帳號")
            u1,u2,u3,u4,u5=st.columns([2,2,2,1.5,1])
            with u1: nu =st.text_input("帳號",placeholder="英文小寫",key="nu",label_visibility="collapsed")
            with u2: npw=st.text_input("密碼",type="password",placeholder="至少4碼",key="npw",label_visibility="collapsed")
            with u3: nd =st.text_input("顯示名稱",placeholder="如：小明",key="nd",label_visibility="collapsed")
            with u4: nr =st.selectbox("角色",["user","admin"],key="nr",label_visibility="collapsed")
            with u5: nb =st.button("➕ 建立",type="primary",use_container_width=True,key="nb")
            if nb:
                ok,msg=db.create_user(nu,npw,nd,nr)
                if ok:
                    st.success(f"✅ {msg}")
                    st.info(f"帳號：`{nu.strip().lower()}` ｜ 初始密碼：`{npw}` ｜ 請傳給用戶，提醒登入後修改密碼")
                else: st.error(f"❌ {msg}")
                st.rerun()
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
                    st.markdown(f"<span style='color:#94a3b8;font-size:13px'>TG：{tg_s} ｜ 觀察：{wl_n}支 ｜ 目標：{tgt_n}支</span>",unsafe_allow_html=True)
                with r3:
                    rpw=st.text_input("重設密碼",type="password",placeholder="新密碼",key=f"rpw_{uname}",label_visibility="collapsed")
                    if st.button("🔑 重設",key=f"rset_{uname}",use_container_width=True):
                        ok,msg=db.admin_reset_password(uname,rpw)
                        st.success(msg) if ok else st.error(msg)
                with r4:
                    if uname!=user["username"]:
                        if st.button("🗑️",key=f"du_{uname}",use_container_width=True):
                            ok,msg=db.delete_user(uname)
                            st.success(msg) if ok else st.error(msg); st.rerun()
                    else: st.caption("（自己）")
