# NSE Daily Watchlist - rules + ML ranking, quarterly results, charts, stored history (free)

## Quick start (your PC)
1. Install Python 3.10+ (python.org). In this folder: `pip install -r requirements.txt`
2. After 4:00 PM IST on a trading day: `python main.py`  (about 5-8 minutes: 5 years of prices + results for top candidates)
3. Open `site/index.html`. Click any stock for charts, results and reasons.
Options: `--demo` fake data preview | `--nofund` skip results | `--force` run on holidays | `--notify` Telegram.
Check the strategy on real data first: `python backtest.py`

## Does it store my watchlist?  Yes
- `output/watchlist_YYYY-MM-DD.csv` : each day's list.
- `data/history.csv` : every pick ever given. On the next run each pick is auto-graded (buy next open, ATR stop/target, else sell at close, 0.2% cost) and shown in the "Your track record" section with hit rate and cumulative curve.
- Keep the folder (or the repo) so history keeps growing. Run daily on the same machine.

## Automatic 5 PM IST + phone access (optional, free)
GitHub repo (upload all files) > Settings > Pages > Source: GitHub Actions > Actions > run daily-watchlist once. The workflow also commits `data/` back so history persists. Free Pages needs a public repo (your picks and history would be public); use Telegram secrets (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`) or Cloudflare Pages for privacy.

## How the engine works
1. Universe: ~120 liquid NSE stocks in 13 sectors, 5 years of data. Hard filters: above 50 and 200 EMA, turnover over Rs10 cr, price 50+.
2. Rule score (0-100): trend, momentum, relative strength vs Nifty, RSI zone, MACD, volume/close strength, near 52-week high, volatility, minus anti-chase penalties.
3. ML ranker (gradient boosting, 30 features incl. cross-sectional ranks, sector momentum, Nifty state) predicts who lands in the top quartile of next-day open-to-close return. It is trained walk-forward and used ONLY if it beats the rules on the latest 150 unseen days; otherwise the tool falls back to rules automatically. Final = 50% rules + 50% ML rank.
4. Quarterly results: Strong +5, Weak -10 (and no BUY), results within 3 days -5.
5. Market regime: Nifty bearish -> only 2 per sector, no BUY.
6. Entry zone, stop (1.5 ATR), target (2 ATR). The "Model check" and "Track record" sections show how well it is really doing.

## Honest limits
Next-day returns are mostly noise; a realistic edge is a few percentage points of hit rate and a few hundredths of a percent per trade. No one can guarantee profit. Paper-trade 4+ weeks and read the track record before risking money. Risk 1% per trade. Free Yahoo data can be late or missing. Not investment advice.
