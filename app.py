"""
ai_report.py — AI 深度個股分析報告引擎
使用 Groq API（免費）生成完整的專業分析報告書
Groq 免費額度：每天 14,400 次請求，Llama 3.3 70B 模型
包含：技術面、基本面、多因子、波浪理論、美股連動、利多利空新聞
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timedelta

# ─────────────────────────────────────────
# 取得 Anthropic API Key
# ─────────────────────────────────────────
def _api_key() -> str:
    """讀取 Groq API Key（完全免費，至 groq.com 註冊取得）"""
    try:
        import streamlit as st
        return st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY",""))
    except Exception:
        return os.environ.get("GROQ_API_KEY","")

# ─────────────────────────────────────────
# 技術指標計算
# ─────────────────────────────────────────
def _sar(high, low, af0=0.02, af_max=0.2):
    n=len(high); sar=np.zeros(n); trend=np.ones(n)
    ep=np.zeros(n); af=np.full(n,af0)
    sar[0]=low[0]; ep[0]=high[0]
    for i in range(1,n):
        sar[i]=sar[i-1]+af[i-1]*(ep[i-1]-sar[i-1])
        if trend[i-1]==1:
            if low[i]<sar[i]:
                trend[i]=-1;sar[i]=ep[i-1];ep[i]=low[i];af[i]=af0
            else:
                trend[i]=1
                if high[i]>ep[i-1]: ep[i]=high[i];af[i]=min(af[i-1]+af0,af_max)
                else: ep[i]=ep[i-1];af[i]=af[i-1]
                sar[i]=min(sar[i],low[i-1])
                if i>1: sar[i]=min(sar[i],low[i-2])
        else:
            if high[i]>sar[i]:
                trend[i]=1;sar[i]=ep[i-1];ep[i]=high[i];af[i]=af0
            else:
                trend[i]=-1
                if low[i]<ep[i-1]: ep[i]=low[i];af[i]=min(af[i-1]+af0,af_max)
                else: ep[i]=ep[i-1];af[i]=af[i-1]
                sar[i]=max(sar[i],high[i-1])
                if i>1: sar[i]=max(sar[i],high[i-2])
    return sar

def _calc(df):
    if df is None or df.empty: return df
    n=len(df)
    df["SAR"]=_sar(df["High"].values,df["Low"].values) if n>5 else np.nan
    for p in [5,10,20,60,120,240]:
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
    df["BB_UP"]=df["BB_MID"]+2*std
    df["BB_LO"]=df["BB_MID"]-2*std
    df["BB_PCT"]=(df["Close"]-df["BB_LO"])/(df["BB_UP"]-df["BB_LO"])
    # RSI 14
    delta=df["Close"].diff()
    gain=delta.clip(lower=0).rolling(14).mean()
    loss=(-delta.clip(upper=0)).rolling(14).mean()
    rs=gain/loss.replace(0,np.nan)
    df["RSI"]=100-100/(1+rs)
    return df

def _get_df(code):
    for sfx in [".TW",".TWO"]:
        try:
            df=yf.Ticker(code+sfx).history(period="2y")
            if not df.empty: return df, sfx
        except: pass
    return None, None

# ─────────────────────────────────────────
# 1. 基本面資料
# ─────────────────────────────────────────
def _get_fundamental(code, sfx):
    try:
        t=yf.Ticker(code+sfx)
        info=t.info
        # 財務摘要
        return {
            "market_cap":   info.get("marketCap"),
            "pe":           info.get("trailingPE") or info.get("forwardPE"),
            "pb":           info.get("priceToBook"),
            "eps":          info.get("trailingEps") or info.get("forwardEps"),
            "roe":          info.get("returnOnEquity"),
            "revenue":      info.get("totalRevenue"),
            "net_income":   info.get("netIncomeToCommon"),
            "gross_margin": info.get("grossMargins"),
            "profit_margin":info.get("profitMargins"),
            "debt_equity":  info.get("debtToEquity"),
            "current_ratio":info.get("currentRatio"),
            "dividend":     info.get("lastDividendValue") or info.get("dividendRate",0),
            "div_yield":    info.get("dividendYield"),
            "ex_date":      info.get("exDividendDate"),
            "target_mean":  info.get("targetMeanPrice"),
            "target_high":  info.get("targetHighPrice"),
            "target_low":   info.get("targetLowPrice"),
            "analyst_count":info.get("numberOfAnalystOpinions"),
            "recommendation":info.get("recommendationKey","N/A"),
            "52w_high":     info.get("fiftyTwoWeekHigh"),
            "52w_low":      info.get("fiftyTwoWeekLow"),
            "beta":         info.get("beta"),
            "sector":       info.get("sector",""),
            "industry":     info.get("industry",""),
            "employees":    info.get("fullTimeEmployees"),
            "description":  info.get("longBusinessSummary","")[:300] if info.get("longBusinessSummary") else "",
        }
    except: return {}

# ─────────────────────────────────────────
# 2. 最新新聞
# ─────────────────────────────────────────
def _get_news(code, sfx, max_n=8):
    news_list=[]
    try:
        t=yf.Ticker(code+sfx)
        for n in (t.news or [])[:max_n]:
            title=n.get("title","")
            link =n.get("link","")
            ts   =n.get("providerPublishTime",0)
            pub  =datetime.fromtimestamp(ts).strftime("%m/%d %H:%M") if ts else ""
            src  =n.get("publisher","")
            bull_kw=["上漲","突破","創高","法人買超","獲利","成長","正向","利多","調升目標","優於預期","超越"]
            bear_kw=["下跌","跌破","虧損","賣超","警示","減碼","利空","調降","風險","跌停","裁員","召回"]
            sentiment=("🟢 利多" if any(k in title for k in bull_kw) else
                       "🔴 利空" if any(k in title for k in bear_kw) else "⚪ 中性")
            news_list.append({"title":title,"link":link,"pub":pub,"src":src,"sentiment":sentiment})
    except: pass
    return news_list

# ─────────────────────────────────────────
# 3. 美股連動
# ─────────────────────────────────────────
def _get_us_market(df_tw):
    result={}
    benchmarks={"QQQ":"那斯達克QQQ","SOXX":"費城半導體SOXX","SPY":"S&P500 SPY","^VIX":"恐慌指數VIX"}
    try:
        tw_ret=df_tw["Close"].pct_change().dropna().iloc[-60:]
        for ticker,name in benchmarks.items():
            try:
                df_us=yf.Ticker(ticker).history(period="3mo")
                if df_us.empty: continue
                us_today=df_us["Close"].iloc[-1]; us_prev=df_us["Close"].iloc[-2]
                pct=(us_today-us_prev)/us_prev*100
                us_ret=df_us["Close"].pct_change().dropna()
                merged=pd.concat([tw_ret,us_ret],axis=1,join="inner")
                corr=merged.iloc[:,0].corr(merged.iloc[:,1]) if len(merged)>10 else 0
                result[ticker]={"name":name,"price":round(us_today,2),
                                "pct":round(pct,2),"corr":round(corr,2)}
            except: pass
    except: pass
    return result

# ─────────────────────────────────────────
# 4. 波浪識別
# ─────────────────────────────────────────
def _wave(df):
    if df is None or len(df)<15: return "N/A","N/A"
    c=df["Close"].iloc[-1]
    m20=df["MA20"].iloc[-1] if not pd.isna(df["MA20"].iloc[-1]) else c
    m60=df["MA60"].iloc[-1] if not pd.isna(df["MA60"].iloc[-1]) else c
    k=df["K"].iloc[-1]; pk=df["K"].iloc[-2]
    h=df["MACD_HIST"].iloc[-1]; ph=df["MACD_HIST"].iloc[-2]
    wave_map={
        "3-3":("3-3 主升急漲","多頭最強波段，動能充沛，建議沿5MA持倉"),
        "3-5":("3-5 噴出末段","主升末端過熱，建議逢高分批出場"),
        "3-1":("3-1 初升啟動","趨勢剛翻多，可輕倉布局，停損設前低"),
        "3-a":("3-a 高檔震盪","漲勢放緩，量縮整理，觀察是否縮量"),
        "4-a":("4-a 初跌修正","正常回測，等0.382支撐再加碼"),
        "4-b":("4-b 反彈逃命","空頭反彈，趨勢仍弱，逢高減碼"),
        "4-c":("4-c 修正末端","K值低檔，接近底部，等KD金叉確認"),
        "C-3":("C-3 主跌段","空頭核心波，避免抄底"),
        "C-5":("C-5 趕底急殺","極端超賣，觀察止跌K棒"),
        "B-a":("B-a 跌深反彈","空頭中短線反彈，謹慎操作"),
        "B-c":("B-c 反彈高點","空頭格局未改，此為出場機會"),
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
    info=wave_map.get(label,(label,""))
    return info[0],info[1]

# ─────────────────────────────────────────
# 5. SOP 判斷
# ─────────────────────────────────────────
def _sop(df):
    if df is None or len(df)<30: return {}
    t=df.iloc[-1]; p=df.iloc[-2]
    kd_cross=(p["K"]<p["D"]) and (t["K"]>t["D"])
    cond_kd=t["K"]>t["D"] or kd_cross
    cond_macd=t["MACD_HIST"]>0
    cond_sar=float(t["Close"])>float(t["SAR"])
    hard=cond_kd and cond_macd and cond_sar
    vma=t["VOL_MA5"] if t["VOL_MA5"]>0 else 1
    vol_r=round(float(t["Volume"])/float(vma),1)
    wlabel,_=_wave(df)
    if hard:
        signal="SELL" if any(x in wlabel for x in ["3-5","B-c","C-3"]) else "BUY"
    else:
        signal="WATCH"
    return {
        "signal":signal,"hard_pass":hard,
        "kd":"✅金叉" if kd_cross else ("✅多頭" if cond_kd else "❌空方"),
        "macd":"✅翻紅" if (p["MACD_HIST"]<=0 and cond_macd) else ("✅紅柱" if cond_macd else "❌綠柱"),
        "sar":"✅多方" if cond_sar else "❌空方",
        "vol_ratio":vol_r,"met":sum([cond_kd,cond_macd,cond_sar]),
    }

# ─────────────────────────────────────────
# 6. 彙整所有資料 → 給 Claude 的完整 context
# ─────────────────────────────────────────
def _build_context(code, name, df, fundamental, news, us_market,
                   wave_title, wave_advice, sop, target_price=None):
    t=df.iloc[-1]; p=df.iloc[-2]
    c=float(t["Close"]); pct=(c-float(p["Close"]))/float(p["Close"])*100
    atr=float(t["ATR"]) if not pd.isna(t["ATR"]) else c*0.02
    hi=df["High"].iloc[-120:].max(); lo=df["Low"].iloc[-120:].min(); diff=hi-lo

    def _f(v,d=2): return f"{v:.{d}f}" if v and not pd.isna(v) else "N/A"
    def _m(v): return f"{v/1e8:.1f}億" if v and v>1e8 else f"{v/1e4:.0f}萬" if v else "N/A"

    # 技術指標摘要
    tech_lines=[
        f"現價={c:.2f} 漲跌={pct:+.2f}%",
        f"成交量={int(t['Volume']/1000)}張 量比5MA={sop.get('vol_ratio',0)}x",
        f"52週高={_f(fundamental.get('52w_high'))} 低={_f(fundamental.get('52w_low'))}",
        f"KD K={t['K']:.1f} D={t['D']:.1f} | {sop.get('kd','N/A')}",
        f"MACD Hist={t['MACD_HIST']:+.4f} | {sop.get('macd','N/A')}",
        f"RSI={_f(t.get('RSI',np.nan),1)}",
        f"SAR={_f(t['SAR'])} | {sop.get('sar','N/A')}",
        f"5MA={_f(t.get('MA5',np.nan))} 20MA={_f(t.get('MA20',np.nan))} 60MA={_f(t.get('MA60',np.nan))} 120MA={_f(t.get('MA120',np.nan))}",
        f"布林上軌={_f(t['BB_UP'])} 中軌={_f(t['BB_MID'])} 下軌={_f(t['BB_LO'])} 位置={_f(t['BB_PCT']*100,1)}%",
        f"ATR={_f(atr)}",
        f"費波那契：0.382={_f(hi-diff*0.382)} 0.500={_f(hi-diff*0.5)} 0.618={_f(hi-diff*0.618)}",
        f"SOP三線：{sop.get('met',0)}/3達標 → 訊號={sop.get('signal','N/A')}",
        f"艾略特波浪：{wave_title}",
    ]

    # 基本面摘要
    fund_lines=[
        f"市值={_m(fundamental.get('market_cap'))}",
        f"本益比P/E={_f(fundamental.get('pe'),1)} 股價淨值比P/B={_f(fundamental.get('pb'),2)}",
        f"EPS={_f(fundamental.get('eps'))} ROE={_f(fundamental.get('roe',0)*100 if fundamental.get('roe') else None,1)}%",
        f"毛利率={_f(fundamental.get('gross_margin',0)*100 if fundamental.get('gross_margin') else None,1)}% 淨利率={_f(fundamental.get('profit_margin',0)*100 if fundamental.get('profit_margin') else None,1)}%",
        f"負債比={_f(fundamental.get('debt_equity'),1)} 流動比={_f(fundamental.get('current_ratio'),2)}",
        f"現金股利={_f(fundamental.get('dividend'))} 殖利率={_f(fundamental.get('div_yield',0)*100 if fundamental.get('div_yield') else None,2)}%",
        f"法人目標價：平均={_f(fundamental.get('target_mean'))} 高={_f(fundamental.get('target_high'))} 低={_f(fundamental.get('target_low'))}",
        f"分析師評等={fundamental.get('recommendation','N/A')} 覆蓋分析師={fundamental.get('analyst_count','N/A')}人",
        f"行業={fundamental.get('industry','')} 員工={fundamental.get('employees','N/A')}人",
    ]
    if fundamental.get("description"):
        fund_lines.append(f"公司簡介：{fundamental['description']}")

    # 美股資料
    us_lines=[]
    for tk,v in us_market.items():
        icon="🔺" if v["pct"]>0 else "💚" if v["pct"]<0 else "➖"
        us_lines.append(f"{v['name']}={v['price']} {icon}{v['pct']:+.2f}% 相關係數={v['corr']}")

    # 最新新聞
    news_lines=[f"{n['sentiment']} [{n['pub']}]{n['src']} {n['title']}" for n in news]

    # 目標價
    tgt_line=f"用戶設定目標價={target_price}" if target_price else "用戶未設定目標價"

    ctx=f"""
