import argparse, os, datetime as dt
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from universe import SECTOR_OF
import data, strategy as S, report, fundamentals as F, webpage, ml, history

def _l(s, n=120): return [None if pd.isna(x) else round(float(x), 2) for x in s.iloc[-n:]]

def reasons(r, fd):
    out = []
    out.append("Uptrend: price above 50 and 200-day averages" if r.ema50 > r.ema200 else "Price above 200-day but 50-day average not yet above it")
    out.append(f"60-day return {r.ret60*100:.1f}% ({r.rs*100:+.1f}% vs Nifty)")
    out.append(f"RSI {r.rsi:.0f}: " + ("healthy momentum" if 50 <= r.rsi <= 70 else "overheated, pullback risk" if r.rsi > 70 else "weak momentum"))
    out.append(f"{r.dist_hi*100:.1f}% from 52-week high" + (" (breakout zone)" if r.dist_hi > -0.05 else ""))
    out.append(f"Volume {r.vol_ratio:.1f}x its 20-day average; closed at {r.close_loc*100:.0f}% of day's range")
    if r.ret1 > 0.05: out.append(f"Warning: already up {r.ret1*100:.1f}% today, so chasing is risky")
    if r.ext > 3: out.append("Warning: stretched far above 20-day average")
    g = fd.get("grade")
    if g and g != "N/A": out.append(f"Latest quarterly results: {g}")
    d = fd.get("next_result_days")
    if d is not None and 0 <= d <= 3: out.append(f"Warning: results due in {d} day(s), so expect a big gap move either way")
    return out

def run(demo=False, top=5, notify=False, force=False, nofund=False):
    tickers = list(SECTOR_OF)
    stocks, bench = data.demo_data(tickers, n=1100, edge=0.12) if demo else (data.download(tickers, "5y"), data.bench_close("5y"))
    if not stocks: raise SystemExit("No data downloaded.")
    ist = dt.datetime.now(dt.timezone(dt.timedelta(hours=5.5))).date(); last = bench.index[-1].date()
    if not demo and not force and last != ist:
        print(f"Latest candle {last} != today {ist} (market holiday or data not ready). Use --force to override."); return
    reg = S.regime(bench); per_sector = top if reg != "BEARISH" else 2
    panel = ml.build_panel(stocks, bench, SECTOR_OF)
    today = panel[(panel.date == panel.date.max()) & panel.rule.notna()].copy()
    if today.empty: print("No stock passed filters today."); return
    today, health = ml.apply(panel, today); print("Model:", health["reason"], "AUC", health["auc"])
    tot = {}
    for t in stocks: tot[SECTOR_OF[t]] = tot.get(SECTOR_OF[t], 0) + 1
    ok = today.groupby("sector").size().to_dict()
    sel = today.sort_values("final", ascending=False).groupby("sector").head(8)
    rows = list(sel.itertuples())
    if nofund: funds = [{} for _ in rows]
    else:
        with ThreadPoolExecutor(6) as ex: funds = list(ex.map(lambda r: F.get(r.ticker[:-3], demo), rows))
    items = []
    for row, fd in zip(rows, funds):
        adj = {"Strong": 5, "Weak": -10}.get(fd.get("grade"), 0); d = fd.get("next_result_days")
        if d is not None and 0 <= d <= 3: adj -= 5
        sc = max(0, min(100, row.final + adj)); v = S.verdict(sc, reg)
        if fd.get("grade") == "Weak" and v == "BUY": v = "WATCH"
        f = S.features(stocks[row.ticker], bench); r = f.iloc[-1]; px, atr = r.close, r.atr
        items.append(dict(sector=row.sector, symbol=row.ticker[:-3], close=round(px, 2), score=round(sc, 1), verdict=v,
            ml_pct=None if pd.isna(row.ml_pct) else round(row.ml_pct, 1), rsi=round(r.rsi, 1), ret1=round(r.ret1*100, 2), ret60=round(r.ret60*100, 1),
            rs=round(r.rs*100, 1), vol_x=round(r.vol_ratio, 2), dist_hi=round(r.dist_hi*100, 1), entry=f"{px-0.25*atr:.1f} - {px+0.25*atr:.1f}",
            stop=round(px-1.5*atr, 1), target=round(px+2*atr, 1), reasons=reasons(r, fd), fund=fd,
            chart=dict(d=list(f.index[-120:].strftime("%d %b")), c=_l(f.close), e20=_l(f.ema20), e50=_l(f.ema50), e200=_l(f.ema200), v=_l(stocks[row.ticker].Volume))))
    items.sort(key=lambda x: -x["score"])
    if reg != "BEARISH": items = [i for i in items if i["verdict"] in ("BUY", "WATCH")]
    final, n = [], {}
    for i in items:
        if n.get(i["sector"], 0) < per_sector: n[i["sector"]] = n.get(i["sector"], 0) + 1; final.append(i)
    best = {}
    for i in final: best.setdefault(i["sector"], i["score"])
    order = sorted(best, key=lambda s: -best[s]); final.sort(key=lambda i: (order.index(i["sector"]), -i["score"]))
    for k, i in enumerate(final): i["id"] = k
    os.makedirs("data", exist_ok=True); hp = "data/history_demo.csv" if demo else "data/history.csv"
    h = history.evaluate(history.load(hp), stocks); h = history.record(h, final, str(last)); h.to_csv(hp, index=False)
    hs = history.summary(h)
    secs = [dict(name=s, passing=ok.get(s, 0), total=tot[s], best=best.get(s)) for s in sorted(tot, key=lambda s: -ok.get(s, 0)/tot[s])]
    webpage.build(dict(date=str(last), regime=reg, sectors=secs, picks=final, health=health, history=hs))
    df = pd.DataFrame([{k: i[k] for k in ("sector","symbol","close","score","verdict","entry","stop","target")} for i in final])
    os.makedirs("output", exist_ok=True); df.to_csv(f"output/watchlist_{last}.csv", index=False)
    txt = report.to_text(df, reg, str(last))
    if hs["n"]: txt += f"\n\nTrack record: {hs['n']} trades, hit {hs['hit']}%, avg {hs['avg']}% per trade (net)"
    print(txt); print("\nWebsite written to site/index.html")
    if notify: report.telegram(txt)

if __name__ == "__main__":
    a = argparse.ArgumentParser()
    for f in ("--demo", "--notify", "--force", "--nofund"): a.add_argument(f, action="store_true")
    a.add_argument("--top", type=int, default=5); run(**vars(a.parse_args()))
