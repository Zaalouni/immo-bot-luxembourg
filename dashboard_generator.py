#!/usr/bin/env python3
# =============================================================================
# dashboard_generator.py — Generateur de dashboard HTML pour immo-bot
# =============================================================================
# Usage : python dashboard_generator.py
# Output: dashboards/index.html  (standalone, ouvre dans navigateur)
#         dashboards/archives/YYYY-MM-DD.html
#         dashboards/data/listings.json
# =============================================================================
import sqlite3, json, os, sys
from datetime import datetime
from pathlib import Path

DB_PATH = 'listings.db'
OUT_DIR = Path('dashboards')
ARCHIVES_DIR = OUT_DIR / 'archives'
DATA_DIR = OUT_DIR / 'data'


def load_listings():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT id, listing_id, site, title, city, price, rooms, surface,
                        url, latitude, longitude, distance_km, created_at, notified
                 FROM listings ORDER BY created_at DESC''')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def calc_stats(listings):
    if not listings:
        return {}
    prices   = [l['price']       for l in listings if l.get('price')       and l['price']   > 0]
    surfaces = [l['surface']     for l in listings if l.get('surface')     and l['surface'] > 0]
    dists    = [l['distance_km'] for l in listings if l.get('distance_km') is not None]
    by_site  = {}
    for l in listings:
        s = l.get('site', '?')
        by_site[s] = by_site.get(s, 0) + 1
    pm2 = [round(l['price'] / l['surface'], 1) for l in listings
           if l.get('price') and l.get('surface') and l['price'] > 0 and l['surface'] > 0]
    return {
        'total':        len(listings),
        'notified':     sum(1 for l in listings if l.get('notified')),
        'avg_price':    round(sum(prices) / len(prices))    if prices   else 0,
        'min_price':    min(prices)                         if prices   else 0,
        'max_price':    max(prices)                         if prices   else 0,
        'avg_surface':  round(sum(surfaces) / len(surfaces)) if surfaces else 0,
        'avg_distance': round(sum(dists) / len(dists), 1)  if dists    else None,
        'by_site':      by_site,
        'avg_prix_m2':  round(sum(pm2) / len(pm2), 1)      if pm2      else 0,
    }


def generate_html(listings, stats, generated_at):
    listings_json = json.dumps(listings, ensure_ascii=False, default=str)

    sites    = sorted(set(l.get('site', '')  for l in listings if l.get('site')))
    cities   = sorted(set(l.get('city', '')  for l in listings if l.get('city')),
                      key=lambda x: x.lower())

    sites_options  = '\n'.join(f'<option value="{s}">{s}</option>' for s in sites)
    cities_options = '\n'.join(f'<option value="{c}">{c}</option>' for c in cities)

    by_site_badges = ' '.join(
        f'<span class="badge bg-secondary me-1">{site}: {count}</span>'
        for site, count in sorted(stats.get('by_site', {}).items())
    )

    avg_dist_str = (f"{stats['avg_distance']} km" if stats.get('avg_distance') is not None else 'N/A')

    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Immo Bot Luxembourg — Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.datatables.net/1.13.8/css/dataTables.bootstrap5.min.css" rel="stylesheet">
<link href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" rel="stylesheet">
<style>
  body {{ background:#f8f9fa; font-size:.9rem; }}
  .stat-card {{ border-radius:12px; border:none; box-shadow:0 2px 8px rgba(0,0,0,.08); }}
  .stat-val  {{ font-size:1.8rem; font-weight:700; line-height:1; }}
  .stat-label {{ font-size:.75rem; color:#6c757d; text-transform:uppercase; letter-spacing:.05em; }}
  #map {{ height:380px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.08); }}
  .filter-card, .table-container {{ border-radius:12px; border:none; box-shadow:0 2px 8px rgba(0,0,0,.08); background:white; }}
  .badge-site {{ font-size:.7rem; padding:.25em .5em; }}
  #compare-btn {{ display:none; }}
  a.al {{ text-decoration:none; color:#0d6efd; }}
  a.al:hover {{ text-decoration:underline; }}
  .pm2 {{ font-size:.75rem; color:#6c757d; }}
  th {{ white-space:nowrap; }}
</style>
</head>
<body>

<nav class="navbar navbar-dark bg-dark mb-4">
  <div class="container-fluid">
    <span class="navbar-brand fw-bold">🏠 Immo Bot Luxembourg</span>
    <span class="text-secondary small">Mis à jour : {generated_at}</span>
  </div>
</nav>

<div class="container-fluid px-4">

<!-- STATS -->
<div class="row g-3 mb-4">
  <div class="col-6 col-md-2"><div class="card stat-card h-100"><div class="card-body text-center">
    <div class="stat-val text-primary">{stats.get('total',0)}</div><div class="stat-label">Annonces</div>
  </div></div></div>
  <div class="col-6 col-md-2"><div class="card stat-card h-100"><div class="card-body text-center">
    <div class="stat-val text-success">{stats.get('avg_price',0):,}€</div><div class="stat-label">Prix moyen</div>
  </div></div></div>
  <div class="col-6 col-md-2"><div class="card stat-card h-100"><div class="card-body text-center">
    <div class="stat-val text-info">{stats.get('avg_surface',0)} m²</div><div class="stat-label">Surface moy.</div>
  </div></div></div>
  <div class="col-6 col-md-2"><div class="card stat-card h-100"><div class="card-body text-center">
    <div class="stat-val text-warning">{stats.get('avg_prix_m2',0)}€</div><div class="stat-label">€/m² moyen</div>
  </div></div></div>
  <div class="col-6 col-md-2"><div class="card stat-card h-100"><div class="card-body text-center">
    <div class="stat-val text-danger">{stats.get('min_price',0):,}€</div><div class="stat-label">Prix min</div>
  </div></div></div>
  <div class="col-6 col-md-2"><div class="card stat-card h-100"><div class="card-body text-center">
    <div class="stat-val">{stats.get('max_price',0):,}€</div><div class="stat-label">Prix max</div>
  </div></div></div>
</div>

<div class="card filter-card mb-3 p-2">
  <span class="text-muted small me-2">Sites :</span>{by_site_badges}
  <span class="ms-3 text-muted small">Notifiées : <strong>{stats.get('notified',0)}</strong></span>
  <span class="ms-3 text-muted small">Distance moy. : <strong>{avg_dist_str}</strong></span>
</div>

<!-- FILTRES -->
<div class="card filter-card mb-4">
  <div class="card-header fw-semibold py-2">🔍 Filtres</div>
  <div class="card-body">
    <div class="row g-2 align-items-end">
      <div class="col-12 col-md-2">
        <label class="form-label mb-1 small">Site</label>
        <select id="f-site" class="form-select form-select-sm" multiple size="3">
          {sites_options}
        </select>
      </div>
      <div class="col-12 col-md-2">
        <label class="form-label mb-1 small">Ville</label>
        <select id="f-city" class="form-select form-select-sm" multiple size="3">
          {cities_options}
        </select>
      </div>
      <div class="col-6 col-md-1">
        <label class="form-label mb-1 small">Prix min €</label>
        <input id="f-pmin" type="number" class="form-control form-control-sm" placeholder="1000" step="100">
      </div>
      <div class="col-6 col-md-1">
        <label class="form-label mb-1 small">Prix max €</label>
        <input id="f-pmax" type="number" class="form-control form-control-sm" placeholder="3000" step="100">
      </div>
      <div class="col-6 col-md-1">
        <label class="form-label mb-1 small">Surface min m²</label>
        <input id="f-smin" type="number" class="form-control form-control-sm" placeholder="0">
      </div>
      <div class="col-6 col-md-1">
        <label class="form-label mb-1 small">Pièces</label>
        <select id="f-rooms" class="form-select form-select-sm">
          <option value="">Toutes</option>
          <option value="1">1</option><option value="2">2</option>
          <option value="3">3</option><option value="4">4+</option>
        </select>
      </div>
      <div class="col-6 col-md-1">
        <label class="form-label mb-1 small">Dist. max km</label>
        <input id="f-dmax" type="number" class="form-control form-control-sm" placeholder="15">
      </div>
      <div class="col-6 col-md-1">
        <label class="form-label mb-1 small">Notifié</label>
        <select id="f-notif" class="form-select form-select-sm">
          <option value="">Tous</option>
          <option value="1">Oui</option><option value="0">Non</option>
        </select>
      </div>
      <div class="col-12 col-md-2 d-flex gap-2">
        <button class="btn btn-primary btn-sm w-100" onclick="applyFilters()">Appliquer</button>
        <button class="btn btn-outline-secondary btn-sm w-100" onclick="resetFilters()">Reset</button>
      </div>
    </div>
  </div>
</div>

<div class="mb-3">
  <button id="compare-btn" class="btn btn-warning btn-sm" onclick="openCompare()">
    ⚖️ Comparer (<span id="cmp-cnt">0</span> sélectionnées)
  </button>
</div>

<!-- TABLEAU -->
<div class="table-container mb-4" style="overflow-x:auto">
  <table id="tbl" class="table table-hover table-sm table-bordered mb-0" style="width:100%">
    <thead class="table-dark">
      <tr>
        <th><input type="checkbox" id="chk-all" onchange="toggleAll(this)"></th>
        <th>Site</th><th>Ville</th><th>Prix €</th><th>m²</th><th>€/m²</th>
        <th>Pièces</th><th>Distance</th><th>Titre</th><th>Date</th><th>✉️</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
</div>

<!-- CARTE -->
<div class="card filter-card mb-5">
  <div class="card-header fw-semibold py-2">🗺️ Carte des annonces géolocalisées</div>
  <div class="card-body p-2"><div id="map"></div></div>
</div>

</div>

<!-- MODAL COMPARATEUR -->
<div class="modal fade" id="cmp-modal" tabindex="-1">
  <div class="modal-dialog modal-xl modal-dialog-scrollable">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">⚖️ Comparateur</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body" id="cmp-body"></div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.8/js/dataTables.bootstrap5.min.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const ALL = {listings_json};
let filtered = [...ALL];
let cmpSet = new Set();
let dt, mapObj, mapMarkers = [];

const SITE_COLORS = {{
  'Athome.lu':'bg-primary','Immotop.lu':'bg-success','Luxhome.lu':'bg-info text-dark',
  'VIVI.lu':'bg-warning text-dark','Nextimmo.lu':'bg-secondary','Newimmo.lu':'bg-danger',
  'Unicorn.lu':'bg-dark','Wortimmo.lu':'bg-primary'
}};

window.addEventListener('DOMContentLoaded', () => {{ render(filtered); initMap(); }});

function fmt(n) {{ return n != null ? Number(n).toLocaleString('fr-FR') : '—'; }}
function trunc(s,n) {{ return s && s.length>n ? s.slice(0,n)+'…' : (s||'—'); }}
function dBadge(d) {{
  if(d==null) return 'bg-secondary';
  return d<2?'bg-success':d<5?'bg-primary':d<10?'bg-warning text-dark':'bg-danger';
}}
function dColor(d) {{
  if(d==null) return '#6c757d';
  return d<2?'#198754':d<5?'#0d6efd':d<10?'#ffc107':'#dc3545';
}}

function render(data) {{
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  data.forEach(l => {{
    const pm2 = (l.price>0&&l.surface>0) ? Math.round(l.price/l.surface*10)/10 : '';
    const dist = l.distance_km!=null
      ? `<span class="badge ${{dBadge(l.distance_km)}}">${{l.distance_km.toFixed(1)}} km</span>`
      : '<span class="text-muted small">—</span>';
    const site = l.site||'—';
    const sc = SITE_COLORS[site]||'bg-secondary';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><input type="checkbox" class="cchk" value="${{l.id}}" onchange="togCmp(${{l.id}},this)"></td>
      <td><span class="badge ${{sc}} badge-site">${{site}}</span></td>
      <td>${{l.city||'—'}}</td>
      <td class="fw-bold">${{l.price?fmt(l.price)+' €':'—'}}</td>
      <td>${{l.surface||'—'}}</td>
      <td class="pm2">${{pm2?pm2+' €':'—'}}</td>
      <td>${{l.rooms||'—'}}</td>
      <td>${{dist}}</td>
      <td><a class="al" href="${{l.url}}" target="_blank" title="${{l.title}}">${{trunc(l.title,55)}}</a></td>
      <td class="text-muted small">${{l.created_at?l.created_at.slice(0,10):'—'}}</td>
      <td class="text-center">${{l.notified?'✅':''}}</td>`;
    tbody.appendChild(tr);
  }});
  if(dt) {{ dt.destroy(); }}
  dt = $('#tbl').DataTable({{
    paging:true, pageLength:25, ordering:true, order:[[3,'asc']], searching:true,
    language:{{ url:'https://cdn.datatables.net/plug-ins/1.13.8/i18n/fr-FR.json' }},
    columnDefs:[{{ orderable:false, targets:[0,8] }}]
  }});
  document.getElementById('chk-all').checked = false;
  updateMap(data);
}}

function applyFilters() {{
  const sites  = [...document.getElementById('f-site').selectedOptions].map(o=>o.value).filter(v=>v);
  const cities = [...document.getElementById('f-city').selectedOptions].map(o=>o.value).filter(v=>v);
  const pmin   = parseFloat(document.getElementById('f-pmin').value)||0;
  const pmax   = parseFloat(document.getElementById('f-pmax').value)||Infinity;
  const smin   = parseFloat(document.getElementById('f-smin').value)||0;
  const rooms  = document.getElementById('f-rooms').value;
  const dmax   = parseFloat(document.getElementById('f-dmax').value)||Infinity;
  const notif  = document.getElementById('f-notif').value;
  filtered = ALL.filter(l => {{
    if(sites.length  && !sites.includes(l.site))  return false;
    if(cities.length && !cities.includes(l.city)) return false;
    if(l.price<pmin || l.price>pmax) return false;
    if(smin>0 && l.surface>0 && l.surface<smin) return false;
    if(rooms) {{ if(rooms==='4'){{if(l.rooms<4)return false;}} else{{if(l.rooms&&l.rooms!=+rooms)return false;}} }}
    if(dmax<Infinity && l.distance_km!=null && l.distance_km>dmax) return false;
    if(notif==='1' && !l.notified) return false;
    if(notif==='0' && l.notified)  return false;
    return true;
  }});
  render(filtered);
}}

function resetFilters() {{
  ['f-site','f-city'].forEach(id=>{{ document.getElementById(id).selectedIndex=-1; }});
  ['f-pmin','f-pmax','f-smin','f-dmax'].forEach(id=>{{ document.getElementById(id).value=''; }});
  document.getElementById('f-rooms').value='';
  document.getElementById('f-notif').value='';
  filtered=[...ALL]; render(filtered);
}}

function initMap() {{
  mapObj = L.map('map').setView([49.6116,6.1319],11);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
    {{attribution:'© OpenStreetMap'}}).addTo(mapObj);
  updateMap(ALL);
}}

function updateMap(data) {{
  mapMarkers.forEach(m=>mapObj.removeLayer(m)); mapMarkers=[];
  data.forEach(l => {{
    if(!l.latitude||!l.longitude) return;
    const col = dColor(l.distance_km);
    const icon = L.divIcon({{
      html:`<div style="background:${{col}};width:12px;height:12px;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 3px #0005"></div>`,
      iconSize:[12,12],iconAnchor:[6,6],className:''
    }});
    const m = L.marker([l.latitude,l.longitude],{{icon}}).bindPopup(
      `<b>${{l.city||''}}</b><br>
       ${{l.price?fmt(l.price)+' €':''}}
       ${{l.surface?'· '+l.surface+' m²':''}}
       ${{l.rooms?'· '+l.rooms+' ch':''}}<br>
       ${{l.distance_km!=null?l.distance_km.toFixed(1)+' km':''}}<br>
       <a href="${{l.url}}" target="_blank">Voir l'annonce</a>`
    ).addTo(mapObj);
    mapMarkers.push(m);
  }});
}}

function togCmp(id,chk) {{
  chk.checked ? cmpSet.add(id) : cmpSet.delete(id);
  const btn=document.getElementById('compare-btn');
  document.getElementById('cmp-cnt').textContent=cmpSet.size;
  btn.style.display=cmpSet.size>=2?'inline-block':'none';
}}
function toggleAll(chk) {{
  document.querySelectorAll('.cchk').forEach(c=>{{
    c.checked=chk.checked; chk.checked?cmpSet.add(+c.value):cmpSet.delete(+c.value);
  }});
  document.getElementById('cmp-cnt').textContent=cmpSet.size;
  document.getElementById('compare-btn').style.display=cmpSet.size>=2?'inline-block':'none';
}}
function openCompare() {{
  const sel=ALL.filter(l=>cmpSet.has(l.id));
  if(sel.length<2) return;
  const fields=[
    ['Site',l=>l.site||'—'],['Ville',l=>l.city||'—'],
    ['Prix',l=>l.price?fmt(l.price)+' €':'—'],
    ['Surface',l=>l.surface?l.surface+' m²':'—'],
    ['€/m²',l=>(l.price&&l.surface)?Math.round(l.price/l.surface*10)/10+' €':'—'],
    ['Pièces',l=>l.rooms||'—'],
    ['Distance',l=>l.distance_km!=null?l.distance_km.toFixed(1)+' km':'—'],
    ['Notifié',l=>l.notified?'✅':'❌'],
    ['Date',l=>l.created_at?l.created_at.slice(0,10):'—'],
    ['Lien',l=>`<a href="${{l.url}}" target="_blank">Voir</a>`],
  ];
  let html='<table class="table table-sm table-bordered"><thead class="table-dark"><tr><th>Critère</th>';
  sel.forEach(l=>{{html+=`<th>${{trunc(l.title,30)}}</th>`;}});
  html+='</tr></thead><tbody>';
  fields.forEach(([lbl,fn])=>{{
    html+=`<tr><td class="fw-semibold">${{lbl}}</td>`;
    sel.forEach(l=>{{html+=`<td>${{fn(l)}}</td>`;}});
    html+='</tr>';
  }});
  html+='</tbody></table>';
  document.getElementById('cmp-body').innerHTML=html;
  new bootstrap.Modal(document.getElementById('cmp-modal')).show();
}}
</script>
</body>
</html>'''


def main():
    if not os.path.exists(DB_PATH):
        print(f"Erreur: {DB_PATH} introuvable"); sys.exit(1)
    OUT_DIR.mkdir(exist_ok=True)
    ARCHIVES_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)

    listings = load_listings()
    stats = calc_stats(listings)
    generated_at = datetime.now().strftime('%d/%m/%Y %H:%M')

    html = generate_html(listings, stats, generated_at)

    index_path = OUT_DIR / 'index.html'
    index_path.write_text(html, encoding='utf-8')

    archive_name = datetime.now().strftime('%Y-%m-%d') + '.html'
    (ARCHIVES_DIR / archive_name).write_text(html, encoding='utf-8')

    (DATA_DIR / 'listings.json').write_text(
        json.dumps(listings, ensure_ascii=False, indent=2, default=str), encoding='utf-8'
    )

    print(f"Dashboard genere : {len(listings)} annonces")
    print(f"  {index_path.resolve()}")


if __name__ == '__main__':
    main()
