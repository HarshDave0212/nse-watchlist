"""Quarterly results via yfinance (free). Values in Rs crore. Any failure -> empty result (never breaks the scan)."""
import random, datetime as dt

def _row(q, names):
    for n in names:
        if n in q.index: return q.loc[n]
    return None

def _grade(qs):
    if not qs: return "N/A"
    last = qs[-1]; ni, rev = last.get("yoy_ni"), last.get("yoy_rev")
    if ni is None or rev is None:
        ni, rev = last.get("qoq_ni"), last.get("qoq_rev")
    if ni is None or rev is None: return "N/A"
    if last["ni"] is not None and last["ni"] < 0 or ni < -10: return "Weak"
    if ni > 10 and rev > 5: return "Strong"
    return "Mixed"

def _growth(a, b):
    """% change; None if base missing or not positive (growth off a loss is meaningless)."""
    if a is None or b is None or b <= 0: return None
    return round((a / b - 1) * 100, 1)

def _build(rows):
    qs = []
    for i, r in enumerate(rows):
        q = dict(r)
        p1, p4 = (rows[i-1] if i >= 1 else None), (rows[i-4] if i >= 4 else None)
        q["qoq_rev"] = _growth(q["rev"], p1["rev"]) if p1 else None
        q["qoq_ni"]  = _growth(q["ni"],  p1["ni"])  if p1 else None
        q["yoy_rev"] = _growth(q["rev"], p4["rev"]) if p4 else None
        q["yoy_ni"]  = _growth(q["ni"],  p4["ni"])  if p4 else None
        qs.append(q)
    return qs

def get(sym, demo=False):
    try:
        if demo:
            rnd = random.Random(sym); base = rnd.uniform(2000, 40000); rows = []
            for i in range(5):
                base *= rnd.uniform(0.95, 1.12)
                rows.append(dict(q=["Sep-25","Dec-25","Mar-26","Jun-26","Sep-26"][i], rev=round(base,0), ni=round(base*rnd.uniform(0.05,0.2),0), eps=round(rnd.uniform(5,60),1)))
            days = rnd.choice([None, None, 2, 20])
        else:
            import yfinance as yf
            t = yf.Ticker(sym + ".NS"); q = t.quarterly_income_stmt
            rev = _row(q, ["Total Revenue", "Operating Revenue"]); ni = _row(q, ["Net Income", "Net Income Common Stockholders"])
            eps = _row(q, ["Diluted EPS", "Basic EPS"])
            rows = []
            for col in sorted(q.columns)[-5:]:
                g = lambda s, k=1e7: None if s is None or s.get(col) != s.get(col) else round(float(s[col]) / k, 1)
                rows.append(dict(q=col.strftime("%b-%y"), rev=g(rev), ni=g(ni), eps=g(eps, 1)))
            days = None
            try:
                ed = t.calendar.get("Earnings Date")
                if ed: days = (min(ed) - dt.date.today()).days
            except Exception: pass
        qs = _build(rows)
        return dict(quarters=qs, grade=_grade(qs), next_result_days=days)
    except Exception as e:
        return dict(quarters=[], grade="N/A", next_result_days=None)
