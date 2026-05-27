import requests
import json
import os
from datetime import datetime, timedelta

# ─── CONFIG ────────────────────────────────────────────────────────────────
API_BASE = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
USER = os.environ["BCENTRAL_USER"]
PASS = os.environ["BCENTRAL_PASS"]

SERIES = {
    "dolar":  "F073.TCO.PRE.Z.D",
    "tpm":    "F022.TPM.TIN.D001.NO.Z.D",
    "ipc":    "F074.IPC.VAR.Z.Z.C.M",
    "imacec": "F032.IMC.IND.Z.Z.EP18.Z.Z.0.M",
}

def fetch(series_id, first, last):
    url = (f"{API_BASE}?user={USER}&pass={PASS}"
           f"&firstdate={first}&lastdate={last}"
           f"&timeseries={series_id}&function=GetSeries")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    print(f"  API response keys: {list(data.keys())}")

    # La API puede devolver Series como dict o como lista
    series = data.get("Series", {})
    if isinstance(series, list):
        series = series[0] if series else {}

    obs = series.get("Obs") if series else None

    # Obs puede venir como None, dict (un solo registro), o lista
    if obs is None:
        print(f"  Aviso: Obs es None para {series_id}, retornando lista vacía")
        return []
    if isinstance(obs, dict):
        obs = [obs]

    result = []
    for o in obs:
        try:
            raw_fecha = o["indexDateString"]
            parts = raw_fecha.split("-")
            # Detectar formato: si el ultimo segmento tiene 4 digitos es DD-MM-YYYY
            if len(parts) == 3 and len(parts[2]) == 4:
                fecha = f"{parts[2]}-{parts[1]}-{parts[0]}"
            # Si el primero tiene 4 digitos ya es YYYY-MM-DD
            elif len(parts) == 3 and len(parts[0]) == 4:
                fecha = raw_fecha
            else:
                fecha = raw_fecha
            result.append({"fecha": fecha, "valor": float(o["value"])})
        except (KeyError, ValueError):
            pass
    # Print first 2 records for debugging
    if result:
        print(f"  Primer registro: {result[0]}")
        print(f"  Ultimo registro: {result[-1]}")
    return result

def build_monthly(dolar, tpm, ipc, imacec):
    by_month = {}
    for d in dolar:
        m = d["fecha"][:7]
        by_month.setdefault(m, {"dolar": [], "tpm": None, "ipc": None, "imacec": None})
        by_month[m]["dolar"].append(d["valor"])
    for d in tpm:
        m = d["fecha"][:7]
        if m in by_month:
            by_month[m]["tpm"] = d["valor"]
    for d in ipc:
        m = d["fecha"][:7]
        if m in by_month:
            by_month[m]["ipc"] = d["valor"]
    for d in imacec:
        m = d["fecha"][:7]
        if m in by_month:
            by_month[m]["imacec"] = d["valor"]

    monthly = []
    for m in sorted(by_month.keys()):
        vals = by_month[m]["dolar"]
        if not vals:
            continue
        monthly.append({
            "mes": m,
            "dolarProm": round(sum(vals) / len(vals), 2),
            "dolarMin":  round(min(vals), 2),
            "dolarMax":  round(max(vals), 2),
            "tpm":    by_month[m]["tpm"],
            "ipc":    by_month[m]["ipc"],
            "imacec": by_month[m]["imacec"],
        })
    return monthly

