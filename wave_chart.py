"""
wave_chart.py V9
單張圖：日K線 + 成交量 + 轉折點波浪標注 + 費波那契
不再依賴 app.py 的 wave_label_d 來決定「是第幾浪」
而是用價格轉折點自動計數，並遵守三大鐵律
wave_label_d 只用來顯示右上角的「KD/MACD/SAR 判斷」輔助參考
"""
import numpy as np
import pandas as pd

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

try:
    from scipy.signal import argrelextrema
    SCIPY_OK = True
except ImportError:
    SCIPY_OK = False

# ─────────────────────────────────────────
# 波浪資訊（劇本說明）
# ─────────────────────────────────────────
WAVE_INFO = {
    "3-1":{"color":"#38bdf8","label":"推動浪起漲初段","emoji":"🌱",
     "desc":"KD/MACD/均線研判：目前處於推動浪初升段，力道逐漸累積中",
     "scenarios":[
      {"name":"✅ 主要（65%）突破確認，等②浪回踩加碼","color":"#38bdf8",
       "desc":"①浪完成後②浪回測38.2~61.8%，是加碼機會，之後③浪才是主攻段。",
       "cond":"量能放大，KD金叉，突破前高","risk":"⚠️ 停損設起漲低點"},
      {"name":"❌ 風險（10%）假突破，仍在整理","color":"#f87171",
       "desc":"量縮無法站穩均線，可能仍在盤整中。","cond":"縮量，KD高檔死叉","risk":"🛑 跌破起漲點停損"},
     ]},
    "3-3":{"color":"#4ade80","label":"推動浪主升段","emoji":"🚀",
     "desc":"KD/MACD/均線研判：目前處於推動浪主升段，多頭最強位置",
     "scenarios":[
      {"name":"✅ 主要（70%）主升浪延伸，量能最大","color":"#4ade80",
       "desc":"推動浪③是最長最強的波段，MACD紅柱持續放大，每次拉回均是加碼點。",
       "cond":"MACD紅柱放大，KD>60，量比>1.5","risk":"⚠️ 乖離>15%先減倉"},
      {"name":"📊 次要（20%）主升尾聲進入修正","color":"#fbbf24",
       "desc":"③浪子浪⑤正在完成，完成後④浪修正。","cond":"量縮，KD高位鈍化","risk":"⚠️ 注意高點反轉"},
      {"name":"❌ 風險（10%）提前結束","color":"#f87171",
       "desc":"爆量長黑③浪提前結束，④浪大幅修正。","cond":"爆量長黑K","risk":"🛑 停損③浪起漲低點"},
     ]},
    "3-5":{"color":"#fbbf24","label":"推動浪末升段","emoji":"🏔️",
     "desc":"KD/MACD/均線研判：目前處於推動浪末升段，注意量價背離",
     "scenarios":[
      {"name":"✅ 主要（50%）末升段完成→修正展開","color":"#fbbf24",
       "desc":"⑤浪完成整個推動浪，之後ABC修正A浪跌幅通常38.2~61.8%。逐步獲利了結。",
       "cond":"量價背離，KD頂背離","risk":"⚠️ 絕不追高，分批減倉"},
      {"name":"📊 次要（30%）⑤浪延伸","color":"#38bdf8",
       "desc":"法人持續買超，⑤浪可能延伸。","cond":"法人買超，量能放大","risk":"⚠️ 嚴設停利"},
      {"name":"❌ 風險（20%）失敗⑤浪急速轉空","color":"#f87171",
       "desc":"無法突破③浪高點，快速進入熊市。","cond":"量縮無法過③浪高","risk":"🛑 停損③浪高點"},
     ]},
    "3-a":{"color":"#94a3b8","label":"高檔震盪整理","emoji":"☕",
     "desc":"KD/MACD/均線研判：推動浪完成後高位整理，修正即將展開",
     "scenarios":[
      {"name":"✅ 主要（55%）ABC修正展開","color":"#f97316",
       "desc":"高位震盪是A浪的一部分，等A浪完成後B浪反彈是出場機會。","cond":"量縮整理，均線走平","risk":"⚠️ 勿加碼"},
      {"name":"❌ 風險（45%）快速轉弱","color":"#f87171",
       "desc":"量增跌破前支撐，A浪下跌加速。","cond":"量增破支撐","risk":"🛑 停損前波高點"},
     ]},
    "4-a":{"color":"#fb923c","label":"修正浪A子浪","emoji":"📉",
     "desc":"KD/MACD/均線研判：處於修正浪A子浪下跌中",
     "scenarios":[
      {"name":"✅ 主要（60%）ABC修正後啟動⑤浪","color":"#4ade80",
       "desc":"A下跌→B反彈→C再跌到0.382~0.5費波，完成後啟動⑤大浪。B浪反彈是輕倉試多機會。",
       "cond":"量縮下跌，接近費波支撐","risk":"⚠️ ④浪不應跌破①浪高點"},
      {"name":"❌ 風險（15%）跌破①浪高點","color":"#f87171",
       "desc":"跌破①浪高點艾略特結構需重新定義。","cond":"帶量跌破①浪高點","risk":"🛑 全部出場"},
     ]},
    "4-b":{"color":"#f97316","label":"修正浪B子浪反彈","emoji":"👀",
     "desc":"KD/MACD/均線研判：處於修正浪B子浪技術反彈",
     "scenarios":[
      {"name":"✅ 主要（65%）B浪反彈後C浪再下探","color":"#f97316",
       "desc":"B浪反彈通常到38.2~61.8%，完成後C浪下跌完成修正浪。","cond":"量縮反彈至壓力位","risk":"⚠️ 不宜追多"},
      {"name":"📊 次要（25%）B浪強勁直接⑤浪","color":"#fbbf24",
       "desc":"B浪量增過前高，修正浪已完成直接啟動⑤大浪。","cond":"量增突破前高","risk":"⚠️ 需確認後才追"},
     ]},
    "4-c":{"color":"#a78bfa","label":"修正浪C子浪末端","emoji":"🪤",
     "desc":"KD/MACD/均線研判：處於修正浪C子浪末端，接近底部",
     "scenarios":[
      {"name":"✅ 主要（65%）C浪見底→啟動⑤大浪","color":"#4ade80",
       "desc":"C浪在0.382~0.618費波支撐見底，KD低位金叉+量縮後帶量長紅=⑤大浪啟動。",
       "cond":"量縮後帶量長紅，KD<30金叉","risk":"⚠️ 停損C浪低點"},
      {"name":"❌ 風險（10%）進入熊市","color":"#f87171",
       "desc":"跌破①浪高點帶量，大級別ABC熊市修正。","cond":"帶量跌破①浪高點","risk":"🛑 全部出場"},
     ]},
    "C-3":{"color":"#f87171","label":"修正浪C浪主跌","emoji":"🔻",
     "desc":"KD/MACD/均線研判：處於ABC修正的C浪主跌段",
     "scenarios":[
      {"name":"✅ 主要（65%）C浪繼續下跌","color":"#f87171",
       "desc":"C浪通常等於A浪長度或1.618倍。主跌段不宜做多。","cond":"量增下跌，均線空頭排列","risk":"🛑 多單全數出清"},
      {"name":"📊 次要（25%）提前完成C浪","color":"#fbbf24",
       "desc":"量縮+KD低位背離+帶量長紅，C浪可能提前完成。","cond":"量縮，KD低位背離","risk":"⚠️ 確認後輕倉試多"},
     ]},
    "C-5":{"color":"#dc2626","label":"C浪末段趕底","emoji":"💥",
     "desc":"KD/MACD/均線研判：C浪末段極端超跌，可能接近底部",
     "scenarios":[
      {"name":"✅ 主要（55%）趕底後反彈，新推動浪開始","color":"#fbbf24",
       "desc":"趕底急殺後通常強力反彈，量縮止跌K棒可輕倉布局。",
       "cond":"量縮後爆量長紅","risk":"⚠️ 輕倉，嚴設停損"},
      {"name":"❌ 風險（45%）繼續探底","color":"#f87171",
       "desc":"無止跌訊號繼續破底。","cond":"量增繼續破低","risk":"🛑 勿抄底"},
     ]},
    "B-a":{"color":"#94a3b8","label":"修正B浪反彈","emoji":"↗️",
     "desc":"KD/MACD/均線研判：空頭格局中B浪技術反彈",
     "scenarios":[
      {"name":"✅ 主要（60%）B浪反彈後C浪下跌","color":"#f87171",
       "desc":"B浪通常反彈到前高38~61.8%後轉弱。是出貨機會。","cond":"量縮反彈","risk":"⚠️ 此反彈是出貨機會"},
      {"name":"📊 次要（25%）B浪強勢是新推動浪起漲","color":"#4ade80",
       "desc":"B浪量增過前高，可能底部確立。","cond":"量增突破前高","risk":"⚠️ 突破確認後才做多"},
     ]},
    "B-c":{"color":"#ef4444","label":"B浪c子浪高點","emoji":"⚠️",
     "desc":"KD/MACD/均線研判：B浪反彈最高點，C主跌即將展開",
     "scenarios":[
      {"name":"✅ 主要（70%）B浪完成，C主跌展開","color":"#f87171",
       "desc":"B浪c子浪為反彈最高點，之後C主跌浪展開。","cond":"KD高位死叉，量縮","risk":"🛑 多單清倉"},
      {"name":"📊 次要（30%）突破前高多頭確立","color":"#4ade80",
       "desc":"放量突破A浪起點，新推動浪開始。","cond":"量增突破前高","risk":"⚠️ 確認後才進場"},
     ]},
    "N/A":{"color":"#64748b","label":"判斷中","emoji":"❓","desc":"資料不足，請稍後","scenarios":[]},
}

