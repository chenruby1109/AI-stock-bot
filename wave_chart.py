"""
wave_chart.py V2 — 完整艾略特波浪計數 + 日K線圖
自動偵測高低點，標示完整浪數（1-2-3-4-5 + A-B-C）
"""
import numpy as np
import pandas as pd
from datetime import datetime

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from scipy.signal import argrelextrema
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False


# ─────────────────────────────────────────
# 波浪資訊對照表
# ─────────────────────────────────────────
WAVE_INFO = {
    "3-1": {"color":"#38bdf8","label":"第1浪","emoji":"🌱","desc":"趨勢初升，多空轉換點",
            "scenarios":[
                {"name":"✅ 主要劇本（65%）：延伸第1浪 → 第2浪修正","color":"#38bdf8",
                 "desc":"成交量逐步放大，突破前高後拉回測試支撐。預計修正38.2%~61.8%為最佳布局點。",
                 "cond":"量能持續，突破前高，KD未死叉","risk":"⚠️ 跌破起漲點型態失效"},
                {"name":"📊 次要劇本（25%）：High-C整理後再攻","color":"#fbbf24",
                 "desc":"第1浪完成後高檔震盪，K值壓縮在40-60區間整理。","cond":"量縮整理，MA5支撐不破","risk":"⚠️ 整理時間過長需警戒"},
                {"name":"❌ 風險劇本（10%）：假突破回起漲點","color":"#f87171",
                 "desc":"量價背離，突破後無法站穩，回測起漲點。","cond":"量縮價漲，KD高檔死叉","risk":"🛑 停損：跌破起漲點"},
            ]},
    "3-3": {"color":"#4ade80","label":"第3浪主升","emoji":"🚀","desc":"最強動力波，主力全力買進",
            "scenarios":[
                {"name":"✅ 主要劇本（70%）：噴出延伸 → 目標1.618倍","color":"#4ade80",
                 "desc":"第3浪最長最強，目標1.618~2.618倍擴展。逢拉回沿5MA操作。",
                 "cond":"MACD紅柱放大，KD>50，量比>1.5","risk":"⚠️ 乖離過大（>15%）先獲利了結部分"},
                {"name":"📊 次要劇本（20%）：橫盤整理後二次攻擊","color":"#fbbf24",
                 "desc":"主升稍歇高檔短暫震盪，MA5跟上後再度出量攻擊。","cond":"量縮整理不破MA10，MACD高檔鈍化","risk":"⚠️ 注意量能是否持續"},
                {"name":"❌ 風險劇本（10%）：提前結束進入第4浪","color":"#f87171",
                 "desc":"長上影線+量縮反轉，主升可能提前結束。","cond":"高檔爆量長黑K，MACD翻綠","risk":"🛑 停損：跌破前一波高點"},
            ]},
    "3-5": {"color":"#fbbf24","label":"第5浪噴出末段","emoji":"🏔️","desc":"主升尾聲，注意高點反轉",
            "scenarios":[
                {"name":"✅ 主要劇本（50%）：完成第5浪 → ABC修正","color":"#fbbf24",
                 "desc":"第5浪完成後預計ABC三波修正，A浪跌幅通常38.2%~61.8%。","cond":"量價背離，KD高檔死叉","risk":"⚠️ 此位置不宜重倉追高"},
                {"name":"📊 次要劇本（30%）：延伸第5浪繼續上攻","color":"#38bdf8",
                 "desc":"法人持續買超第5浪可能延伸，注意RSI背離。","cond":"法人持續買超，量能仍放大","risk":"⚠️ 嚴設停利"},
                {"name":"❌ 風險劇本（20%）：失敗第5浪急速反轉","color":"#f87171",
                 "desc":"無法突破第3浪高點形成失敗第5浪。","cond":"量縮無法過高，KD高檔鈍化後急跌","risk":"🛑 停損：跌破第4浪低點"},
            ]},
    "3-a": {"color":"#94a3b8","label":"高檔震盪","emoji":"☕","desc":"漲勢放緩，等待方向確認",
            "scenarios":[
                {"name":"✅ 主要劇本（55%）：量縮整理後再攻","color":"#4ade80","desc":"高檔收斂整理量縮正常，等待帶量突破。","cond":"量縮，均線持續上揚","risk":"⚠️ 整理過久重新評估"},
                {"name":"❌ 風險劇本（45%）：進入修正","color":"#f87171","desc":"量縮後無法放量突破，進入較大幅度修正。","cond":"MACD翻綠，KD死叉，跌破MA5","risk":"🛑 停損：跌破前波低點"},
            ]},
    "4-a": {"color":"#fb923c","label":"第4浪初跌","emoji":"📉","desc":"主升後正常修正，提供加碼機會",
            "scenarios":[
                {"name":"✅ 主要劇本（60%）：修正至0.382 → 啟動第5浪","color":"#4ade80",
                 "desc":"第4浪回測0.382~0.5費波，完成後啟動第5浪。KD低位金叉是最佳買點。","cond":"量縮見底，KD低檔金叉，守住MA60","risk":"⚠️ 第4浪不應跌破第1浪高點"},
                {"name":"📊 次要劇本（25%）：複雜修正延伸","color":"#fbbf24","desc":"第4浪形成複雜修正（W形、三角整理）。","cond":"量縮震盪，每次反彈力道不足","risk":"⚠️ 耐心等待修正完成"},
                {"name":"❌ 風險劇本（15%）：修正破位重新定義","color":"#f87171","desc":"跌破第1浪高點整個結構需重新定義。","cond":"跌破第1浪頂點，成交量放大下跌","risk":"🛑 確認跌破後立即出場"},
            ]},
    "4-b": {"color":"#f97316","label":"反彈逃命波","emoji":"👀","desc":"空頭反彈，趨勢仍弱",
            "scenarios":[
                {"name":"✅ 主要劇本（65%）：反彈至壓力後繼續下跌","color":"#f87171","desc":"空頭格局中技術性反彈，到壓力後再度下跌。","cond":"量縮反彈，均線空頭排列","risk":"⚠️ 此處不宜做多"},
                {"name":"📊 次要劇本（25%）：反彈力道強形成底部","color":"#fbbf24","desc":"若反彈過前高且量能放大，可能是底部確立。","cond":"量增過前高，KD低位金叉","risk":"⚠️ 確認突破後才可做多"},
            ]},
    "4-c": {"color":"#a78bfa","label":"修正末端","emoji":"🪤","desc":"接近底部，等待反轉訊號",
            "scenarios":[
                {"name":"✅ 主要劇本（60%）：底部確立 → 啟動新一波","color":"#4ade80","desc":"K值低檔鈍化後回升，帶量長紅底部確立。","cond":"K值<20後回升，量縮後帶量紅K","risk":"⚠️ 停損：跌破前低"},
                {"name":"📊 次要劇本（30%）：繼續打底延伸","color":"#fbbf24","desc":"W底或頭肩底正在形成，等待突破頸線。","cond":"量縮震盪，每次跌幅縮小","risk":"⚠️ 耐心等待突破確認"},
                {"name":"❌ 風險劇本（10%）：假底繼續探低","color":"#f87171","desc":"帶量跌破前低，底部型態失敗。","cond":"量增跌破前低","risk":"🛑 立即出場"},
            ]},
    "C-3": {"color":"#f87171","label":"主跌段C浪","emoji":"🔻","desc":"空頭核心，避免抄底",
            "scenarios":[
                {"name":"✅ 主要劇本（65%）：繼續下跌完成C浪目標","color":"#f87171","desc":"C浪通常等於A浪長度或1.618倍，等量縮止跌。","cond":"量增下跌，均線空頭排列","risk":"🛑 多單全數出清"},
                {"name":"📊 次要劇本（25%）：提前完成C浪形成底部","color":"#fbbf24","desc":"量縮後帶量長紅反轉，KD低位背離。","cond":"量縮放量長紅，KD低位背離","risk":"⚠️ 確認反轉後輕倉試做"},
            ]},
    "C-5": {"color":"#dc2626","label":"趕底急殺","emoji":"💥","desc":"恐慌性殺盤，極端超跌",
            "scenarios":[
                {"name":"✅ 主要劇本（55%）：超跌反彈確認底部","color":"#fbbf24","desc":"趕底急殺後通常強烈反彈，止跌K棒（長下影線）可輕倉試做。","cond":"量縮後爆量長紅，KD極低位","risk":"⚠️ 輕倉試做，嚴設停損"},
                {"name":"❌ 風險劇本（45%）：繼續探底","color":"#f87171","desc":"無止跌訊號，恐慌賣壓持續。","cond":"量增繼續破低","risk":"🛑 勿抄底"},
            ]},
    "B-a": {"color":"#94a3b8","label":"跌深反彈","emoji":"↗️","desc":"空頭中的短線反彈",
            "scenarios":[
                {"name":"✅ 主要劇本（60%）：反彈至38.2%~61.8%後繼續空","color":"#f87171","desc":"空頭B浪反彈，到費波壓力後繼續空頭。","cond":"量縮反彈","risk":"⚠️ 空頭格局多單輕倉"},
            ]},
    "B-c": {"color":"#ef4444","label":"反彈高點","emoji":"⚠️","desc":"空頭反彈至壓力區，出場機會",
            "scenarios":[
                {"name":"✅ 主要劇本（70%）：逃命波高點","color":"#f87171","desc":"B浪c段為反彈最高點，是清倉或放空的最佳時機。","cond":"KD高位死叉，量縮，MACD翻綠","risk":"🛑 多單清倉，不追高"},
                {"name":"📊 次要劇本（30%）：突破壓力趨勢反轉","color":"#4ade80","desc":"放量突破前高且MACD翻紅，可能是多頭反轉。","cond":"量增突破前高，KD低位金叉","risk":"⚠️ 突破後確認才進場"},
            ]},
    "N/A": {"color":"#64748b","label":"判斷中","emoji":"❓","desc":"資料不足","scenarios":[]},
}

