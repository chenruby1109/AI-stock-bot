"""
wave_chart.py — 日K線圖 + 波浪標記 + 劇本分析
使用 Plotly 繪製互動式 K線圖，標示當前波浪位置與未來走勢劇本
"""
import numpy as np
import pandas as pd
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False


# ─────────────────────────────────────────
# 波浪顏色與說明對照
# ─────────────────────────────────────────
WAVE_INFO = {
    "3-1": {
        "color":   "#38bdf8",
        "label":   "第1浪",
        "desc":    "趨勢初升，多空轉換點",
        "emoji":   "🌱",
        "scenarios": [
            {
                "name":  "✅ 主要劇本（機率65%）：延伸第1浪 → 進入第2浪修正",
                "color": "#38bdf8",
                "desc":  "成交量逐步放大，突破前高後拉回測試支撐。預計修正幅度 38.2%~61.8%，為最佳布局點。",
                "cond":  "量能持續，突破前高，KD未死叉",
                "risk":  "⚠️ 若跌破起漲點，型態失敗",
            },
            {
                "name":  "📊 次要劇本（機率25%）：High-C 整理後再攻",
                "color": "#fbbf24",
                "desc":  "第1浪完成後高檔震盪，K值壓縮在40-60區間整理，等待再次放量突破。",
                "cond":  "量縮整理，MA5支撐不破，MACD鈍化",
                "risk":  "⚠️ 整理時間過長需警戒",
            },
            {
                "name":  "❌ 風險劇本（機率10%）：假突破 → 回到起漲點",
                "color": "#f87171",
                "desc":  "量價背離，突破後無法站穩，回測起漲點支撐，若跌破則整個波段型態失效。",
                "cond":  "量縮價漲，KD高檔死叉，法人持續賣超",
                "risk":  "🛑 停損：跌破起漲點",
            },
        ],
    },
    "3-3": {
        "color":   "#4ade80",
        "label":   "第3浪主升",
        "desc":    "最強動力波，主力全力買進",
        "emoji":   "🚀",
        "scenarios": [
            {
                "name":  "✅ 主要劇本（機率70%）：噴出延伸 → 目標1.618倍",
                "color": "#4ade80",
                "desc":  "第3浪通常是最長最強的波段，目標1.618~2.618倍擴展。MACD持續紅柱放大，量能爆發，逢拉回沿5MA操作。",
                "cond":  "MACD紅柱放大，KD>50，量比>1.5",
                "risk":  "⚠️ 乖離過大（>15%）可先獲利了結部分",
            },
            {
                "name":  "📊 次要劇本（機率20%）：橫盤整理後二次攻擊",
                "color": "#fbbf24",
                "desc":  "主升稍歇，高檔短暫震盪整理，MA5跟上後再度出量攻擊，為加碼機會。",
                "cond":  "量縮整理不破MA10，MACD高檔鈍化",
                "risk":  "⚠️ 注意量能是否持續",
            },
            {
                "name":  "❌ 風險劇本（機率10%）：提前結束 → 進入第4浪修正",
                "color": "#f87171",
                "desc":  "若出現長上影線+量縮反轉，主升可能提前結束，進入第4浪較大幅度修正。",
                "cond":  "高檔爆量長黑K，MACD翻綠",
                "risk":  "🛑 停損：跌破前一波高點",
            },
        ],
    },
    "3-5": {
        "color":   "#fbbf24",
        "label":   "第5浪噴出末段",
        "desc":    "主升尾聲，注意高點反轉",
        "emoji":   "🏔️",
        "scenarios": [
            {
                "name":  "✅ 主要劇本（機率50%）：完成第5浪 → 進入ABC修正",
                "color": "#fbbf24",
                "desc":  "第5浪完成整個主升結構，預計ABC三波修正，A浪跌幅通常為整個漲幅的38.2%~61.8%。",
                "cond":  "量價背離開始，KD高檔死叉",
                "risk":  "⚠️ 此位置不宜重倉追高",
            },
            {
                "name":  "📊 次要劇本（機率30%）：延伸第5浪繼續上攻",
                "color": "#38bdf8",
                "desc":  "法人持續買超，第5浪可能延伸，但需注意RSI背離與量能是否跟上。",
                "cond":  "法人持續買超，量能仍放大",
                "risk":  "⚠️ 嚴設停利，勿貪戀高點",
            },
            {
                "name":  "❌ 風險劇本（機率20%）：失敗第5浪 → 急速反轉",
                "color": "#f87171",
                "desc":  "若第5浪無法突破第3浪高點，形成失敗第5浪，可能急速下殺進入熊市。",
                "cond":  "量縮無法過高，KD高檔鈍化後急跌",
                "risk":  "🛑 停損：跌破第4浪低點",
            },
        ],
    },
    "3-a": {
        "color":   "#94a3b8",
        "label":   "高檔震盪",
        "desc":    "漲勢放緩，等待方向確認",
        "emoji":   "☕",
        "scenarios": [
            {
                "name":  "✅ 主要劇本（機率55%）：量縮整理後再攻",
                "color": "#4ade80",
                "desc":  "高檔收斂整理，量縮正常，等待帶量突破再追。",
                "cond":  "量縮縮減，均線持續上揚，MACD高位整理",
                "risk":  "⚠️ 整理過久需重新評估",
            },
            {
                "name":  "❌ 風險劇本（機率45%）：進入修正",
                "color": "#f87171",
                "desc":  "若量縮後無法放量突破，可能進入較大幅度的修正。",
                "cond":  "MACD翻綠，KD死叉，跌破MA5",
                "risk":  "🛑 停損：跌破前波低點",
            },
        ],
    },
    "4-a": {
        "color":   "#fb923c",
        "label":   "第4浪初跌",
        "desc":    "主升後正常修正，提供加碼機會",
        "emoji":   "📉",
        "scenarios": [
            {
                "name":  "✅ 主要劇本（機率60%）：修正至0.382 → 啟動第5浪",
                "color": "#4ade80",
                "desc":  "第4浪通常回測0.382~0.5費波，修正完成後啟動第5浪攻擊。KD低位金叉是最佳買點。",
                "cond":  "量縮見底，KD低檔金叉，守住MA60",
                "risk":  "⚠️ 第4浪不應跌破第1浪高點",
            },
            {
                "name":  "📊 次要劇本（機率25%）：複雜修正延伸",
                "color": "#fbbf24",
                "desc":  "第4浪形成複雜修正（W形、三角整理），需要更多時間消化，等待型態完成。",
                "cond":  "量縮震盪，每次反彈力道不足",
                "risk":  "⚠️ 耐心等待修正完成訊號",
            },
            {
                "name":  "❌ 風險劇本（機率15%）：修正破位 → 重新定義波浪",
                "color": "#f87171",
                "desc":  "若跌破第1浪高點，整個艾略特結構需重新定義，可能是更大級別的B浪。",
                "cond":  "跌破第1浪頂點，成交量放大下跌",
                "risk":  "🛑 停損：確認跌破後立即出場",
            },
        ],
    },
    "4-b": {
        "color":   "#f97316",
        "label":   "反彈逃命波",
        "desc":    "空頭反彈，趨勢仍弱",
        "emoji":   "👀",
        "scenarios": [
            {
                "name":  "✅ 主要劇本（機率65%）：反彈至壓力後繼續下跌",
                "color": "#f87171",
                "desc":  "空頭格局中的技術性反彈，反彈至前低（現壓力）或38.2%費波後再度下跌。是出清部位的機會。",
                "cond":  "量縮反彈，均線空頭排列，反彈無法過前高",
                "risk":  "⚠️ 此處不宜做多",
            },
            {
                "name":  "📊 次要劇本（機率25%）：反彈力道強，形成底部",
                "color": "#fbbf24",
                "desc":  "若反彈過前高且量能放大，可能是底部確立，需觀察KD是否出現低位金叉。",
                "cond":  "量增過前高，KD低位金叉，MACD翻紅",
                "risk":  "⚠️ 確認突破後才可考慮做多",
            },
        ],
    },
    "4-c": {
        "color":   "#a78bfa",
        "label":   "修正末端",
        "desc":    "接近底部，等待反轉訊號",
        "emoji":   "🪤",
        "scenarios": [
            {
                "name":  "✅ 主要劇本（機率60%）：底部確立 → 啟動新一波上漲",
                "color": "#4ade80",
                "desc":  "K值低檔鈍化後回升，成交量萎縮後帶量長紅，底部型態確立。此為最佳布局時機，停損設明確低點。",
                "cond":  "K值<20後回升，量縮後帶量紅K，守住長期均線",
                "risk":  "⚠️ 停損：跌破前低",
            },
            {
                "name":  "📊 次要劇本（機率30%）：繼續打底延伸",
                "color": "#fbbf24",
                "desc":  "底部打底需要更多時間，W底或頭肩底正在形成，等待明確突破頸線再進場。",
                "cond":  "量縮震盪，每次跌幅縮小",
                "risk":  "⚠️ 耐心等待突破確認",
            },
            {
                "name":  "❌ 風險劇本（機率10%）：假底 → 繼續探低",
                "color": "#f87171",
                "desc":  "若帶量跌破前低，底部型態失敗，繼續探底。",
                "cond":  "量增跌破前低",
                "risk":  "🛑 停損：立即出場",
            },
        ],
    },
    "C-3": {
        "color":   "#f87171",
        "label":   "主跌段C浪",
        "desc":    "空頭核心，避免抄底",
        "emoji":   "🔻",
        "scenarios": [
            {
                "name":  "✅ 主要劇本（機率65%）：繼續下跌 → 完成C浪目標",
                "color": "#f87171",
                "desc":  "C浪通常等於A浪長度，或A浪的1.618倍。目前處於主跌段，不宜做多，等待量縮止跌訊號。",
                "cond":  "量增下跌，均線空頭排列",
                "risk":  "🛑 多單全數出清，等待止跌",
            },
            {
                "name":  "📊 次要劇本（機率25%）：提前完成C浪，形成底部",
                "color": "#fbbf24",
                "desc":  "若出現量縮後帶量長紅反轉K棒，且KD出現低位背離，C浪可能提前完成。",
                "cond":  "量縮放量長紅，KD低位背離",
                "risk":  "⚠️ 確認反轉後輕倉試做",
            },
        ],
    },
    "C-5": {
        "color":   "#dc2626",
        "label":   "趕底急殺",
        "desc":    "恐慌性殺盤，極端超跌",
        "emoji":   "💥",
        "scenarios": [
            {
                "name":  "✅ 主要劇本（機率55%）：超跌反彈 → 確認底部",
                "color": "#fbbf24",
                "desc":  "趕底急殺後通常出現強烈反彈，配合止跌K棒（長下影線、十字星）可輕倉試做，停損設當日低點。",
                "cond":  "量能極度萎縮後爆量長紅，KD極低位",
                "risk":  "⚠️ 輕倉試做，嚴設停損",
            },
            {
                "name":  "❌ 風險劇本（機率45%）：繼續探底",
                "color": "#f87171",
                "desc":  "若無止跌訊號，恐慌賣壓持續，繼續破底。",
                "cond":  "量增繼續破低",
                "risk":  "🛑 勿抄底，等待明確止跌",
            },
        ],
    },
    "B-a": {
        "color":   "#94a3b8",
        "label":   "跌深反彈",
        "desc":    "空頭中的短線反彈機會",
        "emoji":   "↗️",
        "scenarios": [
            {
                "name":  "✅ 主要劇本（機率60%）：反彈至38.2%~61.8%後繼續空",
                "color": "#f87171",
                "desc":  "空頭B浪反彈，目標費波38.2%或61.8%壓力，到達後繼續空頭。短線可小波段操作，但要控制好停損。",
                "cond":  "量縮反彈",
                "risk":  "⚠️ 空頭格局，多單輕倉短線",
            },
        ],
    },
    "B-c": {
        "color":   "#ef4444",
        "label":   "反彈高點",
        "desc":    "空頭反彈至壓力區，出場機會",
        "emoji":   "⚠️",
        "scenarios": [
            {
                "name":  "✅ 主要劇本（機率70%）：此處為逃命波高點",
                "color": "#f87171",
                "desc":  "B浪c段通常為反彈最高點，是空頭格局中清倉或放空的最佳時機。反彈力道若減弱，下一步是C主跌浪。",
                "cond":  "KD高位死叉，量縮，MACD翻綠",
                "risk":  "🛑 多單清倉，不追高",
            },
            {
                "name":  "📊 次要劇本（機率30%）：突破壓力，趨勢反轉",
                "color": "#4ade80",
                "desc":  "若放量突破前高且MACD翻紅，可能是空頭結束、多頭反轉的訊號。",
                "cond":  "量增突破前高，KD低位金叉完成",
                "risk":  "⚠️ 突破後確認才進場",
            },
        ],
    },
    "N/A": {
        "color":   "#64748b",
        "label":   "判斷中",
        "desc":    "資料不足",
        "emoji":   "❓",
        "scenarios": [],
    },
}

