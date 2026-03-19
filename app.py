"""
AI-stock-bot — app.py  v1.1
新功能：持久化自選股管理（watchlist.json，不刪除永久保存）
SOP：KD金叉/多頭 + MACD翻紅 + SAR多方（三線全達觸發）
軟提示：波浪 3-3/3-5/3-1/4-c + 量比 ≥ 1.5
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from watchlist import get_all, add_stock, remove_stock, update_note, lookup_name

# ─────────────────────────────────────────
# 頁面設定
# ─────────────────────────────────────────
st.set_page_config(page_title="AI Stock Bot", page_icon="🤖", layout="wide")

st.markdown("""
<style>
body { font-family: 'Segoe UI', sans-serif; }

@keyframes glow   { 0%,100%{box-shadow:0 0 6px #00c853} 50%{box-shadow:0 0 22px 8px #00c853} }
@keyframes glow-s { 0%,100%{box-shadow:0 0 6px #ff1744} 50%{box-shadow:0 0 22px 8px #ff1744} }
.sop-buy  { background:linear-gradient(135deg,#003300,#006600);
            border:2px solid #00c853; border-radius:12px; padding:22px 28px;
            margin:14px 0; animation:glow 2s ease-in-out infinite; color:#fff; }
.sop-sell { background:linear-gradient(135deg,#330000,#660000);
            border:2px solid #ff1744; border-radius:12px; padding:22px 28px;
            margin:14px 0; animation:glow-s 2s ease-in-out infinite; color:#fff; }
.sop-title { font-size:22px; font-weight:900; }
.sop-sub   { font-size:15px; margin-top:8px; line-height:2; }
.sop-hint  { background:rgba(255,255,255,.10); border-radius:8px;
             padding:9px 14px; margin-top:10px; font-size:14px; color:#ffe082; }

.watch-box { background:#f8f8f8; border:2px dashed #bbb; border-radius:10px;
             padding:14px 20px; margin:10px 0; font-size:14px; color:#444; }

.wl-hdr { display:flex; gap:8px; padding:8px 14px; background:#e8eaf6;
          font-weight:700; font-size:13px; border-radius:6px 6px 0 0; color:#283593; }

.wc { display:inline-block; font-size:13px; font-weight:700;
      padding:2px 10px; border-radius:20px; margin-right:5px; }
.wb { background:#e8f5e9; color:#2e7d32; border:1px solid #a5d6a7; }
.wr { background:#ffebee; color:#c62828; border:1px solid #ef9a9a; }
.wn { background:#fff3e0; color:#e65100; border:1px solid #ffcc80; }

.px-up   { color:#d32f2f; font-weight:800; font-size:28px; }
.px-down { color:#388e3c; font-weight:800; font-size:28px; }
.px-flat { color:#555;    font-weight:800; font-size:28px; }

.cr { font-size:15px; line-height:2.1; }
.ok { color:#2e7d32; font-weight:600; }
.ng { color:#c62828; font-weight:600; }
.ht { color:#e65100; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Session state
# ─────────────────────────────────────────
for k in ["wl_msg", "wl_msg_type"]:
    if k not in st.session_state:
        st.session_state[k] = ""

# ─────────────────────────────────────────
# 側邊欄
# ─────────────────────────────────────────
with st.sidebar:
    st.title("🤖 AI Stock Bot")
    st.caption("V1.1  |  SOP 三線觸發版")
    st.markdown("---")
    st.subheader("📌 分析個股")
    stock_input = st.text_input("輸入代號", value="2330", placeholder="如 2330")
    run_btn     = st.button("🚀 開始分析", type="primary", use_container_width=True)
    st.markdown("---")
    st.subheader("📲 Telegram 推播")
    tg_token = st.text_input("Bot Token", type="password")
    tg_chat  = st.text_input("Chat ID")
    st.markdown("---")
    st.caption("""**SOP 邏輯**
✅ 硬觸發（三線全達才發訊號）
- KD 金叉 / 多頭排列
- MACD Hist 翻紅
- SAR 多方支撐

💡 軟提示（加分，不影響觸發）
- 波浪：3-3 / 3-5 / 3-1 / 4-c
- 量比 ≥ 1.5""")

# ─────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────
tab_analysis, tab_watchlist = st.tabs(["📊 個股分析", "⭐ 自選股管理"])


# ═══════════════════════════════════════════
# 共用指標函數
# ═══════════════════════════════════════════
@st.cache_data(ttl=1800)
def fetch_stock(symbol: str):
    clean = symbol.strip().replace(".TW","").replace(".TWO","")
    for sfx in [".TW",".TWO"]:
        t = yf.Ticker(clean+sfx)
        try:
            df = t.history(period="2y")
            if df.empty: df = t.history(period="max")
            if not df.empty:
                return df, t.history(period="1mo",interval="60m"), \
                           t.history(period="1mo",interval="30m"), t, clean
        except: continue
    return None,None,None,None,clean


def _sar(hi, lo, a=0.02, am=0.2):
    n=len(hi); sar=np.zeros(n); tr=np.ones(n); ep=np.zeros(n); af=np.full(n,a)
    sar[0]=lo[0]; ep[0]=hi[0]
    for i in range(1,n):
        sar[i]=sar[i-1]+af[i-1]*(ep[i-1]-sar[i-1])
        if tr[i-1]==1:
            if lo[i]<sar[i]: tr[i]=-1; sar[i]=ep[i-1]; ep[i]=lo[i]; af[i]=a
            else:
                tr[i]=1
                if hi[i]>ep[i-1]: ep[i]=hi[i]; af[i]=min(af[i-1]+a,am)
                else: ep[i]=ep[i-1]; af[i]=af[i-1]
                sar[i]=min(sar[i],lo[i-1])
                if i>1: sar[i]=min(sar[i],lo[i-2])
        else:
            if hi[i]>sar[i]: tr[i]=1; sar[i]=ep[i-1]; ep[i]=hi[i]; af[i]=a
            else:
                tr[i]=-1
                if lo[i]<ep[i-1]: ep[i]=lo[i]; af[i]=min(af[i-1]+a,am)
                else: ep[i]=ep[i-1]; af[i]=af[i-1]
                sar[i]=max(sar[i],lo[i-1])
                if i>1: sar[i]=max(sar[i],lo[i-2])
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
    df["BB_MID"]=df["Close"].rolling(20).mean(); std=df["Close"].rolling(20).std()
    df["BB_UP"]=df["BB_MID"]+2*std; df["BB_LO"]=df["BB_MID"]-2*std
    df["BB_PCT"]=(df["Close"]-df["BB_LO"])/(df["BB_UP"]-df["BB_LO"])
    df["VOL_MA5"]=df["Volume"].rolling(5).mean()
    return df


def wave_lbl(df):
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


_WHINTS={
    "3-3":"🌊 3-3 主升急漲（波浪加分）",
    "3-5":"🏔️ 3-5 噴出末段（波浪加分，注意高點）",
    "3-1":"🌱 3-1 初升啟動（波浪提示）",
    "4-c":"🪤 4-c 修正末端（底部波浪提示）",
}


def fib(df):
    w=min(len(df),120); h=df["High"].iloc[-w:].max(); l=df["Low"].iloc[-w:].min(); d=h-l
    return {"0.236":h-d*.236,"0.382":h-d*.382,"0.500":h-d*.5,"0.618":h-d*.618}


def sop(df):
    if df is None or len(df)<30: return {"signal":None,"hard_pass":False}
    t=df.iloc[-1]; p=df.iloc[-2]
    kx=(p["K"]<p["D"])and(t["K"]>t["D"]); kb=t["K"]>t["D"]
    ck=kb or kx; kl="今日金叉✨" if kx else("多頭排列" if kb else "空方排列")
    cm=t["MACD_HIST"]>0
    ml=("今日翻紅🔴" if(p["MACD_HIST"]<=0 and t["MACD_HIST"]>0)
        else("紅柱延伸" if cm else "綠柱整理"))
    cs=float(t["Close"])>float(t["SAR"]); sl="多方支撐↑" if cs else "空方壓力↓"
    hp=ck and cm and cs
    vm=t["VOL_MA5"] if t["VOL_MA5"]>0 else 1
    vr=round(float(t["Volume"])/float(vm),1); cv=vr>=1.5
    wl=wave_lbl(df); cw=wl in("3-3","3-5","3-1","4-c")
    sig=None
    if hp: sig="SELL" if wl in("3-5","B-c","C-3") else "BUY"
    return {"signal":sig,"hard_pass":hp,
            "cond_kd":ck,"kd_lbl":kl,
            "cond_macd":cm,"macd_lbl":ml,
            "cond_sar":cs,"sar_lbl":sl,
            "cond_vol":cv,"vol_ratio":vr,
            "cond_wave":cw,"wave_lbl":wl,"wave_hint":_WHINTS.get(wl)}


def push_tg(tok,cid,sig,name,code,price,s,ba,bc,st_):
    if not tok or not cid or len(tok)<10: return False
    soft=""
    if s["cond_vol"]:  soft+=f"\n💡 量比{s['vol_ratio']}x（加分）"
    if s["wave_hint"]: soft+=f"\n{s['wave_hint']}"
    pl=(f"🦁{ba:.2f} ｜ 🐢{bc:.2f} ｜ 🛑{st_:.2f}"
        if sig=="BUY" else f"⚡出場{price:.2f} ｜ 🛑{st_:.2f}")
    msg=(f"{'🚀' if sig=='BUY' else '⚠️'} <b>AI Stock Bot SOP {'BUY' if sig=='BUY' else 'SELL'}</b>\n\n"
         f"<b>{name}（{code}）</b> {price:.2f}\n"
         f"✅KD：{s['kd_lbl']} ✅MACD：{s['macd_lbl']} ✅SAR：{s['sar_lbl']}"
         f"{soft}\n{pl}\n<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>")
    try:
        r=requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                        json={"chat_id":cid,"text":msg,"parse_mode":"HTML"},timeout=8)
        return r.status_code==200
    except: return False


def wchip(l):
    c="wb" if l[0] in"34" else "wr" if l[0] in"CB" else "wn"
    return f"<span class='wc {c}'>{l}</span>"


def _v(row,key,fb=np.nan):
    v=row.get(key,fb); return fb if pd.isna(v) else v


# ═══════════════════════════════════════════
# TAB 2 — 自選股管理
# ═══════════════════════════════════════════
with tab_watchlist:
    st.subheader("⭐ 我的自選股")
    st.caption("新增後永久保存在 `watchlist.json`，不刪除就一直存在。"
               "cloud_bot.py 每天自動依此清單發送報告。")

    # ── 訊息顯示 ──
    if st.session_state.wl_msg:
        fn = st.success if st.session_state.wl_msg_type=="ok" else st.error
        fn(st.session_state.wl_msg)
        st.session_state.wl_msg = ""; st.session_state.wl_msg_type = ""

    # ── 新增區 ──
    st.markdown("#### ➕ 新增股票")
    ac1,ac2,ac3,ac4 = st.columns([1.2,1.5,2.8,0.9])
    new_code = ac1.text_input("代號", placeholder="2330", key="nc",
                               label_visibility="collapsed")
    new_name = ac2.text_input("名稱（可空）", placeholder="名稱", key="nn",
                               label_visibility="collapsed")
    new_note = ac3.text_input("備註（可空）", placeholder="備註，如：長線佈局", key="no",
                               label_visibility="collapsed")
    add_btn  = ac4.button("➕ 新增", type="primary", use_container_width=True)

    if add_btn and new_code:
        nm = new_name.strip()
        if not nm:
            with st.spinner(f"自動查詢 {new_code} 名稱..."):
                nm = lookup_name(new_code)
        ok, msg = add_stock(new_code, nm, new_note)
        st.session_state.wl_msg = msg
        st.session_state.wl_msg_type = "ok" if ok else "err"
        st.rerun()

    # ── 批次新增 ──
    with st.expander("📋 批次新增（每行一個代號，格式：代號 或 代號,名稱,備註）"):
        batch = st.text_area("每行一筆", placeholder="2330\n2454,聯發科\n3661,世芯-KY,長線觀察",
                              height=110, key="batch")
        if st.button("批次新增", key="ba"):
            lines = [l.strip() for l in batch.splitlines() if l.strip()]
            msgs  = []
            for ln in lines:
                parts = [x.strip() for x in ln.split(",")]
                c=parts[0]; n=parts[1] if len(parts)>1 else ""; nt=parts[2] if len(parts)>2 else ""
                if not n: n=lookup_name(c)
                ok,msg = add_stock(c,n,nt); msgs.append(msg)
            if msgs:
                st.success("\n".join(msgs))
                st.rerun()

    st.markdown("---")

    # ── 清單表 ──
    wl = get_all()
    if not wl:
        st.info("目前清單是空的，請新增股票。")
    else:
        st.markdown(f"📋 共 **{len(wl)}** 支股票")
        # 表頭
        h1,h2,h3,h4,h5 = st.columns([0.7,1.0,1.0,2.4,0.8])
        h1.markdown("**代號**"); h2.markdown("**名稱**"); h3.markdown("**加入日期**")
        h4.markdown("**備註**"); h5.markdown("**操作**")
        st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)

        for code, info in wl.items():
            c1,c2,c3,c4,c5 = st.columns([0.7,1.0,1.0,2.4,0.8])
            c1.markdown(f"**{code}**")
            c2.write(info.get("name",""))
            c3.caption(info.get("added",""))
            note_val = c4.text_input("備註", value=info.get("note",""),
                                      key=f"nt_{code}", label_visibility="collapsed")
            if note_val != info.get("note",""):
                update_note(code, note_val)
            if c5.button("🗑️", key=f"d_{code}", help=f"刪除 {info.get('name',code)}"):
                ok,msg = remove_stock(code)
                st.session_state.wl_msg = msg
                st.session_state.wl_msg_type = "ok" if ok else "err"
                st.rerun()


# ═══════════════════════════════════════════
# TAB 1 — 個股分析
# ═══════════════════════════════════════════
with tab_analysis:
    wl_now = get_all()
    if not run_btn and wl_now:
        st.info("📋 自選股：" +
                "  ".join([f"**{v['name']}**({k})" for k,v in list(wl_now.items())[:8]]) +
                ("  ..." if len(wl_now)>8 else "") +
                "\n\n← 在左側輸入代號並點「開始分析」")

    if run_btn:
        code_in = stock_input.strip().replace(".TW","").replace(".TWO","")
        with st.spinner(f"載入 {code_in}..."):
            df_d,df_60,df_30,ticker,cc = fetch_stock(code_in)
            name = wl_now.get(cc,{}).get("name") or lookup_name(cc)

        if df_d is None or len(df_d)<10:
            st.error("❌ 找不到資料，請確認代號。"); st.stop()

        df_d  = add_ind(df_d)
        df_60 = add_ind(df_60) if df_60 is not None and not df_60.empty else None
        df_30 = add_ind(df_30) if df_30 is not None and not df_30.empty else None

        t=df_d.iloc[-1]; p=df_d.iloc[-2]
        s    = sop(df_d)
        f    = fib(df_d)
        atr  = _v(t,"ATR",t["Close"]*.02)
        wd   = wave_lbl(df_d)
        w60  = wave_lbl(df_60) if df_60 is not None else "N/A"
        w30  = wave_lbl(df_30) if df_30 is not None else "N/A"
        ma5  = _v(t,"MA5",f["0.236"])
        ma20 = _v(t,"MA20",f["0.382"])
        ba   = max(ma5,  f["0.236"])
        bc   = max(ma20, f["0.382"])
        stl  = max(t["Close"]-atr*2, f["0.618"])
        vm   = t["VOL_MA5"] if t["VOL_MA5"]>0 else 1
        vr   = round(t["Volume"]/vm,1)
        diff = t["Close"]-p["Close"]; dp=diff/p["Close"]*100
        pcls = "px-up" if diff>0 else "px-down" if diff<0 else "px-flat"
        sg   = "+" if diff>0 else ""

        # ── 標題 ──
        st.markdown(f"## 📊 {name}（{cc}）")
        hc1,hc2,hc3,hc4 = st.columns([2,1.5,1.5,2.5])
        hc1.markdown(
            f"<span class='{pcls}'>{t['Close']:.2f}</span>"
            f"<span style='font-size:15px;color:#666'> {sg}{diff:.2f}（{sg}{dp:.2f}%）</span>",
            unsafe_allow_html=True)
        hc2.metric("成交量",f"{int(t['Volume']/1000)} 張",f"量比 {vr}x")
        hc3.metric("ATR",f"{atr:.2f}")
        hc4.markdown(f"波浪：{wchip(wd)}{wchip(w60)}{wchip(w30)}",unsafe_allow_html=True)

        # 快速加入自選股
        if cc not in wl_now:
            if st.button("⭐ 加入自選股"):
                ok,msg=add_stock(cc,name)
                st.success(msg) if ok else st.warning(msg)

        st.markdown("---")

        # ── SOP 區塊 ──
        sig = s["signal"]
        if sig in ("BUY","SELL"):
            css  = "sop-buy" if sig=="BUY" else "sop-sell"
            act  = "🚀 BUY — SOP 三線全達，最佳進場！" if sig=="BUY" else "⚠️ SELL — 高檔出場訊號！"
            hh   = ""
            if s["cond_vol"]:  hh+=f"<div>💡 量比 {vr}x（≥1.5 加分）</div>"
            if s["wave_hint"]: hh+=f"<div>{s['wave_hint']}</div>"
            ph   = (f"🦁 激進：<b>{ba:.2f}</b> ｜ 🐢 保守：<b>{bc:.2f}</b> ｜ 🛑 停損：<b>{stl:.2f}</b>"
                    if sig=="BUY" else
                    f"⚡ 出場：<b>{t['Close']:.2f}</b> ｜ 🛑 停損：<b>{stl:.2f}</b>")
            st.markdown(f"""
            <div class='{css}'>
                <div class='sop-title'>{act}</div>
                <div class='sop-sub'>
                    ✅ KD：{s['kd_lbl']} &nbsp;｜&nbsp;
                    ✅ MACD：{s['macd_lbl']} &nbsp;｜&nbsp;
                    ✅ SAR：{s['sar_lbl']}
                </div>
                {'<div class="sop-hint">'+hh+'</div>' if hh else ''}
                <div style='margin-top:12px;font-size:15px'>{ph}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("📲 推播到 Telegram", type="primary"):
                ok=push_tg(tg_token,tg_chat,sig,name,cc,t["Close"],s,ba,bc,stl)
                st.success("✅ 推播成功！") if ok else st.warning("⚠️ 請填入 Token / Chat ID")
        else:
            hn=sum([s["cond_kd"],s["cond_macd"],s["cond_sar"]])
            rows="".join([
                f"<div class='cr'><span class='{'ok' if ok else 'ng'}'>{'✅' if ok else '❌'} {lb}</span></div>"
                for ok,lb in [(s["cond_kd"],f"KD：{s['kd_lbl']}"),
                               (s["cond_macd"],f"MACD：{s['macd_lbl']}"),
                               (s["cond_sar"], f"SAR：{s['sar_lbl']}")]
            ])
            svol=(f"<div class='cr'><span class='ht'>💡 量比 {vr}x（軟提示達標✔）</span></div>" if s["cond_vol"]
                  else f"<div class='cr'><span style='color:#888'>💡 量比 {vr}x（未達1.5）</span></div>")
            swav=(f"<div class='cr'><span class='ht'>{s['wave_hint']}（軟提示達標✔）</span></div>" if s["wave_hint"]
                  else f"<div class='cr'><span style='color:#888'>🌊 波浪 {wd}（不在提示範圍）</span></div>")
            st.markdown(f"""
            <div class='watch-box'>
                👀 <b>SOP 觀察中</b>（硬條件 {hn}/3，尚未觸發）
                <div style='margin-top:8px'>{rows}</div>
                <hr style='border:none;border-top:1px dashed #ccc;margin:8px 0'>
                <b style='font-size:13px;color:#888'>💡 軟提示：</b>{svol}{swav}
            </div>""", unsafe_allow_html=True)

        # ── 波浪 + 均線圖 ──
        st.markdown("---")
        w1,w2,w3=st.columns(3)
        w1.info(f"📅 日線\n\n### {wd}")
        w2.warning(f"⏰ 60分K\n\n### {w60}")
        w3.error(f"⚡ 30分K\n\n### {w30}")
        cd=df_d[["Close","MA5","MA20","MA60"]].iloc[-60:].dropna()
        if not cd.empty:
            st.markdown("#### 📈 近 60 日均線")
            st.line_chart(cd,color=["#000000","#e53935","#43a047","#1e88e5"])
            st.caption("黑:收盤｜紅:5MA｜綠:20MA｜藍:60MA")

        # ── 費波那契 + 布林 ──
        st.markdown("---")
        fc,bc2=st.columns(2)
        with fc:
            st.markdown("#### 📐 費波那契")
            for r,k in [("0.236","0.236"),("0.382","0.382"),("0.500","0.500"),("0.618","0.618")]:
                lv=f[k]; tg="✅ 守住" if t["Close"]>lv else "⚠️ 跌破"
                st.write(f"**{r}**：{lv:.2f} — {tg}")
        with bc2:
            st.markdown("#### 🎯 布林通道")
            bb=float(np.clip(_v(t,"BB_PCT",.5),0,1))
            bm="衝出上軌（賣訊）" if bb>1 else "跌破下軌（買訊）" if bb<0 else "區間震盪"
            st.metric("位置",bm); st.progress(bb)
            st.caption(f"{bb*100:.1f}%（0%=下軌，100%=上軌）")

        # ── 目標價 ──
        st.markdown("---"); st.markdown("#### 🎯 目標價")
        for col,mult,lb in zip(st.columns(3),
                                [1.05,1.10,1.20],
                                ["短線+5%","波段+10%","長線+20%"]):
            tp=t["Close"]*mult; dy=max(5,int((tp-t["Close"])/(atr*.4)*2.5))
            col.metric(lb,f"{tp:.2f}",f"約{dy}天")

        st.caption(f"更新：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ AI Stock Bot V1.1")
