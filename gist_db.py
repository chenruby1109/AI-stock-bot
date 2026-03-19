"""
gist_db.py — GitHub Gist 當資料庫
取代 users.json / targets.json / watchlist.json
資料永久存在 GitHub Gist，重部署不會消失

需要的 Streamlit Secrets：
  GITHUB_TOKEN = "ghp_xxxx"   # GitHub PAT，需要 gist 權限
  GIST_ID      = ""           # 第一次執行後自動建立並印出，再填回來

Gist 結構（單一私密 Gist，3 個檔案）：
  users.json      — 用戶帳號資料
  targets.json    — 目標價
  watchlist.json  — 觀察名單（含全域名稱表）
"""

import os, json, hashlib, requests
from datetime import datetime

# ── 讀取 secrets ──
try:
    import streamlit as st
    _TOKEN   = st.secrets.get("GITHUB_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
    _GIST_ID = st.secrets.get("GIST_ID",      os.environ.get("GIST_ID", ""))
except Exception:
    _TOKEN   = os.environ.get("GITHUB_TOKEN", "")
    _GIST_ID = os.environ.get("GIST_ID", "")

_API = "https://api.github.com"

def _hdr() -> dict:
    return {"Authorization": f"token {_TOKEN}",
            "Accept": "application/vnd.github.v3+json"}

# ════════════════════════════════════════
# Gist 底層讀寫
# ════════════════════════════════════════

def _get_gist_id() -> str:
    global _GIST_ID
    if _GIST_ID:
        return _GIST_ID
    # 自動建立 Gist（首次）
    empty_files = {
        "users.json":     {"content": "{}"},
        "targets.json":   {"content": "{}"},
        "watchlist.json": {"content": "{}"},
    }
    r = requests.post(f"{_API}/gists", headers=_hdr(), json={
        "description": "AI Stock Bot Database",
        "public":      False,
        "files":       empty_files,
    }, timeout=15)
    r.raise_for_status()
    _GIST_ID = r.json()["id"]
    print(f"\n🎉 Gist 自動建立完成！請把以下行加入 Streamlit Secrets：\n"
          f'   GIST_ID = "{_GIST_ID}"\n')
    return _GIST_ID

def _read_all() -> dict:
    """一次讀取 Gist 全部 3 個 JSON 檔，回傳 dict"""
    r = requests.get(f"{_API}/gists/{_get_gist_id()}", headers=_hdr(), timeout=15)
    r.raise_for_status()
    files = r.json().get("files", {})
    result = {}
    for key in ("users", "targets", "watchlist"):
        fname = f"{key}.json"
        raw   = files.get(fname, {}).get("content", "{}")
        try:    result[key] = json.loads(raw)
        except: result[key] = {}
    return result

def _write(key: str, data: dict):
    """把指定 key 寫回 Gist（patch 只更新該檔案）"""
    body = {"files": {f"{key}.json": {
        "content": json.dumps(data, ensure_ascii=False, indent=2)
    }}}
    r = requests.patch(f"{_API}/gists/{_get_gist_id()}",
                       headers=_hdr(), json=body, timeout=15)
    r.raise_for_status()

def _read(key: str) -> dict:
    return _read_all().get(key, {})

# ════════════════════════════════════════
# 工具函式
# ════════════════════════════════════════

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# ════════════════════════════════════════
# 用戶管理
# ════════════════════════════════════════

def _ensure_admin():
    """確保預設管理員存在（首次啟動自動建立）"""
    users = _read("users")
    if "ruby" not in users:
        users["ruby"] = {
            "password_hash":    _hash("admin1234"),
            "role":             "admin",
            "display_name":     "Ruby（管理員）",
            "telegram_chat_id": "",
            "created_at":       _now(),
        }
        _write("users", users)

def login(username: str, password: str) -> dict | None:
    """登入驗證，成功回傳含 username 的 dict，失敗回傳 None"""
    _ensure_admin()
    users = _read("users")
    uname = username.strip().lower()
    u = users.get(uname)
    if u and u["password_hash"] == _hash(password):
        return {**u, "username": uname}
    return None

def get_all_users() -> dict:
    _ensure_admin()
    return _read("users")

def get_user(username: str) -> dict | None:
    return _read("users").get(username)

def create_user(username: str, password: str,
                display_name: str, role: str = "user") -> tuple[bool, str]:
    uname = username.strip().lower()
    if not uname:          return False, "帳號不可為空"
    if len(password) < 4:  return False, "密碼至少 4 碼"
    users = _read("users")
    if uname in users:     return False, f"帳號 {uname} 已存在"
    users[uname] = {
        "password_hash":    _hash(password),
        "role":             role,
        "display_name":     display_name.strip() or uname,
        "telegram_chat_id": "",
        "created_at":       _now(),
    }
    _write("users", users)
    return True, "建立成功"

def delete_user(username: str) -> tuple[bool, str]:
    users = _read("users")
    if username not in users: return False, "帳號不存在"
    if users[username].get("role") == "admin":
        admin_count = sum(1 for v in users.values() if v.get("role") == "admin")
        if admin_count <= 1: return False, "不能刪除唯一的管理員"
    del users[username]
    _write("users", users)
    return True, "已刪除"

def update_telegram(username: str, chat_id: str) -> bool:
    users = _read("users")
    if username not in users: return False
    users[username]["telegram_chat_id"] = chat_id.strip()
    _write("users", users)
    return True

def change_password(username: str, old_pw: str, new_pw: str) -> tuple[bool, str]:
    users = _read("users")
    if username not in users:                      return False, "帳號不存在"
    if users[username]["password_hash"] != _hash(old_pw): return False, "舊密碼錯誤"
    if len(new_pw) < 4:                            return False, "新密碼至少 4 碼"
    users[username]["password_hash"] = _hash(new_pw)
    _write("users", users)
    return True, "密碼已更新"

def admin_reset_password(username: str, new_pw: str) -> tuple[bool, str]:
    if len(new_pw) < 4: return False, "密碼至少 4 碼"
    users = _read("users")
    if username not in users: return False, "帳號不存在"
    users[username]["password_hash"] = _hash(new_pw)
    _write("users", users)
    return True, "已重設密碼"

# ════════════════════════════════════════
# 個人觀察名單
# ════════════════════════════════════════

def add_to_watchlist(username: str, code: str, name: str = "") -> bool:
    """新增股票到個人名單；同時更新全域名稱表"""
    code = code.upper()
    wl   = _read("watchlist")
    user_list = wl.setdefault(username, [])
    if code in user_list: return False   # 已存在
    user_list.append(code)
    # 更新全域名稱表（key = "__names__"）
    if name:
        wl.setdefault("__names__", {})[code] = name
    _write("watchlist", wl)
    return True

def remove_from_watchlist(username: str, code: str) -> bool:
    wl = _read("watchlist")
    user_list = wl.get(username, [])
    if code in user_list:
        user_list.remove(code)
        wl[username] = user_list
        _write("watchlist", wl)
    return True

def get_user_watchlist_codes(username: str) -> list[str]:
    return _read("watchlist").get(username, [])

def get_user_watchlist(username: str) -> list[dict]:
    """回傳 [{code, name}, ...]"""
    wl    = _read("watchlist")
    codes = wl.get(username, [])
    names = wl.get("__names__", {})
    return [{"code": c, "name": names.get(c, c)} for c in codes]

def get_global_watchlist() -> dict:
    """取得全部用戶不重複的股票 {code: name}，供 cloud_bot 掃描"""
    wl    = _read("watchlist")
    names = wl.get("__names__", {})
    all_codes: set = set()
    for k, v in wl.items():
        if k.startswith("__"): continue
        if isinstance(v, list): all_codes.update(v)
    return {code: names.get(code, code) for code in all_codes}

def get_all_users_with_watchlist() -> list[dict]:
    """cloud_bot 用：取得每位用戶 + 他的觀察股票 + TG ID"""
    users = get_all_users()
    wl    = _read("watchlist")
    names = wl.get("__names__", {})
    result = []
    for uname, uinfo in users.items():
        codes = wl.get(uname, [])
        result.append({
            "username":         uname,
            "display_name":     uinfo.get("display_name", uname),
            "telegram_chat_id": uinfo.get("telegram_chat_id", ""),
            "watchlist":        [{"code": c, "name": names.get(c, c)} for c in codes],
        })
    return result

# ════════════════════════════════════════
# 目標價
# ════════════════════════════════════════

def set_target(username: str, display_name: str,
               code: str, price: float, note: str = "") -> bool:
    targets = _read("targets")
    code    = code.upper()
    now     = _now()
    entries = targets.setdefault(code, [])
    # 找已有的 entry 更新
    for e in entries:
        if e["username"] == username:
            e.update({"target_price": price, "note": note.strip(),
                      "display_name": display_name, "updated_at": now})
            _write("targets", targets)
            return True
    # 新增
    entries.append({
        "username":     username,
        "display_name": display_name,
        "target_price": price,
        "note":         note.strip(),
        "created_at":   now,
        "updated_at":   now,
    })
    _write("targets", targets)
    return True

def get_user_target(username: str, code: str) -> dict | None:
    for e in _read("targets").get(code.upper(), []):
        if e["username"] == username: return e
    return None

def get_user_all_targets(username: str) -> dict:
    """回傳 {code: entry_dict}"""
    result = {}
    for code, entries in _read("targets").items():
        for e in entries:
            if e["username"] == username:
                result[code] = e
    return result

def get_all_targets_admin() -> dict:
    """管理員用：全部目標價 {code: [entries]}"""
    return _read("targets")

def delete_target(username: str, code: str) -> bool:
    targets = _read("targets")
    code    = code.upper()
    if code not in targets: return False
    targets[code] = [e for e in targets[code] if e["username"] != username]
    if not targets[code]: del targets[code]
    _write("targets", targets)
    return True

def check_target_reached(current_price: float, target_price: float) -> dict:
    gap     = target_price - current_price
    gap_pct = gap / current_price * 100
    if current_price >= target_price:
        status = "✅ 已達目標"; desc = f"現價已超過目標 {target_price:.2f}"
    elif gap_pct <= 5:
        status = "🔥 即將達標"; desc = f"距目標僅差 {gap:.2f}（{gap_pct:.1f}%）"
    elif gap_pct <= 15:
        status = "📈 推進中";   desc = f"距目標還差 {gap:.2f}（{gap_pct:.1f}%）"
    else:
        status = "⏳ 長線佈局"; desc = f"距目標 {gap:.2f}（{gap_pct:.1f}%），需耐心等待"
    return {"status": status, "desc": desc, "gap": gap, "gap_pct": gap_pct}
