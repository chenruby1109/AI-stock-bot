"""
report_builder.py — 每日個股深度報告生成器
包含：波浪理論、多因子分析、目標價條件、美股連動、最新消息、成交量啟動偵測
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ─────────────────────────────────────────
# 指標計算（獨立，不依賴 app.py）
# ─────────────────────────────────────────
def _sar(high, low, af0=0.02, af_max=0.2):
    n=len(high); sar=np.zeros(n); trend=np.ones(n)
    ep=np.zeros(n); af=np.full(n,af0)
    sar[0]=low[0]; ep[0]=high[0]
    for i in range(1,n):
        sar[i]=sar[i-1]+af[i-1]*(ep[i-1]-sar[i-1])
        if trend[i-1]==1:
            if low[i]<sar[i]:
                trend[i]=-1; sar[i]=ep[i-1]; ep[i]=low[i]; af[i]=af0
            else:
                trend[i]=1
                if high[i]>ep[i-1]: ep[i]=high[i]; af[i]=min(af[i-1]+af0,af_max)
                else: ep[i]=ep[i-1]; af[i]=af[i-1]
                sar[i]=min(sar[i],low[i-1])
                if i>1: sar[i]=min(sar[i],low[i-2])
        else:
            if high[i]>sar[i]:
                trend[i]=1; sar[i]=ep[i-1]; ep[i]=high[i]; af[i]=af0
            else:
                trend[i]=-1
                if low[i]<ep[i-1]: ep[i]=low[i]; af[i]=min(af[i-1]+af0,af_max)
                else: ep[i]=ep[i-1]; af[i]=af[i-1]
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
    return df

def get_df(code: str, period="1y", interval="1d"):
    for sfx in [".TW",".TWO"]:
        try:
            df=yf.Ticker(code+sfx).history(period=period,interval=interval)
            if not df.empty: return df
        except: pass
    return None

# ─────────────────────────────────────────
# 1. 波浪理論分析
# ─────────────────────────────────────────
def analyze_wave(df) -> dict:
    if df is None or len(df)<15:
        return {"label":"N/A","desc":"資料不足","suggestion":""}
    t=df.iloc[-1]; p=df.iloc[-2]
    c=t["Close"]
    m20=t["MA20"] if not pd.isna(t["MA20"]) else c
    m60=t["MA60"] if not pd.isna(t["MA60"]) else c
    k=t["K"]; pk=p["K"]
    h=t["MACD_HIST"]; ph=p["MACD_HIST"]

    wave_map = {
        "3-3": ("3-3 主升急漲",
                "多頭最強波段，MACD 紅柱放大，動能充沛",
                "沿5MA持倉，不追高，等拉回再加碼"),
        "3-5": ("3-5 噴出末段",
                "主升末端，K值高檔，短線過熱風險升高",
                "逢高分批出場，嚴設停利於最近高點下方"),
        "3-1": ("3-1 初升段",
                "趨勢剛翻多，KD 低位金叉，屬起漲初期",
                "可試單，停損設於前低"),
        "3-a": ("3-a 高檔震盪",
                "漲勢放緩，MACD 高位鈍化，需觀察",
                "持股續抱，量縮整理後可再攻"),
        "4-a": ("4-a 初跌修正",
                "主升後回測，正常修正，趨勢仍多",
                "等修正至 0.382 或 20MA 附近再加碼"),
        "4-b": ("4-b 反彈逃命",
                "空頭反彈，趨勢仍弱，是出場機會",
                "反彈至壓力區減碼，嚴控停損"),
        "4-c": ("4-c 修正末端",
                "K值低檔，接近底部，轉機觀察點",
                "等KD低位金叉確認後再進場"),
        "C-3": ("C-3 主跌段",
                "空頭核心波，跌勢最猛烈",
                "避免抄底，等止跌訊號再評估"),
        "C-5": ("C-5 趕底急殺",
                "K值極低，可能是最後一跌",
                "觀察止跌K棒，少量試單，停損要嚴"),
        "B-a": ("B-a 跌深反彈",
                "空頭中的短線反彈，非主升",
                "短線操作，不宜重倉"),
        "B-c": ("B-c 反彈高點",
                "反彈到壓力區，空頭格局未改",
                "此處是放空或出清的機會"),
    }

    if c>=m60:
        if c>m20:
            if h>0 and h>ph: label="3-5" if k>80 else "3-3"
            elif h>0: label="3-a"
            else: label="3-1"
        else:
            if k<20: label="4-c"
            elif k<pk: label="4-a"
            else: label="4-b"
    else:
        if c<m20: label="C-5" if k<20 else "C-3"
        else: label="B-c" if k>80 else "B-a"

    info=wave_map.get(label,("N/A","",""))
    return {"label":label,"title":info[0],"desc":info[1],"suggestion":info[2]}

# ─────────────────────────────────────────
# 2. 多因子分析
# ─────────────────────────────────────────
def analyze_multifactor(df) -> dict:
    if df is None or len(df)<30: return {"score":0,"grade":"N/A","factors":[]}
    t=df.iloc[-1]; p=df.iloc[-2]
    factors=[]

    # ① 趨勢因子 (MA 多頭排列)
    ma_bull=0
    if not pd.isna(t["MA5"])  and t["Close"]>t["MA5"]:  ma_bull+=1
    if not pd.isna(t["MA20"]) and t["Close"]>t["MA20"]: ma_bull+=1
    if not pd.isna(t["MA60"]) and t["Close"]>t["MA60"]: ma_bull+=1
    trend_score=round(ma_bull/3*100)
    factors.append({"name":"趨勢（均線）",
                    "score":trend_score,
                    "detail":f"MA5/20/60 多頭 {ma_bull}/3",
                    "icon":"📈"})

    # ② 動能因子 (KD + MACD)
    mom=0
    if t["K"]>t["D"]: mom+=1
    if t["MACD_HIST"]>0: mom+=1
    if p["MACD_HIST"]<0 and t["MACD_HIST"]>0: mom+=1   # 翻紅加分
    mom_score=min(round(mom/3*100),100)
    factors.append({"name":"動能（KD+MACD）",
                    "score":mom_score,
                    "detail":f"KD {'多' if t['K']>t['D'] else '空'} | MACD {'翻紅🔴' if p['MACD_HIST']<0 and t['MACD_HIST']>0 else ('紅柱' if t['MACD_HIST']>0 else '綠柱')}",
                    "icon":"⚡"})

    # ③ 量能因子
    vma5=t["VOL_MA5"] if t["VOL_MA5"]>0 else 1
    vma20=t["VOL_MA20"] if t["VOL_MA20"]>0 else 1
    vol_ratio=t["Volume"]/vma5
    vol_score=min(int(vol_ratio/2*100),100)
    # 量增價漲最優，量縮價漲次之
    if vol_ratio>=1.5 and t["Close"]>p["Close"]: vol_score=min(vol_score+20,100)
    elif vol_ratio<0.8: vol_score=max(vol_score-20,0)
    vol_desc=("爆量攻擊🔥" if vol_ratio>=2 else
              "放量上漲" if vol_ratio>=1.5 and t["Close"]>p["Close"] else
              "量縮整理" if vol_ratio<0.8 else "量能正常")
    factors.append({"name":"量能",
                    "score":vol_score,
                    "detail":f"量比 {vol_ratio:.1f}x | {vol_desc}",
                    "icon":"📊"})

    # ④ 位置因子 (布林 + 費波)
    bb_pct=(t["Close"]-t["BB_LO"])/(t["BB_UP"]-t["BB_LO"]) if not pd.isna(t["BB_LO"]) else 0.5
    if 0.2<=bb_pct<=0.8: pos_score=80
    elif bb_pct>1: pos_score=30   # 衝出上軌
    elif bb_pct<0: pos_score=60   # 跌破下軌（超跌反彈機會）
    else: pos_score=50
    pos_desc=("衝出上軌（過熱）" if bb_pct>1 else
              "跌破下軌（超跌）" if bb_pct<0 else
              f"通道 {bb_pct*100:.0f}% 位置")
    factors.append({"name":"位置（布林）",
                    "score":pos_score,
                    "detail":pos_desc,
                    "icon":"🎯"})

    # ⑤ SAR 因子
    sar_bull=float(t["Close"])>float(t["SAR"])
    sar_score=80 if sar_bull else 20
    factors.append({"name":"趨勢停損（SAR）",
                    "score":sar_score,
                    "detail":"SAR 多方支撐 ✅" if sar_bull else "SAR 空方壓力 ❌",
                    "icon":"🛡️"})

    total=round(sum(f["score"] for f in factors)/len(factors))
    grade=("S 極強 🏆" if total>=85 else
           "A 強勢 🔥" if total>=70 else
           "B 中性 📊" if total>=50 else
           "C 偏弱 ⚠️" if total>=35 else
           "D 空頭 🔴")
    return {"score":total,"grade":grade,"factors":factors}

# ─────────────────────────────────────────
# 3. 目標價達成條件分析
# ─────────────────────────────────────────
def analyze_target_conditions(df, target_price: float) -> dict:
    if df is None or len(df)<30: return {}
    t=df.iloc[-1]; c=t["Close"]
    atr=float(t["ATR"]) if not pd.isna(t["ATR"]) else c*0.02
    gap=target_price-c
    gap_pct=gap/c*100

    if c>=target_price:
        return {"reached":True,"status":"✅ 已達標","conditions":[],"est_days":0}

    # 估算天數：gap / (ATR * 0.4) * reality_factor
    est_days=max(5,int(gap/max(atr*0.4,0.01)*2.0)) if gap>0 else 0

    # 需要滿足的條件
    conditions=[]
    m20=t["MA20"] if not pd.isna(t["MA20"]) else c
    m60=t["MA60"] if not pd.isna(t["MA60"]) else c

    conditions.append({
        "ok": t["Close"]>m60,
        "text": f"站上季線（{m60:.2f}）— 中線多頭確立"
    })
    conditions.append({
        "ok": t["MACD_HIST"]>0,
        "text": "MACD 翻紅 — 動能轉正"
    })
    conditions.append({
        "ok": t["K"]>t["D"],
        "text": "KD 多頭排列 — 短期趨勢向上"
    })
    conditions.append({
        "ok": float(t["Volume"])>float(t["VOL_MA5"])*1.2,
        "text": "成交量放大 — 主力進場"
    })
    met=sum(1 for x in conditions if x["ok"])

    # 關鍵壓力位
    hi=df["High"].iloc[-120:].max(); lo=df["Low"].iloc[-120:].min(); diff=hi-lo
    resistances=[]
    for r,lbl in [(hi-diff*0.236,"0.236"),(hi-diff*0.382,"0.382"),(m20,"20MA"),(m60,"60MA")]:
        if c<r<target_price: resistances.append(f"{lbl} {r:.2f}")

    return {
        "reached": False,
        "status":  f"距目標 {gap_pct:.1f}%（差 {gap:.2f} 元）",
        "conditions": conditions,
        "met": met,
        "est_days": est_days,
        "resistances": resistances,
    }

# ─────────────────────────────────────────
# 4. 美股連動分析
# ─────────────────────────────────────────
def analyze_us_correlation(code: str, df_tw) -> dict:
    try:
        end=datetime.now(); start=end-timedelta(days=90)
        # 選擇對標指數
        benchmarks={"QQQ":"那斯達克 QQQ","SOXX":"費城半導體 SOXX","SPY":"S&P500 SPY"}
        results={}
        tw_ret=df_tw["Close"].pct_change().dropna().iloc[-60:]

        for ticker,name in benchmarks.items():
            try:
                df_us=yf.Ticker(ticker).history(period="3mo")
                if df_us.empty: continue
                us_ret=df_us["Close"].pct_change().dropna()
                # 對齊日期
                merged=pd.concat([tw_ret,us_ret],axis=1,join="inner")
                if len(merged)<10: continue
                corr=merged.iloc[:,0].corr(merged.iloc[:,1])
                us_today=df_us.iloc[-1]; us_prev=df_us.iloc[-2]
                us_pct=(us_today["Close"]-us_prev["Close"])/us_prev["Close"]*100
                results[ticker]={"name":name,"corr":round(corr,2),"us_pct":round(us_pct,2)}
            except: continue

        if not results: return {"available":False}

        # 找最高相關
        best=max(results.items(),key=lambda x:abs(x[1]["corr"]))
        corr_val=best[1]["corr"]
        corr_desc=("高度正相關 🔗" if corr_val>0.6 else
                   "中度正相關" if corr_val>0.3 else
                   "低相關" if corr_val>0 else
                   "負相關（反向）")
        # 推論影響
        us_trend=all(v["us_pct"]>0 for v in results.values())
        us_weak=all(v["us_pct"]<-1 for v in results.values())
        impact=("📈 美股全面上漲，利多台股今日走勢" if us_trend else
                "📉 美股全面下跌，留意開盤賣壓" if us_weak else
                "↔️ 美股漲跌互見，影響有限")

        return {
            "available": True,
            "results":   results,
            "best_name": best[1]["name"],
            "corr_val":  corr_val,
            "corr_desc": corr_desc,
            "impact":    impact,
        }
    except: return {"available":False}

# ─────────────────────────────────────────
# 5. 最新消息（利多/利空）
# ─────────────────────────────────────────
def get_news(code: str, max_items: int = 5) -> list:
    """從 yfinance 取得最新新聞"""
    news_list=[]
    for sfx in [".TW",".TWO"]:
        try:
            ticker=yf.Ticker(code+sfx)
            news=ticker.news
            if not news: continue
            for n in news[:max_items]:
                title=n.get("title","")
                link =n.get("link","")
                ts   =n.get("providerPublishTime",0)
                pub  =datetime.fromtimestamp(ts).strftime("%m/%d %H:%M") if ts else ""
                # 簡單利多/利空關鍵字判斷
                bull_kw=["上漲","突破","創高","買超","法人","獲利","成長","正向","利多","買進","調升"]
                bear_kw=["下跌","跌破","虧損","賣超","警示","減碼","利空","調降","風險","跌停"]
                sentiment="🟢" if any(k in title for k in bull_kw) else \
                           "🔴" if any(k in title for k in bear_kw) else "⚪"
                news_list.append({"title":title,"link":link,"pub":pub,"sentiment":sentiment})
            break
        except: pass
    return news_list

# ─────────────────────────────────────────
# 6. 成交量啟動偵測
# ─────────────────────────────────────────
def analyze_volume_activation(df) -> dict:
    if df is None or len(df)<20: return {"activated":False,"desc":"資料不足"}
    t=df.iloc[-1]; p=df.iloc[-2]
    vma5 =t["VOL_MA5"]  if t["VOL_MA5"]>0  else 1
    vma20=t["VOL_MA20"] if t["VOL_MA20"]>0 else 1
    vol_ratio_5 =t["Volume"]/vma5
    vol_ratio_20=t["Volume"]/vma20

    # 量能趨勢：近 5 日量是否逐步放大
    recent_vols=df["Volume"].iloc[-5:].values
    vol_trend_up=recent_vols[-1]>recent_vols[0] if len(recent_vols)==5 else False
    vol_acceleration=recent_vols[-1]/max(recent_vols[-3],1)  # 近3日加速比

    # 判斷啟動條件
    activated=False; signals=[]; level="normal"

    if vol_ratio_5>=2.0 and t["Close"]>p["Close"]:
        activated=True; level="strong"
        signals.append(f"🔥 今日量比5MA達 {vol_ratio_5:.1f}x，爆量大漲")
    elif vol_ratio_5>=1.5 and t["Close"]>p["Close"]:
        activated=True; level="moderate"
        signals.append(f"🚀 今日量比5MA達 {vol_ratio_5:.1f}x，放量上漲")
    elif vol_trend_up and vol_ratio_5>=1.2:
        activated=True; level="early"
        signals.append(f"📈 連續放量 5 日，量能逐步堆疊（加速比 {vol_acceleration:.1f}x）")

    if vol_ratio_20>=1.8:
        signals.append(f"⚡ 相較月均量放大 {vol_ratio_20:.1f}x，異常大量")

    # 量縮
    if not activated:
        if vol_ratio_5<0.6: signals.append(f"💤 今日量比 {vol_ratio_5:.1f}x，成交量極度萎縮")
        elif vol_ratio_5<0.8: signals.append(f"😴 今日量比 {vol_ratio_5:.1f}x，量縮整理")
        else: signals.append(f"📊 今日量比 {vol_ratio_5:.1f}x，量能平穩")

    level_map={"strong":"🔥 強力啟動","moderate":"🚀 量能啟動","early":"📈 初步啟動","normal":"😴 未啟動"}
    return {
        "activated":    activated,
        "level":        level_map.get(level,"未知"),
        "signals":      signals,
        "vol_ratio_5":  round(vol_ratio_5,1),
        "vol_ratio_20": round(vol_ratio_20,1),
    }

# ─────────────────────────────────────────
# 7. 技術面分析（SOP + 指標數值 + 買賣建議）
# ─────────────────────────────────────────
def analyze_technical(df) -> dict:
    """完整技術面解析：SOP 狀態、KD/MACD/SAR 數值、費波、買賣建議"""
    if df is None or len(df)<30:
        return {"sop_signal":None,"advice":"資料不足","detail":[]}
    t=df.iloc[-1]; p=df.iloc[-2]
    c=float(t["Close"])

    # ── SOP 三線判斷 ──
    kd_cross=(p["K"]<p["D"]) and (t["K"]>t["D"])
    kd_bull =t["K"]>t["D"]
    cond_kd =kd_bull or kd_cross
    kd_lbl  ="今日金叉✨" if kd_cross else ("多頭排列" if kd_bull else "空方排列")

    cond_macd=t["MACD_HIST"]>0
    macd_lbl =("今日翻紅🔴" if (p["MACD_HIST"]<=0 and t["MACD_HIST"]>0)
                else ("紅柱延伸" if cond_macd else "綠柱整理"))

    cond_sar=c>float(t["SAR"])
    sar_lbl ="多方支撐" if cond_sar else "空方壓力"

    hard_pass=cond_kd and cond_macd and cond_sar
    met_count=sum([cond_kd,cond_macd,cond_sar])

    # ── 費波那契 ──
    hi=df["High"].iloc[-120:].max(); lo=df["Low"].iloc[-120:].min(); diff=hi-lo
    fib236=hi-diff*0.236; fib382=hi-diff*0.382
    fib500=hi-diff*0.500; fib618=hi-diff*0.618

    # ── ATR 買賣點 ──
    atr=float(t["ATR"]) if not pd.isna(t["ATR"]) else c*0.02
    ma5 =float(t["MA5"])  if not pd.isna(t.get("MA5", np.nan))  else c
    ma20=float(t["MA20"]) if not pd.isna(t.get("MA20",np.nan))  else c
    ma60=float(t["MA60"]) if not pd.isna(t.get("MA60",np.nan))  else c

    buy_agg =max(ma5,  fib236)
    buy_con =max(ma20, fib382)
    stop_loss=max(c-atr*2, fib618)
    target1  =round(c*1.05,2)
    target2  =round(c*1.10,2)

    # ── 綜合買賣建議 ──
    wave=analyze_wave(df)
    wlabel=wave["label"]

    if hard_pass:
        if wlabel in ("3-5","B-c","C-3"):
            sop_signal="SELL"
            advice=f"⚠️ <b>SELL 出場</b>：SOP 三線多頭但波浪已至 {wlabel}（高檔），建議分批出場"
        else:
            sop_signal="BUY"
            advice=f"🚀 <b>BUY 進場</b>：SOP 三線全達（KD+MACD+SAR），波浪 {wlabel}，最佳買入時機"
    elif met_count==2:
        sop_signal="WATCH_CLOSE"
        missing=[]
        if not cond_kd:   missing.append("KD")
        if not cond_macd: missing.append("MACD")
        if not cond_sar:  missing.append("SAR")
        advice=f"👀 <b>密切觀察</b>：SOP {met_count}/3，還差 {'/'.join(missing)} 翻多即可進場"
    elif met_count==1:
        sop_signal="WAIT"
        advice=f"⏳ <b>耐心等待</b>：SOP {met_count}/3，條件尚未成熟，持續觀察"
    else:
        sop_signal="AVOID"
        advice=f"🔴 <b>暫時迴避</b>：SOP 三線全空，空頭格局（{wlabel}），不宜進場"

    # ── 均線多空排列 ──
    ma_status=[]
    if c>ma5:   ma_status.append("5MA✅")
    else:       ma_status.append("5MA❌")
    if c>ma20:  ma_status.append("20MA✅")
    else:       ma_status.append("20MA❌")
    if c>ma60:  ma_status.append("60MA✅")
    else:       ma_status.append("60MA❌")
    ma_bull_count=sum([c>ma5, c>ma20, c>ma60])

    detail=[
        f"📐 KD：K={t['K']:.1f} D={t['D']:.1f}｜{kd_lbl}",
        f"📐 MACD Hist：{t['MACD_HIST']:+.3f}｜{macd_lbl}",
        f"📐 SAR：{float(t['SAR']):.2f}（現價{c:.2f}）｜{sar_lbl}",
        f"📐 均線站上：{' '.join(ma_status)}（{ma_bull_count}/3）",
        f"📐 費波：0.382={fib382:.2f}｜0.500={fib500:.2f}｜0.618={fib618:.2f}",
        f"💡 建議買點：激進 {buy_agg:.2f}（5MA/0.236）｜保守 {buy_con:.2f}（20MA/0.382）",
        f"💡 目標1：{target1}（+5%）｜目標2：{target2}（+10%）",
        f"🛑 建議停損：{stop_loss:.2f}（2ATR / 費波0.618取高）",
    ]

    return {
        "sop_signal": sop_signal,
        "advice":     advice,
        "detail":     detail,
        "met_count":  met_count,
        "buy_agg":    buy_agg,
        "buy_con":    buy_con,
        "stop_loss":  stop_loss,
    }

# ─────────────────────────────────────────
# 8. 組裝完整 Telegram 報告
# ─────────────────────────────────────────
def build_full_report(code: str, name: str,
                      target_price: float | None = None,
                      username: str = "") -> str:
    df=get_df(code)
    if df is None: return f"❌ {name}（{code}）資料無法取得"
    df=add_ind(df)
    t=df.iloc[-1]; p=df.iloc[-2]
    pct=(t["Close"]-p["Close"])/p["Close"]*100
    icon="🔺" if pct>0 else "💚" if pct<0 else "➖"

    wave=analyze_wave(df)
    mf  =analyze_multifactor(df)
    vol =analyze_volume_activation(df)
    us  =analyze_us_correlation(code,df)
    news=get_news(code,3)
    tech=analyze_technical(df)      # ← 新增技術面

    lines=[]

    # ── 標頭 ──
    lines.append(f"━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 <b>{name}（{code}）每日報告</b>")
    lines.append(f"💰 現價：<b>{t['Close']:.2f}</b> {icon} {pct:+.2f}%")
    lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━")

    # ── ① 技術面 SOP 買賣建議（最優先，最重要） ──
    lines.append(f"\n🎖️ <b>買賣建議</b>")
    lines.append(f"   {tech['advice']}")
    for d in tech["detail"]:
        lines.append(f"   {d}")

    # ── ② 多因子評分 ──
    lines.append(f"\n🏆 <b>多因子評分：{mf['score']}分 | {mf['grade']}</b>")
    for f in mf["factors"]:
        bar=int(f["score"]/10)
        bar_str="█"*bar+"░"*(10-bar)
        lines.append(f"   {f['icon']} {f['name']}：{f['score']}分 |{bar_str}|")
        lines.append(f"      └ {f['detail']}")

    # ── ③ 波浪理論 ──
    lines.append(f"\n🌊 <b>波浪理論：{wave['title']}</b>")
    lines.append(f"   分析：{wave['desc']}")
    lines.append(f"   操作：<b>{wave['suggestion']}</b>")

    # ── ④ 成交量啟動 ──
    lines.append(f"\n📦 <b>成交量：{vol['level']}</b>")
    for s in vol["signals"]:
        lines.append(f"   {s}")

    # ── ⑤ 目標價條件（個人化） ──
    if target_price and target_price>0:
        tc=analyze_target_conditions(df,target_price)
        lines.append(f"\n🎯 <b>你的目標價：{target_price:.2f}｜{tc['status']}</b>")
        if not tc.get("reached"):
            lines.append(f"   預估達標：約 {tc.get('est_days',0)} 個交易日")
            lines.append(f"   達成條件（{tc.get('met',0)}/{len(tc.get('conditions',[]))} 已達）：")
            for cond in tc.get("conditions",[]):
                ok_icon="✅" if cond["ok"] else "❌"
                lines.append(f"   {ok_icon} {cond['text']}")
            if tc.get("resistances"):
                lines.append(f"   🚧 壓力路徑：{' → '.join(tc['resistances'])}")
    else:
        lines.append(f"\n🎯 <b>目標價</b>：尚未設定（可在 app.py 目標價頁面設定）")

    # ── ⑥ 美股連動 ──
    if us.get("available"):
        lines.append(f"\n🌏 <b>美股連動</b>（最相關：{us['best_name']} 相關係數 {us['corr_val']}｜{us['corr_desc']}）")
        lines.append(f"   {us['impact']}")
        for ticker,v in us["results"].items():
            dir_icon="🔺" if v["us_pct"]>0 else "💚"
            lines.append(f"   {v['name']}：{dir_icon}{v['us_pct']:+.2f}%（相關 {v['corr']}）")
    else:
        lines.append(f"\n🌏 <b>美股連動</b>：今日資料無法取得")

    # ── ⑦ 最新消息 ──
    if news:
        lines.append(f"\n📰 <b>最新消息</b>")
        for n in news:
            lines.append(f"   {n['sentiment']} [{n['pub']}] {n['title']}")
    else:
        lines.append(f"\n📰 <b>最新消息</b>：暫無相關新聞")

    lines.append(f"\n━━━━━━━━━━━━━━━━━━━━")
    if username: lines.append(f"<i>📬 {username} 專屬報告</i>")

    return "\n".join(lines)