def get_wave_info(label: str) -> dict:
    """取得波浪詳細資訊，找不到時用 N/A"""
    return WAVE_INFO.get(label, WAVE_INFO["N/A"])


def build_kline_chart(df: pd.DataFrame, wave_label_d: str,
                      stock_name: str = "", code: str = "") -> "go.Figure | None":
    """
    繪製互動日K線圖，含：
    - OHLC 蠟燭圖（近60日）
    - 5MA / 20MA / 60MA
    - 成交量長條圖
    - 波浪位置標注
    """
    if not PLOTLY_OK or df is None or len(df) < 10:
        return None

    df = df.copy().iloc[-90:]   # 近90日

    wave = get_wave_info(wave_label_d)
    wave_color = wave["color"]

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.72, 0.28],
        vertical_spacing=0.03,
    )

    # ── K線 ──
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"],   close=df["Close"],
        increasing_line_color="#4ade80",
        decreasing_line_color="#f87171",
        increasing_fillcolor="rgba(74,222,128,0.8)",
        decreasing_fillcolor="rgba(248,113,113,0.8)",
        name="K線",
        line_width=1,
    ), row=1, col=1)

    # ── 均線 ──
    for ma, color, width in [(5,"#f97316",1.5),(20,"#38bdf8",1.5),(60,"#a78bfa",1.5)]:
        col_name = f"MA{ma}"
        if col_name in df.columns:
            s = df[col_name].dropna()
            if len(s) > 0:
                fig.add_trace(go.Scatter(
                    x=s.index, y=s.values,
                    mode="lines",
                    line=dict(color=color, width=width),
                    name=f"{ma}MA",
                    opacity=0.9,
                ), row=1, col=1)

    # ── 波浪標注（最後一根K棒加箭頭）──
    last_idx  = df.index[-1]
    last_high = float(df["High"].iloc[-1])
    last_close= float(df["Close"].iloc[-1])
    fig.add_annotation(
        x=last_idx,
        y=last_high * 1.018,
        text=f"  {wave['emoji']} {wave['label']}",
        showarrow=True,
        arrowhead=2,
        arrowsize=1.2,
        arrowcolor=wave_color,
        arrowwidth=2,
        font=dict(size=13, color=wave_color, family="Outfit"),
        bgcolor="rgba(6,11,24,0.85)",
        bordercolor=wave_color,
        borderwidth=1,
        borderpad=5,
        row=1, col=1,
    )

    # ── 成交量 ──
    colors = ["rgba(74,222,128,0.6)" if c >= o else "rgba(248,113,113,0.6)"
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=df.index,
        y=df["Volume"],
        marker_color=colors,
        name="成交量",
        showlegend=False,
    ), row=2, col=1)

    # 量均線
    if "VOL_MA5" in df.columns:
        vm = df["VOL_MA5"].dropna()
        fig.add_trace(go.Scatter(
            x=vm.index, y=vm.values,
            mode="lines",
            line=dict(color="#fbbf24", width=1.2),
            name="量5MA",
        ), row=2, col=1)

    # ── 版面 ──
    title_text = f"{stock_name}（{code}）日K線圖  ｜  當前波浪：{wave['emoji']} {wave['label']} — {wave['desc']}"
    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=14, color="#94a3b8", family="Outfit"),
            x=0,
        ),
        paper_bgcolor="rgba(6,11,24,0)",
        plot_bgcolor ="rgba(6,11,24,0)",
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h", x=0, y=1.02,
            font=dict(size=11, color="#64748b"),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=500,
        font=dict(family="Outfit"),
    )
    for ax in ["xaxis","xaxis2","yaxis","yaxis2"]:
        fig.update_layout(**{ax: dict(
            gridcolor="rgba(255,255,255,0.05)",
            showgrid=True,
            zeroline=False,
            color="#475569",
            tickfont=dict(size=11, family="JetBrains Mono"),
        )})
    fig.update_layout(
        yaxis2=dict(
            title="成交量",
            titlefont=dict(size=10),
        )
    )
    return fig
