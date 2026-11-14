import numpy as np, pandas as pd
from universe import BENCH

def download(tickers, period="2y"):
    import yfinance as yf
    out = {}
    for i in range(0, len(tickers), 40):          # batches avoid Yahoo throttling
        chunk = tickers[i:i+40]
        df = yf.download(chunk, period=period, interval="1d", auto_adjust=True,
                         group_by="ticker", threads=True, progress=False)
        for t in chunk:
            try:
                d = df[t].dropna(subset=["Close"])
                if len(d) > 260: out[t] = d
            except Exception: pass
    return out

def bench_close(period="2y"):
    import yfinance as yf
    return yf.download(BENCH, period=period, auto_adjust=True, progress=False)["Close"].squeeze()

def demo_data(tickers, n=500, seed=7, edge=0.0):
    rng = np.random.default_rng(seed); idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    mk = rng.normal(0.0004, 0.009, n); out = {}
    for t in tickers:
        r = mk*0.7 + rng.normal(rng.uniform(-0.0002,0.0009), rng.uniform(0.01,0.022), n)
        for k in range(1, n): r[k] += edge*r[k-1]          # planted autocorrelation to test the ML path
        c = rng.uniform(100,3000)*np.exp(np.cumsum(r)); o = c*(1+rng.normal(0,0.004,n))
        h = np.maximum(o,c)*(1+abs(rng.normal(0,0.006,n))); l = np.minimum(o,c)*(1-abs(rng.normal(0,0.006,n)))
        out[t] = pd.DataFrame({"Open":o,"High":h,"Low":l,"Close":c,"Volume":rng.uniform(5e5,5e6,n)}, index=idx)
    return out, pd.Series(100*np.exp(np.cumsum(mk)), index=idx)
