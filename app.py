"""
AI-stock-bot — Streamlit 主程式 V2.0
多用戶、登入、目標價、個人觀察名單、管理員後台
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import auth
import targets as tgt
import watchlist as wl

st.set_page_config(page_title="AI Stock Bot", page_icon="🤖", layout="wide")
st.markdown("""
<style>
body{font-family:'Segoe UI',sans-serif;}
@keyframes glow{0%,100%{box-shadow:0 0 6px #00c853}50%{box-shadow:0 0 22px 8px #00c853}}
@keyframes glow-s{0%,100%{box-shadow:0 0 6px #ff1744}50%{box-shadow:0 0 22px 8px #ff1744}}
.sop-buy{background:linear-gradient(135deg,#003300,#006600);border:2px solid #00c853;
    border-radius:12px;padding:20px 26px;margin:12px 0;animation:glow 2s infinite;color:#fff;}
.sop-sell{background:linear-gradient(135deg,#330000,#660000);border:2px solid #ff1744;
    border-radius:12px;padding:20px 26px;margin:12px 0;animation:glow-s 2s infinite;color:#fff;}
.sop-title{font-size:22px;font-weight:900;letter-spacing:1px;}
.sop-sub{font-size:14px;margin-top:8px;line-height:1.9;}
.watch-b{background:#f9f9f9;border:2px dashed #bbb;border-radius:10px;
    padding:14px 20px;margin:10px 0;font-size:14px;color:#444;}
.pass{color:#2e7d32;font-weight:600;} .fail{color:#c62828;font-weight:600;}
.hint{color:#e65100;font-weight:600;} .cond-row{font-size:15px;line-height:2;}
.wchip{display:inline-block;font-size:13px;font-weight:bold;
    padding:2px 10px;border-radius:20px;margin-right:6px;}
.wbull{background:#e8f5e9;color:#2e7d32;border:1px solid #a5d6a7;}
.wbear{background:#ffebee;color:#c62828;border:1px solid #ef9a9a;}
.wneut{background:#fff3e0;color:#e65100;border:1px solid #ffcc80;}
.pup{color:#d32f2f;font-weight:800;font-size:26px;}
.pdn{color:#388e3c;font-weight:800;font-size:26px;}
.pflt{color:#555;font-weight:800;font-size:26px;}
.login-wrap{display:flex;align-items:center;justify-content:center;min-height:70vh;}
.badge-admin{background:#e3f2fd;color:#1565c0;font-size:12px;
    padding:2px 8px;border-radius:10px;font-weight:600;margin-left:6px;}
.badge-user{background:#f3e5f5;color:#6a1b9a;font-size:12px;
    padding:2px 8px;border-radius:10px;font-weight:600;margin-left:6px;}
</style>
""", unsafe_allow_html=True)

# ── Session init ──
if "user" not in st.session_state:
    st.session_state.user = None

def logout():
    st.session_state.user = None
    st.rerun()

# ════════════════════════════════════════
# 登入頁
# ════════════════════════════════════════
if st.session_state.user is None:
    _,mid,_ = st.columns([1,1.4,1])
    with mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("## 🤖 AI Stock Bot")
            st.caption("V2.0 多用戶版 — 請先登入")
            st.markdown("---")
            uname = st.text_input("帳號", placeholder="輸入帳號")
            upw   = st.text_input("密碼", type="password", placeholder="輸入密碼")
            if st.button("🔐 登入", type="primary", use_container_width=True):
                u = auth.login(uname, upw)
                if u:
                    st.session_state.user = u
                    st.success(f"歡迎，{u['display_name']}！")
                    st.rerun()
                else:
                    st.error("❌ 帳號或密碼錯誤")
            st.caption("預設管理員帳號：ruby / admin1234（請登入後立即修改密碼）")
    st.stop()

# ════════════════════════════════════════
# 已登入
# ════════════════════════════════════════
user = st.session_state.user
is_admin = user.get("role") == "admin"

with st.sidebar:
    st.markdown(f"### 👤 {user['display_name']}")
    badge = "👑 管理員" if is_admin else "👤 一般用戶"
    st.caption(f"{badge}  |  @{user['username']}")
    st.markdown("---")
    st.subheader("📲 Telegram 推播")
    tg_token = st.text_input("Bot Token", type="password",
                              placeholder="從 BotFather 取得", key="sb_tok")
    tg_chat  = st.text_input("Chat ID",
                              value=user.get("telegram_chat_id",""),
                              placeholder="你的 Chat ID", key="sb_chat")
    if st.button("💾 儲存 Chat ID", use_container_width=True):
        auth.update_telegram(user["username"], tg_chat)
        st.session_state.user["telegram_chat_id"] = tg_chat
        st.success("✅ 已儲存")
    st.markdown("---")
    st.caption("SOP 條件：KD金叉/多頭 + MACD翻紅 + SAR多方")
    if st.button("🚪 登出", use_container_width=True):
        logout()

# ── Tabs ──
_tabs = ["📊 個股分析","📋 觀察名單","🎯 目標價","⚙️ 帳號設定"]
if is_admin: _tabs.append("👑 用戶管理")
tabs = st.tabs(_tabs)
tab_ana = tabs[0]; tab_wl = tabs[1]; tab_tgt = tabs[2]; tab_acc = tabs[3]
tab_admin = tabs[4] if is_admin else None

# ════════════════════════════════════════
# 技術指標工具函數
# ════════════════════════════════════════
@st.cache_data(ttl=1800)
def fetch_stock(symbol):
    clean = symbol.strip().replace(".TW","").replace(".TWO","")
    for sfx in [".TW",".TWO"]:
        try:
            t = yf.Ticker(clean+sfx)
            df = t.history(period="2y")
            if df.empty: df = t.history(period="max")
            if not df.empty:
                return df, t.history(period="1mo",interval="60m"), \
                       t.history(period="1mo",interval="30m"), t, clean
        except: continue
    return None,None,None,None,clean

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

def _sar(high,low,af0=0.02,af_max=0.2):
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
    df["VOL_MA20"]=df["Volume"].rolling(20).mean()
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
    macd_label="今日翻紅🔴" if (p["MACD_HIST"]<=0 and t["MACD_HIST"]>0) else \
               ("紅柱延伸" if cond_macd else "綠柱整理")
    cond_sar=float(t["Close"])>float(t["SAR"])
    sar_label="多方支撐↑" if cond_sar else "空方壓力↓"
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
    return {"high":hi,"low":lo,"0.236":hi-d*0.236,"0.382":hi-d*0.382,
            "0.500":hi-d*0.5,"0.618":hi-d*0.618}

def push_tg(token,chat_id,signal,name,code,price,sop,buy_agg,buy_con,stop):
    if not token or not chat_id: return False
    e="🚀" if signal=="BUY" else "⚠️"
    a="BUY — SOP 三線觸發！" if signal=="BUY" else "SELL — 高檔出場！"
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

# ════════════════════════════════════════
# TAB 1：個股分析
# ════════════════════════════════════════
with tab_ana:
    st.markdown("### 🔍 個股分析")
    c1,c2,c3=st.columns([3,1,2])
    with c1: si=st.text_input("代號","2330",label_visibility="collapsed",key="ana_in")
    with c2: run_btn=st.button("🚀 分析",type="primary",use_container_width=True)
    with c3: add_wl=st.button("➕ 加入觀察名單",use_container_width=True,key="ana_wl")

    if add_wl and si:
        cc2=si.strip().replace(".TW","").replace(".TWO","")
        nm2=fetch_name(cc2)
        auth.add_to_watchlist(user["username"],cc2)
        wl.add(cc2,nm2)
        st.success(f"✅ {nm2}（{cc2}）已加入觀察名單")

    if run_btn:
        cc=si.strip().replace(".TW","").replace(".TWO","")
        with st.spinner(f"載入 {cc} ..."):
            df_d,df_60,df_30,_ticker,cc=fetch_stock(cc)
            nm=fetch_name(cc)
        if df_d is None or len(df_d)<10:
            st.error("❌ 找不到資料，請確認代號"); st.stop()

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
        pcls="pup" if diff>0 else "pdn" if diff<0 else "pflt"
        ps="+" if diff>0 else ""

        st.markdown(f"## {nm}（{cc}）")
        co1,co2,co3=st.columns([2,2,3])
        co1.markdown(f"<span class='{pcls}'>{t['Close']:.2f}</span>",unsafe_allow_html=True)
        co1.caption(f"{ps}{diff:.2f}（{ps}{dp:.2f}%）")
        co2.metric("成交量",f"{int(t['Volume']/1000)} 張",f"量比 {vol_r}x")
        co3.markdown(f"波浪：{wchip(w_d)}{wchip(w_60)}{wchip(w_30)}",unsafe_allow_html=True)

        # 個人目標價快速顯示
        my_tgt=tgt.get_user_target(user["username"],cc)
        if my_tgt:
            tc=tgt.check_target_reached(t["Close"],my_tgt["target_price"])
            st.info(f"🎯 你的目標價：**{my_tgt['target_price']:.2f}** ｜ {tc['status']} — {tc['desc']}")

        st.markdown("---")
        signal=sop["signal"]
        if signal in ("BUY","SELL"):
            css="sop-buy" if signal=="BUY" else "sop-sell"
            atxt="🚀 BUY — SOP 三線全達！" if signal=="BUY" else "⚠️ SELL — 高檔出場訊號！"
            hints=""
            if sop["cond_vol"]:  hints+=f"<div>💡 量比{vol_r}x（≥1.5加分）</div>"
            if sop["wave_hint"]: hints+=f"<div>{sop['wave_hint']}</div>"
            phtml=(f"<b>🦁 激進:{buy_agg:.2f}</b>｜<b>🐢 保守:{buy_con:.2f}</b>｜<b>🛑 停損:{stop:.2f}</b>"
                   if signal=="BUY"
                   else f"<b>⚡ 出場:{t['Close']:.2f}</b>｜<b>🛑 停損:{stop:.2f}</b>")
            st.markdown(f"""<div class='{css}'>
                <div class='sop-title'>{atxt}</div>
                <div class='sop-sub'>✅KD:{sop['kd_label']} &nbsp;｜&nbsp;
                ✅MACD:{sop['macd_label']} &nbsp;｜&nbsp;✅SAR:{sop['sar_label']}</div>
                {'<div style="background:rgba(255,255,255,0.1);border-radius:8px;padding:8px 12px;margin-top:10px;color:#ffe082">'+hints+'</div>' if hints else ''}
                <div style='margin-top:12px;font-size:15px'>{phtml}</div>
            </div>""",unsafe_allow_html=True)
            _,_,tg_col=st.columns(3)
            with tg_col:
                if st.button("📲 推播到Telegram",type="primary",use_container_width=True):
                    ok=push_tg(tg_token,tg_chat,signal,nm,cc,t["Close"],sop,buy_agg,buy_con,stop)
                    st.success("✅ 推播成功！") if ok else st.warning("⚠️ 請先在側邊欄填入Token/ID")
        else:
            hc=sum([sop["cond_kd"],sop["cond_macd"],sop["cond_sar"]])
            rows="".join([f"<div class='cond-row'><span class='{'pass' if ok else 'fail'}'>{'✅' if ok else '❌'} {lb}</span></div>"
                          for ok,lb in [(sop["cond_kd"],f"KD:{sop['kd_label']}"),
                                        (sop["cond_macd"],f"MACD:{sop['macd_label']}"),
                                        (sop["cond_sar"],f"SAR:{sop['sar_label']}")]])
            soft_h=(f"<span class='hint'>💡 量比{vol_r}x≥1.5 ✔</span><br>" if sop["cond_vol"]
                    else f"<span style='color:#888'>💡 量比{vol_r}x（未達1.5）</span><br>")
            soft_h+=(f"<span class='hint'>{sop['wave_hint']} ✔</span>" if sop["wave_hint"]
                     else f"<span style='color:#888'>🌊 波浪{w_d}（非提示範圍）</span>")
            st.markdown(f"""<div class='watch-b'>👀 <b>SOP觀察中</b>（硬條件{hc}/3達標）
                <div style='margin-top:10px'>{rows}</div>
                <hr style='border:none;border-top:1px dashed #ccc;margin:10px 0'>
                <b style='font-size:13px;color:#888'>軟提示：</b><br>{soft_h}
            </div>""",unsafe_allow_html=True)

        st.markdown("---")
        cw1,cw2,cw3=st.columns(3)
        cw1.info(f"📅 日線\n\n### {w_d}")
        cw2.warning(f"⏰ 60分\n\n### {w_60}")
        cw3.error(f"⚡ 30分\n\n### {w_30}")
        cd=df_d[["Close","MA5","MA20","MA60"]].iloc[-60:].dropna()
        if not cd.empty:
            st.markdown("#### 📈 近60日均線圖")
            st.line_chart(cd,color=["#000000","#e53935","#43a047","#1e88e5"])
            st.caption("黑:收盤｜紅:5MA｜綠:20MA｜藍:60MA")

        st.markdown("---")
        fc,bc=st.columns(2)
        with fc:
            st.markdown("#### 📐 費波那契")
            prc=t["Close"]
            for ratio,key in [("0.236","0.236"),("0.382","0.382"),("0.500","0.500"),("0.618","0.618")]:
                lvl=fib[key]; tag="✅ 守住" if prc>lvl else "⚠️ 跌破"
                st.write(f"**{ratio}**：{lvl:.2f} — {tag}")
        with bc:
            st.markdown("#### 🎯 布林通道")
            bb=_v(t,"BB_PCT",0.5)
            bm="衝出上軌（賣訊）" if bb>1 else "跌破下軌（買訊）" if bb<0 else "區間震盪"
            st.metric("位置",bm); st.progress(float(np.clip(bb,0,1)))
            st.caption(f"通道{bb*100:.0f}%位置")

        st.markdown("---"); st.markdown("#### 🎯 目標價預估")
        t1,t2,t3=st.columns(3)
        for col,mult,lb in [(t1,1.05,"短線+5%"),(t2,1.10,"波段+10%"),(t3,1.20,"長線+20%")]:
            tp=t["Close"]*mult; days=max(5,int((tp-t["Close"])/max(atr*0.4,0.01)*2.5))
            col.metric(lb,f"{tp:.2f}",f"約{days}天")
        st.caption(f"更新：{datetime.now().strftime('%Y-%m-%d %H:%M')} | AI Stock Bot V2.0")

# ════════════════════════════════════════
# TAB 2：觀察名單
# ════════════════════════════════════════
with tab_wl:
    st.markdown("### 📋 我的觀察名單")
    st.caption("個人獨立名單，Cloud Bot 每天自動發送報告到你的 Telegram。")
    with st.container(border=True):
        a1,a2,a3=st.columns([2,2,1])
        with a1: nc=st.text_input("代號",placeholder="如 2330",key="wl_c",label_visibility="collapsed")
        with a2: nn=st.text_input("名稱（空白自動查詢）",placeholder="如 台積電",key="wl_n",label_visibility="collapsed")
        with a3: ab=st.button("➕ 新增",type="primary",use_container_width=True,key="wl_ab")
    if ab and nc:
        code_in=nc.strip().replace(".TW","").replace(".TWO","")
        nm_in=nn.strip() or fetch_name(code_in)
        auth.add_to_watchlist(user["username"],code_in)
        wl.add(code_in,nm_in)
        st.success(f"✅ 已新增 {nm_in}（{code_in}）"); st.rerun()

    st.markdown("---")
    my_codes=auth.get_user_watchlist(user["username"])
    st.markdown(f"#### 追蹤中：{len(my_codes)} 支")
    if not my_codes:
        st.info("尚無觀察股票，請在上方新增 ☝️")
    else:
        wl_data=wl.load()
        for code in my_codes:
            nm=wl_data.get(code,{}).get("name",code) if code in wl_data else code
            my_tgt_e=tgt.get_user_target(user["username"],code)
            tgt_txt=f"🎯 目標：{my_tgt_e['target_price']:.2f}" if my_tgt_e else "尚無目標價"
            cl1,cl2,cl3,cl4=st.columns([1,2,2,1])
            cl1.markdown(f"**{code}**"); cl2.write(nm); cl3.caption(tgt_txt)
            with cl4:
                if st.button("🗑️",key=f"rwl_{code}",use_container_width=True):
                    auth.remove_from_watchlist(user["username"],code)
                    st.success(f"已移除 {code}"); st.rerun()

    st.markdown("---")
    st.markdown("#### 📅 每日自動推播時間")
    st.markdown("""
| 時間 | 內容 |
|------|------|
| 09:30 | 🌅 開盤掃描 |
| 10:20 / 12:00 | 🔔 盤中戰略 + SOP 狀態 |
| 13:36 | 🌇 收盤確認 |
| 18:40 | 🌙 **個人深度報告** (波浪+多因子+目標價+美股+新聞+量能) |
| 即時 | ⚡ SOP 三線觸發立即推播 |
> 需啟動 `cloud_bot.py` 才會自動發送。
""")

# ════════════════════════════════════════
# TAB 3：目標價
# ════════════════════════════════════════
with tab_tgt:
    st.markdown("### 🎯 目標價管理")
    with st.container(border=True):
        st.markdown("#### ➕ 設定目標價")
        t1c,t2c,t3c,t4c=st.columns([2,1.5,2,1])
        with t1c: tc_code=st.text_input("代號",placeholder="如 2330",key="tc",label_visibility="collapsed")
        with t2c: tc_price=st.number_input("目標價",min_value=0.0,step=0.5,format="%.2f",key="tp",label_visibility="collapsed")
        with t3c: tc_note=st.text_input("備註",placeholder="如 波段目標",key="tn",label_visibility="collapsed")
        with t4c: tc_btn=st.button("💾 儲存",type="primary",use_container_width=True,key="ts")
    if tc_btn and tc_code and tc_price>0:
        code_in=tc_code.strip().replace(".TW","").replace(".TWO","")
        ok=tgt.set_target(user["username"],user["display_name"],code_in,tc_price,tc_note)
        st.success(f"✅ 已設定 {code_in} 目標價 {tc_price:.2f}") if ok else st.error("儲存失敗")
        st.rerun()

    st.markdown("---")
    my_tgts=tgt.get_user_all_targets(user["username"])
    st.markdown(f"#### 📌 我的目標價（{len(my_tgts)} 支）")
    if not my_tgts:
        st.info("尚無目標價，請在上方設定 ☝️")
    else:
        for code,entry in my_tgts.items():
            nm=fetch_name(code)
            price_now=None
            try:
                for sfx in [".TW",".TWO"]:
                    df_tmp=yf.Ticker(code+sfx).history(period="5d")
                    if not df_tmp.empty: price_now=df_tmp["Close"].iloc[-1]; break
            except: pass
            with st.container(border=True):
                r1,r2,r3=st.columns([3,3,1])
                with r1:
                    st.markdown(f"**{nm}（{code}）**")
                    if price_now:
                        tc2=tgt.check_target_reached(price_now,entry["target_price"])
                        st.markdown(f"🎯 目標：**{entry['target_price']:.2f}** ｜ {tc2['status']}")
                        if entry.get("note"): st.caption(f"備註：{entry['note']}")
                with r2:
                    if price_now:
                        gap_p=abs((entry["target_price"]-price_now)/price_now*100)
                        st.metric("現價",f"{price_now:.2f}",
                                  f"距目標{gap_p:.1f}%" if price_now<entry["target_price"] else "✅已達標")
                        st.progress(float(np.clip(price_now/entry["target_price"],0,1)))
                    st.caption(f"設定於 {entry.get('updated_at','—')}")
                with r3:
                    if st.button("🗑️",key=f"dt_{code}",use_container_width=True):
                        tgt.delete_target(user["username"],code)
                        st.success(f"已刪除"); st.rerun()

    # 管理員總覽
    if is_admin:
        st.markdown("---")
        st.markdown("#### 👑 全用戶目標價總覽（管理員限定）")
        all_tgts=tgt.get_all_targets_admin()
        if not all_tgts:
            st.info("尚無任何用戶設定目標價")
        else:
            for code,entries in all_tgts.items():
                nm=fetch_name(code)
                with st.expander(f"📌 {nm}（{code}）— {len(entries)} 人設定"):
                    for e in entries:
                        dot="🔵" if e["username"]==user["username"] else "⚪"
                        st.markdown(f"{dot} **{e['display_name']}**（@{e['username']}）"
                                    f" 目標：{e['target_price']:.2f}｜"
                                    f"{e.get('note','—')}｜{e.get('updated_at','—')}")

# ════════════════════════════════════════
# TAB 4：帳號設定
# ════════════════════════════════════════
with tab_acc:
    st.markdown("### ⚙️ 帳號設定")
    with st.container(border=True):
        st.markdown("#### 🔑 修改密碼")
        op=st.text_input("舊密碼",type="password",key="op")
        np1=st.text_input("新密碼",type="password",key="np1")
        np2=st.text_input("確認新密碼",type="password",key="np2")
        if st.button("更新密碼",type="primary"):
            if np1!=np2: st.error("❌ 兩次新密碼不一致")
            else:
                ok,msg=auth.change_password(user["username"],op,np1)
                st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")
    with st.container(border=True):
        st.markdown("#### 📲 Telegram 設定")
        st.caption("設定後 Cloud Bot 每天自動發送個人深度報告")
        cur_id=user.get("telegram_chat_id","")
        new_id=st.text_input("我的 Telegram Chat ID",value=cur_id,placeholder="從 @userinfobot 取得")
        if st.button("💾 儲存",type="primary",key="save_tg_acc"):
            auth.update_telegram(user["username"],new_id)
            st.session_state.user["telegram_chat_id"]=new_id
            st.success("✅ 已儲存！Cloud Bot 下次將發送到此 ID")
    st.markdown("---")
    st.markdown("#### ℹ️ 帳號資訊")
    info=auth.get_user(user["username"])
    ca,cb=st.columns(2)
    ca.metric("帳號",user["username"])
    ca.metric("角色","管理員👑" if is_admin else "一般用戶")
    cb.metric("顯示名稱",user["display_name"])
    cb.metric("建立時間",info.get("created_at","—") if info else "—")

# ════════════════════════════════════════
# TAB 5：用戶管理（管理員限定）
# ════════════════════════════════════════
if is_admin and tab_admin:
    with tab_admin:
        st.markdown("### 👑 用戶管理")
        with st.container(border=True):
            st.markdown("#### ➕ 新增用戶")
            u1,u2,u3,u4,u5=st.columns([2,2,2,1.5,1])
            with u1: nu=st.text_input("帳號",placeholder="英文小寫",key="nu",label_visibility="collapsed")
            with u2: npw=st.text_input("密碼",type="password",placeholder="至少4碼",key="npw",label_visibility="collapsed")
            with u3: nd=st.text_input("顯示名稱",placeholder="如：小明",key="nd",label_visibility="collapsed")
            with u4: nr=st.selectbox("角色",["user","admin"],key="nr",label_visibility="collapsed")
            with u5: nb=st.button("➕",type="primary",use_container_width=True,key="nb")
            if nb:
                ok,msg=auth.create_user(nu,npw,nd,nr)
                st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}"); st.rerun()

        st.markdown("---")
        all_users=auth.get_all_users()
        st.markdown(f"#### 👥 用戶列表（{len(all_users)} 人）")
        for uname,uinfo in all_users.items():
            rbadge=("<span class='badge-admin'>👑 管理員</span>" if uinfo.get("role")=="admin"
                    else "<span class='badge-user'>👤 一般用戶</span>")
            tg_s="✅ 已設定" if uinfo.get("telegram_chat_id") else "❌ 未設定"
            wl_n=len(uinfo.get("watchlist",[]))
            tgt_n=len(tgt.get_user_all_targets(uname))
            with st.container(border=True):
                r1,r2,r3,r4=st.columns([3,2,2,1])
                with r1:
                    st.markdown(f"**{uinfo.get('display_name',uname)}** (@{uname}) {rbadge}",
                                unsafe_allow_html=True)
                    st.caption(f"建立：{uinfo.get('created_at','—')}")
                with r2:
                    st.write(f"📲 TG：{tg_s}")
                    st.write(f"📋 觀察：{wl_n}支 ｜ 🎯 目標：{tgt_n}支")
                with r3:
                    rpw=st.text_input("重設密碼",type="password",placeholder="輸入新密碼",
                                      key=f"rpw_{uname}",label_visibility="collapsed")
                    if st.button("🔑 重設",key=f"rset_{uname}",use_container_width=True):
                        ok,msg=auth.admin_reset_password(uname,rpw)
                        st.success(msg) if ok else st.error(msg)
                with r4:
                    if uname!=user["username"]:
                        if st.button("🗑️",key=f"du_{uname}",use_container_width=True):
                            ok,msg=auth.delete_user(uname)
                            st.success(msg) if ok else st.error(msg); st.rerun()
                    else: st.caption("（自己）")
