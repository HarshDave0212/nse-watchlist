"""Multi-factor swing/positional-momentum score (0-100). Vectorised, so the same code feeds live scan and backtest.
Not a guarantee of profit: it ranks stocks by how many independent, well-known edges line up."""
import numpy as np, pandas as pd

def _rsi(c, n=14):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100/(1 + up/dn.replace(0, np.nan))

def features(df, bench):
    c,h,l,v = df.Close, df.High, df.Low, df.Volume
    f = pd.DataFrame(index=df.index); f["close"] = c
    e = lambda s: c.ewm(span=s, adjust=False).mean()
    f["ema20"],f["ema50"],f["ema200"] = e(20),e(50),e(200)
    tr = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    f["atr"] = tr.ewm(alpha=1/14, adjust=False).mean(); f["atr_pct"] = f.atr/c
    f["rsi"] = _rsi(c)
    macd = e(12)-e(26); f["macdh"] = macd - macd.ewm(span=9, adjust=False).mean()
    f["ret1"],f["ret20"],f["ret60"],f["ret120"] = c.pct_change(), c.pct_change(20), c.pct_change(60), c.pct_change(120)
    b = bench.reindex(df.index).ffill(); f["rs"] = f.ret60 - b.pct_change(60)
    f["vol_ratio"] = v/v.rolling(20).mean()
    f["close_loc"] = ((c-l)/(h-l).replace(0,np.nan)).fillna(0.5)
    f["dist_hi"] = c/h.rolling(252, min_periods=120).max() - 1
    f["ext"] = (c-f.ema20)/f.atr                       # how stretched above 20-EMA, in ATRs
    f["turnover"] = (c*v).rolling(20).mean()
    f["ret3"], f["ret5"] = c.pct_change(3), c.pct_change(5)
    f["macd_n"] = f.macdh/c
    f["g_e20"], f["g_2050"], f["g_50200"] = c/f.ema20-1, f.ema20/f.ema50-1, f.ema50/f.ema200-1
    f["lturn"] = np.log1p(f.turnover); f["gap"] = df.Open/c.shift()-1
    return f

def score(f):
    u = lambda x: x.clip(0,1)
    s  = (f.close>f.ema50)*8 + (f.ema50>f.ema200)*8 + (f.close>f.ema200)*4               # trend      20
    s += u(f.ret60/0.25)*10 + u(f.ret120/0.40)*5 + u(f.rs/0.15)*10                          # momentum+RS 25
    s += 15*(1-(f.rsi-62).abs()/12).clip(lower=0)                                           # RSI sweet spot 15
    s += (f.macdh>0)*5 + (f.macdh>f.macdh.shift())*5                                           # MACD       10
    s += u((f.vol_ratio-0.8)/1.2)*5 + f.close_loc*5                                         # volume+close strength 10
    s += 10*(1+f.dist_hi/0.10).clip(0,1)                                                    # near 52w high 10
    s += ((f.atr_pct>0.012)&(f.atr_pct<0.04))*10                                            # tradable volatility 10
    # anti-chase penalties (the "ran 15% today" problem)
    s -= (f.ret1>0.08)*15 + (f.ext>3)*10 + (f.rsi>75)*10 + (f.ret1<-0.03)*10 + (f.ret20>0.35)*10
    ok = (f.close>f.ema50)&(f.close>f.ema200)&(f.turnover>1e8)&(f.close>=50)
    return s.where(ok)

def regime(bench):
    e20,e50,e200 = [bench.ewm(span=n, adjust=False).mean().iloc[-1] for n in (20,50,200)]
    c = bench.iloc[-1]
    if c>e50 and e20>e50: return "BULLISH"
    if c<e200: return "BEARISH"
    return "NEUTRAL"

def verdict(sc, reg):
    if reg=="BEARISH": return "AVOID/WAIT" if sc<80 else "WATCH ONLY"
    return "BUY" if sc>=75 else "WATCH" if sc>=60 else "SKIP"
