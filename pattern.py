"""
pattern.py — 技術型態偵測引擎
支援：頭肩頸、雙頂底、三重頂底、三角形、旗形、楔形、矩形、通道、菱形 等 30+ 種
"""
import numpy as np
from scipy.signal import argrelextrema

# ─────────────────────────────────────────────────────
# 基礎工具
# ─────────────────────────────────────────────────────
def _pivots(H, L, order=5):
    H, L = np.array(H, float), np.array(L, float)
    hi = set(argrelextrema(H, np.greater_equal, order=order)[0])
    lo = set(argrelextrema(L, np.less_equal,    order=order)[0])
    pts = []
    for i in sorted(hi | lo):
        t = "H" if i in hi and (i not in lo or H[i]>L[i]) else "L"
        p = H[i] if t=="H" else L[i]
        pts.append((i, p, t))
    # 去除相鄰同類型
    clean = []
    for pt in pts:
        if clean and clean[-1][2]==pt[2]:
            clean[-1] = pt if (pt[2]=="H" and pt[1]>clean[-1][1]) or \
                               (pt[2]=="L" and pt[1]<clean[-1][1]) else clean[-1]
        else:
            clean.append(pt)
    return clean

def _linreg(xs, ys):
    """線性回歸，回傳 (slope, intercept)"""
    n = len(xs)
    if n < 2: return 0, ys[0] if ys else 0
    sx,sy,sxy,sxx = sum(xs),sum(ys),sum(x*y for x,y in zip(xs,ys)),sum(x*x for x in xs)
    denom = n*sxx - sx*sx
    if denom == 0: return 0, sy/n
    s = (n*sxy - sx*sy)/denom
    b = (sy - s*sx)/n
    return s, b

def _pct(a,b): return (b-a)/a*100 if a else 0

# ─────────────────────────────────────────────────────
# 每種型態的偵測函式
# 回傳 None 或 dict(name, emoji, color, desc, reliability, target, stop, keylines)
# ─────────────────────────────────────────────────────

def _head_shoulders(pts, H, L, C, direction="top"):
    """頭肩頂/底"""
    sign = 1 if direction=="top" else -1
    typ  = "H" if direction=="top" else "L"
    cands = [p for p in pts if p[2]==typ]
    if len(cands) < 3: return None
    for i in range(len(cands)-2):
        ls,h,rs = cands[i], cands[i+1], cands[i+2]
        # 頭比兩肩高（頂）或低（底）
        if direction=="top":
            if not (h[1]>ls[1] and h[1]>rs[1]): continue
            if abs(_pct(ls[1],rs[1]))>15: continue  # 兩肩高度相近
        else:
            if not (h[1]<ls[1] and h[1]<rs[1]): continue
            if abs(_pct(ls[1],rs[1]))>15: continue
        # 頸線
        troughs = [p for p in pts if p[2]!=typ and ls[0]<p[0]<rs[0]]
        if len(troughs)<2: continue
        t1,t2 = troughs[0], troughs[-1]
        nk_slope, nk_b = _linreg([t1[0],t2[0]],[t1[1],t2[1]])
        nk = t1[1]  # 頸線價位（近似）
        head_size = abs(h[1]-nk)
        target    = nk - head_size if direction=="top" else nk + head_size
        return dict(
            name="頭肩頂" if direction=="top" else "頭肩底",
            emoji="🏔️" if direction=="top" else "🏔️",
            color="#f87171" if direction=="top" else "#4ade80",
            bias="bearish" if direction=="top" else "bullish",
            desc=f"頸線 {nk:.2f}，頭部 {h[1]:.2f}，突破後目標 {target:.2f}",
            reliability=85,
            target=target, stop=rs[1],
            keylines=[(t1[0],t1[1],t2[0],t2[1],"neckline")],
            pts=[ls,h,rs,t1,t2],
        )
    return None

