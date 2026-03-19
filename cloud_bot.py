"""
AI-stock-bot — Telegram 雲端哨兵 V2.0
每用戶個人化報告：波浪+多因子+目標價+美股連動+新聞+量能
"""
import yfinance as yf, pandas as pd, numpy as np
import requests, time, os
from datetime import datetime, timedelta
import auth, watchlist as wl, targets as tgt
from report_builder import build_full_report

TG_TOKEN  = os.environ.get("TG_TOKEN",   "你的_BOT_TOKEN")
TG_CHAT   = os.environ.get("TG_CHAT_ID", "你的_CHAT_ID")
SOP_COOLDOWN    = 4 * 3600
SIGNAL_COOLDOWN = 1 * 3600

def tg_send(msg, chat_id=None):
    cid = chat_id or TG_CHAT
    if not cid: return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id":cid,"text":msg,"parse_mode":"HTML",
                  "disable_web_page_preview":True}, timeout=10)
    except Exception as e: print(f"[TG] {e}")

def get_df(code, period="1y", interval="1d"):
    for sfx in [".TW",".TWO"]:
        try:
            df=yf.Ticker(code+sfx).history(period=period,interval=interval)
            if not df.empty: return df
        except: pass
    return None

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
    for p in [5,10,20,60]:
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
    return df

def wave_label(df):
    if df is None or len(df)<15: return "N/A"
    c=df["Close"].iloc[-1]
    m20=df["MA20"].iloc[-1] if not pd.isna(df["MA20"].iloc[-1]) else c
    m60=df["MA60"].iloc[-1] if "MA60" in df.columns and not pd.isna(df["MA60"].iloc[-1]) else c
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
    empty={"signal":None,"hard_pass":False,"kd_lbl":"N/A","macd_lbl":"N/A",
           "sar_lbl":"N/A","cond_kd":False,"cond_macd":False,"cond_sar":False,
           "vol_ratio":0,"cond_vol":False,"wave":"N/A","wave_hint":None}
    if df is None or len(df)<30: return empty
    t=df.iloc[-1]; p=df.iloc[-2]
    kd_cross=(p["K"]<p["D"]) and (t["K"]>t["D"])
    cond_kd=t["K"]>t["D"] or kd_cross
    kd_lbl="今日金叉✨" if kd_cross else ("多頭排列" if cond_kd else "空方排列")
    cond_macd=t["MACD_HIST"]>0
    macd_lbl="今日翻紅🔴" if (p["MACD_HIST"]<=0 and t["MACD_HIST"]>0) else \
             ("紅柱延伸" if cond_macd else "綠柱整理")
    cond_sar=float(t["Close"])>float(t["SAR"])
    sar_lbl="多方支撐↑" if cond_sar else "空方壓力↓"
    hard_pass=cond_kd and cond_macd and cond_sar
    vma=t["VOL_MA5"] if t["VOL_MA5"]>0 else 1
    vol_ratio=round(float(t["Volume"])/float(vma),1)
    wave=wave_label(df)
    wave_hint={"3-3":"🌊 3-3主升急漲","3-5":"🏔️ 3-5噴出末段",
               "3-1":"🌱 3-1初升","4-c":"🪤 4-c修正末端"}.get(wave)
    signal=None
    if hard_pass: signal="SELL" if wave in ("3-5","B-c","C-3") else "BUY"
    return {"signal":signal,"hard_pass":hard_pass,
            "cond_kd":cond_kd,"kd_lbl":kd_lbl,
            "cond_macd":cond_macd,"macd_lbl":macd_lbl,
            "cond_sar":cond_sar,"sar_lbl":sar_lbl,
            "cond_vol":vol_ratio>=1.5,"vol_ratio":vol_ratio,
            "wave":wave,"wave_hint":wave_hint}

