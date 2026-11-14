import json, os
TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>NSE Daily Watchlist</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{--bg:#f6f7f9;--card:#fff;--tx:#1b1f24;--mut:#667;--bd:#e1e4e8;--g:#0a7d4f;--a:#b7791f;--r:#c0392b;--b:#2563eb}
@media(prefers-color-scheme:dark){:root{--bg:#0f1318;--card:#171c23;--tx:#e6e9ee;--mut:#98a2b3;--bd:#2a313b;--g:#34d399;--a:#fbbf24;--r:#f87171;--b:#60a5fa}}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--tx)}
header,main{max-width:1100px;margin:0 auto;padding:16px}h1{margin:0;font-size:22px}small,.mut{color:var(--mut)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.tile,.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px}.tile b{display:block;font-size:20px}
.bar{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}select{padding:7px;border-radius:8px;border:1px solid var(--bd);background:var(--card);color:var(--tx)}
.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:640px}th,td{padding:8px;border-bottom:1px solid var(--bd);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}tr[data-i]{cursor:pointer}tr[data-i]:hover{background:rgba(120,130,150,.12)}
.pill{padding:2px 8px;border-radius:99px;font-size:12px;font-weight:600;border:1px solid}.BUY{color:var(--g)}.WATCH{color:var(--a)}.WATCHONLY,.AVOIDWAIT,.SKIP{color:var(--r)}
.up{color:var(--g)}.dn{color:var(--r)}h3{margin:22px 0 8px}
#modal{position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;overflow:auto;padding:16px;z-index:9}
#box{background:var(--bg);max-width:900px;margin:0 auto;border-radius:12px;padding:16px;position:relative}
#x{position:absolute;right:12px;top:8px;font-size:26px;cursor:pointer;border:0;background:none;color:var(--tx)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}.ch{position:relative;height:260px}
.warn{color:var(--r)}ul{padding-left:18px;margin:6px 0}details{margin-top:18px}
</style></head><body>
<header><h1>NSE Daily Watchlist</h1><small id="sub"></small>
<div class="tiles" id="tiles"></div>
<div class="card"><b>Sector strength</b> <small>(% of stocks passing trend, liquidity and strength filters)</small><div class="ch" style="height:240px"><canvas id="secChart"></canvas></div></div>
</header><main>
<div class="bar"><select id="sec"><option value="">All sectors</option></select>
<select id="vd"><option value="">All verdicts</option><option>BUY</option><option>WATCH</option></select></div>
<div id="list"></div><div id="hist"></div>
<details class="card"><summary><b>How to read this page</b></summary><ul>
<li><b>Score</b> (0-100) blends trend, momentum, relative strength vs Nifty, RSI, MACD, volume, closeness to 52-week high and volatility, minus penalties for chasing stocks that already spiked. 75+ is BUY, 60-75 WATCH.</li>
<li><b>Price chart</b>: price above the rising 50 (blue) and 200 (red) day lines means an uptrend. Price far above the 20-day line means stretched.</li>
<li><b>Volume bars</b>: rising price on rising volume is more reliable than on thin volume.</li>
<li><b>Results</b>: Strong = profit up over 10% and revenue up over 5% year on year. Weak = profit falling over 10% or a loss. Check results dates: a result inside 3 days makes the next day a gamble.</li>
<li><b>Entry/Stop/Target</b>: stop is 1.5 ATR below, target 2 ATR above. Risk at most 1% of capital per trade. No signal guarantees next-day profit.</li></ul></details>
<p class="mut">Educational screening output, not investment advice. Data: Yahoo Finance (free, may be delayed or incomplete).</p>
</main>
<div id="modal"><div id="box"><button id="x">&times;</button><div id="mb"></div></div></div>
<script>
const D=__DATA__,$=s=>document.querySelector(s);let charts=[];
const cls=v=>v.replace(/[^A-Z]/g,''),sg=n=>(n>0?'+':'')+n,fmt=n=>n==null?'-':Number(n).toLocaleString('en-IN');
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
$('#sub').textContent='Generated '+D.date+' after market close. Picks are for the next trading day.';
const buys=D.picks.filter(p=>p.verdict==='BUY').length,rc={BULLISH:'up',BEARISH:'dn',NEUTRAL:''}[D.regime];
$('#tiles').innerHTML=`<div class="tile">Nifty regime<b class="${rc}">${D.regime}</b></div><div class="tile">Picks<b>${D.picks.length}</b></div><div class="tile">BUY signals<b>${buys}</b></div><div class="tile">Strongest sector<b style="font-size:16px">${D.sectors[0].name}</b></div><div class="tile">Ranking engine<b style="font-size:16px">${D.health.used?'Rules + ML':'Rules only'}</b></div>`;
D.sectors.forEach(s=>$('#sec').insertAdjacentHTML('beforeend',`<option>${s.name}</option>`));
new Chart($('#secChart'),{type:'bar',data:{labels:D.sectors.map(s=>s.name),datasets:[{data:D.sectors.map(s=>Math.round(100*s.passing/s.total)),backgroundColor:css('--b')}]},
options:{maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{max:100,ticks:{callback:v=>v+'%'}},x:{ticks:{maxRotation:60,font:{size:10}}}}}});
function render(){const sec=$('#sec').value,vd=$('#vd').value;let h='';
D.sectors.forEach(s=>{if(sec&&sec!==s.name)return;const rows=D.picks.filter(p=>p.sector===s.name&&(!vd||p.verdict===vd));if(!rows.length)return;
h+=`<h3>${s.name} <small>${s.passing}/${s.total} pass filters</small></h3><div class="card wrap"><table><tr><th>Stock</th><th>Price</th><th>Score</th><th>Verdict</th><th>Today</th><th>60d</th><th>RSI</th><th>Results</th><th>Entry zone</th><th>Stop</th><th>Target</th></tr>`;
rows.forEach(p=>{const g=p.fund.grade||'N/A';h+=`<tr data-i="${p.id}"><td><b>${p.symbol}</b></td><td>${fmt(p.close)}</td><td>${p.score}</td><td><span class="pill ${cls(p.verdict)}">${p.verdict}</span></td><td class="${p.ret1>=0?'up':'dn'}">${sg(p.ret1)}%</td><td class="${p.ret60>=0?'up':'dn'}">${sg(p.ret60)}%</td><td>${p.rsi}</td><td class="${g==='Strong'?'up':g==='Weak'?'dn':''}">${g}</td><td>${p.entry}</td><td>${p.stop}</td><td>${p.target}</td></tr>`});
h+='</table></div>'});
$('#list').innerHTML=h||'<p>No picks match.</p>';document.querySelectorAll('tr[data-i]').forEach(r=>r.onclick=()=>openM(+r.dataset.i))}
$('#sec').onchange=$('#vd').onchange=render;render();
(function(){const H=D.history,hd=D.health,n=v=>v==null?'-':v;
let h=`<h3>Model check <small>(walk-forward on unseen days)</small></h3><div class="card">${hd.used?'<b class="up">ML ranking is ACTIVE.</b>':'<b>ML ranking is OFF</b>, using rules only.'} ${hd.reason||''}<br>
Validation days: ${n(hd.val_days)} | AUC: ${n(hd.auc)}<br>ML top-5 daily: avg ${n(hd.ml_avg)}%, hit ${n(hd.ml_hit)}%, edge vs average stock ${n(hd.ml_lift)}%<br>Rules top-5 daily: avg ${n(hd.rule_avg)}%, hit ${n(hd.rule_hit)}%, edge ${n(hd.rule_lift)}% (all after 0.2% costs, buy at open, sell at close)</div>`;
h+='<h3>Your track record <small>(all picks are stored in data/history.csv)</small></h3>';
if(!H.n){h+='<div class="card">No finished trades yet. Results fill in automatically from the next trading day.</div>'}
else{h+=`<div class="card">${H.n} trades over ${H.days} days | hit rate <b>${H.hit}%</b> | avg per trade <b>${H.avg}%</b> | BUY: ${H.BUY.n} trades, hit ${n(H.BUY.hit)}%, avg ${n(H.BUY.avg)}% | WATCH: ${H.WATCH.n} trades, hit ${n(H.WATCH.hit)}%<div class="ch" style="height:200px"><canvas id="cv"></canvas></div></div>
<div class="card wrap" style="margin-top:10px"><table><tr><th>Date</th><th>Stock</th><th>Verdict</th><th>Score</th><th>Outcome</th><th>Net return</th></tr>`+H.recent.map(r=>`<tr><td>${r.date}</td><td>${r.symbol}</td><td>${r.verdict}</td><td>${r.score}</td><td>${r.outcome}</td><td class="${r.ret>=0?'up':'dn'}">${sg(r.ret)}%</td></tr>`).join('')+'</table></div>'}
$('#hist').innerHTML=h;
if(H.n)new Chart($('#cv'),{type:'line',data:{labels:H.curve.d,datasets:[{label:'Cumulative % (equal weight, daily)',data:H.curve.v,borderColor:css('--g'),pointRadius:0}]},options:{maintainAspectRatio:false}})})();
function mk(id,cfg){charts.push(new Chart($(id),cfg))}
function openM(i){const p=D.picks[i],c=p.chart,f=p.fund,qs=f.quarters||[];charts.forEach(x=>x.destroy());charts=[];
let t=`<h2>${p.symbol} <small>${p.sector}</small> <span class="pill ${cls(p.verdict)}">${p.verdict}</span></h2>
<p>Price <b>${fmt(p.close)}</b> | Score <b>${p.score}</b> | Entry ${p.entry} | Stop <b class="dn">${p.stop}</b> | Target <b class="up">${p.target}</b></p>
<ul>${p.reasons.map(r=>`<li class="${r.startsWith('Warning')?'warn':''}">${r}</li>`).join('')}</ul>
<div class="grid2"><div class="card"><div class="ch"><canvas id="c1"></canvas></div></div><div class="card"><div class="ch"><canvas id="c2"></canvas></div></div></div>`;
if(qs.length){t+=`<h3>Quarterly results <small>(Rs crore)</small></h3><div class="card"><div class="ch"><canvas id="c3"></canvas></div></div><div class="card wrap" style="margin-top:10px"><table><tr><th>Quarter</th><th>Revenue</th><th>Net profit</th><th>EPS</th><th>Rev YoY</th><th>Profit YoY</th><th>Profit QoQ</th></tr>`+
qs.slice().reverse().map(q=>{const gc=v=>v==null?'-':`<span class="${v>=0?'up':'dn'}">${sg(v)}%</span>`;return `<tr><td>${q.q}</td><td>${fmt(q.rev)}</td><td>${fmt(q.ni)}</td><td>${q.eps??'-'}</td><td>${gc(q.yoy_rev)}</td><td>${gc(q.yoy_ni)}</td><td>${gc(q.qoq_ni)}</td></tr>`}).join('')+`</table></div><p class="mut">Verdict on results: <b>${f.grade}</b>${f.next_result_days!=null&&f.next_result_days>=0?' | Next results in ~'+f.next_result_days+' days':''}</p>`}
else t+='<p class="mut">Quarterly results unavailable from the free data source for this stock.</p>';
$('#mb').innerHTML=t;$('#modal').style.display='block';
const ds=(l,d,col,w)=>({label:l,data:d,borderColor:col,borderWidth:w||1.2,pointRadius:0,tension:.1});
mk('#c1',{type:'line',data:{labels:c.d,datasets:[ds('Price',c.c,css('--tx'),2),ds('EMA20',c.e20,css('--a')),ds('EMA50',c.e50,css('--b')),ds('EMA200',c.e200,css('--r'))]},options:{maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{title:{display:true,text:'Price with moving averages (120 days)'}},scales:{x:{ticks:{maxTicksLimit:6}}}}});
mk('#c2',{type:'bar',data:{labels:c.d,datasets:[{label:'Volume',data:c.v,backgroundColor:css('--b')}]},options:{maintainAspectRatio:false,plugins:{legend:{display:false},title:{display:true,text:'Volume'}},scales:{x:{ticks:{maxTicksLimit:6}}}}});
if(qs.length)mk('#c3',{data:{labels:qs.map(q=>q.q),datasets:[{type:'bar',label:'Revenue',data:qs.map(q=>q.rev),backgroundColor:css('--b'),yAxisID:'y'},{type:'line',label:'Net profit',data:qs.map(q=>q.ni),borderColor:css('--g'),backgroundColor:css('--g'),yAxisID:'y1'}]},options:{maintainAspectRatio:false,scales:{y:{position:'left'},y1:{position:'right',grid:{drawOnChartArea:false}}}}})}
const close=()=>{$('#modal').style.display='none'};$('#x').onclick=close;$('#modal').onclick=e=>{if(e.target.id==='modal')close()};
document.onkeydown=e=>{if(e.key==='Escape')close()};
</script></body></html>"""

def build(payload, outdir="site"):
    os.makedirs(outdir, exist_ok=True)
    open(f"{outdir}/index.html", "w", encoding="utf-8").write(TEMPLATE.replace("__DATA__", json.dumps(payload, separators=(",", ":"))))
    open(f"{outdir}/.nojekyll", "w").close()
