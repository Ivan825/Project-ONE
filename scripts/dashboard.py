#!/usr/bin/env python3
"""Generate a self-contained HTML dashboard from a run directory.

Usage:
    python scripts/dashboard.py runs/C_s42_n2000 [-o dashboard.html]

The output is a single file: macrostate timelines, an animated force-layout
network with a time scrubber, and a per-agent inspector. No server needed.
"""
import argparse
import json
import os


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rundir")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(args.rundir, "config.json")))
    globals_ = load_jsonl(os.path.join(args.rundir, "global_states.jsonl"))
    snaps = load_jsonl(os.path.join(args.rundir, "snapshots.jsonl"))
    nodes = load_jsonl(os.path.join(args.rundir, "nodes.jsonl"))
    if not snaps:
        raise SystemExit("No snapshots.jsonl in this run (re-run with "
                         "snapshot_interval > 0) — dashboard needs snapshots.")

    payload = {
        "config": {k: cfg.get(k) for k in
                   ("condition", "seed", "steps", "distortion", "shock_step",
                    "initial_population")},
        "globals": globals_,
        "snapshots": snaps,
        "agents": {str(n["id"]): n for n in nodes},
    }
    html = TEMPLATE.replace("/*__DATA__*/null", json.dumps(payload))
    out = args.out or os.path.join(args.rundir, "dashboard.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"wrote {out}  ({os.path.getsize(out)/1e6:.1f} MB, "
          f"{len(snaps)} snapshots, {len(globals_)} global states)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Project ONE — Run Dashboard</title>
<style>
.viz-root{
  color-scheme: light;
  --surface-1:#fcfcfb; --surface-2:#f0efec;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --text-muted:#8a8880;
  --grid:#e4e2dc; --series-1:#2a78d6; --accent:#eb6834;
  --ramp-250:#86b6ef; --ramp-350:#5598e7; --ramp-450:#2a78d6; --ramp-550:#1c5cab; --ramp-650:#104281;
}
@media (prefers-color-scheme: dark){
  :root:where(:not([data-theme="light"])) .viz-root{
    color-scheme: dark;
    --surface-1:#1a1a19; --surface-2:#262624;
    --text-primary:#ffffff; --text-secondary:#c3c2b7; --text-muted:#807f76;
    --grid:#33332f; --series-1:#3987e5; --accent:#d95926;
    --ramp-250:#86b6ef; --ramp-350:#5598e7; --ramp-450:#3987e5; --ramp-550:#1c5cab; --ramp-650:#184f95;
  }
}
*{box-sizing:border-box;margin:0}
body{font:14px/1.45 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
     background:var(--surface-1);color:var(--text-primary);padding:20px 24px}
h1{font-size:19px;letter-spacing:.2px}
.sub{color:var(--text-secondary);font-size:12.5px;margin:3px 0 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin-bottom:18px}
.card{background:var(--surface-1);border:1px solid var(--grid);border-radius:8px;padding:10px 12px 6px}
.card h3{font-size:12px;color:var(--text-secondary);font-weight:600;margin-bottom:2px}
.card .cur{font-size:16px;font-weight:700;font-variant-numeric:tabular-nums}
.main{display:grid;grid-template-columns:1fr 300px;gap:14px}
#netcard{position:relative}
#net{width:100%;height:520px;display:block;border-radius:6px}
.controls{display:flex;align-items:center;gap:10px;margin-top:8px;font-size:12px;color:var(--text-secondary)}
.controls input[type=range]{flex:1;accent-color:var(--series-1)}
button,select{background:var(--surface-2);color:var(--text-primary);border:1px solid var(--grid);
       border-radius:6px;padding:4px 12px;font-size:12.5px;cursor:pointer}
button:hover{border-color:var(--text-muted)}
#inspector{font-size:12.5px}
#inspector h3{font-size:13px;margin-bottom:6px}
#inspector table{width:100%;border-collapse:collapse}
#inspector td{padding:2.5px 4px;border-bottom:1px solid var(--grid)}
#inspector td:first-child{color:var(--text-secondary)}
#inspector td:last-child{text-align:right;font-variant-numeric:tabular-nums}
.hint{color:var(--text-muted);font-size:12px;margin-top:8px}
.tip{position:fixed;pointer-events:none;background:var(--surface-2);border:1px solid var(--grid);
     border-radius:6px;padding:5px 9px;font-size:12px;display:none;z-index:9;
     font-variant-numeric:tabular-nums;box-shadow:0 2px 8px rgba(0,0,0,.12)}
details{margin-top:18px}
summary{cursor:pointer;color:var(--text-secondary);font-size:13px}
#dtable{width:100%;border-collapse:collapse;font-size:11.5px;margin-top:8px;font-variant-numeric:tabular-nums}
#dtable th,#dtable td{padding:3px 8px;border-bottom:1px solid var(--grid);text-align:right}
#dtable th{color:var(--text-secondary);position:sticky;top:0;background:var(--surface-1)}
.legend{display:flex;gap:14px;align-items:center;font-size:11.5px;color:var(--text-secondary);margin-top:6px;flex-wrap:wrap}
.sw{display:inline-block;width:10px;height:10px;border-radius:5px;margin-right:4px;vertical-align:-1px}
</style></head>
<body class="viz-root">
<h1>PROJECT ONE — run dashboard</h1>
<div class="sub" id="meta"></div>
<div class="grid" id="charts"></div>
<div class="main">
  <div class="card" id="netcard">
    <h3>Network through time <span id="snaplabel" style="font-weight:400"></span></h3>
    <canvas id="net"></canvas>
    <div class="controls">
      <button id="play">▶ Play</button>
      <select id="speed">
        <option value="900">slow</option>
        <option value="450" selected>normal</option>
        <option value="180">fast</option>
      </select>
      <input type="range" id="scrub" min="0" value="0">
      <span id="tlabel"></span>
    </div>
    <div class="legend"><span><span class="sw" style="background:var(--ramp-250)"></span>early generation</span>
      <span><span class="sw" style="background:var(--ramp-650)"></span>late generation</span>
      <span>node size = energy</span>
      <span><span class="sw" style="background:var(--accent)"></span>selected</span></div>
  </div>
  <div class="card"><div id="inspector"><h3>Agent inspector</h3>
    <div class="hint">Click a node to inspect its traits, lineage and fate.</div></div></div>
</div>
<details><summary>Data table — global states S(t)</summary>
  <div style="max-height:300px;overflow:auto"><table id="dtable"></table></div></details>
<div class="tip" id="tip"></div>
<script>
const DATA = /*__DATA__*/null;
const css = k => getComputedStyle(document.body).getPropertyValue(k).trim();

// ---------- header ----------
const c = DATA.config;
document.getElementById('meta').textContent =
  `condition ${c.condition}` + (c.condition==='F' ? ` (${c.distortion})` : '') +
  ` · seed ${c.seed} · ${c.steps} steps · initial population ${c.initial_population}` +
  (c.shock_step ? ` · shock at t=${c.shock_step}` : '');

// ---------- timeline small multiples ----------
const SERIES = [["population","Population",0],["fragmentation","Fragmentation",1],
  ["cooperation","Cooperation rate",1],["centralization","Centralization",1],
  ["inequality","Inequality (Gini)",1],["turnover","Turnover",1]];
const G = DATA.globals, tip = document.getElementById('tip');
function chart(key,label,norm){
  const card=document.createElement('div');card.className='card';
  card.innerHTML=`<h3>${label}</h3><div class="cur"></div><canvas height="90"></canvas>`;
  document.getElementById('charts').appendChild(card);
  const cv=card.querySelector('canvas'), cur=card.querySelector('.cur');
  const xs=G.map(g=>g.t), ys=G.map(g=>g[key]??0);
  cur.textContent = (norm? ys[ys.length-1].toFixed(3) : ys[ys.length-1]);
  function draw(hoverI){
    const W=cv.clientWidth, H=cv.height, dpr=window.devicePixelRatio||1;
    cv.width=W*dpr; cv.style.width=W+'px';
    const ctx=cv.getContext('2d'); ctx.scale(dpr,1); ctx.clearRect(0,0,W,H);
    const ymax=norm?Math.max(1e-9,Math.max(...ys)):Math.max(...ys)*1.08, pad=4;
    const X=i=>pad+(W-2*pad)*(xs[i]-xs[0])/Math.max(1,xs[xs.length-1]-xs[0]);
    const Y=v=>H-8-(H-16)*(v/ymax);
    ctx.strokeStyle=css('--grid');ctx.lineWidth=1;
    [0.5].forEach(f=>{ctx.beginPath();ctx.moveTo(pad,Y(ymax*f));ctx.lineTo(W-pad,Y(ymax*f));ctx.stroke();});
    if(c.shock_step){const sx=pad+(W-2*pad)*(c.shock_step-xs[0])/Math.max(1,xs[xs.length-1]-xs[0]);
      ctx.strokeStyle=css('--accent');ctx.setLineDash([3,3]);ctx.beginPath();
      ctx.moveTo(sx,4);ctx.lineTo(sx,H-4);ctx.stroke();ctx.setLineDash([]);}
    ctx.strokeStyle=css('--series-1');ctx.lineWidth=2;ctx.lineJoin='round';ctx.beginPath();
    ys.forEach((v,i)=>i?ctx.lineTo(X(i),Y(v)):ctx.moveTo(X(i),Y(v)));ctx.stroke();
    if(hoverI!=null){ctx.strokeStyle=css('--text-muted');ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(X(hoverI),4);ctx.lineTo(X(hoverI),H-4);ctx.stroke();
      ctx.fillStyle=css('--series-1');ctx.beginPath();
      ctx.arc(X(hoverI),Y(ys[hoverI]),3.5,0,7);ctx.fill();
      ctx.strokeStyle=css('--surface-1');ctx.lineWidth=2;ctx.beginPath();
      ctx.arc(X(hoverI),Y(ys[hoverI]),3.5,0,7);ctx.stroke();}
  }
  cv.addEventListener('mousemove',e=>{
    const r=cv.getBoundingClientRect();
    const i=Math.round((e.clientX-r.left-4)/(r.width-8)*(xs.length-1));
    if(i<0||i>=xs.length)return;
    draw(i);
    tip.style.display='block';tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY-10)+'px';
    tip.textContent=`t=${xs[i]}  ${label}: ${norm?ys[i].toFixed(3):ys[i]}`;
  });
  cv.addEventListener('mouseleave',()=>{tip.style.display='none';draw(null);});
  new ResizeObserver(()=>draw(null)).observe(card);
  draw(null);
}
SERIES.forEach(s=>chart(...s));

// ---------- data table ----------
const tbl=document.getElementById('dtable');
const cols=['t','population','components','fragmentation','cooperation','centralization','inequality','turnover','mean_degree'];
tbl.innerHTML='<tr>'+cols.map(k=>`<th>${k}</th>`).join('')+'</tr>'+
  G.map(g=>'<tr>'+cols.map(k=>{const v=g[k];return `<td>${typeof v==='number'&&!Number.isInteger(v)?v.toFixed(3):(v??'')}</td>`}).join('')+'</tr>').join('');

// ---------- network with time scrubber ----------
const SN=DATA.snapshots, net=document.getElementById('net'), nctx=net.getContext('2d');
const scrub=document.getElementById('scrub'); scrub.max=SN.length-1;
let cur=0, sel=null, playing=false;
const pos={};  // persistent positions across snapshots
function hash(n){let h=2166136261;const s=String(n);for(const ch of s){h^=ch.charCodeAt(0);h=Math.imul(h,16777619)}return (h>>>0)/4294967295;}
function ensure(id,W,H){if(!pos[id])pos[id]={x:W*(0.15+0.7*hash(id)),y:H*(0.15+0.7*hash(id+'y')),vx:0,vy:0};return pos[id];}
function layoutStep(snap,W,H){
  const ids=snap.nodes.map(n=>n[0]), idset=new Set(ids);
  const k=18*Math.sqrt(W*H/Math.max(1,ids.length))/120;
  ids.forEach(id=>ensure(id,W,H));
  // repulsion (grid-bucketed for speed)
  for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){
    const a=pos[ids[i]],b=pos[ids[j]];let dx=a.x-b.x,dy=a.y-b.y;
    let d2=dx*dx+dy*dy;if(d2<1)d2=1;if(d2>16000)continue;
    const f=900*k/d2;const d=Math.sqrt(d2);dx/=d;dy/=d;
    a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f;}
  // springs
  snap.edges.forEach(([u,v])=>{if(!idset.has(u)||!idset.has(v))return;
    const a=pos[u],b=pos[v];let dx=b.x-a.x,dy=b.y-a.y;
    const d=Math.max(1,Math.hypot(dx,dy)),f=(d-45)*0.015;dx/=d;dy/=d;
    a.vx+=dx*f*d*0.02;a.vy+=dy*f*d*0.02;b.vx-=dx*f*d*0.02;b.vy-=dy*f*d*0.02;});
  // center pull + integrate
  ids.forEach(id=>{const p=pos[id];
    p.vx+=(W/2-p.x)*0.012;p.vy+=(H/2-p.y)*0.012;
    p.vx*=0.6;p.vy*=0.6;p.x+=p.vx;p.y+=p.vy;
    p.x=Math.max(8,Math.min(W-8,p.x));p.y=Math.max(8,Math.min(H-8,p.y));});
}
function genColor(gen,maxGen){
  const ramp=['--ramp-250','--ramp-350','--ramp-450','--ramp-550','--ramp-650'];
  const i=Math.min(ramp.length-1,Math.floor(gen/Math.max(1,maxGen)* (ramp.length-1) +1e-9));
  return css(ramp[i]);
}
function drawNet(){
  const W=net.clientWidth,H=520,dpr=window.devicePixelRatio||1;
  net.width=W*dpr;net.height=H*dpr;net.style.height=H+'px';
  nctx.setTransform(dpr,0,0,dpr,0,0);nctx.clearRect(0,0,W,H);
  const snap=SN[cur];if(!snap)return;
  const maxGen=Math.max(1,...snap.nodes.map(n=>n[2]));
  nctx.strokeStyle=css('--grid');nctx.lineWidth=1;nctx.globalAlpha=0.85;
  const idset=new Set(snap.nodes.map(n=>n[0]));
  snap.edges.forEach(([u,v])=>{if(!idset.has(u)||!idset.has(v))return;
    const a=pos[u],b=pos[v];if(!a||!b)return;
    nctx.beginPath();nctx.moveTo(a.x,a.y);nctx.lineTo(b.x,b.y);nctx.stroke();});
  nctx.globalAlpha=1;
  snap.nodes.forEach(([id,en,gen])=>{const p=pos[id];if(!p)return;
    const r=3+Math.min(6,Math.sqrt(Math.max(0,en))*0.55);
    nctx.fillStyle=(id===sel)?css('--accent'):genColor(gen,maxGen);
    nctx.beginPath();nctx.arc(p.x,p.y,r,0,7);nctx.fill();
    nctx.strokeStyle=css('--surface-1');nctx.lineWidth=2;nctx.stroke();});
  document.getElementById('snaplabel').textContent=`— t=${snap.t}, ${snap.nodes.length} alive, ${snap.edges.length} edges`;
  document.getElementById('tlabel').textContent=`t=${snap.t}`;
}
function tick(){for(let i=0;i<3;i++)layoutStep(SN[cur],net.clientWidth,520);drawNet();requestAnimationFrame(tick);}
scrub.addEventListener('input',()=>{cur=+scrub.value;});
document.getElementById('play').addEventListener('click',function(){
  playing=!playing;this.textContent=playing?'⏸ Pause':'▶ Play';
  if(playing){const step=()=>{if(!playing)return;
    cur=(cur+1)%SN.length;scrub.value=cur;
    if(cur===SN.length-1)playing=false,this.textContent='▶ Play';
    else setTimeout(step,+document.getElementById('speed').value);};step();}
});
net.addEventListener('click',e=>{
  const r=net.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
  let best=null,bd=400;
  SN[cur].nodes.forEach(([id])=>{const p=pos[id];if(!p)return;
    const d=(p.x-x)**2+(p.y-y)**2;if(d<bd){bd=d;best=id;}});
  sel=best; inspect(best);
});
function inspect(id){
  const el=document.getElementById('inspector');
  if(id==null){el.innerHTML='<h3>Agent inspector</h3><div class="hint">Click a node to inspect.</div>';return;}
  const a=DATA.agents[String(id)]||{};
  const tr=a.traits||{};
  const rows=[["id",id],["generation",a.generation],["parent",a.parent??"—"],
    ["born t",a.birth],["died t",a.death??"alive at end"],["cause",a.cause??"—"],
    ["age",a.age],["offspring",a.offspring],
    ...Object.entries(tr).map(([k,v])=>[k,(+v).toFixed(3)])];
  // lineage chain upward
  let chain=[],p=a.parent,guard=0;
  while(p!=null&&guard++<8){chain.push(p);p=(DATA.agents[String(p)]||{}).parent;}
  el.innerHTML='<h3>Agent '+id+'</h3><table>'+
    rows.map(([k,v])=>`<tr><td>${k}</td><td>${v??"—"}</td></tr>`).join('')+'</table>'+
    (chain.length?`<div class="hint">ancestry: ${chain.join(' ← ')}</div>`:'<div class="hint">founding agent</div>');
}
tick();
</script></body></html>
"""

if __name__ == "__main__":
    main()