def get_wave_info(label):
    return WAVE_INFO.get(label, WAVE_INFO["N/A"])


# ─────────────────────────────────────────
# 高低點偵測
# ─────────────────────────────────────────
def _find_pivots(df, order=5):
    """
    找轉折高低點
    回傳 pivots: [(index_pos, price, 'H'/'L'), ...]
    """
    closes = df["Close"].values
    highs  = df["High"].values
    lows   = df["Low"].values

    hi_idx = argrelextrema(highs, np.greater_equal, order=order)[0]
    lo_idx = argrelextrema(lows,  np.less_equal,    order=order)[0]

    pivots = []
    for i in hi_idx:
        pivots.append((i, highs[i], "H"))
    for i in lo_idx:
        pivots.append((i, lows[i], "L"))

    pivots.sort(key=lambda x: x[0])

    # 去重：相鄰同型留最極值
    clean = []
    for p in pivots:
        if clean and clean[-1][2] == p[2]:
            if p[2] == "H" and p[1] >= clean[-1][1]:
                clean[-1] = p
            elif p[2] == "L" and p[1] <= clean[-1][1]:
                clean[-1] = p
        else:
            clean.append(p)
    return clean


# ─────────────────────────────────────────
# 波浪計數（簡化版艾略特）
# ─────────────────────────────────────────
def _count_waves(pivots, trend="bull"):
    """
    從轉折點序列嘗試標示艾略特波浪
    回傳 labels: [(index_pos, price, label_text, color), ...]
    """
    if len(pivots) < 3:
        return []

    labels = []

    # 多頭浪計數：L→H→L→H→L→H = 1-2-3-4-5
    # 空頭浪計數：H→L→H→L→H→L = A-B-C
    bull_labels = ["①","②","③","④","⑤","⓪"]
    bear_labels = ["Ⓐ","Ⓑ","Ⓒ"]
    sub_labels  = ["ⅰ","ⅱ","ⅲ","ⅳ","ⅴ"]

    bull_colors = {
        "①":"#38bdf8","②":"#f97316","③":"#4ade80",
        "④":"#fb923c","⑤":"#fbbf24","⓪":"#94a3b8",
    }
    bear_colors = {"Ⓐ":"#f87171","Ⓑ":"#fb923c","Ⓒ":"#dc2626"}

    # 找最近一個低點作為起浪點
    # 取最後 min(11, len) 個轉折點
    recent = pivots[-min(12, len(pivots)):]

    # 判斷多空：若低點在左高點在右 → 多頭
    if len(recent) >= 2:
        is_bull = recent[-1][2] == "H" or (
            recent[-1][2] == "L" and
            recent[-2][2] == "H" and
            recent[-1][1] > recent[0][1]
        )
    else:
        is_bull = trend == "bull"

    if is_bull:
        # 多頭：找最近的低→高→低→高→低→高序列
        wave_n = 0
        prev_type = None
        for pos, price, ptype in recent:
            if wave_n == 0 and ptype == "L":
                labels.append((pos, price, "起", "#64748b"))
                wave_n = 1
                prev_type = "L"
            elif wave_n <= 5 and ptype != prev_type:
                if wave_n < len(bull_labels):
                    lbl = bull_labels[wave_n - 1]
                    labels.append((pos, price, lbl, bull_colors.get(lbl,"#94a3b8")))
                wave_n += 1
                prev_type = ptype
    else:
        # 空頭/修正：A-B-C
        wave_n = 0
        prev_type = None
        for pos, price, ptype in recent:
            if wave_n == 0 and ptype == "H":
                labels.append((pos, price, "頂", "#f87171"))
                wave_n = 1
                prev_type = "H"
            elif wave_n <= 3 and ptype != prev_type:
                if wave_n - 1 < len(bear_labels):
                    lbl = bear_labels[wave_n - 1]
                    labels.append((pos, price, lbl, bear_colors.get(lbl,"#f87171")))
                wave_n += 1
                prev_type = ptype

    return labels


