"""
wave_engine.py — 符合艾略特三大鐵律的波浪計數引擎

三大鐵律（推動浪）：
  1. 第2浪不可跌破第1浪起點
  2. 第3浪不可是最短驅動浪（在1/3/5中最長）
  3. 第4浪低點不可低於第1浪高點

額外規則：
  - B浪通常不超過A浪起點
  - 修正浪通常回測前浪38.2% 或 61.8%
  - 交替原則：2/4浪交替（一個簡單一個複雜）

回傳：
  - 合法的波浪序列
  - 當前所在浪位
  - 驗證結果
"""

import numpy as np
from scipy.signal import argrelextrema


# ──────────────────────────────────────
# 轉折點偵測
# ──────────────────────────────────────
def find_pivots(highs, lows, order):
    if order < 1: order = 1
    n = len(highs)
    if n < order * 2 + 1: return []
    hi_idx = argrelextrema(highs, np.greater_equal, order=order)[0]
    lo_idx = argrelextrema(lows,  np.less_equal,    order=order)[0]
    pivots = [(i, highs[i], "H") for i in hi_idx] + \
             [(i, lows[i],  "L") for i in lo_idx]
    pivots.sort(key=lambda x: x[0])
    # 去重：相鄰同型取極值
    clean = []
    for p in pivots:
        if clean and clean[-1][2] == p[2]:
            if (p[2]=="H" and p[1] >= clean[-1][1]) or \
               (p[2]=="L" and p[1] <= clean[-1][1]):
                clean[-1] = p
        else:
            clean.append(p)
    return clean


# ──────────────────────────────────────
# 推動浪計數（1-2-3-4-5）+ 三大鐵律驗證
# ──────────────────────────────────────
def count_impulse(pivots):
    """
    嘗試從 pivots 中找出符合三大鐵律的 1-2-3-4-5 浪
    pivots: [(index, price, 'H'/'L'), ...]
    回傳: {
        'valid': bool,
        'waves': [(idx, price, label), ...],  # 起點+1+2+3+4+5
        'violations': [str, ...],
        'current_wave': str,  # 最後標到的浪
    }
    """
    # 需要至少 L H L H L H（起點+1+2+3+4+5）= 6個轉折點
    # 從 Low 開始（多頭）
    candidates = _find_impulse_start(pivots, "L")
    if not candidates:
        return {"valid": False, "waves": [], "violations": ["轉折點不足"], "current_wave": "?"}
    return candidates


def _find_impulse_start(pivots, start_type="L"):
    """
    在轉折點序列中找最近的有效五浪結構
    嘗試不同起點，找最靠近末端且合法的序列
    """
    best = None
    # 從後往前嘗試不同起點
    for start_i in range(len(pivots)-1, -1, -1):
        if pivots[start_i][2] != start_type:
            continue
        seq = [pivots[start_i]]  # 起點
        wave_type = "H" if start_type == "L" else "L"
        wave_n = 1

        for j in range(start_i+1, len(pivots)):
            if pivots[j][2] == wave_type:
                seq.append(pivots[j])
                wave_n += 1
                wave_type = "L" if wave_type == "H" else "H"
                if wave_n > 5:
                    break

        if len(seq) < 2:
            continue

        # 有幾個轉折點就驗證幾浪
        result = _validate_impulse(seq, start_type)
        if result["valid"] or len(result["waves"]) >= 3:
            # 取最靠近末端的有效結果
            if best is None or seq[0][0] > best["waves"][0][0]:
                best = result
            if result["valid"]:
                break  # 找到完整合法五浪就停

    if best is None:
        # fallback：不驗證，直接標
        return _no_validate(pivots, start_type)
    return best


