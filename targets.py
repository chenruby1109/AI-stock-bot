"""
targets.py — 目標價管理模組
targets.json 格式：
{
  "2330": [
    {
      "username":    "user1",
      "display_name":"小明",
      "target_price": 1200.0,
      "note":         "長線目標",
      "created_at":  "2026-03-20 10:00",
      "updated_at":  "2026-03-20 10:00"
    }
  ]
}
"""
import json, os
from datetime import datetime

TARGETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "targets.json")

def _load() -> dict:
    if not os.path.exists(TARGETS_FILE): return {}
    try:
        with open(TARGETS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def _save(data: dict):
    with open(TARGETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ════════════════════════════════════════
# 公開 API
# ════════════════════════════════════════
def set_target(username: str, display_name: str,
               code: str, price: float, note: str = "") -> bool:
    """新增或更新某用戶對某股的目標價"""
    data = _load()
    code = code.strip().upper()
    entries = data.setdefault(code, [])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    # 找已有的 entry
    for e in entries:
        if e["username"] == username:
            e["target_price"] = price
            e["note"]         = note.strip()
            e["display_name"] = display_name
            e["updated_at"]   = now
            _save(data); return True
    # 新增
    entries.append({
        "username":     username,
        "display_name": display_name,
        "target_price": price,
        "note":         note.strip(),
        "created_at":   now,
        "updated_at":   now,
    })
    _save(data); return True

def get_user_target(username: str, code: str) -> dict | None:
    """取得某用戶對某股的目標價"""
    entries = _load().get(code.upper(), [])
    for e in entries:
        if e["username"] == username: return e
    return None

def get_all_targets_for_code(code: str) -> list:
    """（管理員用）取得某股所有人的目標價"""
    return _load().get(code.upper(), [])

def get_all_targets_admin() -> dict:
    """（管理員用）取得全部目標價資料"""
    return _load()

def get_user_all_targets(username: str) -> dict:
    """取得某用戶所有股票的目標價 → {code: entry}"""
    result = {}
    for code, entries in _load().items():
        for e in entries:
            if e["username"] == username:
                result[code] = e
    return result

def delete_target(username: str, code: str) -> bool:
    data = _load(); code = code.upper()
    if code not in data: return False
    data[code] = [e for e in data[code] if e["username"] != username]
    if not data[code]: del data[code]
    _save(data); return True

def check_target_reached(current_price: float, target_price: float) -> dict:
    """分析目標價達成情況"""
    gap = target_price - current_price
    gap_pct = gap / current_price * 100
    if current_price >= target_price:
        status = "✅ 已達目標"
        desc   = f"目前 {current_price:.2f} 已超過目標 {target_price:.2f}"
    elif gap_pct <= 5:
        status = "🔥 即將達標"
        desc   = f"距目標僅差 {gap:.2f}（{gap_pct:.1f}%）"
    elif gap_pct <= 15:
        status = "📈 推進中"
        desc   = f"距目標還差 {gap:.2f}（{gap_pct:.1f}%）"
    else:
        status = "⏳ 長線佈局"
        desc   = f"距目標 {gap:.2f}（{gap_pct:.1f}%），需耐心等待"
    return {"status": status, "desc": desc, "gap": gap, "gap_pct": gap_pct}