# ─────────────────────────────────────────
# 主繪圖函式
# ─────────────────────────────────────────
def build_kline_chart(df, wave_label_d, stock_name="", code=""):
    if not PLOTLY_OK or df is None or len(df) < 20:
        return None

    from scipy.signal import argrelextrema as _are

    df = df.copy()
    # 取近 120 日
    df = df.iloc[-120:].copy()
    df = df.reset_index()
    # index 欄位可能叫 Date 或 Datetime
    date_col = "Date" if "Date" in df.columns else df.columns[0]

    wave  = get_wave_info(wave_label_d)
    wcolor = wave["color"]

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.72, 0.28],
        vertical_spacing=0.02,
        subplot_titles=("", ""),
    )

    x_idx = list(range(len(df)))  # 用整數 index 避免時區問題
    x_dates = df[date_col].astype(str).tolist()

    # ── K線 ──
    fig.add_trace(go.Candlestick(
        x=x_dates,
        open=df["Open"], high=df["High"],
        low=df["Low"],   close=df["Close"],
        increasing=dict(line=dict(color="#4ade80",width=1), fillcolor="rgba(74,222,128,0.85)"),
        decreasing=dict(line=dict(color="#f87171",width=1), fillcolor="rgba(248,113,113,0.85)"),
        name="K線", whiskerwidth=0.3,
    ), row=1, col=1)

    # ── 均線 ──
    for ma, col, w in [(5,"#f97316",1.5),(20,"#38bdf8",1.5),(60,"#a78bfa",1.5)]:
        col_n = f"MA{ma}"
        if col_n in df.columns:
            s = df[col_n].dropna()
            if len(s):
                fig.add_trace(go.Scatter(
                    x=[x_dates[i] for i in s.index],
                    y=s.values,
                    mode="lines",
                    line=dict(color=col, width=w),
                    name=f"{ma}MA", opacity=0.9,
                ), row=1, col=1)

    # ── 偵測高低點 ──
    try:
        pivots = _find_pivots(df, order=max(3, len(df)//25))
    except Exception:
        pivots = []

    # ── 波浪連線 ──
    if len(pivots) >= 2:
        px = [x_dates[p[0]] for p in pivots if p[0] < len(x_dates)]
        py = [p[1] for p in pivots if p[0] < len(x_dates)]
        fig.add_trace(go.Scatter(
            x=px, y=py,
            mode="lines",
            line=dict(color="rgba(148,163,184,0.35)", width=1.2, dash="dot"),
            name="波浪連線", showlegend=False,
        ), row=1, col=1)

    # ── 波浪計數標注 ──
    trend_now = "bull" if wave_label_d.startswith(("3","4")) else "bear"
    wave_labels = _count_waves(pivots, trend_now)

    for pos, price, lbl, lbl_color in wave_labels:
        if pos >= len(x_dates):
            continue
        is_high = any(p[0]==pos and p[2]=="H" for p in pivots)
        ay = -30 if is_high else 30
        fig.add_annotation(
            x=x_dates[pos],
            y=price,
            text=f"<b>{lbl}</b>",
            showarrow=True,
            arrowhead=2,
            arrowsize=0.8,
            arrowwidth=1.5,
            arrowcolor=lbl_color,
            ax=0, ay=ay,
            font=dict(size=14, color=lbl_color, family="Outfit"),
            bgcolor="rgba(6,11,24,0.75)",
            bordercolor=lbl_color,
            borderwidth=1,
            borderpad=4,
        )

    # ── 當前波浪標注（最後一根K棒）──
    last_x     = x_dates[-1]
    last_high  = float(df["High"].iloc[-1])
    fig.add_annotation(
        x=last_x,
        y=last_high * 1.022,
        text=f"  {wave['emoji']} {wave['label']}",
        showarrow=True,
        arrowhead=2,
        arrowsize=1.3,
        arrowcolor=wcolor,
        arrowwidth=2,
        ax=0, ay=-40,
        font=dict(size=13, color=wcolor, family="Outfit"),
        bgcolor="rgba(6,11,24,0.88)",
        bordercolor=wcolor,
        borderwidth=1.5,
        borderpad=6,
    )

    # ── 成交量 ──
    vol_colors = [
        "rgba(74,222,128,0.55)" if float(c) >= float(o) else "rgba(248,113,113,0.55)"
        for c, o in zip(df["Close"], df["Open"])
    ]
    fig.add_trace(go.Bar(
        x=x_dates, y=df["Volume"],
        marker_color=vol_colors,
        name="成交量", showlegend=False,
    ), row=2, col=1)

    if "VOL_MA5" in df.columns:
        vm = df["VOL_MA5"].dropna()
        fig.add_trace(go.Scatter(
            x=[x_dates[i] for i in vm.index],
            y=vm.values,
            mode="lines",
            line=dict(color="#fbbf24", width=1.2),
            name="量5MA",
        ), row=2, col=1)

    # ── 版面 ──
    title_str = (f"{stock_name}（{code}）日K線 ｜ 當前波浪：{wave['emoji']} {wave['label']}"
                 f" — {wave['desc']}")
    fig.update_layout(
        title=dict(text=title_str, font=dict(size=13,color="#94a3b8",family="Outfit"), x=0),
        paper_bgcolor="rgba(6,11,24,0)",
        plot_bgcolor ="rgba(6,11,24,0)",
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h", x=0, y=1.03,
            font=dict(size=11,color="#64748b"),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=0,r=0,t=48,b=0),
        height=520,
        font=dict(family="Outfit"),
        hovermode="x unified",
    )
    axis_style = dict(
        gridcolor="rgba(255,255,255,0.05)",
        showgrid=True, zeroline=False,
        color="#475569",
        tickfont=dict(size=11,family="JetBrains Mono"),
    )
    fig.update_layout(
        xaxis=axis_style,  xaxis2=axis_style,
        yaxis=axis_style,  yaxis2=axis_style,
    )
    return fig
