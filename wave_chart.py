"""
wave_chart.py V4
- 上圖：中期大浪（90日，大 order）→ 標 ①②③④⑤ / A-B-C
- 下圖：近期子浪（最近 35 日，小 order）→ 標 ⅰⅱⅲⅳⅴ / a-b-c
  兩張圖一起 show，讓用戶同時看全局 + 子浪細節
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

# ─────────────────────────────────────────
# 波浪資訊（含劇本）
# ─────────────────────────────────────────
WAVE_INFO = {
    "3-1": {"color":"#38bdf8","label":"第①浪 ⅰ子浪","emoji":"🌱","desc":"起漲初動，試探性上攻",
        "scenarios":[
            {"name":"✅ 主要（65%）延伸①浪→②浪修正布局","color":"#38bdf8",
             "desc":"①浪完成後ⅱ回測38.2~61.8%，之後ⅲ才是主攻。現在是耐心等ⅱ低點加碼的機會。","cond":"量能放大，KD金叉，MACD翻紅","risk":"⚠️ 停損：①浪起漲低點"},
            {"name":"📊 次要（25%）高C整理後直攻ⅲ","color":"#fbbf24",
             "desc":"量縮整理後帶量長紅，直接進入ⅲ強攻段。","cond":"量縮後量增，站上所有短期均線","risk":"⚠️ 量縮破MA5需重新判斷"},
            {"name":"❌ 風險（10%）假突破，①浪未完成","color":"#f87171",
             "desc":"量價背離，突破後縮量，可能仍在①浪形成中。","cond":"縮量無法站上，KD高檔死叉","risk":"🛑 跌破起漲點停損"},
        ]},
    "3-3": {"color":"#4ade80","label":"第③浪主升段","emoji":"🚀","desc":"最強最長的主升浪，量能最大",
        "scenarios":[
            {"name":"✅ 主要（70%）③浪延伸，目標1.618~2.618","color":"#4ade80",
             "desc":"③浪最強，子浪ⅰ→ⅱ→ⅲ→ⅳ→ⅴ仍未完成。MACD紅柱持續放大，每次拉回均是加碼點。","cond":"MACD紅柱最高，量能最大，KD>60","risk":"⚠️ 乖離>15%先減倉等回踩"},
            {"name":"📊 次要（20%）③浪尾聲進入④浪修正","color":"#fbbf24",
             "desc":"③浪ⅴ子浪正在完成，完成後④浪修正回測38.2%費波。","cond":"量開始縮，KD高位鈍化","risk":"⚠️ 注意高點反轉"},
            {"name":"❌ 風險（10%）③浪提前結束大幅修正","color":"#f87171",
             "desc":"爆量長黑③浪可能提前結束，④浪修正達整段漲幅50%。","cond":"爆量長黑K，MACD翻綠","risk":"🛑 停損③浪起漲低點"},
        ]},
    "3-5": {"color":"#fbbf24","label":"第⑤浪末升段","emoji":"🏔️","desc":"主升尾聲，量價背離訊號出現",
        "scenarios":[
            {"name":"✅ 主要（50%）⑤浪完成→ABC大修正","color":"#fbbf24",
             "desc":"⑤浪完成整個五浪結構，A浪跌幅通常38.2~61.8%整個升幅。逐步獲利了結，等A浪底部再布局。","cond":"量價背離，KD頂背離，RSI>80","risk":"⚠️ 絕不追高，分批減倉"},
            {"name":"📊 次要（30%）⑤浪延伸仍有上攻空間","color":"#38bdf8",
             "desc":"法人持續買超量能仍放大，⑤浪可能延伸，最終都進入ABC修正。","cond":"法人買超持續，量能放大","risk":"⚠️ 嚴設停利，勿戀戰"},
            {"name":"❌ 風險（20%）失敗⑤浪急速轉空","color":"#f87171",
             "desc":"無法突破③浪高點形成失敗⑤浪，快速進入熊市。","cond":"量縮無法過③浪高，KD高位死叉","risk":"🛑 停損③浪高點"},
        ]},
    "3-a": {"color":"#94a3b8","label":"⑤浪後高檔震盪","emoji":"☕","desc":"五浪完成後高位整理",
        "scenarios":[
            {"name":"✅ 主要（55%）ABC修正已開始等A浪低點","color":"#f97316",
             "desc":"高位震盪是A浪的一部分，等A浪完成後B浪反彈出場機會。","cond":"量縮整理，均線走平","risk":"⚠️ 勿在此加碼"},
            {"name":"❌ 風險（45%）快速轉弱大A浪開始","color":"#f87171",
             "desc":"量增跌破前支撐，A浪下跌加速。","cond":"量增破支撐，MACD翻綠","risk":"🛑 停損前波高點"},
        ]},
    "4-a": {"color":"#fb923c","label":"④浪修正（a子浪下跌）","emoji":"📉","desc":"主升後④浪a子浪下跌中",
        "scenarios":[
            {"name":"✅ 主要（60%）a→b→c修正後啟動⑤浪","color":"#4ade80",
             "desc":"a子浪下跌後b子浪反彈，c子浪再跌到0.382~0.5費波，完成後啟動⑤浪。b浪反彈是輕倉試多機會。","cond":"量縮下跌，接近費波支撐","risk":"⚠️ 第4浪不應跌破第1浪高點"},
            {"name":"📊 次要（25%）④浪複雜修正W型或三角","color":"#fbbf24",
             "desc":"④浪複雜修正需更多時間，但最終啟動⑤浪。","cond":"量縮震盪，高低點收斂","risk":"⚠️ 耐心等待"},
            {"name":"❌ 風險（15%）跌破①浪高點重新定義","color":"#f87171",
             "desc":"跌破①浪頂點艾略特結構需重新定義。","cond":"帶量跌破①浪高點","risk":"🛑 全部出場"},
        ]},
    "4-b": {"color":"#f97316","label":"④浪修正（b子浪反彈）","emoji":"👀","desc":"④浪b子浪技術反彈",
        "scenarios":[
            {"name":"✅ 主要（65%）b浪反彈完成後c浪再下探","color":"#f97316",
             "desc":"b浪反彈通常到前低（現壓力），完成後c浪下跌完成④浪，之後啟動⑤浪。","cond":"量縮反彈至38.2~61.8%壓力","risk":"⚠️ 此反彈不宜追多"},
            {"name":"📊 次要（25%）b浪強勁跳過c浪直接⑤浪","color":"#fbbf24",
             "desc":"b浪量增過前高，可能④浪已完成，直接啟動⑤浪。","cond":"量增，b浪突破前高","risk":"⚠️ 需確認後才追"},
        ]},
    "4-c": {"color":"#a78bfa","label":"④浪修正末端（c子浪）","emoji":"🪤","desc":"④浪c子浪，接近底部等⑤浪",
        "scenarios":[
            {"name":"✅ 主要（65%）c浪見底→啟動⑤浪","color":"#4ade80",
             "desc":"c浪在0.382~0.618費波支撐見底，KD低位金叉+量縮帶量長紅=⑤浪啟動訊號，最佳布局點。","cond":"量縮後帶量長紅，KD<30金叉，守費波0.382","risk":"⚠️ 停損c浪低點"},
            {"name":"📊 次要（25%）c浪延伸多測一個費波","color":"#fbbf24",
             "desc":"c浪比預期更深，測到0.618才見底，⑤浪仍會啟動。","cond":"量繼續縮，慢慢探低","risk":"⚠️ 等量縮止跌再進場"},
            {"name":"❌ 風險（10%）五浪結束進入熊市A浪","color":"#f87171",
             "desc":"跌破①浪高點帶量，整個五浪主升完成，下方是大級別ABC熊市修正。","cond":"帶量跌破①浪高點","risk":"🛑 全部出場"},
        ]},
    "C-3": {"color":"#f87171","label":"ABC修正C浪（主跌段）","emoji":"🔻","desc":"空頭C浪主跌，避免抄底",
        "scenarios":[
            {"name":"✅ 主要（65%）C浪繼續下跌目標A浪1~1.618倍","color":"#f87171",
             "desc":"C浪通常等於A浪或A浪1.618倍。主跌段中量增下跌，不宜做多。","cond":"量增下跌，均線空頭排列","risk":"🛑 多單全數出清"},
            {"name":"📊 次要（25%）提前完成C浪出現底部","color":"#fbbf24",
             "desc":"量縮+KD低位背離+帶量長紅，C浪可能提前完成。","cond":"量縮，KD低位背離","risk":"⚠️ 確認後輕倉試多"},
        ]},
    "C-5": {"color":"#dc2626","label":"C浪末段趕底","emoji":"💥","desc":"恐慌殺盤極端超跌接近尾聲",
        "scenarios":[
            {"name":"✅ 主要（55%）趕底後強力反彈，新五浪即將開始","color":"#fbbf24",
             "desc":"趕底急殺後通常強力反彈，量縮止跌K棒（長下影）可輕倉布局。","cond":"量縮後爆量長紅，KD極低位回升","risk":"⚠️ 輕倉試做，嚴設停損"},
            {"name":"❌ 風險（45%）繼續探底","color":"#f87171",
             "desc":"無止跌訊號繼續破底。","cond":"量增繼續破低","risk":"🛑 勿抄底"},
        ]},
    "B-a": {"color":"#94a3b8","label":"ABC修正B浪（反彈）","emoji":"↗️","desc":"空頭格局B浪技術反彈",
        "scenarios":[
            {"name":"✅ 主要（60%）B浪反彈至38~61.8%後C浪下跌","color":"#f87171",
             "desc":"B浪通常反彈到前高38~61.8%後轉弱，之後C浪才是底部。","cond":"量縮反彈，均線仍空頭排列","risk":"⚠️ 此反彈是出貨機會"},
            {"name":"📊 次要（25%）B浪強勢，可能是新五浪起漲","color":"#4ade80",
             "desc":"B浪量增過前高，可能底部確立，新五浪上升啟動。","cond":"量增突破前高，KD低位金叉","risk":"⚠️ 突破確認後才做多"},
        ]},
    "B-c": {"color":"#ef4444","label":"B浪c子浪（反彈高點）","emoji":"⚠️","desc":"B浪反彈最高點，C浪即將展開",
        "scenarios":[
            {"name":"✅ 主要（70%）B浪完成，C主跌浪展開","color":"#f87171",
             "desc":"B浪c子浪為反彈最高點，之後C主跌浪展開。減倉逃命的最後機會。","cond":"KD高位死叉，量縮，MACD翻綠","risk":"🛑 多單清倉，不追高"},
            {"name":"📊 次要（30%）突破前高空頭結束多頭確立","color":"#4ade80",
             "desc":"放量突破A浪起點，ABC修正結束，新五浪多頭開始。","cond":"量增突破前高，所有均線翻多","risk":"⚠️ 確認後才進場"},
        ]},
    "N/A": {"color":"#64748b","label":"波浪判斷中","emoji":"❓","desc":"資料不足","scenarios":[]},
}

def get_wave_info(label):
    return WAVE_INFO.get(label, WAVE_INFO["N/A"])


def _find_pivots(highs, lows, order):
    if order < 1: order = 1
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


def _add_wave_traces(fig, df_seg, x_dates_seg, x_offset,
                     order, labels_list, colors_dict, start_type,
                     row, font_size, arrow_len, show_line=True,
                     line_color="rgba(148,163,184,0.4)"):
    """在指定的 subplot row 上繪製波浪連線 + 標注"""
    highs = df_seg["High"].values.astype(float)
    lows  = df_seg["Low"].values.astype(float)

    try:
        pivots = _find_pivots(highs, lows, order)
    except Exception:
        return []

    if not pivots:
        return []

    # 波浪連線
    if show_line and len(pivots) >= 2:
        px = [x_dates_seg[p[0]] for p in pivots if p[0] < len(x_dates_seg)]
        py = [p[1] for p in pivots if p[0] < len(x_dates_seg)]
        fig.add_trace(go.Scatter(
            x=px, y=py, mode="lines",
            line=dict(color=line_color, width=1.2, dash="dot"),
            showlegend=False,
        ), row=row, col=1)

    # 標注波浪
    result = []
    wave_n = 0
    prev_type = None
    started = False
    for pos, price, ptype in pivots:
        if pos >= len(x_dates_seg): continue
        if not started:
            if ptype == start_type:
                started = True
                prev_type = ptype
            continue
        if ptype != prev_type and wave_n < len(labels_list):
            lbl = labels_list[wave_n]
            lbl_color = colors_dict.get(lbl, "#94a3b8")
            is_hi = (ptype == "H")
            ay = -arrow_len if is_hi else arrow_len
            fig.add_annotation(
                x=x_dates_seg[pos], y=price,
                text=f"<b>{lbl}</b>",
                showarrow=True, arrowhead=2,
                arrowsize=0.85, arrowwidth=1.8,
                arrowcolor=lbl_color,
                ax=0, ay=ay,
                font=dict(size=font_size, color=lbl_color, family="Outfit"),
                bgcolor="rgba(6,11,24,0.82)",
                bordercolor=lbl_color, borderwidth=1.2, borderpad=4,
                row=row, col=1,
            )
            result.append((pos, price, lbl, lbl_color, ptype))
            wave_n += 1
            prev_type = ptype

    return result


def build_kline_chart(df, wave_label_d, stock_name="", code=""):
    if not PLOTLY_OK or df is None or len(df) < 20:
        return None

    wave   = get_wave_info(wave_label_d)
    wcolor = wave["color"]

    # 大浪：取近 90 日
    df_big = df.iloc[-90:].copy().reset_index()
    date_col = "Date" if "Date" in df_big.columns else df_big.columns[0]
    x_big = df_big[date_col].astype(str).tolist()
    n_big = len(df_big)

    # 子浪：取近 35 日
    df_sub = df.iloc[-35:].copy().reset_index()
    x_sub  = df_sub[date_col].astype(str).tolist()

    is_bull = wave_label_d.startswith(("3","4"))
    BULL_MAIN   = ["①","②","③","④","⑤"]
    BEAR_MAIN   = ["Ⓐ","Ⓑ","Ⓒ"]
    BULL_COLORS = {"①":"#38bdf8","②":"#fb923c","③":"#4ade80","④":"#f97316","⑤":"#fbbf24"}
    BEAR_COLORS = {"Ⓐ":"#f87171","Ⓑ":"#fb923c","Ⓒ":"#dc2626"}
    BULL_SUB    = ["ⅰ","ⅱ","ⅲ","ⅳ","ⅴ"]
    BEAR_SUB    = ["a","b","c"]
    BULL_SUB_C  = {"ⅰ":"#7dd3fc","ⅱ":"#fed7aa","ⅲ":"#86efac","ⅳ":"#fdba74","ⅴ":"#fde68a"}
    BEAR_SUB_C  = {"a":"#fca5a5","b":"#fdba74","c":"#f87171"}

    main_labels  = BULL_MAIN  if is_bull else BEAR_MAIN
    main_colors  = BULL_COLORS if is_bull else BEAR_COLORS
    sub_labels   = BULL_SUB   if is_bull else BEAR_SUB
    sub_colors   = BULL_SUB_C  if is_bull else BEAR_SUB_C
    start_type   = "L" if is_bull else "H"

    big_order = max(5, n_big // 12)  # 大浪：較大 order
    sub_order = 2                     # 子浪：order=2，更敏感

    # ── 建立 3 rows subplot ──
    # Row1: 大浪K線（90日）
    # Row2: 子浪K線（35日，放大版）
    # Row3: 成交量（35日）
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=False,
        row_heights=[0.42, 0.38, 0.20],
        vertical_spacing=0.04,
        subplot_titles=(
            f"📊 大浪結構（近90日）— ①②③④⑤ / A-B-C",
            f"🔍 子浪細節（近35日）— ⅰⅱⅲⅳⅴ / a-b-c",
            "",
        ),
    )

    # ══════════════════════════════════
    # ROW 1：大浪（90日 K線）
    # ══════════════════════════════════
    fig.add_trace(go.Candlestick(
        x=x_big,
        open=df_big["Open"], high=df_big["High"],
        low=df_big["Low"],   close=df_big["Close"],
        increasing=dict(line=dict(color="#4ade80",width=1), fillcolor="rgba(74,222,128,0.8)"),
        decreasing=dict(line=dict(color="#f87171",width=1), fillcolor="rgba(248,113,113,0.8)"),
        name="K線（大）", showlegend=False,
    ), row=1, col=1)

    for ma, c, w in [(5,"#f97316",1),(20,"#38bdf8",1),(60,"#a78bfa",1)]:
        cn = f"MA{ma}"
        if cn in df_big.columns:
            s = df_big[cn].dropna()
            if len(s):
                fig.add_trace(go.Scatter(
                    x=[x_big[i] for i in s.index], y=s.values,
                    mode="lines", line=dict(color=c,width=w),
                    name=f"{ma}MA", showlegend=(ma==20), opacity=0.7,
                ), row=1, col=1)

    _add_wave_traces(
        fig, df_big, x_big, 0,
        order=big_order,
        labels_list=main_labels, colors_dict=main_colors,
        start_type=start_type,
        row=1, font_size=14, arrow_len=40,
        line_color="rgba(148,163,184,0.35)",
    )

    # ══════════════════════════════════
    # ROW 2：子浪（35日 K線）
    # ══════════════════════════════════
    fig.add_trace(go.Candlestick(
        x=x_sub,
        open=df_sub["Open"], high=df_sub["High"],
        low=df_sub["Low"],   close=df_sub["Close"],
        increasing=dict(line=dict(color="#4ade80",width=1), fillcolor="rgba(74,222,128,0.85)"),
        decreasing=dict(line=dict(color="#f87171",width=1), fillcolor="rgba(248,113,113,0.85)"),
        name="K線（子）", showlegend=False,
    ), row=2, col=1)

    for ma, c, w in [(5,"#f97316",1.2),(20,"#38bdf8",1.2)]:
        cn = f"MA{ma}"
        if cn in df_sub.columns:
            s = df_sub[cn].dropna()
            if len(s):
                fig.add_trace(go.Scatter(
                    x=[x_sub[i] for i in s.index], y=s.values,
                    mode="lines", line=dict(color=c,width=w),
                    name=f"{ma}MA", showlegend=False, opacity=0.8,
                ), row=2, col=1)

    sub_result = _add_wave_traces(
        fig, df_sub, x_sub, 0,
        order=sub_order,
        labels_list=sub_labels, colors_dict=sub_colors,
        start_type=start_type,
        row=2, font_size=13, arrow_len=32,
        line_color="rgba(255,255,255,0.2)",
    )

    # 當前波浪標注（子浪圖最後一根K棒）
    last_x_sub   = x_sub[-1]
    last_high_sub = float(df_sub["High"].iloc[-1])
    fig.add_annotation(
        x=last_x_sub, y=last_high_sub*1.025,
        text=f"  {wave['emoji']} {wave['label']}",
        showarrow=True, arrowhead=2,
        arrowsize=1.3, arrowwidth=2.5, arrowcolor=wcolor,
        ax=0, ay=-48,
        font=dict(size=13, color=wcolor, family="Outfit"),
        bgcolor="rgba(6,11,24,0.9)",
        bordercolor=wcolor, borderwidth=2, borderpad=7,
        row=2, col=1,
    )

    # ══════════════════════════════════
    # ROW 3：成交量（35日）
    # ══════════════════════════════════
    vol_colors = [
        "rgba(74,222,128,0.55)" if float(c)>=float(o)
        else "rgba(248,113,113,0.55)"
        for c,o in zip(df_sub["Close"], df_sub["Open"])
    ]
    fig.add_trace(go.Bar(
        x=x_sub, y=df_sub["Volume"],
        marker_color=vol_colors,
        name="成交量", showlegend=False,
    ), row=3, col=1)
    if "VOL_MA5" in df_sub.columns:
        vm = df_sub["VOL_MA5"].dropna()
        if len(vm):
            fig.add_trace(go.Scatter(
                x=[x_sub[i] for i in vm.index], y=vm.values,
                mode="lines", line=dict(color="#fbbf24",width=1.2),
                name="量5MA", showlegend=False,
            ), row=3, col=1)

    # ══════════════════════════════════
    # Layout
    # ══════════════════════════════════
    last_sub_lbl = sub_result[-1][2] if sub_result else "?"
    title_str = (f"{stock_name}（{code}）波浪分析  ｜  "
                 f"當前：{wave['emoji']} {wave['label']}  ｜  "
                 f"子浪最後標示：{last_sub_lbl}")

    fig.update_layout(
        title=dict(text=title_str, font=dict(size=12,color="#94a3b8",family="Outfit"),x=0),
        paper_bgcolor="rgba(6,11,24,0)",
        plot_bgcolor ="rgba(6,11,24,0)",
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=False,
        legend=dict(orientation="h",x=0,y=1.02,
                    font=dict(size=10,color="#64748b"),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0,r=0,t=52,b=0),
        height=680,
        font=dict(family="Outfit"),
        hovermode="x unified",
    )
    axis_s = dict(
        gridcolor="rgba(255,255,255,0.05)", showgrid=True,
        zeroline=False, color="#475569",
        tickfont=dict(size=10,family="JetBrains Mono"),
    )
    for ax in ["xaxis","xaxis2","xaxis3","yaxis","yaxis2","yaxis3"]:
        fig.update_layout(**{ax: axis_s.copy()})

    # Subplot 標題樣式
    for ann in fig.layout.annotations:
        if ann.text:
            ann.font = dict(size=11, color="#64748b", family="Outfit")

    return fig