def _double_top_bottom(pts, C, direction="top"):
    typ = "H" if direction=="top" else "L"
    cands = [p for p in pts if p[2]==typ]
    if len(cands)<2: return None
    for i in range(len(cands)-1):
        a,b = cands[i], cands[i+1]
        if abs(_pct(a[1],b[1]))>4: continue   # 兩頂高度相近（差<4%）
        mid = [p for p in pts if p[2]!=typ and a[0]<p[0]<b[0]]
        if not mid: continue
        valley = mid[0]
        nk = valley[1]
        head = (a[1]+b[1])/2
        target = nk - (head-nk) if direction=="top" else nk + (nk-head)
        return dict(
            name="雙重頂(M頭)" if direction=="top" else "雙重底(W底)",
            emoji="Ⓜ️" if direction=="top" else "Ⓦ",
            color="#f87171" if direction=="top" else "#4ade80",
            bias="bearish" if direction=="top" else "bullish",
            desc=f"兩{'頂' if direction=='top' else '底'}均在 {a[1]:.2f}~{b[1]:.2f}，頸線 {nk:.2f}，目標 {target:.2f}",
            reliability=78,
            target=target, stop=max(a[1],b[1]) if direction=="top" else min(a[1],b[1]),
            keylines=[], pts=[a,b,valley],
        )
    return None

def _triple_top_bottom(pts, C, direction="top"):
    typ = "H" if direction=="top" else "L"
    cands = [p for p in pts if p[2]==typ]
    if len(cands)<3: return None
    for i in range(len(cands)-2):
        a,b,c = cands[i],cands[i+1],cands[i+2]
        spread = max(a[1],b[1],c[1])-min(a[1],b[1],c[1])
        if spread/max(a[1],b[1],c[1]) > 0.05: continue
        mids = [p for p in pts if p[2]!=typ and a[0]<p[0]<c[0]]
        if len(mids)<2: continue
        nk = (mids[0][1]+mids[-1][1])/2
        head = (a[1]+b[1]+c[1])/3
        target = nk-(head-nk) if direction=="top" else nk+(nk-head)
        return dict(
            name="三重頂" if direction=="top" else "三重底",
            emoji="🔱" if direction=="top" else "🔱",
            color="#f87171" if direction=="top" else "#4ade80",
            bias="bearish" if direction=="top" else "bullish",
            desc=f"三{'頂' if direction=='top' else '底'}均在 {min(a[1],b[1],c[1]):.2f}~{max(a[1],b[1],c[1]):.2f}，目標 {target:.2f}",
            reliability=75, target=target,
            stop=max(a[1],b[1],c[1]) if direction=="top" else min(a[1],b[1],c[1]),
            keylines=[], pts=[a,b,c],
        )
    return None

