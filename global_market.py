"""
global_market.py — 全球市場情報模組
功能：
  1. 根據股票產業自動選擇相關美股/ETF/全球指數
  2. 抓取全球相關產業龍頭股
  3. 抓取 Trump Truth Social 最新發文
  4. 相關產業最新新聞
"""
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re

# ─────────────────────────────────────────
# 產業對應關係表
# ─────────────────────────────────────────
INDUSTRY_MAP = {
    # 半導體/IC設計
    "semiconductor": {
        "name": "半導體",
        "us_etf":   [("SOXX","費城半導體ETF"),("SMH","半導體ETF"),("QQQ","那斯達克")],
        "us_stocks":[("NVDA","輝達"),("AMD","超微"),("INTC","英特爾"),("QCOM","高通"),("MU","美光")],
        "global":   [("005930.KS","三星電子"),("000660.KS","SK海力士"),("6723.T","瑞薩電子")],
        "keywords": ["semiconductor","chip","AI","NVIDIA","tariff","export control"],
    },
    # 記憶體/DRAM
    "memory": {
        "name": "記憶體",
        "us_etf":   [("SOXX","費城半導體ETF"),("SMH","半導體ETF")],
        "us_stocks":[("MU","美光科技"),("WDC","威騰電子"),("STX","希捷")],
        "global":   [("005930.KS","三星電子"),("000660.KS","SK海力士"),("6702.T","富士通")],
        "keywords": ["DRAM","memory","HBM","NAND","tariff"],
    },
    # PCB/電路板
    "pcb": {
        "name": "PCB電路板",
        "us_etf":   [("XLK","科技ETF"),("SOXX","費城半導體ETF")],
        "us_stocks":[("APH","安費諾"),("TE","泰科電子"),("TTM","TTM Technologies")],
        "global":   [("6770.T","村田製作所"),("6971.T","京瓷")],
        "keywords": ["PCB","circuit board","AI server","tariff"],
    },
    # 電子零組件
    "electronic": {
        "name": "電子零組件",
        "us_etf":   [("XLK","科技ETF"),("IYW","科技ETF")],
        "us_stocks":[("AAPL","蘋果"),("MSFT","微軟"),("GOOGL","Google")],
        "global":   [("6758.T","索尼"),("6752.T","松下"),("005930.KS","三星")],
        "keywords": ["electronics","supply chain","tariff","Apple"],
    },
    # 通訊/網路
    "telecom": {
        "name": "電信通訊",
        "us_etf":   [("IYZ","電信ETF"),("XLC","通訊ETF")],
        "us_stocks":[("T","AT&T"),("VZ","Verizon"),("TMUS","T-Mobile")],
        "global":   [("9432.T","NTT"),("0941.HK","中國移動")],
        "keywords": ["5G","telecom","network","spectrum"],
    },
    # 金融
    "financial": {
        "name": "金融",
        "us_etf":   [("XLF","金融ETF"),("KBE","銀行ETF")],
        "us_stocks":[("JPM","摩根大通"),("BAC","美國銀行"),("GS","高盛")],
        "global":   [("0005.HK","匯豐"),("8306.T","三菱UFJ")],
        "keywords": ["Fed","interest rate","bank","financial"],
    },
    # 電動車/汽車
    "auto": {
        "name": "汽車/電動車",
        "us_etf":   [("DRIV","電動車ETF"),("LIT","鋰電池ETF")],
        "us_stocks":[("TSLA","特斯拉"),("GM","通用汽車"),("F","福特")],
        "global":   [("7203.T","豐田"),("005380.KS","現代汽車"),("BYDDF","比亞迪")],
        "keywords": ["EV","electric vehicle","tariff","Tesla","battery"],
    },
    # 默認（大盤相關）
    "default": {
        "name": "大盤",
        "us_etf":   [("SPY","S&P500"),("QQQ","那斯達克"),("DIA","道瓊")],
        "us_stocks":[("AAPL","蘋果"),("MSFT","微軟"),("NVDA","輝達")],
        "global":   [("^N225","日經225"),("^HSI","恆生指數"),("^KS11","韓國KOSPI")],
        "keywords": ["tariff","Fed","economy","trade war"],
    },
}

