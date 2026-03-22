"""
wave_chart.py V10
自動拉長時間軸直到找到合法艾略特結構
盤整偵測：三角收斂 / 箱型整理 / 旗形
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
WAVE_INFO = {
    "3-1":{"color":"#38bdf8","label":"推動浪起漲初段","emoji":"🌱",
     "desc":"KD/MACD/均線研判：目前處於推動浪初升段，力道逐漸累積中",
     "scenarios":[
      {"name":"✅ 主要（65%）突破確認，等②浪回踩加碼","color":"#38bdf8",
       "desc":"①浪完成後②浪回測38.2~61.8%，是加碼機會，之後③浪才是主攻段。","cond":"量能放大，KD金叉，突破前高","risk":"⚠️ 停損設起漲低點"},
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
# 三大鐵律艾略特計數（自動拉長時間軸）
# ─────────────────────────────────────────
def _count_elliott_bull(df_full, is_bull=True):
    """
    嘗試不同時間長度，直到找到符合三大鐵律的結構
    試順序：60 → 90 → 120 → 180 → 250 日
    """
    LBLS   = ["起","①","②","③","④","⑤"]
    COLORS = {"起":"#64748b","①":"#38bdf8","②":"#fb923c",
              "③":"#4ade80","④":"#f97316","⑤":"#fbbf24"}
    BEAR_LBLS   = ["頂","(A)","(B)","(C)"]
    BEAR_COLORS = {"頂":"#64748b","(A)":"#f87171","(B)":"#fb923c","(C)":"#dc2626"}

    lbls   = LBLS   if is_bull else BEAR_LBLS
    colors = COLORS if is_bull else BEAR_COLORS
    s_type = "L"    if is_bull else "H"

    best = None
    best_period = 60

    for period in [60, 90, 120, 180, 250]:
        df_s = df_full.iloc[-period:].copy() if len(df_full) >= period else df_full.copy()
        H = df_s["High"].values.astype(float)
        L = df_s["Low"].values.astype(float)
        n = len(H)

        order = max(4, n // 12)
        pivots = _find_pivots(H, L, order)
        if len(pivots) < 3: continue

        # 嘗試從不同起點計數
        for start_i in range(len(pivots)-1, max(-1, len(pivots)-15), -1):
            if pivots[start_i][2] != s_type: continue
            seq = [pivots[start_i]]
            want = "H" if s_type=="L" else "L"
            for j in range(start_i+1, len(pivots)):
                if pivots[j][2] == want:
                    seq.append(pivots[j])
                    want = "L" if want=="H" else "H"
                if len(seq) >= 6: break

            if len(seq) < 2: continue
            waves = [(seq[i][0], seq[i][1], lbls[i])
                     for i in range(min(len(seq), len(lbls)))]
            viols = []

            if is_bull and len(waves) >= 3:
                w0, w1, w2 = waves[0][1], waves[1][1], waves[2][1]
                if w2 <= w0:
                    viols.append(f"❌ 鐵律1：②低({w2:.2f})≤起點({w0:.2f})")
            if is_bull and len(waves) >= 6:
                w0,w1,w2,w3,w4,w5 = [w[1] for w in waves[:6]]
                len1 = w1-w0; len3 = w3-w2; len5 = w5-w4
                if len3 < len1 and len3 < len5:
                    viols.append(f"❌ 鐵律2：③浪({len3:.2f})是最短驅動浪")
                if w4 <= w1:
                    viols.append(f"❌ 鐵律3：④低({w4:.2f})≤①高({w1:.2f})")

            conf = 50 + len(waves)*6 - len(viols)*25
            conf = max(0, min(100, conf))

            candidate = {
                "waves": waves, "violations": viols,
                "current": waves[-1][2] if waves else "?",
                "confidence": conf, "period": period,
                "df_slice": df_s, "H": H, "L": L,
            }
            if best is None or conf > best["confidence"]:
                best = candidate; best_period = period
            if conf >= 75 and not viols: break

        if best and best["confidence"] >= 75 and not best["violations"]:
            break

    if best is None:
        df_s = df_full.iloc[-90:].copy()
        H = df_s["High"].values.astype(float)
        L = df_s["Low"].values.astype(float)
        return {"waves":[],"violations":["轉折點不足"],"current":"?",
                "confidence":0,"period":90,"df_slice":df_s,"H":H,"L":L}
    return best


# ─────────────────────────────────────────
# 盤整型態偵測
# ─────────────────────────────────────────
def detect_consolidation(df, recent_n=30):
    """
    偵測最近 recent_n 根K棒是否出現盤整型態
    回傳: {"type": str, "support": float, "resistance": float, "desc": str} or None
    """
    if df is None or len(df) < recent_n:
        return None

    seg = df.iloc[-recent_n:].copy()
    H = seg["High"].values.astype(float)
    L = seg["Low"].values.astype(float)
    C = seg["Close"].values.astype(float)

    hi_max = H.max(); lo_min = L.min()
    hi_recent = H[-10:].max(); lo_recent = L[-10:].min()
    rng = hi_max - lo_min
    if rng <= 0: return None
    rng_pct = rng / lo_min * 100

    # 壓縮率（三角收斂）
    first_half_rng = H[:recent_n//2].max() - L[:recent_n//2].min()
    second_half_rng= H[recent_n//2:].max() - L[recent_n//2:].min()
    compression = second_half_rng / first_half_rng if first_half_rng > 0 else 1

    # 箱型判斷：整體振幅 < 8%，且收盤在中段
    if rng_pct < 8:
        mid = (hi_max + lo_min) / 2
        close_in_range = np.sum((C >= lo_min*1.01) & (C <= hi_max*0.99)) / len(C)
        if close_in_range > 0.7:
            return {
                "type": "📦 箱型整理",
                "support": lo_min,
                "resistance": hi_max,
                "desc": f"箱型盤整，振幅 {rng_pct:.1f}%。壓力：{hi_max:.2f}｜支撐：{lo_min:.2f}",
                "color": "#38bdf8",
                "break_up": f"突破 {hi_max:.2f} 帶量→多頭啟動",
                "break_dn": f"跌破 {lo_min:.2f} 帶量→下殺",
            }

    # 三角收斂：後段振幅縮小到前段 60% 以下
    if compression < 0.60:
        return {
            "type": "🔺 三角收斂",
            "support": lo_recent,
            "resistance": hi_recent,
            "desc": f"三角收斂中，後段振幅縮小至前段 {compression*100:.0f}%。等待方向突破。",
            "color": "#fbbf24",
            "break_up": f"帶量突破 {hi_recent:.2f}→多頭",
            "break_dn": f"帶量跌破 {lo_recent:.2f}→空頭",
        }

    # 旗形（急漲或急跌後橫盤）
    pre_seg = df.iloc[-recent_n-15:-recent_n] if len(df) > recent_n+15 else None
    if pre_seg is not None and len(pre_seg) > 5:
        pre_move = (pre_seg["Close"].iloc[-1] - pre_seg["Close"].iloc[0]) / pre_seg["Close"].iloc[0] * 100
        if abs(pre_move) > 8 and rng_pct < 5:
            flag_type = "🚩 多頭旗形" if pre_move > 0 else "🚩 空頭旗形"
            clr = "#4ade80" if pre_move > 0 else "#f87171"
            return {
                "type": flag_type,
                "support": lo_min,
                "resistance": hi_max,
                "desc": f"前段{'急漲' if pre_move>0 else '急跌'} {abs(pre_move):.1f}% 後橫盤整理，旗形完成後延續原方向。",
                "color": clr,
                "break_up": f"帶量突破 {hi_max:.2f}→延續{'上漲' if pre_move>0 else '下跌'}",
                "break_dn": f"跌破 {lo_min:.2f}→型態失效",
            }
    return None


# ─────────────────────────────────────────
# 費波那契水平線
# ─────────────────────────────────────────
def _add_fib_lines(fig, row, lo_p, hi_p):
    diff = hi_p - lo_p
    for ratio, name, alpha in [
        (0.236,"23.6%",0.3),(0.382,"38.2%",0.55),
        (0.500,"50.0%",0.40),(0.618,"61.8%",0.55),
    ]:
        level = hi_p - diff * ratio
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

    # ── 自動選最佳時間長度 ──
    result      = _count_elliott_bull(df, is_bull)
    df_plot     = result["df_slice"]
    H           = result["H"]
    L           = result["L"]
    best_period = result["period"]
    waves       = result["waves"]
    violations  = result["violations"]
    confidence  = result["confidence"]
    current     = result["current"]

    df_plot = df_plot.reset_index()
    if "level_0" in df_plot.columns: df_plot = df_plot.drop(columns=["level_0"])
    dc = "Date" if "Date" in df_plot.columns else df_plot.columns[0]
    x_d = df_plot[dc].astype(str).tolist()

    # 重新對齊 H/L（reset_index 後長度一致）
    H = df_plot["High"].values.astype(float)
    L = df_plot["Low"].values.astype(float)
    C = df_plot["Close"].values.astype(float)

    # ── 盤整偵測 ──
    consol = detect_consolidation(df_plot, recent_n=min(30, len(df_plot)//3))

    # ── Subplots ──
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.02,
    )

    # ── 日K 蠟燭圖 ──
    fig.add_trace(go.Candlestick(
        x=x_d, open=df_plot["Open"], high=df_plot["High"],
        low=df_plot["Low"], close=df_plot["Close"],
        increasing=dict(line=dict(color="#4ade80",width=1),fillcolor="rgba(74,222,128,0.82)"),
        decreasing=dict(line=dict(color="#f87171",width=1),fillcolor="rgba(248,113,113,0.82)"),
        name="K線", showlegend=False,
    ), row=1, col=1)

    # ── 均線 ──
    for ma, mc, mw, show in [
        (5,"#f97316",1,False),(20,"#38bdf8",1.5,True),(60,"#a78bfa",1,False)
    ]:
        cn = f"MA{ma}"
        if cn in df_plot.columns:
            s = df_plot[cn].dropna()
            if len(s):
                fig.add_trace(go.Scatter(
                    x=[x_d[i] for i in s.index], y=s.values,
                    mode="lines", line=dict(color=mc,width=mw),
                    name=f"{ma}MA", showlegend=show, opacity=0.75,
                ), row=1, col=1)

    # ── 波浪折線 ──
    WAVE_COLORS = {
        "起":"#64748b","頂":"#64748b",
        "①":"#38bdf8","②":"#fb923c","③":"#4ade80","④":"#f97316","⑤":"#fbbf24",
        "(A)":"#f87171","(B)":"#fb923c","(C)":"#dc2626",
    }

    if len(waves) >= 2:
        lx = [x_d[w[0]] for w in waves if w[0]<len(x_d)]
        ly = [H[w[0]] if abs(w[1]-H[w[0]])<abs(w[1]-L[w[0]]) else L[w[0]]
              for w in waves if w[0]<len(x_d)]
        fig.add_trace(go.Scatter(
            x=lx, y=ly, mode="lines",
            line=dict(color="#f97316", width=2.8),
            opacity=0.82, showlegend=False, hoverinfo="skip",
        ), row=1, col=1)

    # 動態調整標注位置避免重疊
    used_positions = []  # 記錄已用的 (x_idx, y_range) 避免重疊

    for i, (idx, price, lbl) in enumerate(waves):
        if idx >= len(x_d): continue
        lc   = WAVE_COLORS.get(lbl, "#94a3b8")
        is_hi= abs(price - H[idx]) < abs(price - L[idx])

        # 基礎偏移：高點往上，低點往下
        base_ay = -55 if is_hi else 55

        # 如果鄰近標注位置重疊，交錯偏移
        # 檢查前後2個標注是否 x 位置接近
        ay = base_ay
        nearby = [w for j,w in enumerate(waves) if j!=i and abs(w[0]-idx)<8]
        if nearby:
            # 如果附近有標注，交替左右偏移
            ax_offset = -30 if i % 2 == 0 else 30
        else:
            ax_offset = 0

        price_str = f"{price:.2f}" if price < 1000 else f"{int(price):,}"
        fig.add_annotation(
            x=x_d[idx], y=price,
            text=f"<b>{lbl}</b><br><span style='font-size:10px;font-family:JetBrains Mono'>{price_str}</span>",
            showarrow=True, arrowhead=0,
            arrowwidth=1.5, arrowcolor=lc,
            ax=ax_offset, ay=ay,
            font=dict(size=13, color=lc, family="Outfit"),
            bgcolor="rgba(6,11,24,0.88)",
            bordercolor=lc, borderwidth=1.5, borderpad=5,
            align="center", row=1, col=1,
        )
        fig.add_trace(go.Scatter(
            x=[x_d[idx]], y=[price], mode="markers",
            marker=dict(color=lc, size=8, symbol="circle",
                        line=dict(color="white",width=1)),
            showlegend=False, hoverinfo="skip",
        ), row=1, col=1)

    # ── 當前浪色塊 ──
    if len(waves) >= 2:
        last_idx = waves[-1][0]
        lc = WAVE_COLORS.get(waves[-1][2], "#94a3b8")
        prev_idx = waves[-2][0]
        x0 = x_d[min(prev_idx, len(x_d)-1)]
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

    # ── 盤整框 ──
    if consol:
        ctype = consol["type"]
        csup  = consol["support"]
        cres  = consol["resistance"]
        cc    = consol["color"]
        # 框住最近盤整區間
        x0_c  = x_d[max(0, len(x_d)-30)]
        x1_c  = x_d[-1]
        try:
            r,g,b=int(cc[1:3],16),int(cc[3:5],16),int(cc[5:7],16)
            fig.add_shape(type="rect",x0=x0_c,x1=x1_c,
                y0=csup*0.998,y1=cres*1.002,
                fillcolor=f"rgba({r},{g},{b},0.05)",
                line=dict(color=f"rgba({r},{g},{b},0.45)",width=1.5,dash="dashdot"),
                row=1,col=1)
            # 壓力線
            fig.add_shape(type="line",x0=x0_c,x1=x1_c,y0=cres,y1=cres,
                line=dict(color=f"rgba({r},{g},{b},0.7)",width=1.5,dash="dash"),
                row=1,col=1)
            # 支撐線
            fig.add_shape(type="line",x0=x0_c,x1=x1_c,y0=csup,y1=csup,
                line=dict(color=f"rgba({r},{g},{b},0.7)",width=1.5,dash="dash"),
                row=1,col=1)
        except: pass

        fig.add_annotation(
            x=x_d[max(0,len(x_d)-28)], y=cres*1.003,
            text=f"<b>{ctype}</b>  壓力 {cres:.2f}",
            showarrow=False, xanchor="left",
            font=dict(size=11, color=cc, family="Outfit"),
            bgcolor="rgba(6,11,24,0.8)",
            bordercolor=cc, borderwidth=1, borderpad=4,
            row=1, col=1,
        )
        fig.add_annotation(
            x=x_d[max(0,len(x_d)-28)], y=csup*0.997,
            text=f"支撐 {csup:.2f}  ↑{consol['break_up'][:20]}",
            showarrow=False, xanchor="left",
            font=dict(size=10, color="#64748b", family="Outfit"),
            bgcolor="rgba(6,11,24,0.75)",
            borderpad=3,
            row=1, col=1,
        )

    # ── 費波那契 ──
    if waves:
        lo_p = float(min(p[1] for p in waves if "L" in [p] or True))
        hi_p = float(max(p[1] for p in waves if True))
        lo_p = min([w[1] for w in waves])
        hi_p = max([w[1] for w in waves])
        _add_fib_lines(fig, row=1, lo_p=lo_p, hi_p=hi_p)

    # ── ⑤浪子浪標注（當 main_wave 在⑤浪時，在日K圖上標示子浪） ──
    # ── ⑤浪子浪標注 ──
    try:
        _w_map2 = {w[2]: w[1] for w in waves}
        _w4k = next((w[0] for w in waves if w[2] == "④"), None)
        _w4_price = _w_map2.get("④", 0)
    except:
        _w4k = None; _w4_price = 0

    if current == "⑤" and _w4k is not None and _w4_price > 0 and (len(x_d) - _w4k) >= 6:
        _sH = H[_w4k:]
        _sL = L[_w4k:]
        _n  = len(_sH)

        # 用滑動視窗找轉折：窗口 win 根，找局部高低點
        def _rolling_turns(sh, sl, win=3):
            turns = []
            for i in range(win, len(sh) - win):
                is_hi = (sh[i] == max(sh[i-win:i+win+1]))
                is_lo = (sl[i] == min(sl[i-win:i+win+1]))
                if is_hi and not is_lo:
                    turns.append((i, float(sh[i]), "H"))
                elif is_lo and not is_hi:
                    turns.append((i, float(sl[i]), "L"))
            return turns

        # 嘗試 win=3，不夠就降到 win=2
        _turns = _rolling_turns(_sH, _sL, win=3)
        if len(_turns) < 4:
            _turns = _rolling_turns(_sH, _sL, win=2)

        # 去除相鄰同類型，保留更極端的
        def _clean(turns):
            if not turns: return []
            out = [turns[0]]
            for t in turns[1:]:
                if t[2] == out[-1][2]:
                    if (t[2]=="H" and t[1]>out[-1][1]) or (t[2]=="L" and t[1]<out[-1][1]):
                        out[-1] = t
                else:
                    out.append(t)
            return out

        _turns = _clean(_turns)

        # ⑤浪從低點起：L→H→L→H→L→H
        _seq = []
        _want = "L"
        for _t in _turns:
            if _t[2] == _want:
                _seq.append(_t)
                _want = "H" if _want=="L" else "L"
            if len(_seq) >= 6: break

        if len(_seq) >= 2:
            # 連線
            _sx = [x_d[_w4k + t[0]] for t in _seq if _w4k+t[0]<len(x_d)]
            _sy = [t[1] for t in _seq[:len(_sx)]]
            fig.add_trace(go.Scatter(
                x=_sx, y=_sy, mode="lines",
                line=dict(color="rgba(148,163,184,0.35)", width=1.5, dash="dot"),
                showlegend=False, hoverinfo="skip",
            ), row=1, col=1)

        _SDEF = [("⑤起","#64748b"),("5-1","#7dd3fc"),("5-2","#fed7aa"),
                 ("5-3","#86efac"),("5-4","#fdba74"),("5-5","#fde68a")]

        for _si, (_ri, _sp, _st) in enumerate(_seq[:6]):
            _ki = _w4k + _ri
            if _ki >= len(x_d): continue
            _lbl, _clr = _SDEF[_si]
            _ishi = (_st == "H")
            _ay2  = H[_ki] if _ishi else L[_ki]
            _off  = -42 if _ishi else 42
            fig.add_annotation(
                x=x_d[_ki], y=_ay2, text=f"<b>{_lbl}</b>",
                showarrow=True, arrowhead=0, arrowwidth=1.5,
                arrowcolor=_clr, ax=0, ay=_off,
                font=dict(size=11, color=_clr, family="Outfit"),
                bgcolor="rgba(6,11,24,0.88)",
                bordercolor=_clr, borderwidth=1.5, borderpad=4,
                row=1, col=1,
            )
            fig.add_trace(go.Scatter(
                x=[x_d[_ki]], y=[_ay2], mode="markers",
                marker=dict(color=_clr, size=7, symbol="circle",
                            line=dict(color="white", width=1.5)),
                showlegend=False, hoverinfo="skip",
            ), row=1, col=1)

        # ── ▶ NOW ──
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
          for c,o in zip(df_plot["Close"],df_plot["Open"])]
    fig.add_trace(go.Bar(
        x=x_d, y=df_plot["Volume"], marker_color=vc,
        name="成交量", showlegend=False,
    ), row=2, col=1)
    if "VOL_MA5" in df_plot.columns:
        vm = df_plot["VOL_MA5"].dropna()
        if len(vm):
            fig.add_trace(go.Scatter(
                x=[x_d[i] for i in vm.index], y=vm.values,
                mode="lines", line=dict(color="#fbbf24",width=1.2),
                name="量5MA", showlegend=False,
            ), row=2, col=1)

    # ── 右上角資訊框：波浪計數 + 目標價預估 ──
    conf_color = "#4ade80" if confidence>=70 else "#fbbf24" if confidence>=50 else "#f87171"

    # 計算費波那契目標價預估文字
    target_hint = ""
    w_map = {w[2]: w[1] for w in waves}
    w0 = w_map.get("起", 0); w1 = w_map.get("①", 0)
    w2 = w_map.get("②", 0); w3 = w_map.get("③", 0)
    w4 = w_map.get("④", 0)
    len1 = (w1 - w0) if w1 > w0 else 0
    len3 = (w3 - w2) if w3 > w2 else 0
    cp = float(C[-1]) if len(C) > 0 else 0

    if current == "④" and len1 > 0 and w4 > 0:
        t_eq  = w4 + len1
        t_618 = w4 + len1 * 0.618
        t_1618= w4 + len1 * 1.618
        target_hint = (f"<br><span style='font-size:10px;color:#fbbf24'>"
                       f"⑤浪目標：{t_618:.1f} / <b>{t_eq:.1f}</b> / {t_1618:.1f}</span>")
    elif current == "③" and len1 > 0 and w2 > 0:
        t3 = w2 + len1 * 1.618
        t3b= w2 + len1 * 2.618
        target_hint = (f"<br><span style='font-size:10px;color:#4ade80'>"
                       f"③延伸目標：<b>{t3:.1f}</b> / {t3b:.1f}</span>")
    elif current == "⑤" and len1 > 0 and w4 > 0:
        t5 = w4 + len1
        t5b= w4 + len1 * 1.618
        target_hint = (f"<br><span style='font-size:10px;color:#f97316'>"
                       f"⑤浪目標：{t5:.1f}（延伸{t5b:.1f}）</span>")
    elif current == "②" and len1 > 0 and w1 > 0:
        s382 = w1 - len1 * 0.382
        s618 = w1 - len1 * 0.618
        target_hint = (f"<br><span style='font-size:10px;color:#fb923c'>"
                       f"②支撐：38.2%={s382:.1f} / 61.8%={s618:.1f}</span>")

    consol_line = ""
    if consol:
        consol_line = f"<br><span style='color:{consol['color']};font-size:10px'>{consol['type']}  突破 {consol['resistance']:.2f}</span>"
    vio_line = ""
    if violations:
        vio_line = f"<br><span style='color:#fbbf24;font-size:10px'>⚠️ {violations[0][:30]}</span>"

    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.99, y=0.99,
        text=(
            f"<b>{wave['emoji']} 波浪計數：{current}</b><br>"
            f"<span style='font-size:11px;color:#94a3b8'>KD/MACD：{wave['label']}</span><br>"
            f"<span style='font-size:10px;color:{conf_color}'>信心度 {confidence}%  採用 {best_period} 日</span>"
            f"{target_hint}{vio_line}{consol_line}"
        ),
        showarrow=False, xanchor="right", align="right",
        font=dict(size=12, color=wcolor, family="Outfit"),
        bgcolor="rgba(6,11,24,0.92)",
        bordercolor=wcolor, borderwidth=2, borderpad=10,
    )

    # ── 鐵律警示 ──
    for i, v in enumerate(violations[:2]):
        fig.add_annotation(
            xref="paper", yref="paper",
            x=0.01, y=0.28-i*0.05,
            text=f"<span style='color:#fbbf24'>{v}</span>",
            showarrow=False, xanchor="left",
            font=dict(size=9, color="#fbbf24", family="Outfit"),
            bgcolor="rgba(6,11,24,0.75)",
            bordercolor="#fbbf24", borderwidth=1, borderpad=4,
        )

    # ── Layout ──
    title_str = (
        f"{stock_name}（{code}）  {wave['emoji']} {wave['label']}"
        f"  ｜  計數：{current}  ｜  採用{best_period}日"
    )
    if consol:
        title_str += f"  ｜  {consol['type']}"

    fig.update_layout(
        title=dict(text=title_str, font=dict(size=12,color="#e2e8f0",family="Outfit"),x=0),
        paper_bgcolor="rgba(6,11,24,0)", plot_bgcolor="rgba(6,11,24,0)",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h",x=0,y=1.04,
                    font=dict(size=10,color="#64748b"),bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0,r=0,t=52,b=0),
        height=640, font=dict(family="Outfit"), hovermode="x unified",
    )
    ax = dict(gridcolor="rgba(255,255,255,0.05)",showgrid=True,zeroline=False,
              color="#475569",tickfont=dict(size=10,family="JetBrains Mono"))
    fig.update_layout(xaxis=ax.copy(),xaxis2=ax.copy(),yaxis=ax.copy(),yaxis2=ax.copy())
    return fig


# ═══════════════════════════════════════════════════════
# 波浪目標價計算引擎（黃金比例 + 費波那契擴展）
# ═══════════════════════════════════════════════════════

def calc_wave_targets(result: dict, current_price: float,
                      user_target: float = 0) -> dict:
    """
    根據已計數的波浪結構，計算每個劇本的目標價
    
    result: wave_engine 或 _count_elliott_bull 的回傳
    current_price: 現在收盤價
    user_target: 用戶設定的目標價（0=未設定）
    
    回傳:
    {
        "wave_label": str,         # 當前浪位
        "scenarios": [...],        # 各劇本目標
        "vs_user_target": {...},   # 與用戶目標比較（若有設定）
        "key_levels": {...},       # 關鍵支撐壓力
    }
    """
    waves  = result.get("waves", [])
    current = result.get("current", "?")

    if len(waves) < 2:
        return {"wave_label": current, "scenarios": [], "vs_user_target": {}, "key_levels": {}}

    # ── 從已計數的波浪提取關鍵價位 ──
    # 格式：[(idx, price, label), ...]
    w_prices = {w[2]: w[1] for w in waves}

    # 找起點（①浪起點）
    w0 = w_prices.get("起", w_prices.get("頂", current_price * 0.7))
    # ①浪高點、②浪低點等
    w1 = w_prices.get("①", 0)
    w2 = w_prices.get("②", 0)
    w3 = w_prices.get("③", 0)
    w4 = w_prices.get("④", 0)
    w5 = w_prices.get("⑤", 0)

    # ── 計算各浪長度 ──
    len1 = (w1 - w0) if w1 > w0 else 0
    len3 = (w3 - w2) if w3 > w2 else 0

    scenarios = []

    # ═══════════════════════
    # 依據當前浪位計算目標
    # ═══════════════════════

    if current in ("①", "起"):
        # 在①浪 → 預測②浪修正位 + ③浪目標
        if len1 > 0 and w1 > 0:
            s2_382 = w1 - len1 * 0.382
            s2_618 = w1 - len1 * 0.618
            s3_target_1618 = w2 + len1 * 1.618 if w2 > 0 else w1 + len1 * 1.618
            s3_target_2618 = w2 + len1 * 2.618 if w2 > 0 else w1 + len1 * 2.618

            scenarios = [
                {
                    "name": "📈 ②浪回測後進場（保守）",
                    "prob": 65, "color": "#38bdf8",
                    "target": s3_target_1618,
                    "entry": s2_618,
                    "stop":  w0 * 0.99,
                    "basis": f"①浪漲幅 {len1:.2f}，③浪目標 = ②浪低點 + 1.618 倍",
                    "desc": f"等②浪回測至 {s2_618:.2f}~{s2_382:.2f} 加碼，③浪目標 {s3_target_1618:.2f}",
                },
                {
                    "name": "🚀 強勢③浪直攻（激進）",
                    "prob": 25, "color": "#4ade80",
                    "target": s3_target_2618,
                    "entry": current_price,
                    "stop":  w0 * 0.99,
                    "basis": "③浪 = ①浪 × 2.618 倍（強勢推動浪）",
                    "desc": f"③浪強力延伸目標 {s3_target_2618:.2f}，需搭配爆量確認",
                },
            ]

    elif current in ("②",):
        # 在②浪修正 → 預測②浪底部 + ③浪目標
        if len1 > 0 and w1 > 0:
            bottom_382 = w1 - len1 * 0.382
            bottom_618 = w1 - len1 * 0.618
            s3_from_382 = bottom_382 + len1 * 1.618
            s3_from_618 = bottom_618 + len1 * 1.618

            scenarios = [
                {
                    "name": "📊 ②浪38.2%支撐反彈",
                    "prob": 45, "color": "#fbbf24",
                    "target": s3_from_382,
                    "entry": bottom_382,
                    "stop":  bottom_618 * 0.99,
                    "basis": "②浪回測38.2%費波支撐後啟動③浪",
                    "desc": f"②浪支撐 {bottom_382:.2f}，③浪目標 {s3_from_382:.2f}",
                },
                {
                    "name": "🪤 ②浪61.8%深度修正",
                    "prob": 40, "color": "#a78bfa",
                    "target": s3_from_618,
                    "entry": bottom_618,
                    "stop":  w0 * 0.99,
                    "basis": "②浪回測61.8%黃金比例後啟動③浪",
                    "desc": f"②浪支撐 {bottom_618:.2f}，③浪目標 {s3_from_618:.2f}",
                },
                {
                    "name": "❌ ②浪破起漲點，結構失效",
                    "prob": 15, "color": "#f87171",
                    "target": w0 * 0.95,
                    "entry": 0,
                    "stop":  w0 * 0.99,
                    "basis": "②浪跌破起漲點，①浪計數錯誤",
                    "desc": "若跌破起漲點，整個推動浪失效，應出清持股",
                },
            ]

    elif current in ("③",):
        # 在③浪 → 預測③浪目標 + ④浪修正
        if len1 > 0 and w2 > 0:
            t3_1618  = w2 + len1 * 1.618
            t3_2618  = w2 + len1 * 2.618
            t3_4236  = w2 + len1 * 4.236
            correction_382 = 0
            correction_618 = 0

        elif len3 > 0 and w2 > 0:
            t3_1618  = w2 + len3
            t3_2618  = w2 + len3 * 1.618
            t3_4236  = w2 + len3 * 2.618
        else:
            t3_1618 = current_price * 1.20
            t3_2618 = current_price * 1.35
            t3_4236 = current_price * 1.50

        scenarios = [
            {
                "name": "🚀 ③浪主升1.618目標",
                "prob": 50, "color": "#4ade80",
                "target": t3_1618,
                "entry": current_price,
                "stop":  w2 if w2 > 0 else current_price * 0.92,
                "basis": "③浪 = ①浪 × 1.618（最常見擴展比例）",
                "desc": f"③浪第一目標 {t3_1618:.2f}，完成後④浪修正",
            },
            {
                "name": "💥 ③浪延伸2.618目標",
                "prob": 30, "color": "#38bdf8",
                "target": t3_2618,
                "entry": current_price,
                "stop":  w2 if w2 > 0 else current_price * 0.92,
                "basis": "③浪強力延伸至2.618倍（牛市加速）",
                "desc": f"強勢③浪延伸目標 {t3_2618:.2f}，量能需持續放大",
            },
            {
                "name": "⚠️ ③浪提前結束，進④浪修正",
                "prob": 20, "color": "#f97316",
                "target": current_price * 1.05,
                "entry": 0,
                "stop":  w2 if w2 > 0 else current_price * 0.92,
                "basis": "量縮價漲背離，③浪可能提前完成",
                "desc": f"注意量價背離，若出現長上影線可先減碼",
            },
        ]

    elif current in ("④",):
        # 在④浪修正 → 預測④浪底部 + ⑤浪目標
        if len3 > 0 and w3 > 0:
            bottom_382 = w3 - len3 * 0.382
            bottom_618 = w3 - len3 * 0.618

            # ⑤浪通常等於①浪，或①浪的0.618/1.618
            t5_eq1     = bottom_382 + len1 if len1 > 0 else bottom_382 * 1.15
            t5_618     = bottom_382 + len1 * 0.618 if len1 > 0 else bottom_382 * 1.10
            t5_1618    = bottom_382 + len1 * 1.618 if len1 > 0 else bottom_382 * 1.25

            scenarios = [
                {
                    "name": "🎯 ④浪38.2%完成→啟動⑤浪",
                    "prob": 55, "color": "#4ade80",
                    "target": t5_eq1,
                    "entry": bottom_382,
                    "stop":  bottom_618 * 0.99,
                    "basis": "④浪回測38.2%支撐後，⑤浪=①浪等長",
                    "desc": f"買點 {bottom_382:.2f}，⑤浪目標 {t5_eq1:.2f}",
                },
                {
                    "name": "📊 ④浪61.8%深修後⑤浪啟動",
                    "prob": 30, "color": "#fbbf24",
                    "target": t5_eq1,
                    "entry": bottom_618,
                    "stop":  w1 * 1.001 if w1 > 0 else bottom_618 * 0.97,
                    "basis": "④浪更深修正至61.8%，⑤浪同樣等於①浪",
                    "desc": f"買點 {bottom_618:.2f}（靠近①高點），⑤浪目標 {t5_eq1:.2f}",
                },
                {
                    "name": "⑤浪延伸強攻",
                    "prob": 15, "color": "#38bdf8",
                    "target": t5_1618,
                    "entry": bottom_382,
                    "stop":  bottom_618 * 0.99,
                    "basis": "⑤浪延伸=①浪×1.618（少見但爆發力強）",
                    "desc": f"若⑤浪量能爆發，延伸目標 {t5_1618:.2f}",
                },
            ]

    elif current in ("⑤",):
        # 在⑤浪末段 → 預測⑤浪頂部 + ABC修正目標
        wave_start = w4 if w4 > 0 else (w_prices.get("④", current_price * 0.85))
        full_move  = w3 - w0 if (w3 > 0 and w0 > 0) else current_price * 0.3

        t5_done_618  = wave_start + len1 * 0.618 if len1 > 0 else current_price * 1.05
        t5_done_eq1  = wave_start + len1 if len1 > 0 else current_price * 1.10
        t5_done_1618 = wave_start + len1 * 1.618 if len1 > 0 else current_price * 1.20

        # ABC修正：A浪通常跌整個五浪漲幅的38.2~61.8%
        a_wave_382 = current_price * (1 - 0.382 * (full_move / current_price)) if full_move > 0 else current_price * 0.85
        a_wave_618 = current_price * (1 - 0.618 * (full_move / current_price)) if full_move > 0 else current_price * 0.75

        scenarios = [
            {
                "name": "🏔️ ⑤浪完成（0.618目標），ABC修正即將展開",
                "prob": 40, "color": "#fbbf24",
                "target": t5_done_618,
                "entry": 0,  # 不建議此時買
                "stop":  wave_start * 0.99,
                "basis": "⑤浪 = ①浪 × 0.618（衰竭型五浪）",
                "desc": f"⑤浪目標 {t5_done_618:.2f}，完成後(A)浪修正至 {a_wave_382:.2f}~{a_wave_618:.2f}",
            },
            {
                "name": "📊 ⑤浪等長（①浪等長），完成後修正",
                "prob": 35, "color": "#f97316",
                "target": t5_done_eq1,
                "entry": 0,
                "stop":  wave_start * 0.99,
                "basis": "⑤浪 = ①浪等長（最常見）",
                "desc": f"⑤浪目標 {t5_done_eq1:.2f}，此後A浪跌至 {a_wave_382:.2f}",
            },
            {
                "name": "🚀 ⑤浪延伸（1.618倍），超強牛市",
                "prob": 15, "color": "#38bdf8",
                "target": t5_done_1618,
                "entry": current_price,
                "stop":  wave_start * 0.99,
                "basis": "⑤浪延伸 = ①浪 × 1.618（強勢行情才有）",
                "desc": f"法人持續買超才考慮追，目標 {t5_done_1618:.2f}",
            },
            {
                "name": "❌ 失敗⑤浪，急速回落",
                "prob": 10, "color": "#f87171",
                "target": a_wave_618,
                "entry": 0,
                "stop":  wave_start * 0.99,
                "basis": "⑤浪無法突破③浪高點 → 快速轉空",
                "desc": f"若無法過③浪高 {w3:.2f}，直接下殺至 {a_wave_618:.2f}",
            },
        ]

    elif current in ("(A)",):
        # 在A浪 → 預測A浪底部 + B浪反彈
        if w3 > 0 and w0 > 0:
            full = w3 - w0
            a_target_382 = w3 - full * 0.382
            a_target_618 = w3 - full * 0.618
            b_target     = a_target_382 + (w3 - a_target_382) * 0.618

            scenarios = [
                {
                    "name": "📉 (A)浪38.2%修正，(B)浪反彈逃命",
                    "prob": 50, "color": "#f97316",
                    "target": a_target_382,
                    "entry": 0,
                    "stop":  w3 * 1.01,
                    "basis": "(A)浪跌至整個五浪漲幅38.2%支撐",
                    "desc": f"(A)浪目標 {a_target_382:.2f}，之後(B)浪反彈至 {b_target:.2f} 是出場機會",
                },
                {
                    "name": "💥 (A)浪61.8%深跌，更大修正",
                    "prob": 35, "color": "#f87171",
                    "target": a_target_618,
                    "entry": 0,
                    "stop":  w3 * 1.01,
                    "basis": "(A)浪跌至整個五浪漲幅61.8%（較深修正）",
                    "desc": f"深度修正至 {a_target_618:.2f}，(B)浪反彈後還有(C)浪",
                },
            ]

    # ── 與用戶目標價比較 ──
    vs_user = {}
    if user_target > 0 and scenarios:
        best_match = min(scenarios, key=lambda s: abs(s["target"] - user_target))
        diff_pct = (user_target - best_match["target"]) / best_match["target"] * 100
        gap_to_target = (user_target - current_price) / current_price * 100

        if abs(diff_pct) < 5:
            alignment = "✅ 目標價與波浪計算高度吻合！"
            alignment_color = "#4ade80"
        elif abs(diff_pct) < 15:
            alignment = "📊 目標價與波浪計算接近"
            alignment_color = "#fbbf24"
        elif user_target > best_match["target"] * 1.2:
            alignment = "⚠️ 目標價偏高，超過波浪預測"
            alignment_color = "#f87171"
        else:
            alignment = "📉 目標價偏保守，低於波浪預測"
            alignment_color = "#94a3b8"

        vs_user = {
            "user_target":      user_target,
            "wave_target":      best_match["target"],
            "diff_pct":         diff_pct,
            "gap_to_target":    gap_to_target,
            "alignment":        alignment,
            "alignment_color":  alignment_color,
            "best_scenario":    best_match["name"],
            "entry_suggestion": _get_entry_suggestion(
                current_price, user_target, best_match, gap_to_target
            ),
        }

    # ── 關鍵支撐壓力 ──
    key_levels = {}
    if waves:
        prices = [w[1] for w in waves]
        key_levels = {
            "support":    [p for p in prices if p < current_price],
            "resistance": [p for p in prices if p > current_price],
        }

    return {
        "wave_label": current,
        "scenarios":  scenarios,
        "vs_user_target": vs_user,
        "key_levels": key_levels,
    }


def _get_entry_suggestion(current: float, user_target: float,
                          best_scenario: dict, gap_pct: float) -> str:
    """根據目前位置 vs 目標，給出進出場建議"""
    entry = best_scenario.get("entry", 0)
    stop  = best_scenario.get("stop", 0)
    tgt   = best_scenario.get("target", 0)

    if gap_pct <= 0:
        return "🎯 已達目標價！建議分批獲利了結，保留部分待突破確認"

    if gap_pct <= 3:
        return f"🔥 接近目標！差距僅 {gap_pct:.1f}%，建議設好停利單 {user_target:.2f}，準備出場"

    if gap_pct <= 10:
        if stop > 0:
            risk = (current - stop) / current * 100
            reward = gap_pct
            rr = reward / risk if risk > 0 else 0
            return (f"📊 距目標 {gap_pct:.1f}%，波浪支撐 {stop:.2f}，"
                    f"風險報酬 1:{rr:.1f}，{'✅ 建議持有' if rr >= 2 else '⚠️ 報酬偏低'}")
        return f"📊 距目標 {gap_pct:.1f}%，建議繼續持有，留意量能變化"

    if entry > 0 and entry < current:
        return (f"⏳ 距目標 {gap_pct:.1f}%，等回測 {entry:.2f} 再加碼，"
                f"停損 {stop:.2f}")
    if entry > 0 and entry > current:
        return (f"⏳ 距目標 {gap_pct:.1f}%，等突破 {entry:.2f} 再追進，"
                f"停損 {stop:.2f}")

    return f"📈 距目標 {gap_pct:.1f}%，依原計畫持有，停損 {stop:.2f}"


# ═══════════════════════════════════════════════════════
# 費波那契目標價視覺化圖表
# ═══════════════════════════════════════════════════════
def build_target_chart(result: dict, current_price: float,
                       stock_name: str = "", code: str = "",
                       user_target: float = 0) -> "go.Figure | None":
    """
    繪製波浪目標價視覺化：
    - 水平線顯示各費波那契目標
    - 現價位置標記
    - 用戶目標價標記（若有）
    - 機率圓餅 + 目標距離百分比
    """
    if not PLOTLY_OK: return None

    waves   = result.get("waves", [])
    current = result.get("current", "?")
    if len(waves) < 2: return None

    w_map = {w[2]: w[1] for w in waves}
    w0 = w_map.get("起", 0)
    w1 = w_map.get("①", 0)
    w2 = w_map.get("②", 0)
    w3 = w_map.get("③", 0)
    w4 = w_map.get("④", 0)
    len1 = (w1 - w0) if w1 > w0 else 0
    len3 = (w3 - w2) if w3 > w2 else 0

    # ── 計算目標價列表 ──
    targets = []

    if current == "④" and len1 > 0 and w4 > 0:
        targets = [
            {"label": "⑤浪 0.618倍", "price": w4 + len1*0.618, "color": "#94a3b8", "prob": 40, "style": "dash"},
            {"label": "⑤浪 等長①",   "price": w4 + len1,       "color": "#fbbf24", "prob": 35, "style": "solid"},
            {"label": "⑤浪 1.618倍", "price": w4 + len1*1.618, "color": "#4ade80", "prob": 15, "style": "dot"},
            {"label": "④支撐 38.2%", "price": w3 - len3*0.382 if len3>0 else w4, "color": "#fb923c", "prob": 0, "style": "dashdot", "type": "support"},
            {"label": "④支撐 61.8%", "price": w3 - len3*0.618 if len3>0 else w4*0.97, "color": "#f87171", "prob": 0, "style": "dashdot", "type": "support"},
        ]
    elif current == "③" and len1 > 0 and w2 > 0:
        targets = [
            {"label": "③浪 1.0倍",   "price": w2 + len1,       "color": "#94a3b8", "prob": 20, "style": "dash"},
            {"label": "③浪 1.618倍", "price": w2 + len1*1.618, "color": "#4ade80", "prob": 50, "style": "solid"},
            {"label": "③浪 2.618倍", "price": w2 + len1*2.618, "color": "#38bdf8", "prob": 30, "style": "dot"},
            {"label": "②支撐 38.2%", "price": w1 - len1*0.382, "color": "#fb923c", "prob": 0, "style": "dashdot", "type": "support"},
            {"label": "②支撐 61.8%", "price": w1 - len1*0.618, "color": "#f87171", "prob": 0, "style": "dashdot", "type": "support"},
        ]
    elif current == "⑤" and w4 > 0 and len1 > 0:
        targets = [
            {"label": "⑤浪 0.618倍", "price": w4 + len1*0.618, "color": "#94a3b8", "prob": 40, "style": "dash"},
            {"label": "⑤浪 等長①",   "price": w4 + len1,       "color": "#fbbf24", "prob": 35, "style": "solid"},
            {"label": "⑤浪 1.618倍", "price": w4 + len1*1.618, "color": "#4ade80", "prob": 15, "style": "dot"},
        ]
    elif current == "②" and len1 > 0 and w1 > 0:
        targets = [
            {"label": "②支撐 38.2%", "price": w1 - len1*0.382, "color": "#fbbf24", "prob": 45, "style": "solid", "type": "support"},
            {"label": "②支撐 50.0%", "price": w1 - len1*0.500, "color": "#f97316", "prob": 20, "style": "dash",  "type": "support"},
            {"label": "②支撐 61.8%", "price": w1 - len1*0.618, "color": "#f87171", "prob": 35, "style": "dot",   "type": "support"},
            {"label": "③浪 1.618倍後", "price": (w1 - len1*0.382) + len1*1.618, "color": "#4ade80", "prob": 0, "style": "dashdot"},
        ]
    elif current in ("(A)",) and w3 > 0 and w0 > 0:
        full = w3 - w0
        targets = [
            {"label": "(A)浪 23.6%修正", "price": w3 - full*0.236, "color": "#94a3b8", "prob": 15, "style": "dash",    "type": "support"},
            {"label": "(A)浪 38.2%修正", "price": w3 - full*0.382, "color": "#fbbf24", "prob": 50, "style": "solid",   "type": "support"},
            {"label": "(A)浪 61.8%修正", "price": w3 - full*0.618, "color": "#f87171", "prob": 35, "style": "dot",     "type": "support"},
        ]

    if not targets: return None

    # ── 收集所有價格，計算 Y 軸範圍 ──
    all_prices = [t["price"] for t in targets if t["price"] > 0]
    all_prices.append(current_price)
    if user_target > 0: all_prices.append(user_target)
    y_min = min(all_prices) * 0.94
    y_max = max(all_prices) * 1.06

    fig = go.Figure()

    # ── 背景色塊：上漲區 / 下跌區 ──
    up_targets   = [t for t in targets if t["price"] > current_price and t.get("type") != "support"]
    down_targets = [t for t in targets if t["price"] < current_price or t.get("type") == "support"]

    if up_targets:
        fig.add_shape(type="rect", x0=0, x1=1, xref="paper",
            y0=current_price, y1=max(t["price"] for t in up_targets)*1.01,
            fillcolor="rgba(74,222,128,0.04)",
            line=dict(width=0))
    if down_targets and [t for t in down_targets if t["price"] < current_price]:
        fig.add_shape(type="rect", x0=0, x1=1, xref="paper",
            y0=min(t["price"] for t in down_targets if t["price"]>0)*0.99, y1=current_price,
            fillcolor="rgba(239,68,68,0.04)",
            line=dict(width=0))

    # ── 目標線 ──
    dash_map = {"solid": "solid", "dash": "dash", "dot": "dot", "dashdot": "dashdot"}

    for t in targets:
        if t["price"] <= 0: continue
        pct = (t["price"] - current_price) / current_price * 100
        direction = "↑" if pct > 0 else "↓"
        prob_txt  = f"  {t['prob']}%" if t["prob"] > 0 else ""
        lbl = f"<b>{t['label']}</b>　{t['price']:.2f}　{direction}{abs(pct):.1f}%{prob_txt}"

        fig.add_shape(type="line", x0=0, x1=1, xref="paper",
            y0=t["price"], y1=t["price"],
            line=dict(color=t["color"], width=2 if t.get("type")!="support" else 1.2,
                      dash=dash_map.get(t["style"],"solid")))

        fig.add_annotation(
            x=0.02, y=t["price"],
            xref="paper",
            text=lbl,
            showarrow=False, xanchor="left",
            font=dict(size=11, color=t["color"], family="JetBrains Mono"),
            bgcolor="rgba(6,11,24,0.82)",
            bordercolor=t["color"], borderwidth=1, borderpad=4,
        )

    # ── 現價線 ──
    fig.add_shape(type="line", x0=0, x1=1, xref="paper",
        y0=current_price, y1=current_price,
        line=dict(color="#ffffff", width=2.5, dash="solid"))
    fig.add_annotation(
        x=0.98, y=current_price,
        xref="paper",
        text=f"<b>▶ 現價 {current_price:.2f}</b>",
        showarrow=False, xanchor="right",
        font=dict(size=12, color="#ffffff", family="Outfit"),
        bgcolor="rgba(6,11,24,0.9)",
        bordercolor="#ffffff", borderwidth=1.5, borderpad=5,
    )

    # ── 用戶目標價線 ──
    if user_target > 0:
        upct = (user_target - current_price) / current_price * 100
        fig.add_shape(type="line", x0=0, x1=1, xref="paper",
            y0=user_target, y1=user_target,
            line=dict(color="#38bdf8", width=2, dash="solid"))
        fig.add_annotation(
            x=0.5, y=user_target,
            xref="paper",
            text=f"<b>🎯 你的目標 {user_target:.2f}</b>（{upct:+.1f}%）",
            showarrow=False, xanchor="center",
            font=dict(size=11, color="#38bdf8", family="Outfit"),
            bgcolor="rgba(6,11,24,0.88)",
            bordercolor="#38bdf8", borderwidth=2, borderpad=5,
        )

    # ── 距離尺（右側）──
    for t in targets:
        if t["price"] <= 0 or t.get("type") == "support": continue
        pct = (t["price"] - current_price) / current_price * 100
        if pct > 0:
            # 畫從現價到目標的虛線箭頭
            fig.add_annotation(
                x=0.96, y=(t["price"] + current_price) / 2,
                xref="paper",
                text=f"+{pct:.1f}%",
                showarrow=False, xanchor="right",
                font=dict(size=10, color="#64748b"),
            )

    # ── 空圖形佔位（讓 go.Figure 有 y 軸）──
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[y_min, y_max],
        mode="markers", marker=dict(opacity=0),
        showlegend=False, hoverinfo="skip",
    ))

    # ── 文字說明框 ──
    wave_emoji = {"④":"🔴","③":"🚀","⑤":"🏔️","②":"📉","(A)":"💥"}.get(current, "📊")
    title_txt = f"{stock_name}（{code}）  {wave_emoji} 當前浪位：{current}  ｜  費波那契目標價"

    fig.update_layout(
        title=dict(text=title_txt, font=dict(size=12, color="#e2e8f0", family="Outfit"), x=0),
        paper_bgcolor="rgba(6,11,24,0)",
        plot_bgcolor="rgba(6,11,24,0)",
        height=340,
        margin=dict(l=0, r=0, t=44, b=10),
        xaxis=dict(visible=False, range=[0, 1]),
        yaxis=dict(
            range=[y_min, y_max],
            gridcolor="rgba(255,255,255,0.05)",
            color="#475569",
            tickfont=dict(size=10, family="JetBrains Mono"),
            showgrid=True, zeroline=False,
        ),
        showlegend=False,
    )
    return fig
