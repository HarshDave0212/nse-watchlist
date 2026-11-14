import html, urllib.request, urllib.parse, os
COLS = ["sector","symbol","close","score","verdict","rsi","ret60_%","rs_%","vol_x","entry_zone","stop","target"]

def to_html(df, reg, date, note=""):
    col = {"BULLISH":"#0a7","NEUTRAL":"#c80","BEARISH":"#c33"}[reg]
    rows = "".join("<tr>"+"".join(f"<td>{html.escape(str(r[c]))}</td>" for c in COLS)+"</tr>" for _,r in df.iterrows())
    return f"""<html><head><meta charset=utf-8><style>body{{font-family:sans-serif;margin:20px}}table{{border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:5px 9px;font-size:13px}}th{{background:#eee}}</style></head><body>
<h2>Watchlist for next trading day (generated {date})</h2>
<p>Market regime (Nifty 50): <b style="color:{col}">{reg}</b> {note}</p>
<table><tr>{''.join(f'<th>{c}</th>' for c in COLS)}</tr>{rows}</table>
<p><small>Educational screening output, not investment advice. No method guarantees next-day profit. Always use the stop-loss and size positions small.
Check upcoming results/news before buying.</small></p></body></html>"""

def to_text(df, reg, date):
    out = [f"WATCHLIST {date} | Nifty regime: {reg}"]
    for sec, g in df.groupby("sector", sort=False):
        out.append(f"\n{sec}")
        out += [f" {r.symbol} {r.close} score {r.score} {r.verdict} SL {r.stop} T {r.target}" for r in g.itertuples()]
    return "\n".join(out)

def telegram(text):
    tok, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (tok and chat): print("Telegram not configured; skipped."); return
    for i in range(0, len(text), 3900):
        data = urllib.parse.urlencode({"chat_id":chat,"text":text[i:i+3900]}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data, timeout=30)
