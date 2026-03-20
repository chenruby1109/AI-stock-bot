"""
wave_chart.py V8
修正核心問題：
  - wave_label_d（如"3-5"）= app.py 根據 KD/MACD/MA 判斷的「大浪.子浪」
  - "3-5" = 第③大浪的第⑤子浪
  - 圖表的標注、說明、劇本都要以此為準
  - 波浪計數引擎（scipy）只用來畫轉折連線，不獨立標浪名
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
# wave_label_d 解碼
# ─────────────────────────────────────────
MAJOR_MAP = {
    "3": ("③","#4ade80"),   # 推動浪的第3浪
    "4": ("④","#f97316"),   # 推動浪的第4浪
    "C": ("Ⓒ","#f87171"),  # 修正浪的C浪
    "B": ("Ⓑ","#fb923c"),  # 修正浪的B浪
}
SUB_MAP = {
    "1": ("①","#38bdf8"),
    "3": ("③","#4ade80"),
    "5": ("⑤","#fbbf24"),
    "a": ("⒜","#fca5a5"),
    "b": ("⒝","#fdba74"),
    "c": ("⒞","#f87171"),
}

def decode_wave(wave_label_d):
    """
    "3-5" → major_sym="③", major_color="#4ade80", sub_sym="⑤", sub_color="#fbbf24"
    "4-a" → major_sym="④", ..., sub_sym="⒜", ...
    "C-3" → major_sym="Ⓒ", ..., sub_sym="③", ...
    """
    parts = wave_label_d.split("-") if "-" in wave_label_d else [wave_label_d, "?"]
    major_key = parts[0]
    sub_key   = parts[1] if len(parts) > 1 else "?"

    major_sym, major_color = MAJOR_MAP.get(major_key, (f"({major_key})", "#94a3b8"))
    sub_sym,   sub_color   = SUB_MAP.get(sub_key,   (sub_key,          "#94a3b8"))

    return {
        "major_sym":   major_sym,
        "major_color": major_color,
        "sub_sym":     sub_sym,
        "sub_color":   sub_color,
        "major_key":   major_key,
        "sub_key":     sub_key,
    }


# ─────────────────────────────────────────
# 波浪資訊（劇本說明）
# ─────────────────────────────────────────
WAVE_INFO = {
    "3-1":{"color":"#38bdf8","label":"③浪中的①子浪（起漲初動）","emoji":"🌱","desc":"③大浪剛啟動，①子浪上攻中",
     "scenarios":[
      {"name":"✅ 主要（65%）①子浪完成→②子浪修正→③子浪爆發","color":"#38bdf8",
       "desc":"③大浪的①子浪完成後，②子浪回測38.2~61.8%，之後③子浪才是真正的爆發段。現在是耐心等②子浪低點加碼的時機。",
       "cond":"量能放大，突破前高，KD金叉","risk":"⚠️ 停損：③大浪起漲低點"},
      {"name":"❌ 風險（10%）假突破，仍在②大浪整理中","color":"#f87171",
       "desc":"若量縮無法站穩均線，可能仍是②大浪的反彈，③大浪未正式啟動。","cond":"縮量，KD高檔死叉","risk":"🛑 跌破③大浪起漲點停損"},
     ]},
    "3-3":{"color":"#4ade80","label":"③浪中的③子浪（主升爆發）","emoji":"🚀","desc":"③大浪的③子浪，雙重主升力道最強",
     "scenarios":[
      {"name":"✅ 主要（70%）③子浪仍在延伸，量能最大","color":"#4ade80",
       "desc":"③大浪的③子浪是整個多頭結構中力道最強的位置（大浪③ × 子浪③）。MACD紅柱持續放大，量比>1.5倍，每次小回踩均是加碼點。目標看③大浪的1.618~2.618倍擴展。",
       "cond":"MACD紅柱持續放大，KD>60持續多頭，量比>1.5","risk":"⚠️ 乖離率超過15%先減半倉等回踩"},
      {"name":"📊 次要（20%）③子浪完成→④子浪短暫修正","color":"#fbbf24",
       "desc":"③子浪即將完成，④子浪修正通常較淺（38.2%費波），是最後加碼⑤子浪的機會。","cond":"MACD紅柱縮短，KD開始鈍化","risk":"⚠️ ④子浪不應跌破①子浪高點（鐵律3）"},
      {"name":"❌ 風險（10%）③大浪提前結束進入④大浪修正","color":"#f87171",
       "desc":"若出現爆量長黑且MACD快速翻綠，可能整個③大浪已完成，即將進入④大浪較大幅修正（回測整個③浪的38.2~61.8%）。","cond":"爆量長黑，MACD快速翻綠","risk":"🛑 停損③大浪起漲低點"},
     ]},
    "3-5":{"color":"#fbbf24","label":"③浪中的⑤子浪（主升尾聲）","emoji":"🏔️","desc":"③大浪的⑤子浪，主升即將結束",
     "scenarios":[
      {"name":"✅ 主要（55%）⑤子浪完成→進入④大浪ABC修正","color":"#fbbf24",
       "desc":"③大浪的⑤子浪完成後，④大浪ABC修正展開。④大浪通常回測③大浪漲幅的38.2%~50%，這是耐心等待④浪完成後布局⑤大浪的時機。",
       "cond":"量價背離（價新高但量縮），KD頂背離","risk":"⚠️ 此位置不宜追高，考慮減倉"},
      {"name":"📊 次要（30%）⑤子浪延伸，③大浪仍繼續","color":"#38bdf8",
       "desc":"若法人持續買超且量能仍放大，⑤子浪可能延伸，③大浪繼續上攻。","cond":"法人持續買超，量能未縮","risk":"⚠️ 嚴設停利，注意轉折"},
      {"name":"❌ 風險（15%）失敗⑤子浪→直接進入④大浪急跌","color":"#f87171",
       "desc":"⑤子浪無法突破③子浪高點（失敗五浪），可能快速轉入④大浪。","cond":"量縮無法過③子浪高，KD高位死叉","risk":"🛑 停損設③子浪高點"},
     ]},
    "3-a":{"color":"#94a3b8","label":"③浪後高檔整理","emoji":"☕","desc":"③大浪完成後高位整理，④大浪修正中",
     "scenarios":[
      {"name":"✅ 主要（55%）④大浪ABC修正展開，等A浪低點","color":"#f97316",
       "desc":"③大浪完成後進入④大浪修正的A子浪，等A子浪完成（量縮止跌）後B子浪反彈，再等C子浪見底後是最佳布局⑤大浪的機會。",
       "cond":"量縮整理，均線開始走平，MA5往下彎","risk":"⚠️ 勿在此加碼，等確認底部"},
      {"name":"❌ 風險（45%）直接快速跌入④大浪","color":"#f87171",
       "desc":"量增跌破前支撐，④大浪修正加速。","cond":"量增破支撐，MACD翻綠","risk":"🛑 停損③大浪高點"},
     ]},
    "4-a":{"color":"#fb923c","label":"④大浪修正的A子浪","emoji":"📉","desc":"④大浪的A子浪下跌中，為正常修正",
     "scenarios":[
      {"name":"✅ 主要（60%）A→B→C三波修正後啟動⑤大浪","color":"#4ade80",
       "desc":"④大浪A子浪下跌後，B子浪反彈到38.2~61.8%壓力，再C子浪下跌至0.382~0.5費波支撐完成④浪，之後啟動⑤大浪。B子浪反彈是輕倉試多機會。",
       "cond":"量縮下跌，每天跌幅縮小，接近費波38.2%","risk":"⚠️ 鐵律3：④浪不應跌破①浪高點"},
      {"name":"📊 次要（25%）④大浪複雜修正（W型或三角整理）","color":"#fbbf24",
       "desc":"④大浪形成更複雜的W底或三角收斂整理，需要更多時間，但最終都會啟動⑤大浪。",
       "cond":"量縮震盪，高低點收斂","risk":"⚠️ 耐心等待，不要搶進"},
      {"name":"❌ 風險（15%）跌破①浪高點違反鐵律3","color":"#f87171",
       "desc":"若跌破①大浪高點，整個艾略特結構需重新定義，可能是更大級別的熊市。",
       "cond":"帶量跌破①大浪高點","risk":"🛑 全部出場，重新評估"},
     ]},
    "4-b":{"color":"#f97316","label":"④大浪修正的B子浪（反彈）","emoji":"👀","desc":"④大浪B子浪技術反彈，趨勢仍在修正",
     "scenarios":[
      {"name":"✅ 主要（65%）B子浪反彈完成→C子浪再下探完成④浪","color":"#f97316",
       "desc":"④大浪的B子浪反彈通常到A子浪跌幅的38.2~61.8%（即原本的壓力位），完成後C子浪下跌完成整個④大浪，之後啟動⑤大浪。",
       "cond":"量縮反彈至壓力位，MACD仍綠柱","risk":"⚠️ 此反彈不宜追多，等C子浪完成"},
      {"name":"📊 次要（25%）B子浪強勁，④浪已完成直接⑤浪","color":"#fbbf24",
       "desc":"若B子浪量增突破前高，④大浪可能已完成，直接啟動⑤大浪。","cond":"量增，B子浪突破前高，MACD翻紅","risk":"⚠️ 需確認後才追"},
     ]},
    "4-c":{"color":"#a78bfa","label":"④大浪修正的C子浪（末端）","emoji":"🪤","desc":"④大浪C子浪，接近底部等⑤大浪啟動",
     "scenarios":[
      {"name":"✅ 主要（65%）C子浪見底→啟動⑤大浪","color":"#4ade80",
       "desc":"④大浪C子浪通常在③大浪漲幅的38.2%~61.8%費波支撐見底。KD低位金叉+量縮後帶量長紅=⑤大浪啟動訊號，是整個多頭結構最後一次大布局機會。",
       "cond":"量縮後帶量長紅K，KD<30出現金叉，守住費波0.382","risk":"⚠️ 停損設C子浪低點，嚴格執行"},
      {"name":"📊 次要（25%）C子浪延伸測61.8%費波","color":"#fbbf24",
       "desc":"C子浪比預期深，測到61.8%費波才見底，但最終⑤大浪仍會啟動。","cond":"量繼續縮，慢慢探低至61.8%費波","risk":"⚠️ 等量縮止跌訊號再進場"},
      {"name":"❌ 風險（10%）跌破①大浪高點，五浪結束進入熊市","color":"#f87171",
       "desc":"若帶量跌破①大浪高點，整個五浪主升結束，下方是大級別(A)(B)(C)熊市修正。",
       "cond":"帶量跌破①大浪高點","risk":"🛑 全部出場，轉為空頭思維"},
     ]},
    "C-3":{"color":"#f87171","label":"(A)(B)(C)修正的(C)浪主跌","emoji":"🔻","desc":"空頭(C)浪主跌段，避免抄底",
     "scenarios":[
      {"name":"✅ 主要（65%）(C)浪繼續下跌，目標(A)浪1~1.618倍","color":"#f87171",
       "desc":"(C)浪通常等於(A)浪長度或1.618倍。目前處於主跌段，量增下跌，不宜做多，等量縮止跌訊號。",
       "cond":"量增下跌，均線空頭排列","risk":"🛑 多單全數出清，空倉等待"},
      {"name":"📊 次要（25%）提前完成(C)浪，形成雙底","color":"#fbbf24",
       "desc":"若量縮+KD低位背離+帶量長紅，(C)浪可能提前完成，新一輪五浪上升即將開始。",
       "cond":"量縮，KD低位背離，帶量長紅K","risk":"⚠️ 確認後輕倉試多"},
     ]},
    "C-5":{"color":"#dc2626","label":"(C)浪末段趕底","emoji":"💥","desc":"恐慌殺盤極端超跌，(C)浪接近尾聲",
     "scenarios":[
      {"name":"✅ 主要（55%）趕底後強力反彈，新五浪即將開始","color":"#fbbf24",
       "desc":"趕底急殺後通常有強力反彈，量縮止跌K棒（長下影線、十字星）可輕倉布局，停損設當日低點。",
       "cond":"量縮後爆量長紅，KD極低位回升，長下影線","risk":"⚠️ 輕倉試做，嚴設停損"},
      {"name":"❌ 風險（45%）超跌延伸繼續探底","color":"#f87171",
       "desc":"無止跌訊號繼續破底，維持空手。","cond":"量增繼續破低","risk":"🛑 勿抄底，等止跌"},
     ]},
    "B-a":{"color":"#94a3b8","label":"(A)(B)(C)修正中的(B)浪反彈","emoji":"↗️","desc":"空頭格局(B)浪技術反彈，是出貨機會",
     "scenarios":[
      {"name":"✅ 主要（60%）(B)浪反彈至38~61.8%後，(C)浪繼續下跌","color":"#f87171",
       "desc":"(B)浪通常反彈到(A)浪起點的38.2%~61.8%後轉弱，之後(C)浪主跌才是真正底部。(B)浪反彈是減倉出貨的機會，不宜追多。",
       "cond":"量縮反彈，均線仍空頭排列","risk":"⚠️ 此反彈是出貨機會，不宜重倉做多"},
      {"name":"📊 次要（25%）(B)浪強勢突破，可能是新五浪起漲","color":"#4ade80",
       "desc":"若(B)浪量增突破(A)浪起點前高，可能是底部確立，新的五浪上升啟動。",
       "cond":"量增突破前高，KD低位金叉，MACD翻紅","risk":"⚠️ 突破確認後才考慮做多"},
     ]},
    "B-c":{"color":"#ef4444","label":"(B)浪的c子浪（反彈高點）","emoji":"⚠️","desc":"(B)浪反彈最高點，(C)主跌浪即將展開",
     "scenarios":[
      {"name":"✅ 主要（70%）(B)浪完成，(C)主跌浪展開","color":"#f87171",
       "desc":"(B)浪c子浪為反彈最高點，此後(C)主跌浪展開，是減倉逃命的最後機會。(C)浪目標通常是(A)浪的1~1.618倍。",
       "cond":"KD高位死叉，量縮，MACD翻綠柱","risk":"🛑 多單清倉，不在此追高"},
      {"name":"📊 次要（30%）突破(A)浪起點，多頭確立","color":"#4ade80",
       "desc":"若放量突破(A)浪起點（前高），(A)(B)(C)修正結束，新的五浪多頭開始。",
       "cond":"量增突破前高，所有均線翻多","risk":"⚠️ 確認後才進場，設好停損"},
     ]},
    "N/A":{"color":"#64748b","label":"波浪判斷中","emoji":"❓","desc":"資料不足，請稍後","scenarios":[]},
}

def get_wave_info(label):
    return WAVE_INFO.get(label, WAVE_INFO["N/A"])


# ─────────────────────────────────────────
# 轉折點偵測（只用來畫連線，不標浪名）
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
# 波浪結構圖：用轉折點連線 + 自動標對應浪名
# 策略：
#   - 偵測轉折點序列（高低交替）
#   - 根據 wave_label_d 知道「現在是第幾浪」
#   - 從後往前回推，標上對應浪號
# ─────────────────────────────────────────
def _get_wave_sequence(is_bull, wave_label_d):
    """根據當前波浪位置，決定要標的完整序列"""
    major_key = wave_label_d.split("-")[0] if "-" in wave_label_d else wave_label_d
    sub_key   = wave_label_d.split("-")[1] if "-" in wave_label_d else ""

    if is_bull:
        # 多頭推動浪序列
        bull_seq = ["起點","①","②","③","④","⑤"]
        # 當前大浪（③或④）的子浪序列
        if major_key == "3":
            sub_seq = ["③起","③①","③②","③③","③④","③⑤"]
        elif major_key == "4":
            sub_seq = ["④起","④A","④B","④C"]
        else:
            sub_seq = []
        return bull_seq, sub_seq
    else:
        abc_seq = ["頂","(A)","(B)","(C)"]
        if major_key == "B":
            sub_seq = ["B起","Ba","Bb","Bc"]
        elif major_key == "C":
            sub_seq = ["C起","C①","C②","C③","C④","C⑤"]
        else:
            sub_seq = []
        return abc_seq, sub_seq


LABEL_COLORS = {
    "起點":"#64748b","③起":"#4ade80","④起":"#f97316","頂":"#f87171",
    "B起":"#fb923c","C起":"#dc2626",
    "①":"#38bdf8","②":"#fb923c","③":"#4ade80","④":"#f97316","⑤":"#fbbf24",
    "③①":"#7dd3fc","③②":"#fed7aa","③③":"#86efac","③④":"#fdba74","③⑤":"#fde68a",
    "④A":"#fca5a5","④B":"#fdba74","④C":"#f87171",
    "(A)":"#f87171","(B)":"#fb923c","(C)":"#dc2626",
    "Ba":"#fca5a5","Bb":"#fdba74","Bc":"#f87171",
    "C①":"#fca5a5","C②":"#fed7aa","C③":"#f87171","C④":"#fdba74","C⑤":"#dc2626",
}

def _plot_wave_line(fig, pivots, x_dates, H, L, row,
                    seq_labels, font_size=14, arrow_len=48, line_width=2.8):
    """
    在轉折點上標注對應的浪名
    pivots: 轉折點列表（已按時間排序）
    seq_labels: 要標的序列（從後往前分配）
    """
    if not pivots or not x_dates:
        return

    # 取最近 N 個轉折點（對應 seq_labels 長度）
    n_labels = len(seq_labels)
    recent_pivots = pivots[-n_labels:] if len(pivots) >= n_labels else pivots

    # 彩色折線連接
    if len(recent_pivots) >= 2:
        lx = [x_dates[p[0]] for p in recent_pivots if p[0]<len(x_dates)]
        ly = [H[p[0]] if p[2]=="H" else L[p[0]] for p in recent_pivots if p[0]<len(x_dates)]
        fig.add_trace(go.Scatter(
            x=lx, y=ly, mode="lines",
            line=dict(color="#f97316", width=line_width),
            opacity=0.8, showlegend=False, hoverinfo="skip",
        ), row=row, col=1)

    # 從後往前分配標籤（讓最後一個轉折點對應當前浪）
    offset = len(seq_labels) - len(recent_pivots)
    for i, (pos, price, ptype) in enumerate(recent_pivots):
        if pos >= len(x_dates): continue
        label_i = i + offset
        if label_i < 0 or label_i >= len(seq_labels): continue
        lbl = seq_labels[label_i]
        lc  = LABEL_COLORS.get(lbl, "#94a3b8")
        is_hi = (ptype == "H")
        ay = -arrow_len if is_hi else arrow_len

        price_str = f"{price:.2f}" if price < 1000 else f"{int(price):,}"
        txt = f"<b>{lbl}</b><br><span style='font-size:10px'>{price_str}</span>"

        fig.add_annotation(
            x=x_dates[pos], y=price,
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
        fig.add_trace(go.Scatter(
            x=[x_dates[pos]], y=[price],
            mode="markers",
            marker=dict(color=lc, size=7, symbol="circle",
                        line=dict(color="white",width=1)),
            showlegend=False, hoverinfo="skip",
        ), row=row, col=1)

    # 色塊：最後一段浪
    if len(recent_pivots) >= 2:
        last_pos = recent_pivots[-1][0]
        last_lbl = seq_labels[-1] if seq_labels else ""
        lc = LABEL_COLORS.get(last_lbl, "#94a3b8")
        x0 = x_dates[min(recent_pivots[-2][0], len(x_dates)-1)]
        x1 = x_dates[-1]
        y0 = float(min(L[last_pos:])) * 0.997
        y1 = float(max(H[last_pos:])) * 1.003
        try:
            r,g,b=int(lc[1:3],16),int(lc[3:5],16),int(lc[5:7],16)
            fig.add_shape(type="rect",x0=x0,x1=x1,y0=y0,y1=y1,
                fillcolor=f"rgba({r},{g},{b},0.06)",
                line=dict(color=f"rgba({r},{g},{b},0.2)",width=1,dash="dot"),
                row=row,col=1)
        except: pass


# ─────────────────────────────────────────
# 費波那契水平線
# ─────────────────────────────────────────
def _add_fib(fig, start_p, end_p, x_dates, row):
    diff = end_p - start_p
    for ratio, name, alpha in [
        (0.236,"23.6%",0.35),(0.382,"38.2%",0.55),
        (0.500,"50.0%",0.45),(0.618,"61.8%",0.55),
    ]:
        level = end_p - diff * ratio
        fig.add_hline(
            y=level, line_dash="dash",
            line_color=f"rgba(148,163,184,{alpha})", line_width=1,
            annotation_text=f"  Fib {name}  {level:.2f}",
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
    wdecode = decode_wave(wave_label_d)

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

    # ── 波浪序列 ──
    main_seq, sub_seq = _get_wave_sequence(is_bull, wave_label_d)

    # ── 轉折點 ──
    big_order = max(5, len(x_d)//10)
    big_pivots = _find_pivots(H_d, L_d, big_order)

    sub_order  = max(3, len(x_h)//15) if has_60 else 3
    sub_pivots = _find_pivots(H_h, L_h, sub_order) if has_60 else []

    # ── Subplots ──
    rows   = 3 if has_60 else 2
    row_h_ = [0.55, 0.30, 0.15] if has_60 else [0.72, 0.28]

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

    # 日K 波浪連線 + 大浪標注
    _plot_wave_line(fig, big_pivots, x_d, H_d, L_d, row=1,
                    seq_labels=main_seq, font_size=14, arrow_len=50, line_width=2.8)

    # 費波那契（從最大低點到最大高點）
    if len(big_pivots) >= 2:
        lo_p = min(p[1] for p in big_pivots if p[2]=="L") if any(p[2]=="L" for p in big_pivots) else L_d.min()
        hi_p = max(p[1] for p in big_pivots if p[2]=="H") if any(p[2]=="H" for p in big_pivots) else H_d.max()
        _add_fib(fig, lo_p, hi_p, x_d, row=1)

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

        # 60分 子浪連線 + 子浪標注
        _plot_wave_line(fig, sub_pivots, x_h, H_h, L_h, row=2,
                        seq_labels=sub_seq if sub_seq else main_seq,
                        font_size=12, arrow_len=32, line_width=2.0)

        # ▶ NOW
        lh = float(df_h["High"].iloc[-1])
        lc_ = float(df_h["Close"].iloc[-1])
        fig.add_annotation(
            x=x_h[-1], y=lh*1.022,
            text=f"<b>▶ NOW  {lc_:.2f}</b>",
            showarrow=True,arrowhead=2,
            arrowsize=1.3,arrowwidth=2.5,arrowcolor=wcolor,
            ax=0,ay=-45,
            font=dict(size=12,color=wcolor,family="Outfit"),
            bgcolor="rgba(6,11,24,0.92)",
            bordercolor=wcolor,borderwidth=2,borderpad=6,
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

    # ══ 右上角：當前位置（清楚標示大浪.子浪）══
    maj_s = wdecode["major_sym"]
    maj_c = wdecode["major_color"]
    sub_s = wdecode["sub_sym"]
    sub_c = wdecode["sub_color"]

    pos_line = (
        f"<span style='color:{maj_c};font-size:16px'><b>大浪 {maj_s}</b></span>"
        f"  →  "
        f"<span style='color:{sub_c};font-size:16px'><b>子浪 {sub_s}</b></span>"
    )

    fig.add_annotation(
        xref="paper",yref="paper",
        x=0.99,y=0.99,
        text=(f"{wave['emoji']} <b>{wave['label']}</b><br>{pos_line}"),
        showarrow=False,xanchor="right",align="right",
        font=dict(size=13,color=wcolor,family="Outfit"),
        bgcolor="rgba(6,11,24,0.92)",
        bordercolor=wcolor,borderwidth=2,borderpad=10,
    )

    # ══ Layout ══
    title_str=(f"{stock_name}（{code}）  {wave['emoji']} {wave['label']}"
               f"  ｜  大浪 {maj_s} → 子浪 {sub_s}")
    fig.update_layout(
        title=dict(text=title_str,font=dict(size=13,color="#e2e8f0",family="Outfit"),x=0),
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
