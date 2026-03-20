"""
wave_chart.py V5
重點改進：
  1. 大浪圖：標示完整 ①②③④⑤，並用色塊標出「當前大浪區間」
  2. 子浪圖：只看最後 30 日，標示完整子浪 ⅰⅱⅲⅳⅴ，色塊標出「當前子浪」
  3. 右上角 + 圖中央大字：清楚顯示「現在：大浪③ 第ⅴ子浪」
  4. app.py 整合：自動計算 wave_position 並傳入
"""
import numpy as np
import pandas as pd

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from scipy.signal import argrelextrema
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False


# ────────────────────────────────────
# 波浪資訊（含劇本）
# ────────────────────────────────────
WAVE_INFO = {
    "3-1":{"color":"#38bdf8","label":"第①浪 ⅰ子浪起漲","emoji":"🌱","desc":"起漲初動，試探性上攻",
     "scenarios":[
      {"name":"✅ 主要（65%）延伸①浪→②浪修正布局","color":"#38bdf8","desc":"①浪完成後ⅱ回測38.2~61.8%，之後ⅲ才是主攻。現在是耐心等ⅱ低點加碼的機會。","cond":"量能放大，KD金叉，MACD翻紅","risk":"⚠️ 停損：①浪起漲低點"},
      {"name":"❌ 風險（10%）假突破仍在整理","color":"#f87171","desc":"量縮無法站上，可能仍在整理中。","cond":"縮量無法站上，KD高檔死叉","risk":"🛑 跌破起漲點停損"},
     ]},
    "3-3":{"color":"#4ade80","label":"第③浪主升段","emoji":"🚀","desc":"最強最長的主升浪",
     "scenarios":[
      {"name":"✅ 主要（70%）③浪延伸，目標1.618~2.618","color":"#4ade80","desc":"③浪最強，子浪ⅰⅱⅲⅳⅴ仍未完成。MACD紅柱持續放大，每次拉回均是加碼點。","cond":"MACD紅柱最高，量能最大，KD>60","risk":"⚠️ 乖離>15%先減倉"},
      {"name":"📊 次要（20%）③浪尾聲進入④修正","color":"#fbbf24","desc":"③浪ⅴ子浪正在完成，完成後④浪修正。","cond":"量縮，KD高位鈍化","risk":"⚠️ 注意高點反轉"},
      {"name":"❌ 風險（10%）③浪提前結束","color":"#f87171","desc":"爆量長黑③浪提前結束，④浪大幅修正。","cond":"爆量長黑K，MACD翻綠","risk":"🛑 停損③浪起漲低點"},
     ]},
    "3-5":{"color":"#fbbf24","label":"第⑤浪末升段","emoji":"🏔️","desc":"主升尾聲，量價背離",
     "scenarios":[
      {"name":"✅ 主要（50%）⑤浪完成→ABC大修正","color":"#fbbf24","desc":"⑤浪完成整個五浪，A浪跌幅通常38.2~61.8%整個升幅。逐步獲利了結。","cond":"量價背離，KD頂背離，RSI>80","risk":"⚠️ 絕不追高，分批減倉"},
      {"name":"📊 次要（30%）⑤浪延伸","color":"#38bdf8","desc":"法人持續買超，⑤浪可能延伸。","cond":"法人買超，量能放大","risk":"⚠️ 嚴設停利"},
      {"name":"❌ 風險（20%）失敗⑤浪急速轉空","color":"#f87171","desc":"無法突破③浪高點，快速進入熊市。","cond":"量縮無法過③浪高","risk":"🛑 停損③浪高點"},
     ]},
    "3-a":{"color":"#94a3b8","label":"⑤浪後高檔震盪","emoji":"☕","desc":"五浪完成後高位整理",
     "scenarios":[
      {"name":"✅ 主要（55%）ABC修正已開始","color":"#f97316","desc":"高位震盪是A浪的一部分，等A浪完成後B浪出場機會。","cond":"量縮整理，均線走平","risk":"⚠️ 勿加碼"},
      {"name":"❌ 風險（45%）快速轉弱","color":"#f87171","desc":"量增跌破前支撐，A浪下跌加速。","cond":"量增破支撐","risk":"🛑 停損前波高點"},
     ]},
    "4-a":{"color":"#fb923c","label":"④浪修正（a子浪）","emoji":"📉","desc":"主升後④浪a子浪下跌",
     "scenarios":[
      {"name":"✅ 主要（60%）a→b→c修正後啟動⑤浪","color":"#4ade80","desc":"a下跌→b反彈→c再跌到0.382費波，完成後啟動⑤浪。b浪是輕倉試多機會。","cond":"量縮下跌，接近費波支撐","risk":"⚠️ 第4浪不應跌破第1浪高點"},
      {"name":"❌ 風險（15%）跌破①浪高點重新定義","color":"#f87171","desc":"跌破①浪頂點艾略特結構需重新定義。","cond":"帶量跌破①浪高點","risk":"🛑 全部出場"},
     ]},
    "4-b":{"color":"#f97316","label":"④浪修正（b子浪反彈）","emoji":"👀","desc":"④浪b子浪技術反彈",
     "scenarios":[
      {"name":"✅ 主要（65%）b反彈完成後c浪再下探","color":"#f97316","desc":"b浪反彈通常到38.2~61.8%，完成後c浪下跌，之後啟動⑤浪。","cond":"量縮反彈至壓力位","risk":"⚠️ 不宜追多"},
      {"name":"📊 次要（25%）b浪強勁直接⑤浪","color":"#fbbf24","desc":"b浪量增過前高，④浪已完成直接啟動⑤浪。","cond":"量增，b浪突破前高","risk":"⚠️ 需確認後才追"},
     ]},
    "4-c":{"color":"#a78bfa","label":"④浪修正末端（c子浪）","emoji":"🪤","desc":"④浪c子浪，接近底部等⑤浪",
     "scenarios":[
      {"name":"✅ 主要（65%）c浪見底→啟動⑤浪","color":"#4ade80","desc":"c浪在0.382~0.618費波支撐見底，KD低位金叉+量縮後帶量長紅=⑤浪啟動訊號。","cond":"量縮後帶量長紅，KD<30金叉","risk":"⚠️ 停損c浪低點"},
      {"name":"❌ 風險（10%）進入熊市","color":"#f87171","desc":"跌破①浪高點帶量，下方是大級別ABC修正。","cond":"帶量跌破①浪高點","risk":"🛑 全部出場"},
     ]},
    "C-3":{"color":"#f87171","label":"ABC修正C浪（主跌）","emoji":"🔻","desc":"空頭C浪主跌，避免抄底",
     "scenarios":[
      {"name":"✅ 主要（65%）C浪繼續下跌","color":"#f87171","desc":"C浪通常等於A浪或A浪1.618倍。主跌段不宜做多。","cond":"量增下跌，均線空頭排列","risk":"🛑 多單出清"},
      {"name":"📊 次要（25%）提前完成C浪","color":"#fbbf24","desc":"量縮+KD低位背離+帶量長紅，C浪可能提前完成。","cond":"量縮，KD低位背離","risk":"⚠️ 確認後輕倉試多"},
     ]},
    "C-5":{"color":"#dc2626","label":"C浪末段趕底","emoji":"💥","desc":"恐慌殺盤極端超跌",
     "scenarios":[
      {"name":"✅ 主要（55%）趕底後反彈，新五浪即將開始","color":"#fbbf24","desc":"趕底後通常強力反彈，量縮止跌K棒可輕倉布局。","cond":"量縮後爆量長紅","risk":"⚠️ 輕倉，嚴設停損"},
      {"name":"❌ 風險（45%）繼續探底","color":"#f87171","desc":"無止跌訊號繼續破底。","cond":"量增繼續破低","risk":"🛑 勿抄底"},
     ]},
    "B-a":{"color":"#94a3b8","label":"ABC修正B浪（反彈）","emoji":"↗️","desc":"空頭格局B浪技術反彈",
     "scenarios":[
      {"name":"✅ 主要（60%）B浪反彈至38~61.8%後C浪下跌","color":"#f87171","desc":"B浪通常反彈到前高38~61.8%後轉弱，之後C浪才是底部。","cond":"量縮反彈","risk":"⚠️ 此反彈是出貨機會"},
     ]},
    "B-c":{"color":"#ef4444","label":"B浪c子浪（反彈高點）","emoji":"⚠️","desc":"B浪反彈最高點，C浪即將展開",
     "scenarios":[
      {"name":"✅ 主要（70%）B浪完成，C主跌浪展開","color":"#f87171","desc":"B浪c子浪為反彈最高點，之後C主跌浪展開。","cond":"KD高位死叉，量縮","risk":"🛑 多單清倉"},
      {"name":"📊 次要（30%）突破前高，多頭確立","color":"#4ade80","desc":"放量突破A浪起點，ABC修正結束，新五浪開始。","cond":"量增突破前高","risk":"⚠️ 確認後才進場"},
     ]},
    "N/A":{"color":"#64748b","label":"波浪判斷中","emoji":"❓","desc":"資料不足","scenarios":[]},
}

