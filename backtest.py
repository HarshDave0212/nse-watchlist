"""Run on your PC with real data: python backtest.py  (prints ML walk-forward health + long-run rule stats, net of costs)."""
import sys, json
from universe import SECTOR_OF
import data, ml
def main(demo=False):
    tk = list(SECTOR_OF); stocks, bench = data.demo_data(tk, n=1100, edge=0.12) if demo else (data.download(tk, "5y"), data.bench_close("5y"))
    p = ml.build_panel(stocks, bench, SECTOR_OF); today = p[p.date == p.date.max()].dropna(subset=["rule"]).copy()
    _, h = ml.apply(p, today); print(json.dumps(h, indent=1))
    e = p[p.rule.notna() & p.ret_next.notna()]
    for th in (60, 75):
        s = e[e.rule >= th]
        print(f"rule>={th}: trades={len(s)} avg {s.ret_next.mean()*100:.3f}% hit {(s.ret_next>0).mean()*100:.1f}% | all eligible avg {e.ret_next.mean()*100:.3f}%")
    print("If neither ML nor rules beat the all-eligible average, the signal is noise: do not trade it with real money.")
if __name__ == "__main__": main("--demo" in sys.argv)