=== 台股個股資料 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] ===
股票：{name}（{code}）

【即時行情 & 技術指標】
{chr(10).join(tech_lines)}

【基本面財務數據】
{chr(10).join(fund_lines)}

【美股市場現況】
{chr(10).join(us_lines) if us_lines else "無法取得"}

【最新新聞（最近8則）】
{chr(10).join(news_lines) if news_lines else "目前無新聞"}

【波浪理論判斷】
當前波浪：{wave_title}
操作建議：{wave_advice}

【SOP訊號】
KD：{sop.get('kd','N/A')} | MACD：{sop.get('macd','N/A')} | SAR：{sop.get('sar','N/A')}
硬條件達標：{sop.get('met',0)}/3 | 最終訊號：{sop.get('signal','N/A')}

【{tgt_line}】
"""
    return ctx

# ─────────────────────────────────────────
# 7. 呼叫 Claude API 生成完整報告
# ─────────────────────────────────────────
def _call_claude(context: str, name: str, code: str) -> str:
    """使用 Groq 免費 API（Llama 3.3 70B）生成分析報告"""
    api_key=_api_key()
    if not api_key:
        return "⚠️ 未設定 GROQ_API_KEY，請至 groq.com 免費註冊，在 Streamlit Secrets 加入 GROQ_API_KEY"

    prompt=f"""你是一位頂尖的台股分析師，擁有技術分析、基本面分析、波浪理論、籌碼分析的專業知識。