def _triangle(H, L, C, pts, n=60):
    """對稱/上升/下降/擴散三角形 + 收斂三角形"""
    H2,L2 = np.array(H[-n:],float), np.array(L[-n:],float)
    xs = list(range(len(H2)))
    hi_idx = [p[0]-len(H)-n for p in pts if p[2]=="H" and p[0]>=len(H)-n][-5:]
    lo_idx = [p[0]-len(H)-n for p in pts if p[2]=="L" and p[0]>=len(H)-n][-5:]
    if len(hi_idx)<2 or len(lo_idx)<2: return None

    hs = _linreg(hi_idx, [H2[i] for i in hi_idx if 0<=i<len(H2)])
    ls = _linreg(lo_idx, [L2[i] for i in lo_idx if 0<=i<len(L2)])
    hs_s, hs_b = hs; ls_s, ls_b = ls

    cp = float(C[-1])
    upper_now = hs_s*(len(H2)-1) + hs_b
    lower_now = ls_s*(len(H2)-1) + ls_b
    width = upper_now - lower_now
    if width <= 0: return None

    # 分類
    if abs(hs_s)<0.05 and ls_s>0.05:
        name,emoji,bias,rel = "上升三角形","📐","bullish",72
        desc = f"上邊水平壓力 {upper_now:.2f}，下邊上升支撐，突破後看漲"
        target = upper_now + width
    elif hs_s<-0.05 and abs(ls_s)<0.05:
        name,emoji,bias,rel = "下降三角形","📐","bearish",72
        desc = f"下邊水平支撐 {lower_now:.2f}，上邊下降壓力，跌破後看跌"
        target = lower_now - width
    elif hs_s<-0.05 and ls_s>0.05:
        name,emoji,bias,rel = "對稱三角形（收斂）","🔺","neutral",65
        desc = f"上下同步收斂，壓力 {upper_now:.2f} 支撐 {lower_now:.2f}，突破方向決定走勢"
        target = upper_now + width if cp > (upper_now+lower_now)/2 else lower_now - width
    elif hs_s>0.05 and ls_s<-0.05:
        name,emoji,bias,rel = "擴散三角形","📐","neutral",55
        desc = f"上下同步擴散，波動加大，不確定性高"
        target = cp * 1.05
    else:
        return None

    return dict(name=name, emoji=emoji, color="#4ade80" if bias=="bullish" else "#f87171" if bias=="bearish" else "#fbbf24",
                bias=bias, desc=desc, reliability=rel, target=target,
                stop=lower_now if bias!="bearish" else upper_now,
                keylines=[(hi_idx[0]+len(H)-n, hs_b+hs_s*hi_idx[0],
                            hi_idx[-1]+len(H)-n, hs_b+hs_s*hi_idx[-1], "upper"),
                           (lo_idx[0]+len(H)-n, ls_b+ls_s*lo_idx[0],
                            lo_idx[-1]+len(H)-n, ls_b+ls_s*lo_idx[-1], "lower")],
                pts=[])

def _channel(H, L, C, n=40):
    """看漲/看跌通道"""
    H2,L2 = np.array(H[-n:],float), np.array(L[-n:],float)
    xs = list(range(len(H2)))
    sh,bh = _linreg(xs, list(H2))
    sl,bl = _linreg(xs, list(L2))
    cp = float(C[-1])
    channel_w = (bh - bl + (sh-sl)*(len(H2)-1)) / 2
    if channel_w <= 0: return None
    # 兩線平行且斜率方向一致
    if abs(sh-sl) > 0.3: return None  # 不夠平行

    if sh > 0.1 and sl > 0.1:
        name,emoji,bias = "看漲通道","📈","bullish"
        desc = f"上軌 {H2[-1]:.2f}，下軌 {L2[-1]:.2f}，回踩下軌是買點"
        target = float(H2[-1]) + channel_w
    elif sh < -0.1 and sl < -0.1:
        name,emoji,bias = "看跌通道","📉","bearish"
        desc = f"上軌 {H2[-1]:.2f}，下軌 {L2[-1]:.2f}，反彈上軌是賣點"
        target = float(L2[-1]) - channel_w
    else:
        return None

    return dict(name=name, emoji=emoji,
                color="#4ade80" if bias=="bullish" else "#f87171",
                bias=bias, desc=desc, reliability=68, target=target,
                stop=float(L2[-1]) if bias=="bullish" else float(H2[-1]),
                keylines=[], pts=[])

