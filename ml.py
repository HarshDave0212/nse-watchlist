"""ML ranking layer. Gradient boosting predicts which eligible stocks land in the TOP QUARTILE of next-day (open->close, net of cost)
returns. It is only used if it beats the rules on 150 unseen days (walk-forward); otherwise the tool silently falls back to rules."""
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
import strategy as S

BASE = ["ret1","ret3","ret5","ret20","ret60","ret120","rs","rsi","macd_n","g_e20","g_2050","g_50200","atr_pct","vol_ratio","close_loc","dist_hi","ext","gap","lturn"]
RK = ["ret5","ret20","ret60","rs","vol_ratio"]
FEATS = BASE + [c+"_rk" for c in RK] + ["sec_ret5","sec_ret20","sec_rs","m_ret1","m_ret5","m_ext"]

def build_panel(stocks, bench, sector_of, cost=0.002):
    parts = []
    for t, df in stocks.items():
        f = S.features(df, bench); f["rule"] = S.score(f)
        f["ret_next"] = df.Close.shift(-1)/df.Open.shift(-1) - 1 - cost       # realistic: buy next open, sell next close
        f["ticker"], f["sector"] = t, sector_of[t]; parts.append(f)
    p = pd.concat(parts); p.index.name = "date"; p = p.reset_index()
    b = bench.squeeze()
    m = pd.DataFrame({"m_ret1": b.pct_change(), "m_ret5": b.pct_change(5), "m_ext": b/b.ewm(span=50, adjust=False).mean()-1})
    p = p.merge(m, left_on="date", right_index=True, how="left")
    for c in RK: p[c+"_rk"] = p.groupby("date")[c].rank(pct=True)
    for c in ("ret5","ret20"): p["sec_"+c] = p.groupby(["date","sector"])[c].transform("mean")
    p["sec_rs"] = p.sec_ret20 - p.groupby("date").ret20.transform("mean")
    return p.replace([np.inf, -np.inf], np.nan)

def _model(): return HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=4, min_samples_leaf=200, l2_regularization=1.0, random_state=0)

def _top(d, col, n=5):
    pk = d.sort_values(col, ascending=False).groupby("date").head(n)
    a = pk.groupby("date").ret_next.mean(); base = d.groupby("date").ret_next.mean().reindex(a.index)
    return dict(avg=round(a.mean()*100, 3), hit=round((a > 0).mean()*100, 1), lift=round((a-base).mean()*100, 3))

def apply(panel, today, val_days=150):
    h = dict(used=False, reason="", auc=None, val_days=None, ml_avg=None, ml_hit=None, ml_lift=None, rule_avg=None, rule_hit=None, rule_lift=None)
    e = panel[panel.rule.notna() & panel.ret_next.notna()].copy(); dates = np.sort(e.date.unique())
    today["ml_pct"] = np.nan; today["final"] = today.rule
    if len(dates) < 400: h["reason"] = "Not enough history for ML."; return today, h
    e["y"] = (e.groupby("date").ret_next.rank(pct=True) >= 0.75).astype(int)
    tr, va = e[e.date < dates[-val_days-1]], e[e.date >= dates[-val_days]].copy()
    m = _model().fit(tr[FEATS], tr.y); va["p"] = m.predict_proba(va[FEATS])[:, 1]
    auc = roc_auc_score(va.y, va.p); ms, rs = _top(va, "p"), _top(va, "rule")
    h.update(auc=round(auc, 3), val_days=val_days, ml_avg=ms["avg"], ml_hit=ms["hit"], ml_lift=ms["lift"], rule_avg=rs["avg"], rule_hit=rs["hit"], rule_lift=rs["lift"])
    if auc > 0.505 and ms["lift"] > 0 and ms["lift"] >= rs["lift"]:
        m2 = _model().fit(e[FEATS], e.y); pr = m2.predict_proba(today[FEATS])[:, 1]
        today["ml_pct"] = pd.Series(pr, index=today.index).rank(pct=True)*100
        today["final"] = 0.5*today.rule + 0.5*today.ml_pct; h["used"] = True; h["reason"] = "ML beat the rules on unseen days."
    else: h["reason"] = "ML did not beat the rules on unseen days, so it was not used."
    return today, h
