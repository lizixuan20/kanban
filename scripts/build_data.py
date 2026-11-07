# -*- coding: utf-8 -*-
"""拉自选股日线 + 算指标 -> data.js"""
import json, os, sys, urllib.request, datetime
import pandas as pd

UA = {"User-Agent": "Mozilla/5.0"}
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "web", "data.js")
if not os.path.isabs(OUT):
    OUT = os.path.join(os.getcwd(), OUT)

def load_syms():
    p = os.path.join(ROOT, "config", "portfolio.json")
    syms = ["sh000001"]
    names = {"sh000001": "上证指数"}
    if os.path.exists(p):
        cfg = json.load(open(p, encoding="utf-8"))
        for it in cfg.get("watchlist", []):
            if it["symbol"] not in syms:
                syms.append(it["symbol"])
            names[it["symbol"]] = it["name"]
    return syms, names

def kline(sym, n=300):
    u = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={sym},day,,,{n},qfq"
    r = urllib.request.Request(u, headers=UA)
    d = json.loads(urllib.request.urlopen(r, timeout=25).read())["data"][sym]
    k = d.get("qfqday") or d.get("day")
    df = pd.DataFrame([x[:6] for x in k], columns=["date","open","close","high","low","volume"])
    for c in ["open","close","high","low","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna().reset_index(drop=True)

def ema(s, n): return s.ewm(span=n, adjust=False).mean()

def indicators(df):
    c, h, l = df["close"], df["high"], df["low"]
    out = {"ma5": c.rolling(5).mean(), "ma10": c.rolling(10).mean(),
           "ma20": c.rolling(20).mean(), "ma60": c.rolling(60).mean()}
    mid = c.rolling(20).mean(); sd = c.rolling(20).std(ddof=0)
    out["boll_up"] = mid + 2*sd; out["boll_mid"] = mid; out["boll_dn"] = mid - 2*sd
    dif = ema(c,12) - ema(c,26); dea = ema(dif,9)
    out["dif"] = dif; out["dea"] = dea; out["macd"] = (dif-dea)*2
    low9 = l.rolling(9).min(); high9 = h.rolling(9).max()
    rsv = (c - low9) / (high9 - low9).replace(0, pd.NA) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    dd = k.ewm(alpha=1/3, adjust=False).mean()
    out["k"] = k; out["d"] = dd; out["j"] = 3*k - 2*dd
    return out

def rnd(x):
    try: v = float(x)
    except Exception: return None
    return None if v != v else round(v, 3)

SYMS, NAMES = load_syms()
result = {"updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "symbols": {}}
for sym in SYMS:
    try:
        df = kline(sym)
        ind = indicators(df)
        result["symbols"][sym] = {
            "name": NAMES.get(sym, sym),
            "dates": df["date"].tolist(),
            "ohlc": [[round(o,3), round(cl,3), round(lo,3), round(hi,3)]
                     for o, cl, lo, hi in zip(df["open"], df["close"], df["low"], df["high"])],
            "volume": [int(v) for v in df["volume"]],
            "ind": {k: [rnd(v) for v in s.tolist()] for k, s in ind.items()},
        }
        print(f"OK   {sym} {NAMES.get(sym,''):12s} rows={len(df)} last={df.iloc[-1]['date']}")
    except Exception as e:
        print(f"FAIL {sym} {type(e).__name__}: {str(e)[:70]}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("window.MARKET_DATA = ")
    json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")
print("saved", OUT, round(os.path.getsize(OUT)/1024,1), "KB")