def get_wave_info(label):
    return WAVE_INFO.get(label, WAVE_INFO["N/A"])


def _find_pivots(highs, lows, order):
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


def _count_and_label(fig, df, x_dates, row,
                     order, labels_list, colors_dict, start_type,
                     font_size=13, arrow_len=38,
                     line_color="rgba(148,163,184,0.35)"):
    """
    轉折點偵測 → 連線 → 標注
    回傳：(labeled_pivots, current_label)
    current_label = 最後標注的浪名
    """
    highs = df["High"].values.astype(float)
    lows  = df["Low"].values.astype(float)
    try:
        pivots = _find_pivots(highs, lows, order)
    except Exception:
        return [], "?"

    if len(pivots) < 2:
        return [], "?"

    # 波浪連線
    px = [x_dates[p[0]] for p in pivots if p[0]<len(x_dates)]
    py = [p[1] for p in pivots if p[0]<len(x_dates)]
    fig.add_trace(go.Scatter(
        x=px, y=py, mode="lines",
        line=dict(color=line_color, width=1.3, dash="dot"),
        showlegend=False,
    ), row=row, col=1)

    labeled = []
    wave_n, prev_type, started = 0, None, False
    current_label = "?"

    for pos, price, ptype in pivots:
        if pos >= len(x_dates): continue
        if not started:
            if ptype == start_type:
                started = True; prev_type = ptype
            continue
        if ptype == prev_type: continue
        if wave_n >= len(labels_list): break

        lbl = labels_list[wave_n]
        lc  = colors_dict.get(lbl, "#94a3b8")
        is_hi = (ptype == "H")
        ay = -arrow_len if is_hi else arrow_len

        fig.add_annotation(
            x=x_dates[pos], y=price,
            text=f"<b>{lbl}</b>",
            showarrow=True, arrowhead=2,
            arrowsize=0.85, arrowwidth=1.8, arrowcolor=lc,
            ax=0, ay=ay,
            font=dict(size=font_size, color=lc, family="Outfit"),
            bgcolor="rgba(6,11,24,0.85)",
            bordercolor=lc, borderwidth=1.5, borderpad=5,
            row=row, col=1,
        )
        labeled.append((pos, price, lbl, lc, ptype))
        current_label = lbl
        wave_n += 1; prev_type = ptype

    # 用色塊高亮最後一段浪
    if len(labeled) >= 1:
        last_pos = labeled[-1][0]
        last_price = labeled[-1][1]
        last_type  = labeled[-1][4]
        # 從最後一個轉折點到現在
        x0 = x_dates[last_pos]
        x1 = x_dates[-1]
        y_vals = df["Close"].values
        y0 = min(y_vals[last_pos:]) * 0.995
        y1 = max(y_vals[last_pos:]) * 1.005
        lc = labeled[-1][3]
        fig.add_shape(
            type="rect",
            x0=x0, x1=x1, y0=y0, y1=y1,
            fillcolor=lc.replace(")", ",0.07)").replace("rgb", "rgba"),
            line=dict(color=lc.replace(")", ",0.3)").replace("rgb","rgba"), width=1),
            row=row, col=1,
        )

    return labeled, current_label