def basic_signals(df):
    if df is None or len(df)<10: return []
    t=df.iloc[-1]; p=df.iloc[-2]; sigs=[]
    if t["Volume"]>t["VOL_MA5"]*1.5 and t["Close"]>p["Close"]*1.02:
        sigs.append("🚀 <b>出量突破</b>")
    if p["K"]<p["D"] and t["K"]>t["D"] and t["K"]<80:
        sigs.append("✅ <b>KD今日金叉</b>")
    if p["MACD_HIST"]<=0 and t["MACD_HIST"]>0:
        sigs.append("🔴 <b>MACD今日翻紅</b>")
    if t["K"]<40 and t["K"]>p["K"] and t["K"]>t["D"]:
        sigs.append("💧 <b>底部咕嚕</b>")
    recent=df.iloc[-10:]
    streak=0
    for x in reversed(((recent["Close"]>=recent["Open"])|(recent["Close"]>recent["Close"].shift(1))).values):
        if x: streak+=1
        else: break
    if 3<=streak<=10: sigs.append(f"🛡️ <b>主力連買{streak}天</b>")
    return sigs

def build_sop_msg(signal,code,name,df,sop):
    t=df.iloc[-1]; p=df.iloc[-2]
    pct=(t["Close"]-p["Close"])/p["Close"]*100
    icon="🔺" if pct>0 else "💚" if pct<0 else "➖"
    atr=float(t["ATR"]) if not pd.isna(t["ATR"]) else float(t["Close"])*0.02
    hi=df["High"].iloc[-120:].max(); lo=df["Low"].iloc[-120:].min(); diff=hi-lo
    ma5=float(t.get("MA5",t["Close"])); ma20=float(t.get("MA20",t["Close"]))
    buy_agg=max(ma5,hi-diff*0.236); buy_con=max(ma20,hi-diff*0.236)
    stop=max(float(t["Close"])-atr*2,hi-diff*0.618)
    e="🚀" if signal=="BUY" else "⚠️"
    a="BUY — SOP三線觸發！" if signal=="BUY" else "SELL — 高檔出場！"
    pl=(f"🦁 激進:<b>{buy_agg:.2f}</b> 🐢 保守:<b>{buy_con:.2f}</b> 🛑 停損:<b>{stop:.2f}</b>"
        if signal=="BUY" else f"⚡ 出場:<b>{t['Close']:.2f}</b> 🛑 停損:<b>{stop:.2f}</b>")
    soft=("" if not sop["cond_vol"] else f"\n💡 量比{sop['vol_ratio']}x≥1.5")+\
         ("" if not sop["wave_hint"] else f"\n{sop['wave_hint']}")
    return (f"{e} <b>AI Stock Bot SOP</b> {e}\n\n"
            f"<b>{name}（{code}）</b> {icon}{t['Close']:.2f}（{pct:+.2f}%）\n"
            f"━━━━━━━━━━━━━━━━━━\n<b>{a}</b>\n"
            f"✅ KD:{sop['kd_lbl']}\n✅ MACD:{sop['macd_lbl']}\n✅ SAR:{sop['sar_lbl']}"
            f"{soft}\n━━━━━━━━━━━━━━━━━━\n{pl}\n"
            f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>")

# ── 定時報告 ──
def report_open():
    watch=wl.to_dict()
    if not watch: tg_send("🌅 <b>09:30開盤掃描</b>\n⚠️ 觀察名單為空"); return
    lines=["🌅 <b>09:30 開盤掃描</b>\n"]
    for code,name in watch.items():
        df=get_df(code); df=add_ind(df)
        if df is None: continue
        t=df.iloc[-1]; p=df.iloc[-2]
        pct=(t["Close"]-p["Close"])/p["Close"]*100; icon="🔺" if pct>0 else "💚" if pct<0 else "➖"
        vr=round(t["Volume"]/t["VOL_MA5"],1) if t["VOL_MA5"]>0 else 0
        sop=sop_check(df); sigs=basic_signals(df)
        sop_t=" ⚡<b>三線達！</b>" if sop["hard_pass"] else ""
        lines.append(f"<b>{name}({code})</b> {icon}{t['Close']:.2f}({pct:+.2f}%) 量比{vr}x{sop_t}\n"
                     +(f"  {'｜'.join(sigs)}\n" if sigs else "  觀察中\n"))
    tg_send("\n".join(lines))

def report_mid(label):
    watch=wl.to_dict()
    if not watch: tg_send(f"🔔 <b>{label}盤中戰略</b>\n⚠️ 觀察名單為空"); return
    lines=[f"🔔 <b>{label} 盤中戰略</b>\n"]
    for code,name in watch.items():
        df=get_df(code); df=add_ind(df)
        if df is None: continue
        t=df.iloc[-1]; p=df.iloc[-2]
        pct=(t["Close"]-p["Close"])/p["Close"]*100; icon="🔺" if pct>0 else "💚" if pct<0 else "➖"
        sop=sop_check(df); sigs=basic_signals(df)
        hn=sum([sop["cond_kd"],sop["cond_macd"],sop["cond_sar"]])
        sl=("🚀 <b>SOP BUY！</b>" if sop["signal"]=="BUY"
            else "⚠️ <b>SOP SELL！</b>" if sop["signal"]=="SELL"
            else f"👀 觀察中（{hn}/3）")
        hints=("" if not sop["cond_vol"] else f" 💡量比{sop['vol_ratio']}x")+\
              ("" if not sop["wave_hint"] else f" 🌊{sop['wave']}")
        lines.append(f"<b>{name}({code})</b> {icon}{t['Close']:.2f}({pct:+.2f}%)\n  {sl}{hints}\n"
                     +(f"  {'｜'.join(sigs)}\n" if sigs else ""))
    tg_send("\n".join(lines))

def report_close():
    watch=wl.to_dict()
    if not watch: tg_send("🌇 <b>13:36收盤確認</b>\n⚠️ 觀察名單為空"); return
    lines=["🌇 <b>13:36 收盤確認</b>\n"]
    for code,name in watch.items():
        df=get_df(code); df=add_ind(df)
        if df is None: continue
        t=df.iloc[-1]; p=df.iloc[-2]
        pct=(t["Close"]-p["Close"])/p["Close"]*100; icon="🔺" if pct>0 else "💚" if pct<0 else "➖"
        atr=float(t["ATR"]) if not pd.isna(t["ATR"]) else float(t["Close"])*0.02
        ma20=float(t.get("MA20",t["Close"]))
        lines.append(f"<b>{name}({code})</b> <b>{icon}{t['Close']:.2f}({pct:+.2f}%)</b>\n"
                     f"  🎯 低接參考:{ma20:.2f} ｜ 🛑 停損:{float(t['Close'])-atr*2:.2f}\n")
    tg_send("\n".join(lines))

def report_evening_personal():
    """18:40 個人化深度報告 — 發送給每位有 Telegram ID 的用戶"""
    all_users=auth.get_all_users()
    for uname,uinfo in all_users.items():
        chat_id=uinfo.get("telegram_chat_id","")
        if not chat_id: continue
        user_codes=uinfo.get("watchlist",[])
        if not user_codes: continue

        user_tgts=tgt.get_user_all_targets(uname)
        tg_send(f"🌙 <b>{uinfo.get('display_name',uname)} 的盤後個人報告</b>\n"
                f"共追蹤 {len(user_codes)} 支股票，以下逐一分析 👇", chat_id=chat_id)

        for code in user_codes:
            try:
                name=wl.to_dict().get(code,code)
                target_price=user_tgts.get(code,{}).get("target_price") if code in user_tgts else None
                msg=build_full_report(code,name,target_price,uinfo.get("display_name",uname))
                tg_send(msg, chat_id=chat_id)
                time.sleep(1)   # 避免 TG rate limit
            except Exception as e:
                tg_send(f"❌ {code} 報告生成失敗：{e}", chat_id=chat_id)

        tg_send(f"✅ 今日報告完畢！祝投資順利 🎯\n"
                f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>",
                chat_id=chat_id)

# ── 主迴圈 ──
SCHEDULE = {
    "09:30":"open","10:20":"mid","12:00":"mid",
    "13:36":"close","18:40":"evening"
}

def run():
    print("🤖 AI Stock Bot V2.0 啟動（個人化報告版）...")
    tg_send(
        "🤖 <b>AI Stock Bot V2.0 上線！</b>\n\n"
        "✨ 新功能：<b>個人化深度報告</b>\n"
        "每日 18:40 依各用戶觀察名單+目標價\n"
        "發送波浪理論、多因子分析、美股連動、最新消息、量能偵測\n\n"
        "登入 app.py 設定你的 Telegram Chat ID 即可接收 📲"
    )

    sent:dict={t:False for t in SCHEDULE}
    sop_h:dict={}; sig_h:dict={}

    while True:
        now=datetime.utcnow()+timedelta(hours=8)
        hm=now.strftime("%H:%M"); wday=now.weekday()
        is_work=wday<=4
        is_active=is_work and 8<=now.hour<=19
        is_trade=is_work and (now.hour==9 or (9<now.hour<13) or (now.hour==13 and now.minute<=30))

        if not is_active:
            print(f"\r💤 {hm} 休市",end="")
            if hm=="00:00":
                for k in sent: sent[k]=False
            time.sleep(60); continue

        users_count=len(auth.get_all_users())
        wl_count=len(wl.to_dict())
        print(f"\r🔄 {hm} {'交易' if is_trade else '盤後'} | 用戶:{users_count} 名單:{wl_count}支",end="")

        # 定時報告
        if hm in SCHEDULE and not sent[hm]:
            rt=SCHEDULE[hm]; print(f"\n⏰ {hm} {rt}")
            if   rt=="open":    report_open()
            elif rt=="mid":     report_mid(hm)
            elif rt=="close":   report_close()
            elif rt=="evening": report_evening_personal()
            sent[hm]=True

        if hm=="08:00":
            for k in sent: sent[k]=False

        # 即時 SOP 掃描
        if is_trade:
            watch=wl.to_dict()
            for code,name in watch.items():
                try:
                    last_sop=sop_h.get(code)
                    sop_ok=not last_sop or (now-last_sop).seconds>=SOP_COOLDOWN
                    if sop_ok:
                        df=get_df(code);
                        if df is None: continue
                        df=add_ind(df); sop=sop_check(df)
                        if sop["signal"] in ("BUY","SELL"):
                            base_msg=build_sop_msg(sop["signal"],code,name,df,sop)
                            # 廣播給所有有設定 TG ID 且名單中有此股的用戶
                            all_users=auth.get_all_users()
                            for uname,uinfo in all_users.items():
                                cid=uinfo.get("telegram_chat_id","")
                                if cid and code in uinfo.get("watchlist",[]):
                                    tg_send(base_msg, chat_id=cid)
                            sop_h[code]=now
                            print(f"\n🚨 {hm} SOP {sop['signal']} → {name}({code})")
                            continue

                    last_sig=sig_h.get(code)
                    sig_ok=not last_sig or (now-last_sig).seconds>=SIGNAL_COOLDOWN
                    if not sig_ok: continue
                    df=get_df(code);
                    if df is None: continue
                    df=add_ind(df); sigs=basic_signals(df)
                    if sigs:
                        t=df.iloc[-1]; p=df.iloc[-2]
                        pct=(t["Close"]-p["Close"])/p["Close"]*100
                        icon="🔺" if pct>0 else "💚" if pct<0 else "➖"
                        msg=(f"🚨 <b>盤中訊號快報</b>\n<b>{name}（{code}）</b>"
                             f" {icon}{t['Close']:.2f}（{pct:+.2f}%）\n"
                             +"\n".join(sigs)+f"\n<i>{hm}</i>")
                        all_users=auth.get_all_users()
                        for uname,uinfo in all_users.items():
                            cid=uinfo.get("telegram_chat_id","")
                            if cid and code in uinfo.get("watchlist",[]):
                                tg_send(msg, chat_id=cid)
                        sig_h[code]=now
                except: pass

        time.sleep(30)

if __name__=="__main__":
    run()
