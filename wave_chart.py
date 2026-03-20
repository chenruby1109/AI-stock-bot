"""
wave_chart.py V3 — 完整艾略特波浪計數（大浪 + 子浪）
邏輯：
  1. 用長週期（order大）找大浪轉折點 → 標示①②③④⑤ / A-B-C
  2. 在最後一段大浪內，用短週期找子浪 → 標示ⅰⅱⅲⅳⅴ / a-b-c
  3. 當前所在浪 = 大浪位置.子浪位置（如 3-3 = 第3大浪的第3子浪）
  4. 全部用同一套邏輯，確保「⑤完成後顯示修正ABC」
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
# 波浪資訊
# ─────────────────────────────────────────
WAVE_INFO = {
    "3-1": {"color":"#38bdf8","label":"第①浪內的ⅰ子浪","emoji":"🌱","desc":"起漲初動，試探性上攻",
        "scenarios":[
            {"name":"✅ 主要劇本（65%）：量能擴張突破前高，進入ⅲ浪加速段","color":"#38bdf8",
             "desc":"ⅰ浪完成後通常有ⅱ浪回測（38.2%~61.8%），之後ⅲ浪才是主攻段，現在是耐心等待ⅱ浪低點加碼的機會。",
             "cond":"量能逐步放大，KD金叉，MACD翻紅","risk":"⚠️ 停損設ⅰ浪起漲低點"},
            {"name":"📊 次要劇本（25%）：形成高C整理後直接攻ⅲ浪","color":"#fbbf24",
             "desc":"量縮整理後帶量長紅，直接進入第ⅲ浪強攻段。","cond":"量縮後量增，站上所有短期均線","risk":"⚠️ 若量縮破MA5需重新判斷"},
            {"name":"❌ 風險劇本（10%）：假突破，大浪①未完成，回測起漲","color":"#f87171",
             "desc":"量價背離，突破後縮量，可能整個①浪還在形成中。","cond":"縮量無法站上，KD高檔死叉","risk":"🛑 停損跌破起漲點"},
        ]},
    "3-3": {"color":"#4ade80","label":"第③浪主升段","emoji":"🚀","desc":"最強最長的主升浪，量能最大",
        "scenarios":[
            {"name":"✅ 主要劇本（70%）：③浪仍在延伸，目標1.618~2.618擴展","color":"#4ade80",
             "desc":"③浪是最強的浪，通常是①浪的1.618倍或更長。MACD紅柱持續放大，每次拉回均是加碼點。子浪ⅲ→ⅳ→ⅴ仍未完成。",
             "cond":"MACD紅柱最高，量能最大，KD>60保持多頭","risk":"⚠️ ③浪過熱乖離超15%可先減倉等回踩"},
            {"name":"📊 次要劇本（20%）：③浪尾聲，即將進入④浪修正","color":"#fbbf24",
             "desc":"③浪的ⅴ子浪正在完成，完成後④浪修正通常回測38.2%費波支撐。","cond":"量開始縮小，KD高位鈍化，MACD紅柱縮短","risk":"⚠️ 注意高點反轉訊號"},
            {"name":"❌ 風險劇本（10%）：③浪提前結束，進入④大幅修正","color":"#f87171",
             "desc":"若出現爆量長黑，③浪可能提前結束，④浪修正幅度可達整段漲幅50%。","cond":"爆量長黑K，MACD翻綠","risk":"🛑 停損設③浪起漲低點"},
        ]},
    "3-5": {"color":"#fbbf24","label":"第⑤浪末升段","emoji":"🏔️","desc":"主升尾聲，出現量價背離訊號",
        "scenarios":[
            {"name":"✅ 主要劇本（50%）：⑤浪完成 → 進入ABC大修正","color":"#fbbf24",
             "desc":"⑤浪完成整個五浪上升結構，之後的A-B-C修正A浪跌幅通常達整個升幅的38.2%~61.8%。現在應逐步獲利了結，等待A浪底部再布局。",
             "cond":"量價背離（價新高但量縮），KD頂背離，RSI>80","risk":"⚠️ 此位置絕不追高，分批減倉"},
            {"name":"📊 次要劇本（30%）：⑤浪延伸，仍有上攻空間","color":"#38bdf8",
             "desc":"若法人持續買超且量能仍放大，⑤浪可能延伸，但最終都會進入ABC修正。","cond":"法人買超持續，量能仍然放大","risk":"⚠️ 嚴設停利，勿戀戰"},
            {"name":"❌ 風險劇本（20%）：失敗⑤浪 → 急速轉空","color":"#f87171",
             "desc":"無法突破③浪高點形成失敗⑤浪，將快速進入熊市結構。","cond":"量縮無法過③浪高，KD高位死叉","risk":"🛑 停損③浪高點，立即出場"},
        ]},
    "3-a": {"color":"#94a3b8","label":"⑤浪後高檔震盪","emoji":"☕","desc":"五浪完成後高位整理，方向待確認",
        "scenarios":[
            {"name":"✅ 主要劇本（55%）：ABC修正已開始，等A浪低點","color":"#f97316",
             "desc":"高位震盪通常是A浪的一部分，等待A浪完成（量縮止跌）後的B浪反彈出場機會。",
             "cond":"量縮整理，均線開始走平","risk":"⚠️ 勿在此加碼"},
            {"name":"❌ 風險劇本（45%）：快速轉弱，大A浪開始","color":"#f87171",
             "desc":"若帶量跌破前支撐，A浪下跌加速。","cond":"量增破支撐，MACD翻綠","risk":"🛑 停損設前波高點"},
        ]},
    "4-a": {"color":"#fb923c","label":"④浪修正中（a子浪）","emoji":"📉","desc":"主升後④浪修正，a子浪下跌中",
        "scenarios":[
            {"name":"✅ 主要劇本（60%）：a→b→c三波修正後啟動⑤浪","color":"#4ade80",
             "desc":"④浪a子浪下跌後，b子浪反彈，c子浪再跌到0.382~0.5費波支撐，完成後啟動⑤浪。b浪反彈是輕倉試多的機會。",
             "cond":"量縮下跌，每天跌幅縮小，接近費波支撐","risk":"⚠️ 第4浪不應跌破第1浪高點"},
            {"name":"📊 次要劇本（25%）：④浪複雜修正（W型或三角）","color":"#fbbf24",
             "desc":"④浪形成更複雜的W底或三角收斂，需要更多時間，但最終都會啟動⑤浪。",
             "cond":"量縮震盪，高低點收斂","risk":"⚠️ 耐心等待，不要搶進"},
            {"name":"❌ 風險劇本（15%）：跌破①浪高點，重新定義結構","color":"#f87171",
             "desc":"若跌破①浪頂點，艾略特結構需重新定義，可能是更大級別的修正。",
             "cond":"帶量跌破①浪高點","risk":"🛑 全部出場，等待重新定義"},
        ]},
    "4-b": {"color":"#f97316","label":"④浪修正中（b子浪反彈）","emoji":"👀","desc":"④浪b子浪技術反彈，空頭趨勢未改",
        "scenarios":[
            {"name":"✅ 主要劇本（65%）：b浪反彈完成後，c浪再下探完成④浪","color":"#f97316",
             "desc":"b浪反彈通常回測到前低（現壓力），反彈完成後c浪下跌才完成整個④浪修正，之後啟動⑤浪。",
             "cond":"量縮反彈至38.2%~61.8%壓力位","risk":"⚠️ 此反彈不宜追多，等c浪底部"},
            {"name":"📊 次要劇本（25%）：b浪強勁，可能跳過c浪直接⑤浪","color":"#fbbf24",
             "desc":"若b浪量增過前高，可能是④浪已完成，直接啟動⑤浪。","cond":"量增，b浪突破前高","risk":"⚠️ 需確認後才追"},
        ]},
    "4-c": {"color":"#a78bfa","label":"④浪修正末端（c子浪）","emoji":"🪤","desc":"④浪c子浪，接近底部等待⑤浪啟動",
        "scenarios":[
            {"name":"✅ 主要劇本（65%）：c浪見底 → 啟動⑤浪主攻","color":"#4ade80",
             "desc":"c浪是④浪最後一段下跌，通常在0.382~0.618費波支撐見底。KD低位金叉+量縮後帶量長紅=⑤浪啟動訊號，是最佳布局點。",
             "cond":"量縮後帶量長紅K，KD<30金叉，守住費波0.382","risk":"⚠️ 停損設c浪低點"},
            {"name":"📊 次要劇本（25%）：c浪延伸，多測一個費波支撐","color":"#fbbf24",
             "desc":"c浪比預期更深，測到0.618費波才見底，但最終⑤浪仍會啟動。","cond":"量繼續縮，慢慢探低","risk":"⚠️ 等量縮止跌再進場"},
            {"name":"❌ 風險劇本（10%）：整個五浪結構結束，進入熊市A浪","color":"#f87171",
             "desc":"若跌破①浪高點且帶量，整個五浪主升已完成，下方是更大級別ABC熊市修正。",
             "cond":"帶量跌破①浪高點","risk":"🛑 全部出場"},
        ]},
    "C-3": {"color":"#f87171","label":"ABC修正的C浪（主跌段）","emoji":"🔻","desc":"空頭C浪主跌，避免抄底",
        "scenarios":[
            {"name":"✅ 主要劇本（65%）：C浪繼續下跌，目標A浪的1倍~1.618倍","color":"#f87171",
             "desc":"C浪通常等於A浪長度，或A浪的1.618倍。目前處於主跌段中段，量增下跌，不宜做多，等量縮止跌訊號。",
             "cond":"量增下跌，均線空頭排列","risk":"🛑 多單全數出清，等止跌"},
            {"name":"📊 次要劇本（25%）：提前完成C浪，量縮背離出現底部","color":"#fbbf24",
             "desc":"若出現量縮+KD低位背離+帶量長紅，C浪可能提前完成。","cond":"量縮，KD低位背離，帶量長紅K","risk":"⚠️ 確認後輕倉試多"},
        ]},
    "C-5": {"color":"#dc2626","label":"C浪末段趕底","emoji":"💥","desc":"恐慌殺盤，極端超跌接近尾聲",
        "scenarios":[
            {"name":"✅ 主要劇本（55%）：趕底後強力反彈，新一輪五浪上升即將開始","color":"#fbbf24",
             "desc":"趕底急殺後通常有強力反彈，若配合量縮止跌K棒（長下影、十字星）可輕倉布局，停損設當日低點。",
             "cond":"量縮後爆量長紅，KD極低位回升","risk":"⚠️ 輕倉試做，嚴設停損"},
            {"name":"❌ 風險劇本（45%）：超跌延伸繼續探底","color":"#f87171",
             "desc":"無止跌訊號，繼續破底。","cond":"量增繼續破低","risk":"🛑 勿抄底，等止跌"},
        ]},
    "B-a": {"color":"#94a3b8","label":"ABC修正的B浪（反彈）","emoji":"↗️","desc":"空頭格局中的B浪技術反彈",
        "scenarios":[
            {"name":"✅ 主要劇本（60%）：B浪反彈至38.2%~61.8%後，C浪繼續下跌","color":"#f87171",
             "desc":"B浪是ABC修正中的反彈浪，通常反彈至前高（即A浪起點）的38.2%~61.8%後轉弱，之後C浪才是真正底部。",
             "cond":"量縮反彈，均線仍空頭排列","risk":"⚠️ 此反彈是出貨機會，不宜重倉做多"},
            {"name":"📊 次要劇本（25%）：B浪強勢，可能是新一波五浪起漲","color":"#4ade80",
             "desc":"若B浪量增過前高，可能是底部確立，新的五浪上升啟動。","cond":"量增突破前高，KD低位金叉","risk":"⚠️ 突破確認後才考慮做多"},
        ]},
    "B-c": {"color":"#ef4444","label":"B浪的c子浪（反彈高點）","emoji":"⚠️","desc":"B浪反彈最高點，C浪即將展開",
        "scenarios":[
            {"name":"✅ 主要劇本（70%）：B浪反彈完成，C主跌浪即將展開","color":"#f87171",
             "desc":"B浪c子浪為反彈最高點，此後C主跌浪展開，空頭格局最終底部才在C浪。這是減倉逃命的最後機會。",
             "cond":"KD高位死叉，量縮，MACD翻綠","risk":"🛑 多單清倉，不在此追高"},
            {"name":"📊 次要劇本（30%）：突破前高，空頭結束多頭確立","color":"#4ade80",
             "desc":"若放量突破A浪起點（前高），ABC修正結束，新的五浪多頭開始。","cond":"量增突破前高，所有均線翻多","risk":"⚠️ 確認後才進場，設好停損"},
        ]},
    "N/A": {"color":"#64748b","label":"波浪判斷中","emoji":"❓","desc":"資料不足，無法判斷","scenarios":[]},
}

def get_wave_info(label):
    return WAVE_INFO.get(label, WAVE_INFO["N/A"])


# ─────────────────────────────────────────
# 轉折點偵測
# ─────────────────────────────────────────
def _find_pivots(highs, lows, order):
    hi_idx = argrelextrema(highs, np.greater_equal, order=order)[0]
    lo_idx = argrelextrema(lows,  np.less_equal,    order=order)[0]
    pivots = [(i, highs[i], "H") for i in hi_idx] + [(i, lows[i], "L") for i in lo_idx]
    pivots.sort(key=lambda x: x[0])
    # 去重同型取極值
    clean = []
    for p in pivots:
        if clean and clean[-1][2] == p[2]:
            if (p[2]=="H" and p[1]>=clean[-1][1]) or (p[2]=="L" and p[1]<=clean[-1][1]):
                clean[-1] = p
        else:
            clean.append(p)
    return clean


# ─────────────────────────────────────────
# 判斷大趨勢（多頭/空頭/修正）
# ─────────────────────────────────────────
def _detect_macro_trend(df):
    """根據均線排列和近期走勢判斷大方向"""
    if len(df) < 60:
        return "bull"
    last = df.iloc[-1]
    ma20 = last.get("MA20", last["Close"])
    ma60 = last.get("MA60", last["Close"])
    close = float(last["Close"])
    if close > float(ma20) > float(ma60):
        return "bull"
    elif close < float(ma20) < float(ma60):
        return "bear"
    else:
        return "mixed"


# ─────────────────────────────────────────
# 波浪計數（大浪）
# ─────────────────────────────────────────
BULL_MAIN = ["①","②","③","④","⑤"]
BEAR_MAIN = ["Ⓐ","Ⓑ","Ⓒ"]
BULL_COLORS = {"①":"#38bdf8","②":"#fb923c","③":"#4ade80","④":"#f97316","⑤":"#fbbf24"}
BEAR_COLORS = {"Ⓐ":"#f87171","Ⓑ":"#fb923c","Ⓒ":"#dc2626"}

# 子浪
BULL_SUB = ["ⅰ","ⅱ","ⅲ","ⅳ","ⅴ"]
BEAR_SUB = ["a","b","c"]
BULL_SUB_C = {"ⅰ":"#7dd3fc","ⅱ":"#fed7aa","ⅲ":"#86efac","ⅳ":"#fdba74","ⅴ":"#fde68a"}
BEAR_SUB_C = {"a":"#fca5a5","b":"#fdba74","c":"#f87171"}


def _label_waves(pivots, labels_list, colors_dict, start_type):
    """從轉折點列表標示波浪"""
    result = []
    wave_n = 0
    prev_type = None
    started = False
    for pos, price, ptype in pivots:
        if not started:
            if ptype == start_type:
                result.append((pos, price, "●", "#64748b", ptype))
                started = True
                prev_type = ptype
            continue
        if ptype != prev_type and wave_n < len(labels_list):
            lbl = labels_list[wave_n]
            result.append((pos, price, lbl, colors_dict.get(lbl,"#94a3b8"), ptype))
            wave_n += 1
            prev_type = ptype
    return result


def build_kline_chart(df, wave_label_d, stock_name="", code=""):
    if not PLOTLY_OK or df is None or len(df) < 20:
        return None

    df = df.copy().iloc[-150:].reset_index()
    date_col = "Date" if "Date" in df.columns else df.columns[0]
    x_dates = df[date_col].astype(str).tolist()
    n = len(df)

    wave    = get_wave_info(wave_label_d)
    wcolor  = wave["color"]
    trend   = _detect_macro_trend(df)

    highs = df["High"].values.astype(float)
    lows  = df["Low"].values.astype(float)

    # ── 大浪轉折點（較大 order）──
    big_order = max(8, n // 15)
    try:
        big_pivots = _find_pivots(highs, lows, big_order)
    except Exception:
        big_pivots = []

    # ── 子浪轉折點（較小 order，只看最後一段大浪）──
    sub_order = max(3, n // 40)
    # 找最後一個大浪起點
    last_big_start = 0
    if len(big_pivots) >= 2:
        last_big_start = big_pivots[-2][0]
    sub_df_start = max(0, last_big_start - 2)

    sub_highs = highs[sub_df_start:]
    sub_lows  = lows[sub_df_start:]
    try:
        sub_pivots_raw = _find_pivots(sub_highs, sub_lows, sub_order)
        sub_pivots = [(p[0] + sub_df_start, p[1], p[2]) for p in sub_pivots_raw]
    except Exception:
        sub_pivots = []

    # ── 判斷大浪標示方式 ──
    is_bull_major = trend in ("bull","mixed") and wave_label_d.startswith(("3","4"))
    if is_bull_major:
        main_labels = _label_waves(big_pivots[-12:], BULL_MAIN, BULL_COLORS, "L")
        sub_labels  = _label_waves(sub_pivots[-10:], BULL_SUB,  BULL_SUB_C,  "L")
    else:
        main_labels = _label_waves(big_pivots[-12:], BEAR_MAIN, BEAR_COLORS, "H")
        sub_labels  = _label_waves(sub_pivots[-10:], BEAR_SUB,  BEAR_SUB_C,  "H")

    # ─────────────────────────────────────────
    # 繪圖
    # ─────────────────────────────────────────
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.72, 0.28], vertical_spacing=0.02,
    )

    # ── K線 ──
    fig.add_trace(go.Candlestick(
        x=x_dates,
        open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing=dict(line=dict(color="#4ade80",width=1), fillcolor="rgba(74,222,128,0.85)"),
        decreasing=dict(line=dict(color="#f87171",width=1), fillcolor="rgba(248,113,113,0.85)"),
        name="K線", whiskerwidth=0.3,
    ), row=1, col=1)

    # ── 均線 ──
    for ma, col, w in [(5,"#f97316",1.5),(20,"#38bdf8",1.5),(60,"#a78bfa",1.5)]:
        cname = f"MA{ma}"
        if cname in df.columns:
            s = df[cname].dropna()
            if len(s):
                fig.add_trace(go.Scatter(
                    x=[x_dates[i] for i in s.index], y=s.values,
                    mode="lines", line=dict(color=col, width=w),
                    name=f"{ma}MA", opacity=0.9,
                ), row=1, col=1)

    # ── 大浪連線 ──
    if len(big_pivots) >= 2:
        bpx = [x_dates[p[0]] for p in big_pivots if p[0] < n]
        bpy = [p[1] for p in big_pivots if p[0] < n]
        fig.add_trace(go.Scatter(
            x=bpx, y=bpy, mode="lines",
            line=dict(color="rgba(148,163,184,0.4)", width=1.5, dash="dot"),
            name="大浪連線", showlegend=False,
        ), row=1, col=1)

    # ── 子浪連線（只在最後一段）──
    sp_in_range = [(p[0],p[1],p[2]) for p in sub_pivots if sub_df_start <= p[0] < n]
    if len(sp_in_range) >= 2:
        spx = [x_dates[p[0]] for p in sp_in_range]
        spy = [p[1] for p in sp_in_range]
        fig.add_trace(go.Scatter(
            x=spx, y=spy, mode="lines",
            line=dict(color="rgba(255,255,255,0.15)", width=1, dash="dashdot"),
            name="子浪連線", showlegend=False,
        ), row=1, col=1)

    # ── 標注大浪 ──
    for pos, price, lbl, lbl_color, ptype in main_labels:
        if pos >= n: continue
        is_hi = (ptype == "H")
        ay = -45 if is_hi else 45
        fig.add_annotation(
            x=x_dates[pos], y=price,
            text=f"<b>{lbl}</b>",
            showarrow=True, arrowhead=2, arrowsize=0.9,
            arrowwidth=2, arrowcolor=lbl_color,
            ax=0, ay=ay,
            font=dict(size=15, color=lbl_color, family="Outfit"),
            bgcolor="rgba(6,11,24,0.85)",
            bordercolor=lbl_color, borderwidth=1.5, borderpad=5,
        )

    # ── 標注子浪（稍小字體，偏移避免重疊）──
    for pos, price, lbl, lbl_color, ptype in sub_labels:
        if pos >= n: continue
        if lbl == "●": continue  # 起始點不標
        is_hi = (ptype == "H")
        # 子浪往反方向偏移，避免和大浪重疊
        ay = -28 if is_hi else 28
        ax = 18
        fig.add_annotation(
            x=x_dates[pos], y=price,
            text=f"<i>{lbl}</i>",
            showarrow=True, arrowhead=1, arrowsize=0.7,
            arrowwidth=1.2, arrowcolor=lbl_color,
            ax=ax, ay=ay,
            font=dict(size=12, color=lbl_color, family="Outfit"),
            bgcolor="rgba(6,11,24,0.7)",
            bordercolor=lbl_color, borderwidth=1, borderpad=3,
            opacity=0.85,
        )

    # ── 當前波浪標注（最後一根K棒）──
    last_x    = x_dates[-1]
    last_high = float(df["High"].iloc[-1])
    fig.add_annotation(
        x=last_x, y=last_high * 1.025,
        text=f"  {wave['emoji']} {wave['label']}",
        showarrow=True, arrowhead=2, arrowsize=1.3,
        arrowwidth=2.5, arrowcolor=wcolor,
        ax=0, ay=-50,
        font=dict(size=13, color=wcolor, family="Outfit"),
        bgcolor="rgba(6,11,24,0.9)",
        bordercolor=wcolor, borderwidth=2, borderpad=7,
    )

    # ── 成交量 ──
    vol_colors = [
        "rgba(74,222,128,0.55)" if float(c)>=float(o) else "rgba(248,113,113,0.55)"
        for c,o in zip(df["Close"],df["Open"])
    ]
    fig.add_trace(go.Bar(
        x=x_dates, y=df["Volume"],
        marker_color=vol_colors,
        name="成交量", showlegend=False,
    ), row=2, col=1)

    if "VOL_MA5" in df.columns:
        vm = df["VOL_MA5"].dropna()
        fig.add_trace(go.Scatter(
            x=[x_dates[i] for i in vm.index], y=vm.values,
            mode="lines", line=dict(color="#fbbf24", width=1.2),
            name="量5MA",
        ), row=2, col=1)

    # ── 說明文字 ──
    # 取最後標注到的大浪 + 子浪
    last_main = main_labels[-1][2] if main_labels else "?"
    last_sub  = sub_labels[-1][2]  if sub_labels  else "?"
    pos_text = f"大浪位置：{last_main}  |  子浪位置：{last_sub}" if last_sub != "?" else f"大浪位置：{last_main}"

    title_str = (f"{stock_name}（{code}）日K線  ｜  當前：{wave['emoji']} {wave['label']}"
                 f"  ｜  {pos_text}")

    fig.update_layout(
        title=dict(text=title_str, font=dict(size=12,color="#94a3b8",family="Outfit"), x=0),
        paper_bgcolor="rgba(6,11,24,0)",
        plot_bgcolor ="rgba(6,11,24,0)",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h",x=0,y=1.04,font=dict(size=11,color="#64748b"),bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0,r=0,t=52,b=0),
        height=540,
        font=dict(family="Outfit"),
        hovermode="x unified",
    )
    axis_s = dict(
        gridcolor="rgba(255,255,255,0.05)", showgrid=True, zeroline=False,
        color="#475569", tickfont=dict(size=11,family="JetBrains Mono"),
    )
    fig.update_layout(xaxis=axis_s, xaxis2=axis_s, yaxis=axis_s, yaxis2=axis_s)
    return fig