# 產業關鍵字 → INDUSTRY_MAP key
SECTOR_KEYWORDS = {
    "semiconductor": ["semiconductor","electronic","半導體","IC","晶片","chip","積體電路"],
    "memory":        ["memory","記憶體","DRAM","NAND","儲存"],
    "pcb":           ["pcb","circuit","電路板","印刷電路"],
    "electronic":    ["electronic","consumer","電子","零組件","connector"],
    "telecom":       ["telecom","communication","電信","通訊","網路"],
    "financial":     ["financial","bank","insurance","金融","銀行","保險"],
    "auto":          ["automobile","auto","vehicle","汽車","電動車","EV"],
}


def detect_industry(code: str) -> dict:
    """
    根據股票代號和 yfinance 資訊偵測產業
    回傳 INDUSTRY_MAP 中對應的 dict
    """
    try:
        for sfx in [".TW",".TWO",""]:
            try:
                info = yf.Ticker(code+sfx).info
                industry  = (info.get("industry","") or "").lower()
                sector    = (info.get("sector","") or "").lower()
                name      = (info.get("longName","") or "").lower()
                combined  = f"{industry} {sector} {name}"
                for key, kws in SECTOR_KEYWORDS.items():
                    if any(kw.lower() in combined for kw in kws):
                        return {**INDUSTRY_MAP[key], "detected_key": key}
                break
            except: continue
    except: pass
    return {**INDUSTRY_MAP["default"], "detected_key": "default"}


def get_market_data(tickers_with_name: list) -> list:
    """
    批次取得行情
    tickers_with_name: [(ticker, name), ...]
    回傳: [{"ticker","name","price","pct","direction"}, ...]
    """
    results = []
    for ticker, name in tickers_with_name:
        try:
            df = yf.Ticker(ticker).history(period="2d")
            if df.empty or len(df) < 2: continue
            price = float(df["Close"].iloc[-1])
            prev  = float(df["Close"].iloc[-2])
            pct   = (price - prev) / prev * 100
            results.append({
                "ticker":    ticker,
                "name":      name,
                "price":     round(price, 2),
                "pct":       round(pct, 2),
                "direction": "🔺" if pct > 0 else "💚" if pct < 0 else "➖",
            })
        except: continue
    return results


def get_trump_posts(max_items: int = 5, extra_keywords: list = None) -> list:
    """
    抓取 Trump 最新言論
    策略1：Truth Social RSS（常被封鎖）
    策略2：Google News 搜尋 Trump 最新新聞
    """
    posts = []

    # 策略1：嘗試 Truth Social
    for rss_url in [
        "https://truthsocial.com/@realDonaldTrump.rss",
        "https://www.trumptruth.com/rss",
    ]:
        try:
            r = requests.get(rss_url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/rss+xml,application/xml;q=0.9",
            }, timeout=8)
            if r.status_code != 200: continue
            root = ET.fromstring(r.content)
            for item in root.iter("item"):
                title = item.findtext("title","")
                desc  = item.findtext("description","")
                link  = item.findtext("link","")
                pub   = item.findtext("pubDate","")
                text  = re.sub(r'<[^>]+>', '', desc or title).strip()
                if not text: continue
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub)
                    time_str = dt.strftime("%m/%d %H:%M")
                except:
                    time_str = pub[:16] if pub else ""
                posts.append({"text": text[:250], "time": time_str, "url": link,
                              "source": "Truth Social"})
                if len(posts) >= max_items: break
            if posts: break
        except: continue

    # 策略2：若策略1失敗，用 Google News 抓 Trump 最新言論新聞
    if not posts:
        try:
            base_kws = extra_keywords or []
            query = "Trump " + " ".join(base_kws[:2]) + " tariff Taiwan" if base_kws else "Trump tariff trade Taiwan semiconductor"
            url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
            r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.iter("item"):
                    title = item.findtext("title","").strip()
                    link  = item.findtext("link","").strip()
                    pub   = item.findtext("pubDate","")
                    if not title: continue
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(pub)
                        time_str = dt.strftime("%m/%d %H:%M")
                    except:
                        time_str = ""
                    posts.append({"text": title[:250], "time": time_str, "url": link,
                                  "source": "Google News"})
                    if len(posts) >= max_items: break
        except: pass

    # 策略3：搜尋英文川普相關最新消息
    if not posts:
        try:
            for q in ["Trump tariff","Trump trade war","Trump Taiwan"]:
                url = f"https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=en-US&gl=US&ceid=US:en"
                r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
                if r.status_code != 200: continue
                root = ET.fromstring(r.content)
                for item in root.iter("item"):
                    title = item.findtext("title","").strip()
                    link  = item.findtext("link","").strip()
                    pub   = item.findtext("pubDate","")
                    if not title: continue
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(pub)
                        time_str = dt.strftime("%m/%d %H:%M")
                    except:
                        time_str = ""
                    posts.append({"text": title[:250], "time": time_str, "url": link,
                                  "source": "Google News (EN)"})
                    if len(posts) >= max_items: break
                if posts: break
        except: pass

    if not posts:
        posts = [{"text": "⚠️ 目前無法取得川普最新言論，請直接前往 truthsocial.com/@realDonaldTrump",
                  "time": "", "url": "https://truthsocial.com/@realDonaldTrump",
                  "source": ""}]
    return posts