請根據以下完整的股票數據，用繁體中文撰寫一份**非常詳細、專業、實用**的個股分析報告書。

{context}

請依照以下格式撰寫完整報告，每個章節都要有實質內容，不要只是重複數字，要有深度的分析判斷：

## 📊 {name}（{code}）個股深度分析報告

### 1. 🔑 執行摘要（3-5句話總結最重要的結論）

### 2. 📈 即時行情 & 技術面分析
- 目前價格位置分析（相對52週高低、均線系統）
- KD、MACD、RSI、SAR 指標解讀
- 布林通道位置意義
- 成交量分析（是否放量、量能趨勢）
- 關鍵支撐壓力位（費波那契）

### 3. 🌊 艾略特波浪理論深度解析
- 目前所在波段位置及意義
- 後續波浪發展預判
- 操作策略建議

### 4. 🏆 多因子評分分析
請對以下5個因子各別評分(0-100)並說明原因：
- 趨勢因子（均線排列）
- 動能因子（KD+MACD）
- 量能因子
- 位置因子（布林+費波）
- 基本面因子
→ 綜合評分與等級（S/A/B/C/D）

### 5. 💎 基本面價值分析
- 本益比、股價淨值比評估（是否合理？）
- 獲利能力分析（EPS、ROE、毛利率）
- 財務健康度（負債、流動比）
- 股利政策（殖利率吸引力）
- 法人目標價 vs 現價（潛在空間）