def main():
    today = datetime.today().strftime("%Y-%m-%d")
    first = (datetime.today() - timedelta(days=365*10)).strftime("%Y-%m-%d")

    print("Fetching dolar...")
    dolar = fetch(SERIES["dolar"], first, today)
    print(f"  {len(dolar)} registros")

    print("Fetching TPM...")
    tpm = fetch(SERIES["tpm"], first, today)
    print(f"  {len(tpm)} registros")
    print("Fetching IPC...")
    ipc = fetch(SERIES["ipc"], first, today)
    print(f"  {len(ipc)} registros")

    print("Fetching IMACEC...")
    imacec = fetch(SERIES["imacec"], first, today)
    print(f"  {len(imacec)} registros")

    monthly = build_monthly(dolar, tpm, ipc, imacec)

    today_dolar = dolar[-1] if dolar else None
    today_tpm = tpm[-1] if tpm else None
    last_ipc    = ipc[-1]   if ipc   else None
    last_imacec = imacec[-1] if imacec else None

    updated_at = datetime.today().strftime("%d/%m/%Y %H:%M UTC")

    # Save data as JSON for reference
    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w") as f:
        json.dump({"monthly": monthly, "today_dolar": today_dolar,
                   "today_tpm": today_tpm, "last_ipc": last_ipc,
                   "last_imacec": last_imacec}, f)

    # ─── Generate HTML ──────────────────────────────────────────────────────
    monthly_json  = json.dumps(monthly)
    dolar_json    = json.dumps(today_dolar)
    tpm_json      = json.dumps(today_tpm)
    ipc_json      = json.dumps(last_ipc)
    imacec_json   = json.dumps(last_imacec)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Monitor Macro Chile</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {{
    --bg:#0d0f14;--surface:#161b27;--surface2:#1e2535;--border:#2a3350;
    --accent:#3b82f6;--accent2:#f59e0b;--accent3:#10b981;--accent4:#ef4444;
    --purple:#a78bfa;--text:#e2e8f0;--muted:#94a3b8;
    --font:'IBM Plex Mono','Courier New',monospace;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);font-family:var(--font);min-height:100vh}}
  header{{padding:20px 28px 16px;border-bottom:1px solid var(--border);
    display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}}
  .logo{{display:flex;align-items:center;gap:12px}}
  .logo-icon{{width:36px;height:36px;background:var(--accent);border-radius:6px;
    display:flex;align-items:center;justify-content:center;font-size:18px}}
  h1{{font-size:16px;letter-spacing:.05em;font-weight:700}}
  .subtitle{{font-size:10px;color:var(--muted);letter-spacing:.1em;margin-top:2px}}
  .live-badge{{display:flex;align-items:center;gap:6px;font-size:10px;color:var(--accent3);
    letter-spacing:.1em;background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.2);
    padding:4px 10px;border-radius:20px}}
  .live-dot{{width:6px;height:6px;background:var(--accent3);border-radius:50%;animation:pulse 2s infinite}}
  @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
  .update-time{{font-size:9px;color:var(--muted)}}
  .kpi-strip{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));
    gap:1px;border-bottom:1px solid var(--border);background:var(--border)}}
  .kpi{{background:var(--surface);padding:14px 20px}}
  .kpi-label{{font-size:9px;color:var(--muted);letter-spacing:.12em;text-transform:uppercase}}
  .kpi-val{{font-size:20px;font-weight:700;margin-top:4px}}
  .kpi-delta{{font-size:9px;margin-top:3px}}
  .kpi-sub{{font-size:8px;color:#374151;margin-top:2px}}
  .up{{color:var(--accent4)}}.down{{color:var(--accent3)}}.neutral{{color:var(--muted)}}
  .toolbar{{padding:10px 20px;border-bottom:1px solid var(--border);
    display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
  .toolbar-label{{font-size:10px;color:var(--muted);letter-spacing:.08em;margin-right:4px}}
  .btn{{padding:5px 12px;border:1px solid var(--border);background:var(--surface2);
    color:var(--muted);font-family:var(--font);font-size:10px;letter-spacing:.08em;
    cursor:pointer;border-radius:4px;transition:all .15s}}
  .btn:hover,.btn.active{{border-color:var(--accent);color:var(--accent);background:rgba(59,130,246,.08)}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--border)}}
  .panel{{background:var(--surface);padding:20px}}
  .panel.full{{grid-column:1/-1}}
  .panel-title{{font-size:10px;letter-spacing:.12em;text-transform:uppercase;
    color:var(--muted);margin-bottom:14px;display:flex;align-items:center;gap:8px}}
  .dot{{width:7px;height:7px;border-radius:50%;display:inline-block}}
  .chart-wrap{{position:relative;height:200px}}
  .chart-wrap-lg{{position:relative;height:250px}}
  .legend{{display:flex;gap:16px;margin-bottom:10px;flex-wrap:wrap}}
  .legend-item{{display:flex;align-items:center;gap:6px;font-size:9px;color:var(--muted)}}
  .today-box{{background:var(--surface2);border:1px solid var(--border);border-radius:6px;
    padding:16px 20px;margin-bottom:16px;display:flex;gap:32px;flex-wrap:wrap}}
  .th-label{{font-size:9px;color:var(--muted);letter-spacing:.1em}}
  .th-val{{font-size:20px;font-weight:700;margin-top:2px}}
  .th-date{{font-size:9px;color:var(--muted);margin-top:2px}}
  .mini-table{{width:100%;border-collapse:collapse;font-size:11px}}
  .mini-table th{{color:var(--muted);font-weight:400;text-align:left;padding:4px 8px;
    border-bottom:1px solid var(--border);font-size:9px;letter-spacing:.08em}}
  .mini-table td{{padding:6px 8px;border-bottom:1px solid rgba(42,51,80,.4)}}
  .mini-table tr:last-child td{{border-bottom:none}}
  .tag{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:700}}
  .tag-up{{background:rgba(239,68,68,.15);color:var(--accent4)}}
  .tag-dn{{background:rgba(16,185,129,.15);color:var(--accent3)}}
  .tag-new{{background:rgba(59,130,246,.15);color:var(--accent)}}
  @media(max-width:700px){{
    .grid{{grid-template-columns:1fr}}
    .panel.full{{grid-column:1}}
    header{{flex-direction:column;align-items:flex-start}}
  }}
</style>
</head>
<body>
<header>
  <div class="logo">
    <div class="logo-icon">🇨🇱</div>
    <div>
      <div style="font-size:10px;color:var(--muted);letter-spacing:.1em">BANCO CENTRAL DE CHILE</div>
      <h1>MONITOR MACROECONÓMICO</h1>
      <div class="subtitle" id="headerSub"></div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
    <div class="live-badge"><div class="live-dot"></div> DATOS DEL DÍA</div>
    <div class="update-time">Actualizado: {updated_at}</div>
  </div>
</header>

<div class="kpi-strip" id="kpiStrip"></div>

<div class="toolbar">
  <span class="toolbar-label">PERÍODO:</span>
  <button class="btn" onclick="setRange(0)"  id="rAll">TODO</button>
  <button class="btn" onclick="setRange(60)" id="r60">5 AÑOS</button>
  <button class="btn active" onclick="setRange(24)" id="r24">2 AÑOS</button>
  <button class="btn" onclick="setRange(12)" id="r12">1 AÑO</button>
  <button class="btn" onclick="setRange(6)"  id="r6">6 MES</button>
</div>

<div class="grid">
  <div class="panel full">
    <div class="panel-title"><span class="dot" style="background:var(--accent)"></span> HOY</div>
    <div class="today-box" id="todayBox"></div>
    <div class="panel-title">
      <span class="dot" style="background:var(--accent)"></span> DÓLAR CLP/USD
      <span class="dot" style="background:var(--accent2);margin-left:8px"></span> TPM %
    </div>
    <div class="legend">
      <div class="legend-item"><span class="dot" style="background:var(--accent)"></span> Dólar prom. mensual (eje izq.)</div>
      <div class="legend-item"><span class="dot" style="background:var(--accent2)"></span> TPM % (eje der.)</div>
    </div>
    <div class="chart-wrap-lg"><canvas id="mainChart"></canvas></div>
  </div>
  <div class="panel">
    <div class="panel-title"><span class="dot" style="background:var(--accent3)"></span> IPC MENSUAL (%)</div>
    <div class="chart-wrap"><canvas id="ipcChart"></canvas></div>
  </div>
  <div class="panel">
    <div class="panel-title"><span class="dot" style="background:var(--purple)"></span> IMACEC</div>
    <div class="chart-wrap"><canvas id="imacecChart"></canvas></div>
  </div>
  <div class="panel full">
    <div class="panel-title"><span class="dot" style="background:var(--muted)"></span> ÚLTIMOS 18 MESES</div>
    <div style="overflow-x:auto"><table class="mini-table" id="dataTable"></table></div>
  </div>
</div>

<script>
const MONTHLY = {monthly_json};
const TODAY_DOLAR  = {dolar_json};
const TODAY_TPM    = {tpm_json};
const LAST_IPC     = {ipc_json};
const LAST_IMACEC  = {imacec_json};

let rangeMonths = 24;
let charts = {{}};

// Header
const first = MONTHLY[0]?.mes || '';
const last  = MONTHLY[MONTHLY.length-1]?.mes || '';
document.getElementById('headerSub').textContent = `Dólar · TPM · IPC · IMACEC — ${{first}} → ${{last}}`;

// KPIs
function renderKPIs() {{
  const last = MONTHLY[MONTHLY.length-1];
  const prev = MONTHLY[MONTHLY.length-2];
  const dolarMax = Math.max(...MONTHLY.map(m => m.dolarMax));
  const items = [
    {{ label:'DÓLAR HOY', val: TODAY_DOLAR ? '$'+TODAY_DOLAR.valor.toFixed(0) : '—', sub: TODAY_DOLAR?.fecha||'' }},
    {{ label:'TPM ACTUAL', val: last.tpm!==null ? last.tpm+'%':'—',
       delta: prev ? last.tpm-prev.tpm : null, unit:'%', upBad:false }},
    {{ label:'IPC ÚLT. MES', val: last.ipc!==null ? (last.ipc>0?'+':'')+last.ipc+'%':'—',
       delta: prev&&last.ipc!==null&&prev.ipc!==null ? last.ipc-prev.ipc : null, unit:'%', upBad:true }},
    {{ label:'IMACEC ÚLT.', val: last.imacec!==null ? last.imacec.toFixed(1):'—',
       delta: prev&&last.imacec!==null&&prev.imacec!==null ? last.imacec-prev.imacec : null, unit:'', upBad:false }},
    {{ label:'MÁX DÓLAR HIST.', val:'$'+dolarMax.toFixed(0), sub:'histórico' }},
    {{ label:'DÓLAR MES ANT.', val: prev ? '$'+prev.dolarProm.toFixed(0):'—', sub:prev?.mes||'' }},
  ];
  document.getElementById('kpiStrip').innerHTML = items.map(k => {{
    let d = '';
    if (k.delta!=null) {{
      const sign = k.delta>=0?'+':'';
      const cls = k.delta===0?'neutral':(k.upBad?(k.delta>0?'up':'down'):(k.delta>0?'down':'up'));
      d = `<div class="kpi-delta ${{cls}}">${{sign}}${{k.delta.toFixed(2)}}${{k.unit}} vs mes ant.</div>`;
    }} else if (k.sub) d = `<div class="kpi-sub">${{k.sub}}</div>`;
    return `<div class="kpi"><div class="kpi-label">${{k.label}}</div><div class="kpi-val">${{k.val}}</div>${{d}}</div>`;
  }}).join('');
}}

// Today box
function renderToday() {{
  document.getElementById('todayBox').innerHTML = `
    <div><div class="th-label">DÓLAR OBSERVADO</div>
      <div class="th-val" style="color:var(--accent)">${{TODAY_DOLAR?'$'+TODAY_DOLAR.valor.toFixed(2):'—'}}</div>
      <div class="th-date">${{TODAY_DOLAR?.fecha||''}}</div></div>
    <div><div class="th-label">TASA POLÍTICA MONETARIA</div>
      <div class="th-val" style="color:var(--accent2)">${{TODAY_TPM?TODAY_TPM.valor+'%':'—'}}</div>
      <div class="th-date">${{TODAY_TPM?.fecha||''}}</div></div>
    <div><div class="th-label">IPC MÁS RECIENTE</div>
      <div class="th-val" style="color:${{LAST_IPC?.valor>0.8?'var(--accent4)':'var(--accent3)'}}">${{LAST_IPC?(LAST_IPC.valor>0?'+':'')+LAST_IPC.valor+'%':'—'}}</div>
      <div class="th-date">${{LAST_IPC?.fecha?.slice(0,7)||''}}</div></div>
    <div><div class="th-label">IMACEC MÁS RECIENTE</div>
      <div class="th-val" style="color:var(--purple)">${{LAST_IMACEC?LAST_IMACEC.valor.toFixed(1):'—'}}</div>
      <div class="th-date">${{LAST_IMACEC?.fecha?.slice(0,7)||''}}</div></div>`;
}}

// Charts
const CB = {{
  responsive:true, maintainAspectRatio:false, animation:{{duration:400}},
  plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'#1e2535',borderColor:'#2a3350',borderWidth:1,
    titleColor:'#94a3b8',bodyColor:'#e2e8f0',
    titleFont:{{family:'IBM Plex Mono,monospace',size:10}},bodyFont:{{family:'IBM Plex Mono,monospace',size:11}}}}}},
  scales:{{
    x:{{grid:{{color:'rgba(42,51,80,.4)'}},ticks:{{color:'#64748b',font:{{size:9}},maxTicksLimit:8}}}},
    y:{{grid:{{color:'rgba(42,51,80,.4)'}},ticks:{{color:'#64748b',font:{{size:9}}}}}}
  }}
}};

