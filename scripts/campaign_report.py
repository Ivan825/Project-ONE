#!/usr/bin/env python3
"""Build an interactive, self-contained HTML report for a campaign.

    python scripts/campaign_report.py campaigns/flagship [-o report.html]

Contents: headline stat tiles, per-outcome distribution plots (every run a dot,
hover for seed), mean trajectories by condition with toggleable series, and the
statistics table. One file, no server.
"""
import argparse
import glob
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign_dir")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    d = args.campaign_dir

    res = json.load(open(os.path.join(d, "results.json")))
    manifest = json.load(open(os.path.join(d, "manifest.json")))

    # Mean trajectories per condition (downsampled x2) for three key series.
    traj = {}
    by_cond = {}
    for p in sorted(glob.glob(os.path.join(d, "runs", "*.json"))):
        r = json.load(open(p))
        by_cond.setdefault(r["condition"], []).append(r["globals"])
    for cond, runs in by_cond.items():
        n = min(len(g) for g in runs)
        ts, series = [], {"population": [], "cooperation": [], "fragmentation": []}
        for i in range(0, n, 2):
            ts.append(runs[0][i]["t"])
            for k in series:
                series[k].append(round(
                    sum(g[i][k] for g in runs) / len(runs), 4))
        traj[cond] = {"t": ts, **series}

    payload = {"stats": res["statistics"], "rows": res["outcomes_per_run"],
               "traj": traj, "manifest": manifest}
    html = TEMPLATE.replace("/*__DATA__*/null", json.dumps(payload))
    out = args.out or os.path.join(d, "report.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"wrote {out} ({os.path.getsize(out)/1e6:.1f} MB)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Project ONE — Flagship Campaign Results</title>
<style>
.viz-root{color-scheme:light;
  --surface-1:#fcfcfb;--surface-2:#f0efec;--grid:#e4e2dc;
  --text-primary:#0b0b0b;--text-secondary:#52514e;--text-muted:#8a8880;
  --A:#2a78d6;--B:#eb6834;--C:#1baf7a;--F:#eda100;--N:#e87ba4;--accent:#e34948}
@media (prefers-color-scheme: dark){
 :root:where(:not([data-theme="light"])) .viz-root{color-scheme:dark;
  --surface-1:#1a1a19;--surface-2:#262624;--grid:#33332f;
  --text-primary:#fff;--text-secondary:#c3c2b7;--text-muted:#807f76;
  --A:#3987e5;--B:#d95926;--C:#199e70;--F:#c98500;--N:#d55181;--accent:#e66767}}
*{box-sizing:border-box;margin:0}
body{font:14px/1.5 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
 background:var(--surface-1);color:var(--text-primary);padding:22px 26px;max-width:1200px;margin:auto}
h1{font-size:20px}
.sub{color:var(--text-secondary);font-size:12.5px;margin:4px 0 18px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin-bottom:20px}
.tile{background:var(--surface-1);border:1px solid var(--grid);border-radius:8px;padding:12px 14px}
.tile .v{font-size:22px;font-weight:700;font-variant-numeric:tabular-nums}
.tile .l{font-size:11.5px;color:var(--text-secondary);margin-top:2px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.card{background:var(--surface-1);border:1px solid var(--grid);border-radius:8px;padding:12px 14px}
.card h3{font-size:12.5px;color:var(--text-secondary);font-weight:600;margin-bottom:8px}
svg{display:block;width:100%}
.legend{display:flex;gap:12px;font-size:12px;color:var(--text-secondary);flex-wrap:wrap;margin-top:6px}
.legend span{cursor:pointer;user-select:none}
.legend .off{opacity:.32;text-decoration:line-through}
.sw{display:inline-block;width:10px;height:10px;border-radius:5px;margin-right:4px;vertical-align:-1px}
.tip{position:fixed;pointer-events:none;background:var(--surface-2);border:1px solid var(--grid);
 border-radius:6px;padding:5px 9px;font-size:12px;display:none;z-index:9;box-shadow:0 2px 8px rgba(0,0,0,.15);
 font-variant-numeric:tabular-nums}
table{border-collapse:collapse;font-size:12px;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:5px 9px;border-bottom:1px solid var(--grid);text-align:right}
th{color:var(--text-secondary)}
td:first-child,th:first-child{text-align:left}
.sig{color:var(--C);font-weight:600}
.ns{color:var(--text-muted)}
.note{font-size:12px;color:var(--text-muted);margin-top:10px}
@media(max-width:860px){.row{grid-template-columns:1fr}}
</style></head><body class="viz-root">
<h1>PROJECT ONE — flagship campaign results</h1>
<div class="sub" id="sub"></div>
<div class="tiles" id="tiles"></div>
<div class="row" id="dists"></div>
<div class="card" style="margin-bottom:14px"><h3>Mean trajectories by condition (click legend to toggle)</h3>
  <div id="trajcharts"></div><div class="legend" id="tlegend"></div></div>
<div class="card"><h3>Statistics — Mann-Whitney U vs. reference, Cliff's δ effect size</h3>
  <div id="stattbl"></div>
  <div class="note">B vs A shows δ = 0.000 on every outcome because condition B is trajectory-identical
  to A under paired seeds: measurement without broadcast is causally inert. The convergence reference
  is N (matched-bandwidth noise), not C, because C's broadcast equals the current state by definition.</div></div>
<div class="tip" id="tip"></div>
<script>
const DATA=/*__DATA__*/null;
const css=k=>getComputedStyle(document.body).getPropertyValue(k).trim();
const COND=["A","B","C","F","N"];
const NAME={A:"A local only",B:"B observed blind",C:"C true feedback",F:"F false feedback",N:"N noise feedback"};
const tip=document.getElementById('tip');
const m=DATA.manifest;
document.getElementById('sub').textContent=
 `${DATA.rows.length} runs · conditions ${m.conditions.join(", ")} × ${m.seeds.length} paired seeds · `+
 `${m.steps} steps · hub-removal shock at t=${m.shock_step} · distortion mode ${m.distortion}`;

// ---- stat tiles ----
const S=DATA.stats;
const tiles=[
 ["δ = "+S.self_model_convergence.F_vs_N.cliffs_delta.toFixed(2),
  "false story vs noise: drift toward the broadcast (perfect separation)"],
 ["p ≈ "+S.self_model_convergence.F_vs_N.p_value.toExponential(1),
  "Mann-Whitney U, F vs N convergence"],
 [(S.cooperation_rate.C_vs_A.median[0]/S.cooperation_rate.C_vs_A.median[1]).toFixed(1)+"×",
  "cooperation under true feedback vs baseline (δ = "+S.cooperation_rate.C_vs_A.cliffs_delta.toFixed(2)+")"],
 ["δ = "+S.fragmentation_post.F_vs_A.cliffs_delta.toFixed(2),
  "fragmentation, false-inverted feedback vs baseline (halved)"],
 ["0.000","every outcome, B vs A — measurement alone is causally inert"],
];
document.getElementById('tiles').innerHTML=tiles.map(([v,l])=>
 `<div class="tile"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');

// ---- distribution strip plots ----
function hash(s){let h=2166136261;for(const c of String(s)){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return (h>>>0)/4294967295;}
const OUTS=[["self_model_convergence","Drift toward broadcast (+ = self-fulfilling)",["C","F","N"]],
 ["cooperation_rate","Cooperation rate (post-transient mean)",COND],
 ["fragmentation_post","Post-shock fragmentation (mean)",COND],
 ["recovery_time_90","Recovery time after shock (steps)",COND]];
for(const [key,title,conds] of OUTS){
  const card=document.createElement('div');card.className='card';
  card.innerHTML=`<h3>${title}</h3>`;
  const W=520,H=210,padL=52,padB=24;
  const rows=DATA.rows.filter(r=>r[key]!=null&&conds.includes(r.condition));
  const vals=rows.map(r=>r[key]);
  const lo=Math.min(...vals),hi=Math.max(...vals),rng=(hi-lo)||1;
  const Y=v=>H-padB-(H-padB-14)*((v-lo)/rng);
  const X=c=>padL+(W-padL-14)*((conds.indexOf(c)+0.5)/conds.length);
  let svg=`<svg viewBox="0 0 ${W} ${H}">`;
  for(const f of [0,0.5,1]){const y=Y(lo+rng*f);
    svg+=`<line x1="${padL}" x2="${W-8}" y1="${y}" y2="${y}" stroke="${css('--grid')}" stroke-width="1"/>`+
    `<text x="${padL-6}" y="${y+4}" text-anchor="end" font-size="10" fill="${css('--text-muted')}">${(lo+rng*f).toPrecision(3)}</text>`;}
  if(lo<0&&hi>0){const y=Y(0);svg+=`<line x1="${padL}" x2="${W-8}" y1="${y}" y2="${y}" stroke="${css('--text-muted')}" stroke-width="1" stroke-dasharray="3 3"/>`;}
  for(const c of conds){
    const cv=rows.filter(r=>r.condition===c);
    // median tick
    const sv=cv.map(r=>r[key]).sort((a,b)=>a-b);
    const med=sv.length%2?sv[(sv.length-1)/2]:(sv[sv.length/2-1]+sv[sv.length/2])/2;
    svg+=`<line x1="${X(c)-22}" x2="${X(c)+22}" y1="${Y(med)}" y2="${Y(med)}" stroke="${css('--text-primary')}" stroke-width="2"/>`;
    for(const r of cv){
      const jx=X(c)+(hash(c+r.seed)-0.5)*34;
      svg+=`<circle cx="${jx}" cy="${Y(r[key])}" r="3.4" fill="${css('--'+c)}" fill-opacity="0.8" stroke="${css('--surface-1')}" stroke-width="1" data-i="${c}|${r.seed}|${r[key]}"/>`;}
    svg+=`<text x="${X(c)}" y="${H-8}" text-anchor="middle" font-size="10.5" fill="${css('--text-secondary')}">${c}</text>`;}
  svg+='</svg>';
  card.innerHTML+=svg;
  document.getElementById('dists').appendChild(card);
  card.querySelectorAll('circle').forEach(el=>{
    el.addEventListener('mousemove',e=>{const [c,s,v]=el.dataset.i.split('|');
      tip.style.display='block';tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY-10)+'px';
      tip.textContent=`${NAME[c]} · seed ${s} · ${(+v).toPrecision(4)}`;});
    el.addEventListener('mouseleave',()=>tip.style.display='none');});
}

// ---- trajectories ----
const hidden=new Set();
const TSER=[["population","Population"],["cooperation","Cooperation"],["fragmentation","Fragmentation"]];
function drawTraj(){
  const host=document.getElementById('trajcharts');host.innerHTML='';
  for(const [key,label] of TSER){
    const W=1100,H=170,padL=46,padB=20;
    let allv=[];
    for(const c of COND)if(!hidden.has(c)&&DATA.traj[c])allv=allv.concat(DATA.traj[c][key]);
    const lo=Math.min(...allv),hi=Math.max(...allv),rng=(hi-lo)||1;
    const T=DATA.traj.A.t,tmax=T[T.length-1];
    const X=t=>padL+(W-padL-10)*(t/tmax), Y=v=>H-padB-(H-padB-16)*((v-lo)/rng);
    let svg=`<svg viewBox="0 0 ${W} ${H}"><text x="${padL}" y="11" font-size="10.5" fill="${css('--text-secondary')}">${label}</text>`;
    for(const f of [0,1]){const y=Y(lo+rng*f);
      svg+=`<line x1="${padL}" x2="${W-8}" y1="${y}" y2="${y}" stroke="${css('--grid')}"/>`+
      `<text x="${padL-5}" y="${y+4}" text-anchor="end" font-size="9.5" fill="${css('--text-muted')}">${(lo+rng*f).toPrecision(3)}</text>`;}
    const shock=DATA.manifest.shock_step;
    svg+=`<line x1="${X(shock)}" x2="${X(shock)}" y1="12" y2="${H-padB}" stroke="${css('--text-muted')}" stroke-dasharray="3 3"/>`;
    for(const c of COND){
      if(hidden.has(c)||!DATA.traj[c])continue;
      const tr=DATA.traj[c];
      let path='M';
      tr.t.forEach((t,i)=>{path+=`${X(t).toFixed(1)},${Y(tr[key][i]).toFixed(1)} `;if(i===0)path+='L';});
      svg+=`<path d="${path}" fill="none" stroke="${css('--'+c)}" stroke-width="1.8"/>`;}
    svg+='</svg>';
    host.innerHTML+=svg;
  }
  document.getElementById('tlegend').innerHTML=COND.map(c=>
   `<span data-c="${c}" class="${hidden.has(c)?'off':''}"><span class="sw" style="background:var(--${c})"></span>${NAME[c]}</span>`).join('');
  document.querySelectorAll('#tlegend span[data-c]').forEach(el=>
   el.addEventListener('click',()=>{const c=el.dataset.c;
     hidden.has(c)?hidden.delete(c):hidden.add(c);drawTraj();}));
}
drawTraj();

// ---- stats table ----
function fm(x,d=4){return typeof x==='number'?(+x).toPrecision(d):x;}
let rows='';
for(const [oname,comps] of Object.entries(S)){
  if(oname==='final_population_medians'||oname==='n_runs')continue;
  for(const [cmp,v] of Object.entries(comps)){
    if(!v||typeof v!=='object'||!('p_value' in v))continue;
    const sig=v.p_value<0.0125; // Bonferroni over 4 primaries
    rows+=`<tr><td>${oname}</td><td>${cmp.replace('_',' ')}</td>`+
      `<td>${fm(v.median[0])}</td><td>${fm(v.median[1])}</td>`+
      `<td class="${sig?'sig':'ns'}">${v.p_value.toExponential(2)}</td>`+
      `<td>${v.cliffs_delta.toFixed(3)}</td></tr>`;}}
document.getElementById('stattbl').innerHTML=
 `<table><tr><th>outcome</th><th>comparison</th><th>median</th><th>ref median</th><th>p</th><th>Cliff's δ</th></tr>${rows}</table>`;
</script></body></html>
"""

if __name__ == "__main__":
    main()