### 6. 🌏 美股連動 & 總體環境
- 與QQQ、SOXX相關性分析
- 當前美股走勢對本股影響
- 總體市場風險評估

### 7. 📰 利多利空新聞解析
- 重要利多消息整理與影響評估
- 重要利空消息整理與風險評估
- 新聞面總體情緒判斷

### 8. 🎯 SOP 買賣建議
- 當前SOP訊號判斷結果
- 明確的進場價位建議（激進/保守）
- 停損設置建議與依據
- 波段目標價（+5%/+10%/+20%）
- 如有用戶目標價，分析達標條件

### 9. ⚠️ 主要風險提示
- 技術面風險（跌破什麼位置需警戒）
- 基本面風險
- 總體環境風險

### 10. 📋 操作策略總結
請給出一個清晰的操作計畫（適合不同風格投資人）

---
⏰ 報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}
⚠️ 本報告僅供參考，投資有風險，請自行判斷。
"""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":       "llama-3.3-70b-versatile",
                "max_tokens":  4000,
                "temperature": 0.3,
                "messages": [
                    {
                        "role":    "system",
                        "content": "你是一位頂尖的台股分析師，請用繁體中文回答，格式清晰專業。"
                    },
                    {
                        "role":    "user",
                        "content": prompt
                    }
                ],
            },
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        elif resp.status_code == 429:
            return "⚠️ Groq 免費額度已達今日上限，請明天再試（每天 14,400 次免費）"
        else:
            return f"❌ Groq API 錯誤 {resp.status_code}：{resp.text[:300]}"
    except Exception as e:
        return f"❌ 呼叫 Groq API 失敗：{e}"

# ─────────────────────────────────────────
# 8. 主入口：生成完整分析報告
# ─────────────────────────────────────────
def generate_full_report(code: str, name: str,
                         target_price: float = None) -> dict:
    """
    回傳 dict：
      report_md   : Claude 生成的完整 Markdown 報告
      sop         : SOP 訊號 dict
      wave_title  : 波浪標題
      news        : 新聞列表
      us_market   : 美股資料
      fundamental : 基本面資料
      current     : {close, pct, vol_ratio, atr, fib}
      error       : None 或錯誤訊息
    """
    df, sfx = _get_df(code)
    if df is None:
        return {"error": f"無法取得 {code} 資料", "report_md": ""}

    df = _calc(df)
    fundamental = _get_fundamental(code, sfx)
    news        = _get_news(code, sfx)
    us_market   = _get_us_market(df)
    wave_title, wave_advice = _wave(df)
    sop         = _sop(df)

    t=df.iloc[-1]; p=df.iloc[-2]
    c=float(t["Close"]); pct=(c-float(p["Close"]))/float(p["Close"])*100
    atr=float(t["ATR"]) if not pd.isna(t["ATR"]) else c*0.02
    hi=df["High"].iloc[-120:].max(); lo=df["Low"].iloc[-120:].min(); diff=hi-lo

    context=_build_context(code,name,df,fundamental,news,us_market,
                           wave_title,wave_advice,sop,target_price)
    report_md=_call_claude(context,name,code)

    return {
        "error":       None,
        "report_md":   report_md,
        "sop":         sop,
        "wave_title":  wave_title,
        "wave_advice": wave_advice,
        "news":        news,
        "us_market":   us_market,
        "fundamental": fundamental,
        "current": {
            "close":     c,
            "pct":       pct,
            "vol_ratio": sop.get("vol_ratio",0),
            "atr":       atr,
            "fib_382":   hi-diff*0.382,
            "fib_500":   hi-diff*0.5,
            "fib_618":   hi-diff*0.618,
            "buy_agg":   max(float(t.get("MA5",c)), hi-diff*0.236),
            "buy_con":   max(float(t.get("MA20",c)), hi-diff*0.382),
            "stop":      max(c-atr*2, hi-diff*0.618),
        }
    }