def _flag_pennant(H, L, C, pts, n=30, mast_n=15):
    """旗形/三角旗形"""
    # 檢查旗桿：前 mast_n 根的大幅移動
    if len(C) < n+mast_n: return None
    mast_move = _pct(C[-n-mast_n], C[-n])
    if abs(mast_move) < 8: return None  # 旗桿需要 8%+ 移動

    flag_H = np.array(H[-n:], float)
    flag_L = np.array(L[-n:], float)
    xs = list(range(n))
    sh,bh = _linreg(xs, list(flag_H))
    sl,bl = _linreg(xs, list(flag_L))

    cp = float(C[-1])
    mast_size = abs(C[-n] - C[-n-mast_n])

    if mast_move > 0:  # 上升旗桿
        if sh < -0.05 and sl < -0.05 and abs(sh-sl)<0.3:
            name,emoji,bias = "看漲旗形","🚩","bullish"
            desc = f"上升旗桿後整理，突破旗形上軌目標 {cp+mast_size:.2f}"
            target = cp + mast_size
        elif sh < -0.05 and sl > 0.05:
            name,emoji,bias = "看漲三角旗","🚩","bullish"
            desc = f"上升旗桿後收斂，突破後目標 {cp+mast_size:.2f}"
            target = cp + mast_size
        elif abs(sh)<0.05 and abs(sl)<0.05:
            name,emoji,bias = "看漲矩形","▬","bullish"
            desc = f"橫向整理區間 {float(flag_L.min()):.2f}~{float(flag_H.max()):.2f}，突破後目標 {cp+mast_size:.2f}"
            target = cp + mast_size
        else: return None
    else:  # 下降旗桿
        if sh > 0.05 and sl > 0.05 and abs(sh-sl)<0.3:
            name,emoji,bias = "看跌旗形","🏴","bearish"
            desc = f"下降旗桿後反彈整理，跌破旗形下軌目標 {cp-mast_size:.2f}"
            target = cp - mast_size
        elif sh > 0.05 and sl < -0.05:
            name,emoji,bias = "看跌三角旗","🏴","bearish"
            desc = f"下降旗桿後收斂，跌破後目標 {cp-mast_size:.2f}"
            target = cp - mast_size
        elif abs(sh)<0.05 and abs(sl)<0.05:
            name,emoji,bias = "看跌矩形","▬","bearish"
            desc = f"橫向整理後繼續下跌，目標 {cp-mast_size:.2f}"
            target = cp - mast_size
        else: return None

    color = "#4ade80" if bias=="bullish" else "#f87171"
    return dict(name=name, emoji=emoji, color=color, bias=bias, desc=desc,
                reliability=70, target=target,
                stop=float(flag_L.min()) if bias=="bullish" else float(flag_H.max()),
                keylines=[], pts=[])

def _wedge(H, L, C, pts, n=40):
    """楔形（看漲/看跌）"""
    H2,L2 = np.array(H[-n:],float), np.array(L[-n:],float)
    xs = list(range(n))
    sh,bh = _linreg(xs, list(H2)); sl,bl = _linreg(xs, list(L2))
    # 楔形：兩線同向但斜率不同（收斂）
    if sh*sl <= 0: return None  # 方向不同不是楔形
    if abs(sh-sl) < 0.05: return None  # 幾乎平行，不收斂

    cp = float(C[-1])
    h_now = bh + sh*(n-1); l_now = bl + sl*(n-1)
    width = abs(h_now - l_now)

    if sh > 0 and sl > 0:  # 兩線都上升
        if sh > sl:  # 上線斜率大，收斂在上
            name,emoji,bias = "看跌楔形（上升楔）","⚠️","bearish"
            desc = f"上升楔形，上邊 {h_now:.2f} 下邊 {l_now:.2f}，跌破下邊後看跌，目標 {l_now-width:.2f}"
            target = l_now - width
        else:
            name,emoji,bias = "看漲楔形（上升楔）","✅","bullish"
            desc = f"收斂上升，突破上邊後繼續看漲，目標 {h_now+width:.2f}"
            target = h_now + width
    else:  # 兩線都下降
        if abs(sh) > abs(sl):  # 上線下降快，收斂在下
            name,emoji,bias = "看漲楔形（下降楔）","✅","bullish"
            desc = f"下降楔形，即將突破，目標 {h_now+width:.2f}"
            target = h_now + width
        else:
            name,emoji,bias = "看跌楔形（下降楔）","⚠️","bearish"
            desc = f"繼續下跌，跌破下邊目標 {l_now-width:.2f}"
            target = l_now - width

    color = "#4ade80" if bias=="bullish" else "#f87171"
    return dict(name=name, emoji=emoji, color=color, bias=bias, desc=desc,
                reliability=66, target=target,
                stop=h_now if bias=="bullish" else l_now,
                keylines=[], pts=[])