def get_wave_info(label):
    return WAVE_INFO.get(label, WAVE_INFO["N/A"])


# ─────────────────────────────────────────
# 轉折點偵測
# ─────────────────────────────────────────
def _find_pivots(highs, lows, order):
    if not SCIPY_OK: return []
    if order < 1: order = 1
    n = len(highs)
    if n < order*2+1: return []
    hi_idx = argrelextrema(highs, np.greater_equal, order=order)[0]
    lo_idx = argrelextrema(lows,  np.less_equal,    order=order)[0]
    pivots = [(i, highs[i], "H") for i in hi_idx] + \
             [(i, lows[i],  "L") for i in lo_idx]
    pivots.sort(key=lambda x: x[0])
    clean = []
    for p in pivots:
        if clean and clean[-1][2] == p[2]:
            if (p[2]=="H" and p[1]>=clean[-1][1]) or \
               (p[2]=="L" and p[1]<=clean[-1][1]):
                clean[-1] = p
        else:
            clean.append(p)
    return clean


# ─────────────────────────────────────────
# 艾略特三大鐵律計數（多頭）
# ─────────────────────────────────────────
def _count_elliott_bull(pivots):
    """
    從轉折點中找符合三大鐵律的最佳五浪結構
    三大鐵律：
      1. ②浪低點 > 起點（②不跌破①浪起點）
      2. ③浪漲幅 ≥ max(①, ⑤)（③不是最短驅動浪）
      3. ④浪低點 > ①浪高點（④不與①重疊）

    回傳：
      waves: [(idx, price, label), ...]
      violations: [str]
      current: str  最後一個標注的浪名
      confidence: int  0~100
    """
    LBLS   = ["起","①","②","③","④","⑤"]
    COLORS = {"起":"#64748b","①":"#38bdf8","②":"#fb923c",
              "③":"#4ade80","④":"#f97316","⑤":"#fbbf24"}

    best_waves      = []
    best_violations = ["轉折點不足，無法完整計數"]
    best_conf       = 0

    # 從後往前嘗試不同起點（找最近的合法結構）
    for start_i in range(len(pivots)-1, max(-1,len(pivots)-20), -1):
        if pivots[start_i][2] != "L":
            continue

        # 從這個低點開始，抓交替的 H L H L H L
        seq = [pivots[start_i]]
        want = "H"
        for j in range(start_i+1, len(pivots)):
            if pivots[j][2] == want:
                seq.append(pivots[j])
                want = "L" if want == "H" else "H"
            if len(seq) >= 6:
                break

        if len(seq) < 2:
            continue

        # 標浪名
        waves = [(seq[i][0], seq[i][1], LBLS[i])
                 for i in range(min(len(seq), len(LBLS)))]

        # 驗證三大鐵律
        viols = []
        conf  = 50 + len(waves)*5

        if len(waves) >= 3:
            w0 = waves[0][1]   # 起點
            w1 = waves[1][1]   # ①高
            w2 = waves[2][1]   # ②低
            # 鐵律1
            if w2 <= w0:
                viols.append(f"❌ 鐵律1：②低({w2:.2f}) ≤ 起點({w0:.2f})")
                conf -= 30

        if len(waves) >= 6:
            w0,w1,w2,w3,w4,w5 = [w[1] for w in waves[:6]]
            len1 = w1 - w0
            len3 = w3 - w2
            len5 = w5 - w4
            # 鐵律2
            if len3 < len1 and len3 < len5:
                viols.append(f"❌ 鐵律2：③浪({len3:.2f})是最短驅動浪")
                conf -= 25
            else:
                conf += 15
            # 鐵律3
            if w4 <= w1:
                viols.append(f"❌ 鐵律3：④低({w4:.2f}) ≤ ①高({w1:.2f})")
                conf -= 25
            else:
                conf += 15

        conf = max(0, min(100, conf))

        # 取最高信心度的結果
        if conf > best_conf or (conf == best_conf and len(waves) > len(best_waves)):
            best_waves      = waves
            best_violations = viols
            best_conf       = conf

        # 找到完整無鐵律違反的就停
        if len(waves) >= 6 and not viols:
            break

    current = best_waves[-1][2] if best_waves else "?"
    return {
        "waves":      best_waves,
        "violations": best_violations,
        "current":    current,
        "confidence": best_conf,
    }


