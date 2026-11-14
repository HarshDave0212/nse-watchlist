"""Stores every watchlist and auto-grades yesterday's picks (buy at next open; stop/target by ATR; sell at close otherwise; 0.2% cost)."""
import os, pandas as pd
COLS = ["date","symbol","sector","verdict","score","ml_pct","ref_close","stop","target","status","eval_date","o","h","l","c","ret","outcome"]
TXT = ["date","symbol","sector","verdict","status","eval_date","outcome"]

def load(path):
    h = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=COLS)
    for c in TXT: h[c] = h[c].astype(object)
    return h.reindex(columns=COLS)

def evaluate(h, stocks, cost=0.002):
    for i, r in h[h.status == "open"].iterrows():
        df = stocks.get(r.symbol + ".NS")
        if df is None: continue
        nx = df[df.index > pd.Timestamp(r.date)]
        if nx.empty: continue
        d = nx.iloc[0]; o, hi, lo, c = [float(d[k]) for k in ("Open","High","Low","Close")]
        if lo <= r.stop: out, ret = "STOP", min(r.stop/o - 1, 0)
        elif hi >= r.target: out, ret = "TARGET", r.target/o - 1
        else: ret = c/o - 1; out = "WIN" if ret > 0 else "LOSS"
        for k, v in zip(("status","eval_date","o","h","l","c","ret","outcome"), ("done", str(nx.index[0].date()), o, hi, lo, c, round((ret-cost)*100, 2), out)): h.at[i, k] = v
    return h

def record(h, picks, date):
    h = h[h.date != date]
    new = pd.DataFrame([dict(date=date, symbol=p["symbol"], sector=p["sector"], verdict=p["verdict"], score=p["score"], ml_pct=p.get("ml_pct"),
                             ref_close=p["close"], stop=p["stop"], target=p["target"], status="open") for p in picks])
    return pd.concat([h, new], ignore_index=True).reindex(columns=COLS)

def summary(h):
    d = h[h.status == "done"].copy(); d["ret"] = d.ret.astype(float)
    if d.empty: return dict(n=0)
    out = dict(n=len(d), days=int(d.date.nunique()), hit=round((d.ret > 0).mean()*100, 1), avg=round(d.ret.mean(), 2))
    for v in ("BUY", "WATCH"):
        x = d[d.verdict == v]; out[v] = dict(n=len(x), hit=round((x.ret > 0).mean()*100, 1) if len(x) else None, avg=round(x.ret.mean(), 2) if len(x) else None)
    daily = d.groupby("date").ret.mean().sort_index(); cur = ((1 + daily/100).cumprod() - 1)*100
    out["curve"] = dict(d=list(daily.index), v=[round(x, 2) for x in cur])
    out["recent"] = d.sort_values(["date","score"], ascending=[False, False]).head(40)[["date","symbol","verdict","score","outcome","ret"]].to_dict("records")
    return out