def get_industry_news(keywords: list, max_items: int = 5) -> list:
    """
    從 Google News RSS 抓取產業相關新聞
    keywords: 搜尋關鍵字列表
    """
    news = []
    query = " OR ".join(keywords[:3])  # 取前3個關鍵字
    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for item in root.iter("item"):
                title = item.findtext("title","").strip()
                link  = item.findtext("link","").strip()
                pub   = item.findtext("pubDate","")
                src_tag = item.find("{http://purl.org/dc/elements/1.1/}creator")
                src   = src_tag.text if src_tag is not None else ""
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub)
                    time_str = dt.strftime("%m/%d %H:%M")
                except:
                    time_str = ""
                if title:
                    bull_kw = ["上漲","突破","創高","買超","成長","正向","利多","調升","超越","漲停","獲利"]
                    bear_kw = ["下跌","跌破","虧損","賣超","警示","利空","調降","風險","跌停","裁員"]
                    sentiment = ("🟢" if any(k in title for k in bull_kw)
                                 else "🔴" if any(k in title for k in bear_kw)
                                 else "⚪")
                    news.append({
                        "title": title,
                        "time":  time_str,
                        "url":   link,
                        "src":   src,
                        "sentiment": sentiment,
                    })
                if len(news) >= max_items: break
    except Exception as e:
        pass
    return news


def get_full_global_report(code: str, stock_name: str = "") -> dict:
    """
    一次取得所有全球市場情報
    回傳 {
        industry_info: dict,
        us_etf_data:   list,
        us_stock_data: list,
        global_data:   list,
        trump_posts:   list,
        industry_news: list,
    }
    """
    industry = detect_industry(code)

    # 個股專屬關鍵字（中文名稱 + 代號 + 產業關鍵字）
    stock_kws = []
    if stock_name: stock_kws.append(stock_name)
    if code:       stock_kws.append(code)
    combined_kws = stock_kws + industry["keywords"][:3]

    # Trump 搜尋也加入個股相關性
    trump_query_extra = stock_kws[:1] + ["tariff","Taiwan","semiconductor"]

    return {
        "industry_info": industry,
        "us_etf_data":   get_market_data(industry["us_etf"]),
        "us_stock_data": get_market_data(industry["us_stocks"]),
        "global_data":   get_market_data(industry["global"]),
        "trump_posts":   get_trump_posts(max_items=5, extra_keywords=trump_query_extra),
        "industry_news": get_industry_news(combined_kws, max_items=8),
        "stock_news":    get_industry_news(stock_kws + ["台股",code], max_items=5) if stock_kws else [],
    }