def _count_elliott_bear(pivots):
    """空頭 ABC 計數"""
    LBLS   = ["頂","(A)","(B)","(C)"]
    COLORS = {"頂":"#64748b","(A)":"#f87171","(B)":"#fb923c","(C)":"#dc2626"}

    waves = []
    want  = "H"
    for pos,price,ptype in reversed(pivots):
        if ptype == want and len(waves) < len(LBLS):
            waves.insert(0, (pos, price, LBLS[len(waves)]))
            want = "L" if want=="H" else "H"
    waves = [(pos,price,LBLS[i]) for i,(pos,price,_) in enumerate(waves[:len(LBLS)])]

    viols = []
    if len(waves) >= 3:
        w0 = waves[0][1]; w1 = waves[1][1]; w2 = waves[2][1]
        if w2 >= w0:
            viols.append(f"⚠️ (B)浪({w2:.2f}) ≥ (A)浪起點({w0:.2f})，注意平坦型修正")

    return {
        "waves":      waves,
        "violations": viols,
        "current":    waves[-1][2] if waves else "?",
        "confidence": 60,
    }


# ─────────────────────────────────────────
# 費波那契水平線
# ─────────────────────────────────────────
def _add_fib_lines(fig, row, lo_p, hi_p):
    diff = hi_p - lo_p
    for ratio, name in [(0.236,"23.6%"),(0.382,"38.2%"),(0.500,"50.0%"),(0.618,"61.8%")]:
        level = hi_p - diff * ratio
        alpha = 0.55 if ratio in (0.382,0.618) else 0.35
        fig.add_hline(
            y=level,
            line_dash="dash",
            line_color=f"rgba(148,163,184,{alpha})",
            line_width=1,
            annotation_text=f"  Fib {name}  {level:.2f}",
            annotation_font=dict(size=9, color="#64748b"),
            row=row, col=1,
        )