function getFiltered() {{
  return rangeMonths ? MONTHLY.slice(-rangeMonths) : MONTHLY;
}}

function destroyChart(id) {{
  if (charts[id]) {{ charts[id].destroy(); delete charts[id]; }}
}}

function renderCharts() {{
  const d = getFiltered();
  const labels = d.map(r => r.mes);

  destroyChart('main');
  charts['main'] = new Chart(document.getElementById('mainChart'), {{
    type:'line', data:{{labels, datasets:[
      {{label:'Dólar',data:d.map(r=>r.dolarProm),borderColor:'#3b82f6',
        backgroundColor:'rgba(59,130,246,.07)',borderWidth:1.5,pointRadius:0,fill:true,tension:.3,yAxisID:'y'}},
      {{label:'TPM',data:d.map(r=>r.tpm),borderColor:'#f59e0b',backgroundColor:'transparent',
        borderWidth:1.5,pointRadius:0,stepped:true,yAxisID:'y2'}}
    ]}},
    options:{{...CB,interaction:{{mode:'index',intersect:false}},scales:{{...CB.scales,
      y:{{...CB.scales.y,title:{{display:true,text:'CLP/USD',color:'#3b82f6',font:{{size:9}}}}}},
      y2:{{position:'right',grid:{{drawOnChartArea:false}},ticks:{{color:'#f59e0b',font:{{size:9}}}},
           title:{{display:true,text:'TPM %',color:'#f59e0b',font:{{size:9}}}}}}
    }}}}
  }});

  destroyChart('ipc');
  const ipcVals = d.map(r=>r.ipc);
  charts['ipc'] = new Chart(document.getElementById('ipcChart'), {{
    type:'bar', data:{{labels, datasets:[{{label:'IPC %',data:ipcVals,borderRadius:2,
      backgroundColor:ipcVals.map(v=>v===null?'transparent':v<0?'rgba(16,185,129,.7)':v>0.8?'rgba(239,68,68,.65)':'rgba(59,130,246,.5)')
    }}]}},
    options:CB
  }});

  destroyChart('imacec');
  charts['imacec'] = new Chart(document.getElementById('imacecChart'), {{
    type:'line', data:{{labels, datasets:[{{label:'IMACEC',data:d.map(r=>r.imacec),
      borderColor:'#a78bfa',backgroundColor:'rgba(167,139,250,.07)',
      borderWidth:1.5,pointRadius:0,fill:true,tension:.4
    }}]}},
    options:CB
  }});
}}

