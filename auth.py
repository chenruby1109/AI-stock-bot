"""
auth.py — 用戶認證模組
users.json 格式：
{
  "ruby": {
    "password_hash": "sha256...",
    "role": "admin",           # admin | user
    "display_name": "Ruby",
    "telegram_chat_id": "",
    "created_at": "2026-03-20 10:00",
    "watchlist": ["2330","2454"]   # 個人觀察名單
  }
}
"""

import json, os, hashlib
from datetime import datetime

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")

# ── 預設管理員帳號（首次啟動自動建立）──
DEFAULT_ADMIN = {
    "username":    "ruby",
    "password":    "admin1234",   # 第一次登入後請立即修改
    "display_name":"Ruby（管理員）",
    "role":        "admin",
}

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _load() -> dict:
    if not os.path.exists(USERS_FILE):
        # 第一次啟動：建立預設管理員
        data = {}
        _create_user(data,
                     DEFAULT_ADMIN["username"],
                     DEFAULT_ADMIN["password"],
                     DEFAULT_ADMIN["display_name"],
                     "admin")
        return data
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def _save(data: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _create_user(data: dict, username: str, password: str,
                 display_name: str, role: str = "user"):
    data[username] = {
        "password_hash":   _hash(password),
        "role":            role,
        "display_name":    display_name,
        "telegram_chat_id":"",
        "created_at":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        "watchlist":       [],
    }
    _save(data)

# ════════════════════════════════════════
# 公開 API
# ════════════════════════════════════════
def login(username: str, password: str) -> dict | None:
    """登入，成功回傳 user dict（含 username），失敗回傳 None"""
    data = _load()
    u = data.get(username.strip().lower())
    if u and u["password_hash"] == _hash(password):
        return {**u, "username": username.strip().lower()}
    return None

def get_all_users() -> dict:
    return _load()

def get_user(username: str) -> dict | None:
    return _load().get(username)

def create_user(username: str, password: str,
                display_name: str, role: str = "user") -> tuple[bool, str]:
    data = _load()
    u = username.strip().lower()
    if not u:            return False, "帳號不可為空"
    if len(password) < 4: return False, "密碼至少 4 碼"
    if u in data:        return False, f"帳號 {u} 已存在"
    _create_user(data, u, password, display_name.strip() or u, role)
    return True, "建立成功"

def delete_user(username: str) -> tuple[bool, str]:
    data = _load()
    if username not in data: return False, "帳號不存在"
    if data[username].get("role") == "admin":
        admins = [k for k,v in data.items() if v.get("role")=="admin"]
        if len(admins) <= 1: return False, "不能刪除唯一的管理員"
    del data[username]; _save(data)
    return True, "已刪除"

def update_telegram(username: str, chat_id: str) -> bool:
    data = _load()
    if username not in data: return False
    data[username]["telegram_chat_id"] = chat_id.strip()
    _save(data); return True

def change_password(username: str, old_pw: str, new_pw: str) -> tuple[bool, str]:
    data = _load()
    if username not in data: return False, "帳號不存在"
    if data[username]["password_hash"] != _hash(old_pw): return False, "舊密碼錯誤"
    if len(new_pw) < 4: return False, "新密碼至少 4 碼"
    data[username]["password_hash"] = _hash(new_pw)
    _save(data); return True, "密碼已更新"

def admin_reset_password(username: str, new_pw: str) -> tuple[bool, str]:
    data = _load()
    if username not in data: return False, "帳號不存在"
    if len(new_pw) < 4: return False, "密碼至少 4 碼"
    data[username]["password_hash"] = _hash(new_pw)
    _save(data); return True, "已重設密碼"

# ── 個人觀察名單（每用戶獨立） ──
def get_user_watchlist(username: str) -> list:
    data = _load()
    return data.get(username, {}).get("watchlist", [])

def add_to_watchlist(username: str, code: str) -> bool:
    data = _load()
    if username not in data: return False
    wl = data[username].setdefault("watchlist", [])
    if code not in wl:
        wl.append(code); _save(data)
    return True

def remove_from_watchlist(username: str, code: str) -> bool:
    data = _load()
    if username not in data: return False
    wl = data[username].get("watchlist", [])
    if code in wl:
        wl.remove(code); _save(data)
    return True
