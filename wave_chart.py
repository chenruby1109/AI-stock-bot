"""
wave_chart.py V7 — 使用 wave_engine 的三大鐵律計數
繪製風格：彩色粗折線 + 轉折點價格標注 + 費波那契水平線
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
    import wave_engine as we
    WE_OK = True
except ImportError:
    WE_OK = False

# ─────────────────────────────────────────
# 波浪資訊（劇本說明）
# ─────────────────────────────────────────
WAVE_INFO = {
    "3-1":{"color":"#38bdf8","label":"第①浪起漲","emoji":"🌱","desc":"起漲初動，試探性上攻",
     "scenarios":[
      {"name":"✅ 主要（65%）延伸①浪→②浪修正布局","color":"#38bdf8",
       "desc":"①浪完成後②浪回測38.2~61.8%，之後③才是主攻。現在是耐心等②低點加碼的機會。",
       "cond":"量能放大，KD金叉，MACD翻紅","risk":"⚠️ 停損：①浪起漲低點"},
      {"name":"❌ 風險（10%）假突破仍在整理","color":"#f87171",
       "desc":"量縮無法站上，可能仍在整理中。","cond":"縮量無法站上，KD高檔死叉","risk":"🛑 跌破起漲點停損"},
     ]},
    "3-3":{"color":"#4ade80","label":"第③浪主升","emoji":"🚀","desc":"最強最長的主升浪",
     "scenarios":[
      {"name":"✅ 主要（70%）③浪延伸，目標1.618~2.618倍","color":"#4ade80",
       "desc":"③浪最強，子浪①②③④⑤仍未完成。MACD紅柱持續放大，每次拉回均是加碼點。",
       "cond":"MACD紅柱最高，量能最大，KD>60","risk":"⚠️ 乖離>15%先減倉"},
      {"name":"📊 次要（20%）③浪尾聲進入④修正","color":"#fbbf24",
       "desc":"③浪子浪5正在完成，完成後④浪修正。","cond":"量縮，KD高位鈍化","risk":"⚠️ 注意高點反轉"},
      {"name":"❌ 風險（10%）③浪提前結束","color":"#f87171",
       "desc":"爆量長黑③浪提前結束，④浪大幅修正。","cond":"爆量長黑K，MACD翻綠","risk":"🛑 停損③浪起漲低點"},
     ]},
    "3-5":{"color":"#fbbf24","label":"第⑤浪末升","emoji":"🏔️","desc":"主升尾聲，量價背離訊號出現",
     "scenarios":[
      {"name":"✅ 主要（50%）⑤浪完成→ABC大修正","color":"#fbbf24",
       "desc":"⑤浪完成整個五浪，(A)浪跌幅通常38.2~61.8%整個升幅。逐步獲利了結。",
       "cond":"量價背離，KD頂背離，RSI>80","risk":"⚠️ 絕不追高，分批減倉"},
      {"name":"📊 次要（30%）⑤浪延伸","color":"#38bdf8",
       "desc":"法人持續買超，⑤浪可能延伸。","cond":"法人買超，量能放大","risk":"⚠️ 嚴設停利"},
      {"name":"❌ 風險（20%）失敗⑤浪急速轉空","color":"#f87171",
       "desc":"無法突破③浪高點，快速進入熊市。","cond":"量縮無法過③浪高","risk":"🛑 停損③浪高點"},
     ]},
    "3-a":{"color":"#94a3b8","label":"⑤浪後高檔整理","emoji":"☕","desc":"五浪完成後高位整理",
     "scenarios":[
      {"name":"✅ 主要（55%）ABC修正已開始","color":"#f97316",
       "desc":"高位震盪是(A)浪的一部分。","cond":"量縮整理，均線走平","risk":"⚠️ 勿加碼"},
      {"name":"❌ 風險（45%）快速轉弱","color":"#f87171",
       "desc":"量增跌破前支撐，(A)浪下跌加速。","cond":"量增破支撐","risk":"🛑 停損前波高點"},
     ]},
    "4-a":{"color":"#fb923c","label":"④浪修正 (A)子浪","emoji":"📉","desc":"主升後④浪(A)子浪下跌",
     "scenarios":[
      {"name":"✅ 主要（60%）(A)(B)(C)修正後啟動⑤浪","color":"#4ade80",
       "desc":"(A)下跌→(B)反彈→(C)再跌完成④浪，之後啟動⑤浪。(B)反彈是輕倉試多機會。",
       "cond":"量縮下跌，接近費波支撐","risk":"⚠️ ④浪不應跌破①浪高點（鐵律3）"},
      {"name":"❌ 風險（15%）跌破①浪高點違反鐵律3","color":"#f87171",
       "desc":"跌破①浪高點，艾略特結構需重新定義。","cond":"帶量跌破①浪高點","risk":"🛑 全部出場"},
     ]},
    "4-b":{"color":"#f97316","label":"④浪修正 (B)子浪反彈","emoji":"👀","desc":"④浪(B)子浪技術反彈",
     "scenarios":[
      {"name":"✅ 主要（65%）(B)反彈完成後(C)浪再下探","color":"#f97316",
       "desc":"(B)浪反彈通常到38.2~61.8%，完成後(C)浪下跌完成④浪。","cond":"量縮反彈至壓力位","risk":"⚠️ 不宜追多"},
      {"name":"📊 次要（25%）(B)浪強勁直接⑤浪","color":"#fbbf24",
       "desc":"(B)浪量增過前高，④浪已完成直接啟動⑤浪。","cond":"量增，(B)浪突破前高","risk":"⚠️ 需確認後才追"},
     ]},
    "4-c":{"color":"#a78bfa","label":"④浪修正末端 (C)子浪","emoji":"🪤","desc":"④浪(C)子浪，接近底部等⑤浪",
     "scenarios":[
      {"name":"✅ 主要（65%）(C)浪見底→啟動⑤浪","color":"#4ade80",
       "desc":"(C)浪在0.382~0.618費波支撐見底，KD低位金叉+量縮後帶量長紅=⑤浪啟動訊號。",
       "cond":"量縮後帶量長紅，KD<30金叉","risk":"⚠️ 停損(C)浪低點"},
      {"name":"❌ 風險（10%）整個五浪結束進入熊市","color":"#f87171",
       "desc":"跌破①浪高點帶量，下方是大級別ABC熊市修正。","cond":"帶量跌破①浪高點","risk":"🛑 全部出場"},
     ]},
    "C-3":{"color":"#f87171","label":"ABC修正(C)浪主跌","emoji":"🔻","desc":"空頭(C)浪主跌",
     "scenarios":[
      {"name":"✅ 主要（65%）(C)浪繼續下跌","color":"#f87171",
       "desc":"(C)浪通常等於(A)浪長度或1.618倍。","cond":"量增下跌，均線空頭排列","risk":"🛑 多單全數出清"},
      {"name":"📊 次要（25%）提前完成(C)浪","color":"#fbbf24",
       "desc":"量縮+KD低位背離+帶量長紅，(C)浪可能提前完成。","cond":"量縮，KD低位背離","risk":"⚠️ 確認後輕倉試多"},
     ]},
    "C-5":{"color":"#dc2626","label":"(C)浪末段趕底","emoji":"💥","desc":"恐慌殺盤極端超跌",
     "scenarios":[
      {"name":"✅ 主要（55%）趕底後反彈，新五浪即將開始","color":"#fbbf24",
       "desc":"趕底急殺後通常強力反彈，量縮止跌K棒可輕倉布局。",
       "cond":"量縮後爆量長紅","risk":"⚠️ 輕倉，嚴設停損"},
      {"name":"❌ 風險（45%）繼續探底","color":"#f87171",
       "desc":"無止跌訊號繼續破底。","cond":"量增繼續破低","risk":"🛑 勿抄底"},
     ]},
    "B-a":{"color":"#94a3b8","label":"ABC修正(B)浪反彈","emoji":"↗️","desc":"空頭(B)浪技術反彈",
     "scenarios":[
      {"name":"✅ 主要（60%）(B)浪反彈後(C)浪下跌","color":"#f87171",
       "desc":"(B)浪通常反彈到前高38~61.8%後轉弱，之後(C)浪才是底部。","cond":"量縮反彈","risk":"⚠️ 此反彈是出貨機會"},
      {"name":"📊 次要（25%）(B)浪強勢是新五浪起漲","color":"#4ade80",
       "desc":"(B)浪量增過前高，可能底部確立，新五浪啟動。","cond":"量增突破前高","risk":"⚠️ 突破確認後才做多"},
     ]},
    "B-c":{"color":"#ef4444","label":"(B)浪(c)子浪高點","emoji":"⚠️","desc":"(B)浪反彈高點，(C)主跌即將展開",
     "scenarios":[
      {"name":"✅ 主要（70%）(B)浪完成，(C)主跌浪展開","color":"#f87171",
       "desc":"(B)浪c子浪為反彈最高點，之後(C)主跌浪展開。","cond":"KD高位死叉，量縮","risk":"🛑 多單清倉"},
      {"name":"📊 次要（30%）突破前高多頭確立","color":"#4ade80",
       "desc":"放量突破(A)浪起點，新五浪多頭開始。","cond":"量增突破前高，所有均線翻多","risk":"⚠️ 確認後才進場"},
     ]},
    "N/A":{"color":"#64748b","label":"波浪判斷中","emoji":"❓","desc":"資料不足","scenarios":[]},
}

def get_wave_info(label):
    return WAVE_INFO.get(label, WAVE_INFO["N/A"])


# ─────────────────────────────────────────
# 在圖上繪製波浪（使用 wave_engine 的合法計數）
# ─────────────────────────────────────────
WAVE_COLORS = {
    "起點":"#64748b","頂點":"#64748b",
    "①":"#38bdf8","②":"#fb923c","③":"#4ade80","④":"#f97316","⑤":"#fbbf24",
    "Ⓐ":"#f87171","Ⓑ":"#fb923c","Ⓒ":"#dc2626",
    "1":"#7dd3fc","2":"#fed7aa","3":"#86efac","4":"#fdba74","5":"#fde68a",
    "a":"#fca5a5","b":"#fdba74","c":"#f87171",
}
LINE_SEGS = {
    "①":"#f97316","②":"#f97316","③":"#f97316","④":"#f97316","⑤":"#f97316",
    "Ⓐ":"#ef4444","Ⓑ":"#ef4444","Ⓒ":"#ef4444",
    "1":"#06b6d4","2":"#06b6d4","3":"#06b6d4","4":"#06b6d4","5":"#06b6d4",
    "a":"#e879f9","b":"#e879f9","c":"#e879f9",
}


def _plot_waves(fig, waves, x_dates, highs, lows, row,
                line_width=2.5, font_size=14, arrow_len=48,
                show_price=True, show_fib=False):
    """
    在 fig 的指定 row 繪製：
    - 彩色粗折線連接轉折點
    - 每個轉折點標注（浪名 + 價格）
    - 可選：費波那契回測水平線
    """
    if not waves:
        return

    # ── 折線段（每段用對應浪顏色）──
    for i in range(len(waves)-1):
        idx0, p0, lbl0 = waves[i]
        idx1, p1, lbl1 = waves[i+1]
        if idx0 >= len(x_dates) or idx1 >= len(x_dates):
            continue
        # 高點用 High，低點用 Low 讓線貼緊 K 棒
        y0 = highs[idx0] if any(h == p0 for h in [highs[idx0]]) else lows[idx0]
        y1 = highs[idx1] if any(h == p1 for h in [highs[idx1]]) else lows[idx1]
        # 用標注的浪名決定顏色
        seg_c = LINE_SEGS.get(lbl1, "#f97316")
        fig.add_trace(go.Scatter(
            x=[x_dates[idx0], x_dates[idx1]],
            y=[p0, p1],
            mode="lines",
            line=dict(color=seg_c, width=line_width),
            opacity=0.82,
            showlegend=False,
            hoverinfo="skip",
        ), row=row, col=1)

    # ── 轉折點標注 ──
    for idx, price, lbl in waves:
        if idx >= len(x_dates):
            continue
        lc = WAVE_COLORS.get(lbl, "#94a3b8")
        is_hi = (price >= highs[idx] * 0.998)   # 判斷是高點還是低點
        ay = -arrow_len if is_hi else arrow_len

        price_str = f"{price:.2f}" if price < 1000 else f"{int(price):,}"
        txt = f"<b>{lbl}</b><br><span style='font-size:10px'>{price_str}</span>" if show_price else f"<b>{lbl}</b>"

        fig.add_annotation(
            x=x_dates[idx], y=price,
            text=txt,
            showarrow=True, arrowhead=0,
            arrowwidth=1.5, arrowcolor=lc,
            ax=0, ay=ay,
            font=dict(size=font_size, color=lc, family="Outfit"),
            bgcolor="rgba(6,11,24,0.88)",
            bordercolor=lc, borderwidth=1.5, borderpad=5,
            align="center",
            row=row, col=1,
        )
        # 轉折圓點
        fig.add_trace(go.Scatter(
            x=[x_dates[idx]], y=[price],
            mode="markers",
            marker=dict(color=lc, size=7, symbol="circle",
                        line=dict(color="white", width=1)),
            showlegend=False, hoverinfo="skip",
        ), row=row, col=1)

    # ── 最後一段浪的色塊（當前進行浪）──
    if len(waves) >= 2:
        last_idx, last_price, last_lbl = waves[-1]
        prev_idx, prev_price, prev_lbl = waves[-2]
        lc = WAVE_COLORS.get(last_lbl, "#94a3b8")
        x0 = x_dates[min(prev_idx, len(x_dates)-1)]
        x1 = x_dates[-1]
        seg_prices = list(highs[prev_idx:]) + list(lows[prev_idx:])
        if seg_prices:
            y0 = min(lows[prev_idx:]) * 0.997
            y1 = max(highs[prev_idx:]) * 1.003
            try:
                r,g,b = int(lc[1:3],16),int(lc[3:5],16),int(lc[5:7],16)
                fig.add_shape(type="rect",
                    x0=x0, x1=x1, y0=y0, y1=y1,
                    fillcolor=f"rgba({r},{g},{b},0.06)",
                    line=dict(color=f"rgba({r},{g},{b},0.2)", width=1, dash="dot"),
                    row=row, col=1)
            except: pass

    # ── 費波那契水平線（可選）──
    if show_fib and len(waves) >= 2:
        # 找最後一個完整浪段（起點→高點）
        lows_idx  = [(idx,p,l) for idx,p,l in waves if not any(h==p for h in [highs[min(idx,len(highs)-1)]])]
        highs_idx = [(idx,p,l) for idx,p,l in waves if p >= highs[min(idx,len(highs)-1)]*0.998]
        if lows_idx and highs_idx and highs_idx[-1][0] > lows_idx[-1][0]:
            fib_start = lows_idx[-1][1]
            fib_end   = highs_idx[-1][1]
            fib = we.fib_levels(fib_start, fib_end)
            for ratio, level in [("38.2%", fib["0.382"]),
                                  ("50.0%", fib["0.500"]),
                                  ("61.8%", fib["0.618"])]:
                fig.add_hline(
                    y=level, line_dash="dash",
                    line_color="rgba(148,163,184,0.4)", line_width=1,
                    annotation_text=f"  Fib {ratio} {level:.2f}",
                    annotation_font=dict(size=9, color="#64748b"),
                    row=row, col=1,
                )


# ─────────────────────────────────────────
# 主繪圖函式
# ─────────────────────────────────────────
def build_kline_chart(df, df_60=None, wave_label_d="N/A",
                      stock_name="", code=""):
    if not PLOTLY_OK or df is None or len(df) < 20:
        return None

    wave    = get_wave_info(wave_label_d)
    wcolor  = wave["color"]
    is_bull = wave_label_d.startswith(("3","4"))

    # ── 日K（近 90 日）──
    df_d = df.iloc[-90:].copy().reset_index()
    if "level_0" in df_d.columns: df_d = df_d.drop(columns=["level_0"])
    dc = "Date" if "Date" in df_d.columns else df_d.columns[0]
    x_d = df_d[dc].astype(str).tolist()
    H_d = df_d["High"].values.astype(float)
    L_d = df_d["Low"].values.astype(float)

    # ── 60分K（近 120 根）──
    has_60 = df_60 is not None and not df_60.empty and len(df_60) >= 10
    if has_60:
        df_h = df_60.iloc[-120:].copy().reset_index()
        if "level_0" in df_h.columns: df_h = df_h.drop(columns=["level_0"])
        dc2 = next((c for c in ["Date","Datetime"] if c in df_h.columns), df_h.columns[0])
        x_h = df_h[dc2].astype(str).tolist()
        H_h = df_h["High"].values.astype(float)
        L_h = df_h["Low"].values.astype(float)

    # ── 三大鐵律波浪計數 ──
    start_t = "L" if is_bull else "H"
    if WE_OK:
        big_order = max(5, len(x_d) // 10)
        try:
            big_pivots = we.find_pivots(H_d, L_d, big_order)
            big_result = we.count_impulse(big_pivots) if is_bull else \
                         _abc_count(big_pivots)
        except Exception:
            big_result = {"waves":[], "violations":["計算錯誤"], "current_wave":"?"}

        if has_60:
            sub_order = max(3, len(x_h) // 15)
            try:
                sub_pivots = we.find_pivots(H_h, L_h, sub_order)
                sub_result = we.count_impulse(sub_pivots) if is_bull else \
                             _abc_count(sub_pivots)
            except Exception:
                sub_result = {"waves":[], "violations":["計算錯誤"], "current_wave":"?"}
    else:
        big_result = {"waves":[], "violations":["wave_engine 未載入"], "current_wave":"?"}
        sub_result = {"waves":[], "violations":[], "current_wave":"?"}

    main_current = big_result.get("current_wave","?")
    sub_current  = sub_result.get("current_wave","?") if has_60 else "—"
    violations   = big_result.get("violations",[])

    # ── Subplots ──
    rows    = 3 if has_60 else 2
    row_h_  = [0.55, 0.30, 0.15] if has_60 else [0.72, 0.28]

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=False,
        row_heights=row_h_,
        vertical_spacing=0.04,
    )

    # ══ ROW 1：日K 大浪 ══
    fig.add_trace(go.Candlestick(
        x=x_d, open=df_d["Open"], high=df_d["High"],
        low=df_d["Low"], close=df_d["Close"],
        increasing=dict(line=dict(color="#4ade80",width=1),fillcolor="rgba(74,222,128,0.82)"),
        decreasing=dict(line=dict(color="#f87171",width=1),fillcolor="rgba(248,113,113,0.82)"),
        name="日K", showlegend=False,
    ), row=1, col=1)
    for ma,mc,mw in [(5,"#f97316",1),(20,"#38bdf8",1.5),(60,"#a78bfa",1)]:
        cn=f"MA{ma}"
        if cn in df_d.columns:
            s=df_d[cn].dropna()
            if len(s):
                fig.add_trace(go.Scatter(
                    x=[x_d[i] for i in s.index],y=s.values,
                    mode="lines",line=dict(color=mc,width=mw),
                    name=f"{ma}MA",showlegend=(ma==20),opacity=0.75,
                ),row=1,col=1)

    _plot_waves(fig, big_result.get("waves",[]), x_d, H_d, L_d,
                row=1, line_width=2.8, font_size=14, arrow_len=50,
                show_price=True, show_fib=True)

    # ══ ROW 2：60分子浪 ══
    if has_60:
        fig.add_trace(go.Candlestick(
            x=x_h, open=df_h["Open"], high=df_h["High"],
            low=df_h["Low"], close=df_h["Close"],
            increasing=dict(line=dict(color="#4ade80",width=1),fillcolor="rgba(74,222,128,0.85)"),
            decreasing=dict(line=dict(color="#f87171",width=1),fillcolor="rgba(248,113,113,0.85)"),
            name="60分K", showlegend=False,
        ), row=2, col=1)
        for ma,mc,mw in [(5,"#f97316",1.2),(20,"#38bdf8",1.2)]:
            cn=f"MA{ma}"
            if cn in df_h.columns:
                s=df_h[cn].dropna()
                if len(s):
                    fig.add_trace(go.Scatter(
                        x=[x_h[i] for i in s.index],y=s.values,
                        mode="lines",line=dict(color=mc,width=mw),
                        name=f"{ma}MA",showlegend=False,opacity=0.8,
                    ),row=2,col=1)

        _plot_waves(fig, sub_result.get("waves",[]), x_h, H_h, L_h,
                    row=2, line_width=2.2, font_size=12, arrow_len=35,
                    show_price=True, show_fib=False)

        # ▶ NOW
        lh = float(df_h["High"].iloc[-1])
        fig.add_annotation(
            x=x_h[-1], y=lh*1.022,
            text="<b>▶ NOW</b>",
            showarrow=True,arrowhead=2,
            arrowsize=1.3,arrowwidth=2.5,arrowcolor=wcolor,
            ax=0,ay=-45,
            font=dict(size=11,color=wcolor,family="Outfit"),
            bgcolor="rgba(6,11,24,0.9)",
            bordercolor=wcolor,borderwidth=2,borderpad=5,
            row=2,col=1,
        )

    # ══ 成交量 ══
    vol_row = 3 if has_60 else 2
    vc = ["rgba(74,222,128,0.5)" if float(c)>=float(o)
          else "rgba(248,113,113,0.5)"
          for c,o in zip(df_d["Close"],df_d["Open"])]
    fig.add_trace(go.Bar(
        x=x_d,y=df_d["Volume"],marker_color=vc,
        name="日量",showlegend=False,
    ),row=vol_row,col=1)
    if "VOL_MA5" in df_d.columns:
        vm=df_d["VOL_MA5"].dropna()
        if len(vm):
            fig.add_trace(go.Scatter(
                x=[x_d[i] for i in vm.index],y=vm.values,
                mode="lines",line=dict(color="#fbbf24",width=1.2),
                name="量5MA",showlegend=False,
            ),row=vol_row,col=1)

    # ══ 右上角：當前位置 ══
    pos_txt = f"大浪：{main_current}"
    if has_60: pos_txt += f"　子浪：{sub_current}"
    pos_desc = we.wave_position_text(big_result, is_bull) if WE_OK else wave["desc"]

    vio_txt = ""
    if violations:
        vio_txt = f"<br><span style='color:#fbbf24;font-size:10px'>⚠️ {violations[0][:30]}</span>"

    fig.add_annotation(
        xref="paper",yref="paper",
        x=0.99,y=0.99,
        text=(f"<b>{wave['emoji']} {wave['label']}</b><br>"
              f"<span style='font-size:11px;color:#94a3b8'>{pos_txt}</span>"
              f"{vio_txt}"),
        showarrow=False,xanchor="right",align="right",
        font=dict(size=13,color=wcolor,family="Outfit"),
        bgcolor="rgba(6,11,24,0.92)",
        bordercolor=wcolor,borderwidth=2,borderpad=10,
    )

    # ══ 鐵律違反警示 ══
    if violations:
        fig.add_annotation(
            xref="paper",yref="paper",
            x=0.01,y=0.56 if has_60 else 0.01,
            text=f"<span style='color:#fbbf24'>⚠️ {violations[0]}</span>",
            showarrow=False,xanchor="left",
            font=dict(size=10,color="#fbbf24",family="Outfit"),
            bgcolor="rgba(6,11,24,0.8)",
            bordercolor="#fbbf24",borderwidth=1,borderpad=5,
        )

    # ══ Layout ══
    title_str=(f"{stock_name}（{code}）艾略特波浪  ｜  "
               f"{wave['emoji']} {wave['label']}  ｜  📍 {pos_txt}")
    fig.update_layout(
        title=dict(text=title_str,font=dict(size=12,color="#e2e8f0",family="Outfit"),x=0),
        paper_bgcolor="rgba(6,11,24,0)",plot_bgcolor="rgba(6,11,24,0)",
        xaxis_rangeslider_visible=False,
        **({"xaxis2_rangeslider_visible":False} if has_60 else {}),
        legend=dict(orientation="h",x=0,y=1.03,
                    font=dict(size=10,color="#64748b"),bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0,r=0,t=52,b=0),
        height=680 if has_60 else 520,
        font=dict(family="Outfit"),hovermode="x unified",
    )
    ax=dict(gridcolor="rgba(255,255,255,0.05)",showgrid=True,zeroline=False,
            color="#475569",tickfont=dict(size=10,family="JetBrains Mono"))
    for k in ["xaxis","xaxis2","xaxis3","yaxis","yaxis2","yaxis3"]:
        try: fig.update_layout(**{k:ax.copy()})
        except: pass
    return fig


def _abc_count(pivots):
    """空頭 A-B-C 計數（簡化版）"""
    LBLS  = ["頂點","Ⓐ","Ⓑ","Ⓒ"]
    waves = []
    i = 0
    for pos,price,ptype in pivots[-6:]:
        if i < len(LBLS):
            waves.append((pos,price,LBLS[i]))
            i += 1
    return {"valid":True,"waves":waves,"violations":[],"current_wave":waves[-1][2] if waves else "?"}
