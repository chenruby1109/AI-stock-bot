"""
wave_chart.py V6
仿專業看盤軟體風格：
  - 粗彩色折線連接轉折點（橙色/藍色）
  - 每個轉折點標示 (1)(2)(3)(4)(5) + 價格
  - 上圖：日K大浪結構（90日）
  - 下圖：60分子浪細節（最近資料）
  - 右側清楚標示「現在在第幾浪」
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
# 波浪資訊（完整劇本）
# ─────────────────────────────────────────
WAVE_INFO = {
    "3-1":{"color":"#38bdf8","label":"第(1)浪起漲","emoji":"🌱","desc":"起漲初動，試探性上攻",
     "scenarios":[
      {"name":"✅ 主要（65%）延伸(1)浪→(2)浪修正布局","color":"#38bdf8",
       "desc":"(1)浪完成後(2)浪回測38.2~61.8%，之後(3)才是主攻。現在是耐心等(2)低點加碼的機會。",
       "cond":"量能放大，KD金叉，MACD翻紅","risk":"⚠️ 停損：(1)浪起漲低點"},
      {"name":"❌ 風險（10%）假突破仍在整理","color":"#f87171",
       "desc":"量縮無法站上，可能仍在整理中。","cond":"縮量無法站上，KD高檔死叉","risk":"🛑 跌破起漲點停損"},
     ]},
    "3-3":{"color":"#4ade80","label":"第(3)浪主升","emoji":"🚀","desc":"最強最長的主升浪，量能最大",
     "scenarios":[
      {"name":"✅ 主要（70%）(3)浪延伸，目標1.618~2.618倍","color":"#4ade80",
       "desc":"(3)浪最強，子浪(3)-1→2→3→4→5仍未完成。MACD紅柱持續放大，每次拉回均是加碼點。",
       "cond":"MACD紅柱最高，量能最大，KD>60","risk":"⚠️ 乖離>15%先減倉"},
      {"name":"📊 次要（20%）(3)浪尾聲進入(4)修正","color":"#fbbf24",
       "desc":"(3)浪子浪5正在完成，完成後(4)浪修正。","cond":"量縮，KD高位鈍化","risk":"⚠️ 注意高點反轉"},
      {"name":"❌ 風險（10%）(3)浪提前結束","color":"#f87171",
       "desc":"爆量長黑(3)浪提前結束，(4)浪大幅修正。","cond":"爆量長黑K，MACD翻綠","risk":"🛑 停損(3)浪起漲低點"},
     ]},
    "3-5":{"color":"#fbbf24","label":"第(5)浪末升","emoji":"🏔️","desc":"主升尾聲，量價背離訊號出現",
     "scenarios":[
      {"name":"✅ 主要（50%）(5)浪完成→(A)(B)(C)大修正","color":"#fbbf24",
       "desc":"(5)浪完成整個五浪，(A)浪跌幅通常38.2~61.8%整個升幅。逐步獲利了結，等(A)浪底部再布局。",
       "cond":"量價背離，KD頂背離，RSI>80","risk":"⚠️ 絕不追高，分批減倉"},
      {"name":"📊 次要（30%）(5)浪延伸","color":"#38bdf8",
       "desc":"法人持續買超，(5)浪可能延伸。","cond":"法人買超，量能放大","risk":"⚠️ 嚴設停利"},
      {"name":"❌ 風險（20%）失敗(5)浪急速轉空","color":"#f87171",
       "desc":"無法突破(3)浪高點，快速進入熊市。","cond":"量縮無法過(3)浪高","risk":"🛑 停損(3)浪高點"},
     ]},
    "3-a":{"color":"#94a3b8","label":"(5)浪後高檔整理","emoji":"☕","desc":"五浪完成後高位整理，(A)(B)(C)修正開始",
     "scenarios":[
      {"name":"✅ 主要（55%）(A)(B)(C)修正已開始，等(A)浪低點","color":"#f97316",
       "desc":"高位震盪是(A)浪的一部分，等(A)浪完成後(B)浪反彈出場機會。","cond":"量縮整理，均線走平","risk":"⚠️ 勿加碼"},
      {"name":"❌ 風險（45%）快速轉弱","color":"#f87171",
       "desc":"量增跌破前支撐，(A)浪下跌加速。","cond":"量增破支撐","risk":"🛑 停損前波高點"},
     ]},
    "4-a":{"color":"#fb923c","label":"(4)浪修正 (A)子浪","emoji":"📉","desc":"主升後(4)浪(A)子浪下跌中",
     "scenarios":[
      {"name":"✅ 主要（60%）(A)→(B)→(C)修正後啟動(5)浪","color":"#4ade80",
       "desc":"(A)下跌→(B)反彈→(C)再跌到0.382費波，完成後啟動(5)浪。(B)浪反彈是輕倉試多機會。",
       "cond":"量縮下跌，接近費波支撐","risk":"⚠️ (4)浪不應跌破(1)浪高點"},
      {"name":"❌ 風險（15%）跌破(1)浪高點重新定義","color":"#f87171",
       "desc":"跌破(1)浪頂點艾略特結構需重新定義。","cond":"帶量跌破(1)浪高點","risk":"🛑 全部出場"},
     ]},
    "4-b":{"color":"#f97316","label":"(4)浪修正 (B)子浪反彈","emoji":"👀","desc":"(4)浪(B)子浪技術反彈",
     "scenarios":[
      {"name":"✅ 主要（65%）(B)反彈完成後(C)浪再下探完成(4)浪","color":"#f97316",
       "desc":"(B)浪反彈通常到38.2~61.8%，完成後(C)浪下跌，之後啟動(5)浪。","cond":"量縮反彈至壓力位","risk":"⚠️ 不宜追多"},
      {"name":"📊 次要（25%）(B)浪強勁直接(5)浪","color":"#fbbf24",
       "desc":"(B)浪量增過前高，(4)浪已完成直接啟動(5)浪。","cond":"量增，(B)浪突破前高","risk":"⚠️ 需確認後才追"},
     ]},
    "4-c":{"color":"#a78bfa","label":"(4)浪修正末端 (C)子浪","emoji":"🪤","desc":"(4)浪(C)子浪，接近底部等(5)浪啟動",
     "scenarios":[
      {"name":"✅ 主要（65%）(C)浪見底→啟動(5)浪","color":"#4ade80",
       "desc":"(C)浪在0.382~0.618費波支撐見底，KD低位金叉+量縮後帶量長紅=(5)浪啟動訊號，最佳布局點。",
       "cond":"量縮後帶量長紅，KD<30金叉","risk":"⚠️ 停損(C)浪低點"},
      {"name":"❌ 風險（10%）整個五浪結束進入熊市","color":"#f87171",
       "desc":"跌破(1)浪高點帶量，下方是大級別(A)(B)(C)熊市修正。","cond":"帶量跌破(1)浪高點","risk":"🛑 全部出場"},
     ]},
    "C-3":{"color":"#f87171","label":"(A)(B)(C)修正 (C)浪主跌","emoji":"🔻","desc":"空頭(C)浪主跌段，避免抄底",
     "scenarios":[
      {"name":"✅ 主要（65%）(C)浪繼續下跌","color":"#f87171",
       "desc":"(C)浪通常等於(A)浪長度或1.618倍。主跌段不宜做多，等量縮止跌。","cond":"量增下跌，均線空頭排列","risk":"🛑 多單全數出清"},
      {"name":"📊 次要（25%）提前完成(C)浪出現底部","color":"#fbbf24",
       "desc":"量縮+KD低位背離+帶量長紅，(C)浪可能提前完成。","cond":"量縮，KD低位背離","risk":"⚠️ 確認後輕倉試多"},
     ]},
    "C-5":{"color":"#dc2626","label":"(C)浪末段趕底","emoji":"💥","desc":"恐慌殺盤極端超跌",
     "scenarios":[
      {"name":"✅ 主要（55%）趕底後強力反彈，新五浪即將開始","color":"#fbbf24",
       "desc":"趕底急殺後通常強力反彈，量縮止跌K棒（長下影線）可輕倉布局，停損設當日低點。",
       "cond":"量縮後爆量長紅，KD極低位回升","risk":"⚠️ 輕倉試做，嚴設停損"},
      {"name":"❌ 風險（45%）繼續探底","color":"#f87171",
       "desc":"無止跌訊號繼續破底。","cond":"量增繼續破低","risk":"🛑 勿抄底"},
     ]},
    "B-a":{"color":"#94a3b8","label":"(A)(B)(C)修正 (B)浪反彈","emoji":"↗️","desc":"空頭格局(B)浪技術反彈",
     "scenarios":[
      {"name":"✅ 主要（60%）(B)浪反彈至38~61.8%後(C)浪下跌","color":"#f87171",
       "desc":"(B)浪通常反彈到前高38~61.8%後轉弱，之後(C)浪才是底部。","cond":"量縮反彈","risk":"⚠️ 此反彈是出貨機會"},
      {"name":"📊 次要（25%）(B)浪強勢，可能是新五浪起漲","color":"#4ade80",
       "desc":"(B)浪量增過前高，可能底部確立，新五浪上升啟動。","cond":"量增突破前高，KD低位金叉","risk":"⚠️ 突破確認後才做多"},
     ]},
    "B-c":{"color":"#ef4444","label":"(B)浪(c)子浪反彈高點","emoji":"⚠️","desc":"(B)浪反彈最高點，(C)主跌即將展開",
     "scenarios":[
      {"name":"✅ 主要（70%）(B)浪完成，(C)主跌浪展開","color":"#f87171",
       "desc":"(B)浪c子浪為反彈最高點，之後(C)主跌浪展開。減倉逃命的最後機會。","cond":"KD高位死叉，量縮，MACD翻綠","risk":"🛑 多單清倉，不追高"},
      {"name":"📊 次要（30%）突破前高，多頭確立","color":"#4ade80",
       "desc":"放量突破(A)浪起點，(A)(B)(C)修正結束，新五浪多頭開始。","cond":"量增突破前高，所有均線翻多","risk":"⚠️ 確認後才進場"},
     ]},
    "N/A":{"color":"#64748b","label":"波浪判斷中","emoji":"❓","desc":"資料不足","scenarios":[]},
}

def get_wave_info(label):
    return WAVE_INFO.get(label, WAVE_INFO["N/A"])


# ─────────────────────────────────────────
# 工具函式
# ─────────────────────────────────────────
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


def _draw_wave(fig, df, x_dates, row, order, wave_lbls, wave_colors, start_type,
               line_color="#f97316", line_width=2.5, font_size=14,
               show_price=True, arrow_len=45):
    """
    仿看盤軟體風格：
    - 彩色粗折線連接所有轉折點
    - 每個轉折點標 (1)(2)(3) + 價格
    - 用半透明色塊標出最後一段浪
    回傳：(labeled_list, current_lbl)
    """
    highs = df["High"].values.astype(float)
    lows  = df["Low"].values.astype(float)
    try:
        pivots = _find_pivots(highs, lows, order)
    except Exception:
        return [], "?"

    if len(pivots) < 2:
        return [], "?"

    # ── 粗彩色折線：連接所有轉折點 ──
    px = [x_dates[p[0]] for p in pivots if p[0] < len(x_dates)]
    # 高點取 High，低點取 Low（讓線更貼 K 棒）
    py = [highs[p[0]] if p[2]=="H" else lows[p[0]]
          for p in pivots if p[0] < len(x_dates)]

    fig.add_trace(go.Scatter(
        x=px, y=py,
        mode="lines",
        line=dict(color=line_color, width=line_width),
        opacity=0.85,
        showlegend=False,
        hoverinfo="skip",
    ), row=row, col=1)

    # ── 標注波浪 ──
    labeled = []
    wave_n, prev_type, started = 0, None, False
    current_lbl = "?"

    for pos, price, ptype in pivots:
        if pos >= len(x_dates): continue
        if not started:
            if ptype == start_type:
                # 起始點小圓點
                fig.add_trace(go.Scatter(
                    x=[x_dates[pos]], y=[price],
                    mode="markers",
                    marker=dict(color=line_color, size=8, symbol="circle"),
                    showlegend=False, hoverinfo="skip",
                ), row=row, col=1)
                started = True; prev_type = ptype
            continue
        if ptype == prev_type: continue
        if wave_n >= len(wave_lbls): break

        lbl = wave_lbls[wave_n]
        lc  = wave_colors.get(lbl, line_color)
        is_hi = (ptype == "H")

        # 價格顯示（四捨五入）
        price_str = f"{price:.2f}" if price < 1000 else f"{int(price):,}"
        display_text = f"<b>{lbl}</b><br><span style='font-size:10px'>{price_str}</span>" if show_price else f"<b>{lbl}</b>"

        ay = -arrow_len if is_hi else arrow_len

        fig.add_annotation(
            x=x_dates[pos], y=price,
            text=display_text,
            showarrow=True,
            arrowhead=0,
            arrowwidth=1.5,
            arrowcolor=lc,
            ax=0, ay=ay,
            font=dict(size=font_size, color=lc, family="Outfit"),
            bgcolor="rgba(6,11,24,0.88)",
            bordercolor=lc,
            borderwidth=1.5,
            borderpad=5,
            align="center",
            row=row, col=1,
        )

        # 轉折點圓點
        fig.add_trace(go.Scatter(
            x=[x_dates[pos]], y=[price],
            mode="markers",
            marker=dict(color=lc, size=7, symbol="circle",
                        line=dict(color="white", width=1)),
            showlegend=False, hoverinfo="skip",
        ), row=row, col=1)

        labeled.append((pos, price, lbl, lc, ptype))
        current_lbl = lbl
        wave_n += 1; prev_type = ptype

    # ── 色塊：最後一段浪的區間 ──
    if labeled:
        last_pos  = labeled[-1][0]
        last_type = labeled[-1][4]
        last_lc   = labeled[-1][3]
        x0 = x_dates[last_pos]
        x1 = x_dates[-1]
        seg = df["Close"].values[last_pos:]
        if len(seg):
            y0 = float(min(df["Low"].values[last_pos:])) * 0.998
            y1 = float(max(df["High"].values[last_pos:])) * 1.002
            try:
                r = int(last_lc[1:3],16)
                g = int(last_lc[3:5],16)
                b = int(last_lc[5:7],16)
                fill_c  = f"rgba({r},{g},{b},0.06)"
                line_c2 = f"rgba({r},{g},{b},0.25)"
            except:
                fill_c  = "rgba(255,255,255,0.05)"
                line_c2 = "rgba(255,255,255,0.2)"
            fig.add_shape(
                type="rect",
                x0=x0, x1=x1, y0=y0, y1=y1,
                fillcolor=fill_c,
                line=dict(color=line_c2, width=1, dash="dot"),
                row=row, col=1,
            )

    return labeled, current_lbl


# ─────────────────────────────────────────
# 主繪圖函式
# ─────────────────────────────────────────
def build_kline_chart(df, df_60=None, wave_label_d="N/A",
                      stock_name="", code=""):
    """
    df      : 日K DataFrame（含 MA5/MA20/MA60/VOL_MA5/SAR 等指標）
    df_60   : 60分K DataFrame（可為 None）
    wave_label_d: 由 app.py 的 wave_label() 計算出的標籤（如 "3-3"）
    """
    if not PLOTLY_OK or df is None or len(df) < 20:
        return None

    wave    = get_wave_info(wave_label_d)
    wcolor  = wave["color"]
    is_bull = wave_label_d.startswith(("3","4"))

    # ── 準備日K資料（近 90 日）──
    df_d = df.iloc[-90:].copy().reset_index()
    if "level_0" in df_d.columns: df_d = df_d.drop(columns=["level_0"])
    dc = "Date" if "Date" in df_d.columns else df_d.columns[0]
    x_d = df_d[dc].astype(str).tolist()

    # ── 準備 60 分資料（最近 120 根）──
    has_60 = df_60 is not None and not df_60.empty and len(df_60) >= 10
    if has_60:
        df_h = df_60.iloc[-120:].copy().reset_index()
        if "level_0" in df_h.columns: df_h = df_h.drop(columns=["level_0"])
        dc2 = "Date" if "Date" in df_h.columns else \
              "Datetime" if "Datetime" in df_h.columns else df_h.columns[0]
        x_h = df_h[dc2].astype(str).tolist()

    # ── 波浪標籤設定 ──
    if is_bull:
        M_LBLS = ["(1)","(2)","(3)","(4)","(5)"]
        M_COLS = {"(1)":"#38bdf8","(2)":"#fb923c","(3)":"#4ade80","(4)":"#f97316","(5)":"#fbbf24"}
        S_LBLS = ["1","2","3","4","5"]
        S_COLS = {"1":"#7dd3fc","2":"#fed7aa","3":"#86efac","4":"#fdba74","5":"#fde68a"}
        start  = "L"
        main_line_color = "#f97316"   # 橙色，類似你分享的截圖
        sub_line_color  = "#06b6d4"   # 青藍色，60分子浪
    else:
        M_LBLS = ["(A)","(B)","(C)"]
        M_COLS = {"(A)":"#f87171","(B)":"#fb923c","(C)":"#dc2626"}
        S_LBLS = ["a","b","c"]
        S_COLS = {"a":"#fca5a5","b":"#fdba74","c":"#f87171"}
        start  = "H"
        main_line_color = "#f97316"
        sub_line_color  = "#e879f9"

    big_order = max(5, len(x_d) // 10)
    sub_order = max(3, len(x_h) // 15) if has_60 else 3

    # ── Subplot 設定 ──
    rows      = 3 if has_60 else 2
    row_h     = [0.55, 0.30, 0.15] if has_60 else [0.70, 0.30]
    sub_titles= (
        ("", "", "") if has_60 else ("", "")
    )

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=False,
        row_heights=row_h,
        vertical_spacing=0.04,
        subplot_titles=sub_titles,
    )

    # ══════════════════════════════════════════
    # ROW 1：日K 大浪
    # ══════════════════════════════════════════
    fig.add_trace(go.Candlestick(
        x=x_d,
        open=df_d["Open"], high=df_d["High"],
        low=df_d["Low"],   close=df_d["Close"],
        increasing=dict(line=dict(color="#4ade80",width=1),
                        fillcolor="rgba(74,222,128,0.82)"),
        decreasing=dict(line=dict(color="#f87171",width=1),
                        fillcolor="rgba(248,113,113,0.82)"),
        name="日K", showlegend=False,
    ), row=1, col=1)

    for ma, mc, mw in [(5,"#f97316",1),(20,"#38bdf8",1.5),(60,"#a78bfa",1)]:
        cn = f"MA{ma}"
        if cn in df_d.columns:
            s = df_d[cn].dropna()
            if len(s):
                fig.add_trace(go.Scatter(
                    x=[x_d[i] for i in s.index], y=s.values,
                    mode="lines", line=dict(color=mc,width=mw),
                    name=f"{ma}MA", showlegend=(ma==20), opacity=0.75,
                ), row=1, col=1)

    main_labeled, main_current = _draw_wave(
        fig, df_d, x_d, row=1,
        order=big_order,
        wave_lbls=M_LBLS, wave_colors=M_COLS,
        start_type=start,
        line_color=main_line_color, line_width=2.5,
        font_size=14, show_price=True, arrow_len=48,
    )

    # 日K 圖左上標題
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.01, y=0.99,
        text="<b>日K 大浪結構</b>",
        showarrow=False, xanchor="left",
        font=dict(size=11, color="#94a3b8", family="Outfit"),
    )

    # ══════════════════════════════════════════
    # ROW 2（或3）：成交量（日K對應）
    # ══════════════════════════════════════════
    vol_row = 3 if has_60 else 2
    # 60分K 在 row2，成交量在 row3
    # 如果沒有60分，成交量在 row2

    if has_60:
        # ── ROW 2：60分子浪 ──
        fig.add_trace(go.Candlestick(
            x=x_h,
            open=df_h["Open"], high=df_h["High"],
            low=df_h["Low"],   close=df_h["Close"],
            increasing=dict(line=dict(color="#4ade80",width=1),
                            fillcolor="rgba(74,222,128,0.85)"),
            decreasing=dict(line=dict(color="#f87171",width=1),
                            fillcolor="rgba(248,113,113,0.85)"),
            name="60分K", showlegend=False,
        ), row=2, col=1)

        for ma, mc, mw in [(5,"#f97316",1.2),(20,"#38bdf8",1.2)]:
            cn = f"MA{ma}"
            if cn in df_h.columns:
                s = df_h[cn].dropna()
                if len(s):
                    fig.add_trace(go.Scatter(
                        x=[x_h[i] for i in s.index], y=s.values,
                        mode="lines", line=dict(color=mc,width=mw),
                        name=f"{ma}MA", showlegend=False, opacity=0.8,
                    ), row=2, col=1)

        sub_labeled, sub_current = _draw_wave(
            fig, df_h, x_h, row=2,
            order=sub_order,
            wave_lbls=S_LBLS, wave_colors=S_COLS,
            start_type=start,
            line_color=sub_line_color, line_width=2.0,
            font_size=12, show_price=True, arrow_len=35,
        )

        # ▶ NOW 箭頭
        lh = float(df_h["High"].iloc[-1])
        fig.add_annotation(
            x=x_h[-1], y=lh*1.02,
            text=f"<b>▶ NOW</b>",
            showarrow=True, arrowhead=2,
            arrowsize=1.3, arrowwidth=2.5, arrowcolor=wcolor,
            ax=0, ay=-45,
            font=dict(size=11, color=wcolor, family="Outfit"),
            bgcolor="rgba(6,11,24,0.9)",
            bordercolor=wcolor, borderwidth=2, borderpad=5,
            row=2, col=1,
        )

        fig.add_annotation(
            xref="paper", yref="paper",
            x=0.01, y=0.42,
            text="<b>60分 子浪細節</b>",
            showarrow=False, xanchor="left",
            font=dict(size=11, color="#94a3b8", family="Outfit"),
        )

        pos_text = f"大浪：{main_current}　子浪：{sub_current}"
    else:
        sub_current = "—"
        pos_text = f"大浪：{main_current}"

    # ── 成交量 ──
    vc = ["rgba(74,222,128,0.5)" if float(c)>=float(o)
          else "rgba(248,113,113,0.5)"
          for c,o in zip(df_d["Close"],df_d["Open"])]
    fig.add_trace(go.Bar(
        x=x_d, y=df_d["Volume"],
        marker_color=vc, name="日量", showlegend=False,
    ), row=vol_row, col=1)
    if "VOL_MA5" in df_d.columns:
        vm=df_d["VOL_MA5"].dropna()
        if len(vm):
            fig.add_trace(go.Scatter(
                x=[x_d[i] for i in vm.index], y=vm.values,
                mode="lines", line=dict(color="#fbbf24",width=1.2),
                name="量5MA", showlegend=False,
            ), row=vol_row, col=1)

    # ══════════════════════════════════════════
    # 右上角：當前位置大框
    # ══════════════════════════════════════════
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.99, y=0.985,
        text=(f"<b>{wave['emoji']} {wave['label']}</b><br>"
              f"<span style='font-size:12px;color:#94a3b8'>{pos_text}</span>"),
        showarrow=False, xanchor="right", align="right",
        font=dict(size=14, color=wcolor, family="Outfit"),
        bgcolor="rgba(6,11,24,0.9)",
        bordercolor=wcolor, borderwidth=2, borderpad=10,
    )

    # ══════════════════════════════════════════
    # Layout
    # ══════════════════════════════════════════
    title_str = (
        f"{stock_name}（{code}）波浪分析  ｜  "
        f"{wave['emoji']} {wave['label']}  ｜  📍 {pos_text}"
    )
    fig.update_layout(
        title=dict(text=title_str,
                   font=dict(size=12, color="#e2e8f0", family="Outfit"), x=0),
        paper_bgcolor="rgba(6,11,24,0)",
        plot_bgcolor ="rgba(6,11,24,0)",
        xaxis_rangeslider_visible=False,
        **({"xaxis2_rangeslider_visible":False} if has_60 else {}),
        legend=dict(orientation="h", x=0, y=1.03,
                    font=dict(size=10,color="#64748b"),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0,r=0,t=52,b=0),
        height=680 if has_60 else 520,
        font=dict(family="Outfit"),
        hovermode="x unified",
    )
    ax = dict(
        gridcolor="rgba(255,255,255,0.05)", showgrid=True,
        zeroline=False, color="#475569",
        tickfont=dict(size=10, family="JetBrains Mono"),
    )
    for k in ["xaxis","xaxis2","xaxis3","yaxis","yaxis2","yaxis3"]:
        try: fig.update_layout(**{k: ax.copy()})
        except: pass

    return fig