def _validate_impulse(seq, start_type="L"):
    """
    驗證序列 seq 是否符合三大鐵律
    seq: [(idx, price, type), ...]  起點 + 後續轉折
    """
    BULL_LBLS = ["起點","①","②","③","④","⑤"]
    BEAR_LBLS = ["頂點","Ⓐ","Ⓑ","Ⓒ"]

    is_bull = (start_type == "L")
    lbls    = BULL_LBLS if is_bull else BEAR_LBLS

    waves   = []
    violations = []

    for i, (idx, price, ptype) in enumerate(seq):
        lbl = lbls[i] if i < len(lbls) else f"({i})"
        waves.append((idx, price, lbl))

    # 需要至少 起點+①+② 才能驗證
    if len(waves) < 3:
        return {"valid": True, "waves": waves, "violations": [],
                "current_wave": waves[-1][2] if waves else "?",
                "complete": False}

    violations = []

    if is_bull and len(waves) >= 3:
        w0_price = waves[0][1]   # 起點（①浪起漲點）
        w1_price = waves[1][1]   # ①浪高點
        w2_price = waves[2][1]   # ②浪低點

        # 鐵律1：②浪不可跌破①浪起點
        if w2_price <= w0_price:
            violations.append(f"❌ 鐵律1違反：②浪低點({w2_price:.2f}) ≤ 起點({w0_price:.2f})")

    if is_bull and len(waves) >= 6:
        w1_len = waves[2][1] - waves[1][1] if len(waves)>2 else 0   # ①浪 = ②低 - 起點... 不對
        # 更正：驅動浪長度
        # 多頭推動浪：①=W1-W0, ③=W3-W2, ⑤=W5-W4
        w0, w1, w2, w3, w4, w5 = [w[1] for w in waves[:6]]
        len1 = w1 - w0   # ①浪漲幅
        len3 = w3 - w2   # ③浪漲幅
        len5 = w5 - w4   # ⑤浪漲幅

        # 鐵律2：③浪不可是最短
        if len3 < len1 and len3 < len5:
            violations.append(f"❌ 鐵律2違反：③浪({len3:.2f}) 是最短驅動浪")

        # 鐵律3：④浪低點不可低於①浪高點
        if w4 <= w1:
            violations.append(f"❌ 鐵律3違反：④浪低點({w4:.2f}) ≤ ①浪高點({w1:.2f})")

    valid = len(violations) == 0
    current = waves[-1][2] if waves else "?"

    return {
        "valid":         valid,
        "waves":         waves,
        "violations":    violations,
        "current_wave":  current,
        "complete":      len(waves) >= 6,
    }


def _no_validate(pivots, start_type="L"):
    """無法找到合法五浪時，退回直接標注"""
    is_bull = (start_type == "L")
    BULL_LBLS = ["起點","①","②","③","④","⑤"]
    BEAR_LBLS = ["頂點","Ⓐ","Ⓑ","Ⓒ"]
    lbls = BULL_LBLS if is_bull else BEAR_LBLS

    waves = []
    i = 0
    for p in pivots[-8:]:
        if i < len(lbls):
            waves.append((p[0], p[1], lbls[i]))
            i += 1

    return {
        "valid": False, "waves": waves,
        "violations": ["⚠️ 資料不足，暫以最近轉折點標示"],
        "current_wave": waves[-1][2] if waves else "?",
        "complete": False,
    }


# ──────────────────────────────────────
# 費波那契回測計算
# ──────────────────────────────────────
def fib_levels(start_price, end_price):
    """計算費波那契回測/擴展位"""
    diff = end_price - start_price
    return {
        "0.236": end_price - diff * 0.236,
        "0.382": end_price - diff * 0.382,
        "0.500": end_price - diff * 0.500,
        "0.618": end_price - diff * 0.618,
        "0.786": end_price - diff * 0.786,
        "1.000": start_price,
        "1.618": start_price - diff * 0.618,
    }


def wave_position_text(result, is_bull=True):
    """生成當前位置的文字描述"""
    if not result["waves"]:
        return "波浪計數不足"

    current = result["current_wave"]
    complete = result.get("complete", False)
    violations = result.get("violations", [])

    if is_bull:
        positions = {
            "起點": "尋找①浪起點中",
            "①": "①浪上升中（起漲初動）",
            "②": "②浪修正中（等待③浪）",
            "③": "③浪主升中（最強波段）",
            "④": "④浪修正中（等待⑤浪）",
            "⑤": "⑤浪末升中（注意反轉）" if not complete else "⑤浪完成，(A)(B)(C)修正即將展開",
        }
    else:
        positions = {
            "頂點": "尋找修正起點中",
            "Ⓐ": "(A)浪下跌中",
            "Ⓑ": "(B)浪反彈中（逃命機會）",
            "Ⓒ": "(C)浪主跌中",
        }

    desc = positions.get(current, f"當前：{current}")
    if violations:
        desc += f"\n⚠️ {violations[0]}"
    return desc