def _diamond(pts, H, L):
    """菱形頂/底（頭肩擴張後收斂）"""
    his = [p for p in pts if p[2]=="H"][-6:]
    los = [p for p in pts if p[2]=="L"][-6:]
    if len(his)<4 or len(los)<4: return None
    # 前半擴張，後半收斂
    hi_spread_first = abs(his[1][1]-his[0][1])
    hi_spread_last  = abs(his[-1][1]-his[-2][1])
    if hi_spread_last >= hi_spread_first: return None  # 要收斂
    nk = (his[-1][1]+los[-1][1])/2
    return dict(
        name="菱形(鑽石頂)", emoji="💎", color="#f87171", bias="bearish",
        desc=f"先擴張後收斂，頸線 {nk:.2f}，跌破後目標 {nk-(his[0][1]-nk):.2f}",
        reliability=60, target=nk-(his[0][1]-nk), stop=his[-1][1],
        keylines=[], pts=his[:2]+los[:2],
    )

def _rectangle(H, L, C, n=30):
    """矩形整理"""
    H2,L2 = np.array(H[-n:],float), np.array(L[-n:],float)
    top = float(H2.max()); bot = float(L2.min())
    rng = top - bot
    if rng/float(C[-1]) > 0.2: return None  # 區間太大
    cp = float(C[-1])
    # 判斷突破方向（用最後 5 根）
    trend = np.polyfit(range(5), list(C[-5:]), 1)[0]
    bias = "bullish" if trend > 0 else "bearish"
    target = top + rng if bias=="bullish" else bot - rng
    return dict(
        name="矩形整理", emoji="▬", color="#fbbf24", bias=bias,
        desc=f"整理區間 {bot:.2f}~{top:.2f}，突破{'上軌' if bias=='bullish' else '下軌'}目標 {target:.2f}",
        reliability=65, target=target,
        stop=bot if bias=="bullish" else top,
        keylines=[], pts=[],
    )