// Table
function renderTable() {{
  const last18 = MONTHLY.slice(-18).reverse();
  const todayMes = TODAY_DOLAR?.fecha?.slice(0,7);
  document.getElementById('dataTable').innerHTML = `
    <thead><tr><th>MES</th><th>DÓLAR PROM</th><th>MÍN</th><th>MÁX</th><th>TPM</th><th>IPC</th><th>IMACEC</th></tr></thead>
    <tbody>${{last18.map((r,i) => {{
      const prev = last18[i+1];
      const dd = prev ? r.dolarProm - prev.dolarProm : 0;
      const tag = prev ? `<span class="tag ${{dd>0?'tag-up':'tag-dn'}}">${{dd>0?'▲':'▼'}}</span>` : '';
      const isNow = r.mes===todayMes;
      return `<tr><td>${{r.mes}} ${{isNow?'<span class="tag tag-new">HOY</span>':''}}</td>
        <td>$${{r.dolarProm.toFixed(0)}} ${{tag}}</td>
        <td style="color:var(--accent3)">$${{r.dolarMin.toFixed(0)}}</td>
        <td style="color:var(--accent4)">$${{r.dolarMax.toFixed(0)}}</td>
        <td style="color:var(--accent2)">${{r.tpm!==null?r.tpm+'%':'—'}}</td>
        <td style="color:${{r.ipc>0.8?'var(--accent4)':r.ipc<0?'var(--accent3)':'var(--text)'}}">${{r.ipc!==null?(r.ipc>0?'+':'')+r.ipc+'%':'—'}}</td>
        <td>${{r.imacec!==null?r.imacec.toFixed(1):'—'}}</td></tr>`;
    }}).join('')}}</tbody>`;
}}

function setRange(m) {{
  rangeMonths = m;
  ['rAll','r60','r24','r12','r6'].forEach(id => document.getElementById(id).classList.remove('active'));
  const map = {{0:'rAll',60:'r60',24:'r24',12:'r12',6:'r6'}};
  if (map[m]) document.getElementById(map[m]).classList.add('active');
  renderCharts();
}}

renderKPIs();
renderToday();
renderCharts();
renderTable();
</script>
</body>
</html>"""

    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Dashboard generado: docs/index.html ({len(html)//1024}KB)")
    print(f"   Dólar hoy: {today_dolar}")
    print(f"   TPM: {today_tpm}")
    print(f"   IPC: {last_ipc}")

if __name__ == "__main__":
    main()
