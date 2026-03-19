"""
watchlist.py — 持久化自選股管理
- 資料存在 watchlist.json（與程式同目錄）
- app.py 與 cloud_bot.py 共用同一份清單
- 不刪除就永久存在
"""

import json
import os
import requests
from datetime import datetime
from pathlib import Path

_WL_PATH = Path(__file__).parent / "watchlist.json"

_DEFAULT = {
    "2454": {"name": "聯發科",  "added": "2025-01-01", "note": ""},
    "3017": {"name": "奇鋐",    "added": "2025-01-01", "note": ""},
    "6805": {"name": "富世達",  "added": "2025-01-01", "note": ""},
    "3661": {"name": "世芯-KY", "added": "2025-01-01", "note": ""},
}


def _load() -> dict:
    if not _WL_PATH.exists():
        _save(_DEFAULT)
        return dict(_DEFAULT)
    try:
        with open(_WL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(_DEFAULT)


def _save(data: dict):
    with open(_WL_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all() -> dict:
    return _load()


def add_stock(code: str, name: str, note: str = "") -> tuple:
    code = code.strip().replace(".TW", "").replace(".TWO", "")
    if not code.isdigit() or len(code) not in (4, 5):
        return False, f"代號格式錯誤：{code}（應為 4~5 位數字）"
    data = _load()
    if code in data:
        return False, f"{code} 已在清單中"
    data[code] = {
        "name":  name.strip() or code,
        "added": datetime.now().strftime("%Y-%m-%d"),
        "note":  note.strip(),
    }
    _save(data)
    return True, f"✅ 已新增 {name or code}（{code}）"


def remove_stock(code: str) -> tuple:
    data = _load()
    if code not in data:
        return False, f"{code} 不在清單中"
    name = data[code].get("name", code)
    del data[code]
    _save(data)
    return True, f"🗑️ 已移除 {name}（{code}）"


def update_note(code: str, note: str):
    data = _load()
    if code in data:
        data[code]["note"] = note.strip()
        _save(data)


def to_simple_dict() -> dict:
    return {k: v["name"] for k, v in _load().items()}


def lookup_name(code: str) -> str:
    import yfinance as yf
    for sfx in [".TW", ".TWO"]:
        try:
            info = yf.Ticker(code + sfx).info
            n = info.get("shortName") or info.get("longName") or ""
            if n:
                return n.replace(" ", "")[:10]
        except:
            pass
    try:
        r   = requests.get("https://histock.tw/stock/rank.aspx?p=all",
                           headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        import pandas as pd
        dfs = pd.read_html(r.text)
        df  = dfs[0]
        cc  = [c for c in df.columns if "代號" in str(c)][0]
        cn  = [c for c in df.columns if "股票" in str(c) or "名稱" in str(c)][0]
        for _, row in df.iterrows():
            c2 = "".join(x for x in str(row[cc]) if x.isdigit())
            if c2 == code:
                return str(row[cn])
    except:
        pass
    return code