# ─────────────────────────────────────────────────────
# 主偵測函式
# ─────────────────────────────────────────────────────
def detect_patterns(df) -> list:
    """
    輸入 DataFrame（含 Open/High/Low/Close），回傳偵測到的型態列表
    每個型態：dict(name, emoji, color, bias, desc, reliability, target, stop)
    """
    H = df["High"].values.astype(float)
    L = df["Low"].values.astype(float)
    C = df["Close"].values.astype(float)

    order = max(3, len(H)//20)
    pts = _pivots(H, L, order)

    results = []
    candidates = [
        # 反轉型態
        lambda: _head_shoulders(pts, H, L, C, "top"),
        lambda: _head_shoulders(pts, H, L, C, "bottom"),
        lambda: _double_top_bottom(pts, C, "top"),
        lambda: _double_top_bottom(pts, C, "bottom"),
        lambda: _triple_top_bottom(pts, C, "top"),
        lambda: _triple_top_bottom(pts, C, "bottom"),
        lambda: _diamond(pts, H, L),
        # 持續型態
        lambda: _triangle(H, L, C, pts, n=min(60,len(H))),
        lambda: _channel(H, L, C, n=min(40,len(H))),
        lambda: _flag_pennant(H, L, C, pts, n=min(20,len(H)), mast_n=min(10,len(H)//3)),
        lambda: _wedge(H, L, C, pts, n=min(40,len(H))),
        lambda: _rectangle(H, L, C, n=min(30,len(H))),
    ]

    for fn in candidates:
        try:
            r = fn()
            if r: results.append(r)
        except: pass

    # 按信心度排序，最多回傳 3 個
    results.sort(key=lambda x: x["reliability"], reverse=True)
    return results[:3]


# ─────────────────────────────────────────────────────
# 圖表版：直接接受 numpy 陣列 + x_d (日期/時間序列)
# ─────────────────────────────────────────────────────
def detect_patterns_for_chart(H, L, C, x_d) -> list:
    """
    給 wave_chart.py 用，接受原始 H/L/C 陣列
    回傳 dict 含 keylines(用 index)、pts(用 index)、target、stop
    """
    import pandas as pd
    n = len(H)
    if n < 20: return []

    # 建立 df
    df_tmp = pd.DataFrame({"High":H,"Low":L,"Close":C})
    
    order = max(3, n//20)
    pts = _pivots(H, L, order)

    results = []
    
    # === 頭肩頂/底 ===
    for direction in ["top","bottom"]:
        typ  = "H" if direction=="top" else "L"
        cands = [p for p in pts if p[2]==typ]
        if len(cands)<3: continue
        for i in range(len(cands)-2):
            ls,h,rs = cands[i],cands[i+1],cands[i+2]
            if direction=="top":
                if not (h[1]>ls[1] and h[1]>rs[1]): continue
                if abs(_pct(ls[1],rs[1]))>18: continue
            else:
                if not (h[1]<ls[1] and h[1]<rs[1]): continue
                if abs(_pct(ls[1],rs[1]))>18: continue
            troughs=[p for p in pts if p[2]!=typ and ls[0]<p[0]<rs[0]]
            if len(troughs)<2: continue
            t1,t2=troughs[0],troughs[-1]
            nk = (t1[1]+t2[1])/2
            head_size=abs(h[1]-nk)
            target=nk-head_size if direction=="top" else nk+head_size
            results.append(dict(
                name="頭肩頂" if direction=="top" else "頭肩底",
                emoji="🏔️", bias="bearish" if direction=="top" else "bullish",
                color="#f87171" if direction=="top" else "#4ade80",
                desc=f"頸線 {nk:.2f}，目標 {target:.2f}",
                reliability=85, target=target, stop=rs[1],
                keylines=[(t1[0],t1[1],t2[0],t2[1],"neckline")],
                pts=[(ls[0],ls[1]),(h[0],h[1]),(rs[0],rs[1])],
            ))
            break

    # === 雙頂/雙底 ===
    for direction in ["top","bottom"]:
        typ="H" if direction=="top" else "L"
        cands=[p for p in pts if p[2]==typ]
        if len(cands)<2: continue
        for i in range(len(cands)-1):
            a,b=cands[i],cands[i+1]
            if abs(_pct(a[1],b[1]))>5: continue
            mid=[p for p in pts if p[2]!=typ and a[0]<p[0]<b[0]]
            if not mid: continue
            valley=mid[0]; nk=valley[1]
            head=(a[1]+b[1])/2
            target=nk-(head-nk) if direction=="top" else nk+(nk-head)
            results.append(dict(
                name="雙重頂(M頭)" if direction=="top" else "雙重底(W底)",
                emoji="Ⓜ️" if direction=="top" else "Ⓦ",
                bias="bearish" if direction=="top" else "bullish",
                color="#f87171" if direction=="top" else "#4ade80",
                desc=f"頸線 {nk:.2f}，目標 {target:.2f}",
                reliability=78, target=target,
                stop=max(a[1],b[1]) if direction=="top" else min(a[1],b[1]),
                keylines=[(valley[0]-5, nk, b[0]+5, nk,"neckline")],
                pts=[(a[0],a[1]),(b[0],b[1]),(valley[0],valley[1])],
            ))
            break

    # === 三角形 ===
    seg_n = min(60, n)
    hi_pts = [p for p in pts if p[2]=="H" and p[0]>=n-seg_n][-5:]
    lo_pts = [p for p in pts if p[2]=="L" and p[0]>=n-seg_n][-5:]
    if len(hi_pts)>=2 and len(lo_pts)>=2:
        hi_xs=[p[0] for p in hi_pts]; hi_ys=[p[1] for p in hi_pts]
        lo_xs=[p[0] for p in lo_pts]; lo_ys=[p[1] for p in lo_pts]
        sh,bh=_linreg(hi_xs,hi_ys); sl,bl=_linreg(lo_xs,lo_ys)
        upper_end=sh*(n-1)+bh; lower_end=sl*(n-1)+bl
        upper_start=sh*hi_xs[0]+bh; lower_start=sl*lo_xs[0]+bl
        width=abs(upper_end-lower_end)
        if width>0:
            if abs(sh)<0.05 and sl>0.05:
                name,bias,color,rel="上升三角形","bullish","#4ade80",72
                target=upper_end+width; desc=f"壓力線 {upper_end:.2f}，突破看漲"
            elif sh<-0.05 and abs(sl)<0.05:
                name,bias,color,rel="下降三角形","bearish","#f87171",72
                target=lower_end-width; desc=f"支撐線 {lower_end:.2f}，跌破看跌"
            elif sh<-0.05 and sl>0.05:
                name,bias,color,rel="對稱三角形(收斂)","neutral","#fbbf24",65
                target=upper_end+width; desc=f"壓力 {upper_end:.2f} 支撐 {lower_end:.2f}"
            elif sh>0.05 and sl<-0.05:
                name,bias,color,rel="擴散三角形","neutral","#a78bfa",55
                target=upper_end; desc=f"波動擴散，不確定性高"
            else:
                name=None
            if name:
                results.append(dict(
                    name=name, emoji="📐", bias=bias, color=color,
                    desc=desc, reliability=rel, target=target,
                    stop=lower_end if bias!="bearish" else upper_end,
                    keylines=[
                        (hi_xs[0],upper_start,n-1,upper_end,"upper"),
                        (lo_xs[0],lower_start,n-1,lower_end,"lower"),
                    ],
                    pts=[],
                ))

    # === 旗形/矩形 ===
    mast_n2=min(15,n//4); flag_n=min(20,n//3)
    if n>mast_n2+flag_n:
        mast_move=_pct(float(C[-(mast_n2+flag_n)]),float(C[-flag_n]))
        if abs(mast_move)>=8:
            fH=H[-flag_n:]; fL=L[-flag_n:]
            xs2=list(range(flag_n))
            sh2,bh2=_linreg(xs2,list(fH)); sl2,bl2=_linreg(xs2,list(fL))
            mast_sz=abs(float(C[-flag_n])-float(C[-(mast_n2+flag_n)]))
            cp2=float(C[-1])
            if mast_move>0 and sh2<-0.03 and sl2<-0.03:
                results.append(dict(name="看漲旗形",emoji="🚩",bias="bullish",
                    color="#4ade80",desc=f"旗桿漲幅{mast_move:.1f}%，整理後目標 {cp2+mast_sz:.2f}",
                    reliability=70,target=cp2+mast_sz,stop=float(min(fL)),
                    keylines=[(n-flag_n,bh2,n-1,bh2+sh2*(flag_n-1),"upper"),
                               (n-flag_n,bl2,n-1,bl2+sl2*(flag_n-1),"lower")],pts=[]))
            elif mast_move<0 and sh2>0.03 and sl2>0.03:
                results.append(dict(name="看跌旗形",emoji="🏴",bias="bearish",
                    color="#f87171",desc=f"旗桿跌幅{abs(mast_move):.1f}%，反彈後目標 {cp2-mast_sz:.2f}",
                    reliability=70,target=cp2-mast_sz,stop=float(max(fH)),
                    keylines=[(n-flag_n,bh2,n-1,bh2+sh2*(flag_n-1),"upper"),
                               (n-flag_n,bl2,n-1,bl2+sl2*(flag_n-1),"lower")],pts=[]))

    results.sort(key=lambda x:x["reliability"], reverse=True)
    return results[:3]