# ─────────────────────────────────────────
# 主繪圖函式：單張圖
# ─────────────────────────────────────────
def build_kline_chart(df, df_60=None, wave_label_d="N/A",
                      stock_name="", code=""):
    if not PLOTLY_OK or df is None or len(df) < 20:
        return None

    wave   = get_wave_info(wave_label_d)
    wcolor = wave["color"]
    is_bull = wave_label_d.startswith(("3","4"))

    # 日K 近 90 日
    df_d = df.iloc[-90:].copy().reset_index()
    if "level_0" in df_d.columns: df_d = df_d.drop(columns=["level_0"])
    dc  = "Date" if "Date" in df_d.columns else df_d.columns[0]
    x_d = df_d[dc].astype(str).tolist()
    H   = df_d["High"].values.astype(float)
    L   = df_d["Low"].values.astype(float)
    C   = df_d["Close"].values.astype(float)

    # ── 單張 subplot：K線(row1) + 成交量(row2) ──
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.02,
    )

    # ── 日K 蠟燭圖 ──
    fig.add_trace(go.Candlestick(
        x=x_d, open=df_d["Open"], high=df_d["High"],
        low=df_d["Low"], close=df_d["Close"],
        increasing=dict(line=dict(color="#4ade80",width=1),
                        fillcolor="rgba(74,222,128,0.82)"),
        decreasing=dict(line=dict(color="#f87171",width=1),
                        fillcolor="rgba(248,113,113,0.82)"),
        name="K線", showlegend=False,
    ), row=1, col=1)

    # ── 均線 ──
    for ma, mc, mw, show in [
        (5,"#f97316",1,False),(20,"#38bdf8",1.5,True),(60,"#a78bfa",1,False)
    ]:
        cn = f"MA{ma}"
        if cn in df_d.columns:
            s = df_d[cn].dropna()
            if len(s):
                fig.add_trace(go.Scatter(
                    x=[x_d[i] for i in s.index], y=s.values,
                    mode="lines", line=dict(color=mc,width=mw),
                    name=f"{ma}MA", showlegend=show, opacity=0.75,
                ), row=1, col=1)

    # ── 艾略特波浪計數 ──
    big_order = max(4, len(x_d)//12)
    pivots    = _find_pivots(H, L, big_order)

    if is_bull:
        result = _count_elliott_bull(pivots)
    else:
        result = _count_elliott_bear(pivots)

    waves      = result["waves"]
    violations = result["violations"]
    confidence = result["confidence"]
    current    = result["current"]

    WAVE_COLORS = {
        "起":"#64748b","頂":"#64748b",
        "①":"#38bdf8","②":"#fb923c","③":"#4ade80","④":"#f97316","⑤":"#fbbf24",
        "(A)":"#f87171","(B)":"#fb923c","(C)":"#dc2626",
    }

    # ── 彩色折線連接轉折點 ──
    if len(waves) >= 2:
        lx = [x_d[w[0]] for w in waves if w[0]<len(x_d)]
        # 高點用 High，低點用 Low 讓線貼緊 K 棒
        ly = []
        for w in waves:
            if w[0] >= len(x_d): continue
            # 判斷是高點還是低點：看是否接近 High
            if abs(w[1] - H[w[0]]) < abs(w[1] - L[w[0]]):
                ly.append(H[w[0]])
            else:
                ly.append(L[w[0]])
        fig.add_trace(go.Scatter(
            x=lx, y=ly, mode="lines",
            line=dict(color="#f97316", width=2.8),
            opacity=0.82, showlegend=False, hoverinfo="skip",
        ), row=1, col=1)

    # ── 標注每個轉折點 ──
    for idx, price, lbl in waves:
        if idx >= len(x_d): continue
        lc  = WAVE_COLORS.get(lbl, "#94a3b8")
        is_hi = abs(price - H[idx]) < abs(price - L[idx])
        ay = -50 if is_hi else 50

        price_str = f"{price:.2f}" if price < 1000 else f"{int(price):,}"
        txt = f"<b>{lbl}</b><br><span style='font-size:10px;font-family:JetBrains Mono'>{price_str}</span>"

        fig.add_annotation(
            x=x_d[idx], y=price,
            text=txt,
            showarrow=True, arrowhead=0,
            arrowwidth=1.5, arrowcolor=lc,
            ax=0, ay=ay,
            font=dict(size=14, color=lc, family="Outfit"),
            bgcolor="rgba(6,11,24,0.88)",
            bordercolor=lc, borderwidth=1.5, borderpad=5,
            align="center",
            row=1, col=1,
        )
        # 圓點
        fig.add_trace(go.Scatter(
            x=[x_d[idx]], y=[price],
            mode="markers",
            marker=dict(color=lc, size=8, symbol="circle",
                        line=dict(color="white",width=1)),
            showlegend=False, hoverinfo="skip",
        ), row=1, col=1)

    # ── 當前浪色塊 ──
    if len(waves) >= 2:
        last_idx = waves[-1][0]
        last_lbl = waves[-1][2]
        lc = WAVE_COLORS.get(last_lbl, "#94a3b8")
        x0 = x_d[min(waves[-2][0], len(x_d)-1)]
        x1 = x_d[-1]
        y0 = float(min(L[last_idx:])) * 0.997
        y1 = float(max(H[last_idx:])) * 1.003
        try:
            r,g,b=int(lc[1:3],16),int(lc[3:5],16),int(lc[5:7],16)
            fig.add_shape(type="rect",x0=x0,x1=x1,y0=y0,y1=y1,
                fillcolor=f"rgba({r},{g},{b},0.07)",
                line=dict(color=f"rgba({r},{g},{b},0.2)",width=1,dash="dot"),
                row=1,col=1)
        except: pass

    # ── 費波那契 ──
    if pivots:
        lo_p = float(min(p[1] for p in pivots if p[2]=="L")) if any(p[2]=="L" for p in pivots) else L.min()
        hi_p = float(max(p[1] for p in pivots if p[2]=="H")) if any(p[2]=="H" for p in pivots) else H.max()
        _add_fib_lines(fig, row=1, lo_p=lo_p, hi_p=hi_p)

    # ── ▶ NOW 箭頭（最後一根K棒）──
    lh = float(H[-1]); lc_ = float(C[-1])
    fig.add_annotation(
        x=x_d[-1], y=lh*1.018,
        text=f"<b>▶ {lc_:.2f}</b>",
        showarrow=True, arrowhead=2,
        arrowsize=1.3, arrowwidth=2.5, arrowcolor=wcolor,
        ax=0, ay=-44,
        font=dict(size=12, color=wcolor, family="Outfit"),
        bgcolor="rgba(6,11,24,0.92)",
        bordercolor=wcolor, borderwidth=2, borderpad=6,
        row=1, col=1,
    )

    # ── 成交量 ──
    vc = ["rgba(74,222,128,0.5)" if float(c)>=float(o)
          else "rgba(248,113,113,0.5)"
          for c,o in zip(df_d["Close"],df_d["Open"])]
    fig.add_trace(go.Bar(
        x=x_d, y=df_d["Volume"], marker_color=vc,
        name="成交量", showlegend=False,
    ), row=2, col=1)
    if "VOL_MA5" in df_d.columns:
        vm = df_d["VOL_MA5"].dropna()
        if len(vm):
            fig.add_trace(go.Scatter(
                x=[x_d[i] for i in vm.index], y=vm.values,
                mode="lines", line=dict(color="#fbbf24",width=1.2),
                name="量5MA", showlegend=False,
            ), row=2, col=1)

    # ── 右上角：波浪位置 ──
    conf_color = "#4ade80" if confidence>=70 else "#fbbf24" if confidence>=50 else "#f87171"
    conf_txt   = f"信心度 {confidence}%"
    vio_str    = ""
    if violations:
        vio_str = f"<br><span style='color:#fbbf24;font-size:10px'>⚠️ {violations[0][:35]}</span>"

    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.99, y=0.99,
        text=(
            f"<b>{wave['emoji']} 波浪計數：{current}</b><br>"
            f"<span style='font-size:11px;color:#94a3b8'>"
            f"KD/MACD研判：{wave['label']}</span>"
            f"<br><span style='font-size:10px;color:{conf_color}'>{conf_txt}</span>"
            f"{vio_str}"
        ),
        showarrow=False, xanchor="right", align="right",
        font=dict(size=13, color=wcolor, family="Outfit"),
        bgcolor="rgba(6,11,24,0.92)",
        bordercolor=wcolor, borderwidth=2, borderpad=10,
    )

    # ── 鐵律違反警示（圖底部）──
    if violations:
        for i, v in enumerate(violations[:2]):
            fig.add_annotation(
                xref="paper", yref="paper",
                x=0.01, y=0.28 - i*0.05,
                text=f"<span style='color:#fbbf24'>{v}</span>",
                showarrow=False, xanchor="left",
                font=dict(size=9, color="#fbbf24", family="Outfit"),
                bgcolor="rgba(6,11,24,0.75)",
                bordercolor="#fbbf24", borderwidth=1, borderpad=4,
            )

    # ── Layout ──
    title_str = (
        f"{stock_name}（{code}）艾略特波浪  ｜  "
        f"計數：{current}  ｜  KD/MACD研判：{wave['label']}"
    )
    fig.update_layout(
        title=dict(text=title_str,
                   font=dict(size=12,color="#e2e8f0",family="Outfit"),x=0),
        paper_bgcolor="rgba(6,11,24,0)",
        plot_bgcolor ="rgba(6,11,24,0)",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h",x=0,y=1.04,
                    font=dict(size=10,color="#64748b"),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0,r=0,t=52,b=0),
        height=560,
        font=dict(family="Outfit"),
        hovermode="x unified",
    )
    ax = dict(
        gridcolor="rgba(255,255,255,0.05)", showgrid=True,
        zeroline=False, color="#475569",
        tickfont=dict(size=10,family="JetBrains Mono"),
    )
    fig.update_layout(
        xaxis=ax.copy(), xaxis2=ax.copy(),
        yaxis=ax.copy(), yaxis2=ax.copy(),
    )
    return fig