def build_kline_chart(df, wave_label_d, stock_name="", code=""):
    if not PLOTLY_OK or df is None or len(df) < 20:
        return None

    wave   = get_wave_info(wave_label_d)
    wcolor = wave["color"]
    is_bull = wave_label_d.startswith(("3","4"))

    date_col = "Date" if "Date" in df.columns else df.reset_index().columns[0]

    # ── 大浪資料：近 90 日 ──
    df_big = df.iloc[-90:].copy().reset_index()
    if "level_0" in df_big.columns: df_big = df_big.drop(columns=["level_0"])
    dc = "Date" if "Date" in df_big.columns else df_big.columns[0]
    x_big = df_big[dc].astype(str).tolist()

    # ── 子浪資料：近 30 日 ──
    df_sub = df.iloc[-30:].copy().reset_index()
    if "level_0" in df_sub.columns: df_sub = df_sub.drop(columns=["level_0"])
    dc2 = "Date" if "Date" in df_sub.columns else df_sub.columns[0]
    x_sub = df_sub[dc2].astype(str).tolist()

    BULL_MAIN  = ["①","②","③","④","⑤"]
    BEAR_MAIN  = ["Ⓐ","Ⓑ","Ⓒ"]
    BULL_MAIN_C= {"①":"#38bdf8","②":"#fb923c","③":"#4ade80","④":"#f97316","⑤":"#fbbf24"}
    BEAR_MAIN_C= {"Ⓐ":"#f87171","Ⓑ":"#fb923c","Ⓒ":"#dc2626"}
    BULL_SUB   = ["ⅰ","ⅱ","ⅲ","ⅳ","ⅴ"]
    BEAR_SUB   = ["a","b","c"]
    BULL_SUB_C = {"ⅰ":"#7dd3fc","ⅱ":"#fed7aa","ⅲ":"#86efac","ⅳ":"#fdba74","ⅴ":"#fde68a"}
    BEAR_SUB_C = {"a":"#fca5a5","b":"#fdba74","c":"#f87171"}

    m_labels = BULL_MAIN  if is_bull else BEAR_MAIN
    m_colors = BULL_MAIN_C if is_bull else BEAR_MAIN_C
    s_labels = BULL_SUB   if is_bull else BEAR_SUB
    s_colors = BULL_SUB_C  if is_bull else BEAR_SUB_C
    start_t  = "L" if is_bull else "H"

    big_order = max(5, len(x_big)//10)
    sub_order = 2

    # ── 建立 subplot：Row1=大浪, Row2=子浪, Row3=成交量 ──
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=False,
        row_heights=[0.42, 0.38, 0.20],
        vertical_spacing=0.04,
        subplot_titles=("", "", ""),
    )

    # ═══════════════════
    # ROW 1：大浪 K線
    # ═══════════════════
    fig.add_trace(go.Candlestick(
        x=x_big,
        open=df_big["Open"], high=df_big["High"],
        low=df_big["Low"],   close=df_big["Close"],
        increasing=dict(line=dict(color="#4ade80",width=1),fillcolor="rgba(74,222,128,0.8)"),
        decreasing=dict(line=dict(color="#f87171",width=1),fillcolor="rgba(248,113,113,0.8)"),
        name="K線", showlegend=False,
    ), row=1, col=1)
    for ma,c,w in [(5,"#f97316",1),(20,"#38bdf8",1.2),(60,"#a78bfa",1)]:
        cn=f"MA{ma}"
        if cn in df_big.columns:
            s=df_big[cn].dropna()
            if len(s):
                fig.add_trace(go.Scatter(
                    x=[x_big[i] for i in s.index],y=s.values,
                    mode="lines",line=dict(color=c,width=w),
                    name=f"{ma}MA",showlegend=(ma==20),opacity=0.75,
                ),row=1,col=1)

    main_labeled, main_current = _count_and_label(
        fig, df_big, x_big, row=1,
        order=big_order,
        labels_list=m_labels, colors_dict=m_colors,
        start_type=start_t,
        font_size=15, arrow_len=42,
        line_color="rgba(148,163,184,0.38)",
    )

    # Row1 標題文字（直接加 annotation）
    fig.add_annotation(
        text="📊 大浪結構（近90日）",
        x=0, y=1.0, xref="paper", yref="paper",
        showarrow=False, xanchor="left",
        font=dict(size=11, color="#64748b", family="Outfit"),
    )

    # ═══════════════════
    # ROW 2：子浪 K線
    # ═══════════════════
    fig.add_trace(go.Candlestick(
        x=x_sub,
        open=df_sub["Open"], high=df_sub["High"],
        low=df_sub["Low"],   close=df_sub["Close"],
        increasing=dict(line=dict(color="#4ade80",width=1),fillcolor="rgba(74,222,128,0.85)"),
        decreasing=dict(line=dict(color="#f87171",width=1),fillcolor="rgba(248,113,113,0.85)"),
        name="K線(子)", showlegend=False,
    ), row=2, col=1)
    for ma,c,w in [(5,"#f97316",1.3),(20,"#38bdf8",1.3)]:
        cn=f"MA{ma}"
        if cn in df_sub.columns:
            s=df_sub[cn].dropna()
            if len(s):
                fig.add_trace(go.Scatter(
                    x=[x_sub[i] for i in s.index],y=s.values,
                    mode="lines",line=dict(color=c,width=w),
                    name=f"{ma}MA",showlegend=False,opacity=0.85,
                ),row=2,col=1)

    sub_labeled, sub_current = _count_and_label(
        fig, df_sub, x_sub, row=2,
        order=sub_order,
        labels_list=s_labels, colors_dict=s_colors,
        start_type=start_t,
        font_size=13, arrow_len=30,
        line_color="rgba(255,255,255,0.18)",
    )

    # ── 當前位置：大字框（子浪圖右上角）──
    pos_text = f"現在：大浪{main_current} → 子浪{sub_current}"
    fig.add_annotation(
        x=0.98, y=0.62,
        xref="paper", yref="paper",
        text=f"<b>{wave['emoji']} {pos_text}</b>",
        showarrow=False, xanchor="right",
        font=dict(size=14, color=wcolor, family="Outfit"),
        bgcolor="rgba(6,11,24,0.88)",
        bordercolor=wcolor, borderwidth=2, borderpad=9,
    )

    # ── 當前箭頭（子浪圖最後一根K棒）──
    lh = float(df_sub["High"].iloc[-1])
    fig.add_annotation(
        x=x_sub[-1], y=lh*1.022,
        text=f"<b>▶ NOW</b>",
        showarrow=True, arrowhead=2,
        arrowsize=1.4, arrowwidth=2.8, arrowcolor=wcolor,
        ax=0, ay=-50,
        font=dict(size=12, color=wcolor, family="Outfit"),
        bgcolor="rgba(6,11,24,0.9)",
        bordercolor=wcolor, borderwidth=2, borderpad=6,
        row=2, col=1,
    )

    # ── 波浪說明（子浪圖左下）──
    fig.add_annotation(
        x=x_sub[0], y=float(df_sub["Low"].iloc[:5].min())*0.993,
        text=f"<i>⬜=當前浪區間  虛線=轉折連線</i>",
        showarrow=False, xanchor="left",
        font=dict(size=9, color="#475569", family="Outfit"),
        row=2, col=1,
    )

    # ═══════════════════
    # ROW 3：成交量
    # ═══════════════════
    vol_c = ["rgba(74,222,128,0.55)" if float(c)>=float(o)
             else "rgba(248,113,113,0.55)"
             for c,o in zip(df_sub["Close"],df_sub["Open"])]
    fig.add_trace(go.Bar(
        x=x_sub, y=df_sub["Volume"],
        marker_color=vol_c, name="成交量", showlegend=False,
    ), row=3, col=1)
    if "VOL_MA5" in df_sub.columns:
        vm=df_sub["VOL_MA5"].dropna()
        if len(vm):
            fig.add_trace(go.Scatter(
                x=[x_sub[i] for i in vm.index],y=vm.values,
                mode="lines",line=dict(color="#fbbf24",width=1.2),
                name="量5MA",showlegend=False,
            ),row=3,col=1)

    # ═══════════════════
    # 全域 Layout
    # ═══════════════════
    title_str = (
        f"{stock_name}（{code}）艾略特波浪分析  ｜  "
        f"{wave['emoji']} {wave['label']}  ｜  "
        f"📍 {pos_text}"
    )
    fig.update_layout(
        title=dict(text=title_str,
                   font=dict(size=12,color="#e2e8f0",family="Outfit"),x=0),
        paper_bgcolor="rgba(6,11,24,0)",
        plot_bgcolor ="rgba(6,11,24,0)",
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=False,
        legend=dict(orientation="h",x=0,y=1.03,
                    font=dict(size=10,color="#64748b"),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0,r=0,t=52,b=0),
        height=700,
        font=dict(family="Outfit"),
        hovermode="x unified",
    )
    ax = dict(
        gridcolor="rgba(255,255,255,0.05)",showgrid=True,zeroline=False,
        color="#475569",tickfont=dict(size=10,family="JetBrains Mono"),
    )
    for k in ["xaxis","xaxis2","xaxis3","yaxis","yaxis2","yaxis3"]:
        fig.update_layout(**{k:ax.copy()})

    return fig
