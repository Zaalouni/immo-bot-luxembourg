#!/usr/bin/env python3
# =============================================================================
# dashboard_generator.py — Generateur de dashboard HTML pour immo-bot
# =============================================================================
# Genere :
#   dashboards/index.html   — Dashboard principal (KPI + graphiques + tableau)
#   dashboards/map.html     — Carte interactive (page separee, legere)
#   dashboards/manifest.json, sw.js, icon.svg  — PWA
#   dashboards/archives/YYYY-MM-DD.html
#   dashboards/data/listings.json
# =============================================================================
import sqlite3, json, os, sys
from datetime import datetime
from pathlib import Path
from collections import Counter

DB_PATH = 'listings.db'
OUT_DIR  = Path('dashboards')
ARCHIVES_DIR = OUT_DIR / 'archives'
DATA_DIR     = OUT_DIR / 'data'

CHART_COLORS = [
    '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16',
]

# ─── Ressources PWA ───────────────────────────────────────────────────────────

ICON_SVG = '''\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
  <rect width="192" height="192" rx="38" fill="#0f172a"/>
  <polygon points="96,30 160,92 140,92 140,158 52,158 52,92 32,92" fill="#ffffff"/>
  <rect x="62" y="92" width="68" height="66" fill="#0f172a"/>
  <rect x="66" y="96" width="60" height="58" fill="#3b82f6" opacity=".25"/>
  <rect x="74" y="118" width="26" height="40" fill="#ffffff" rx="3"/>
  <rect x="68" y="98" width="20" height="16" fill="#ffffff" rx="2"/>
  <rect x="104" y="98" width="20" height="16" fill="#ffffff" rx="2"/>
</svg>'''


def generate_manifest():
    return json.dumps({
        "name": "Immo Bot Luxembourg",
        "short_name": "ImmoBotLU",
        "description": "Dashboard annonces immobilieres Luxembourg",
        "start_url": "./index.html",
        "display": "standalone",
        "background_color": "#f1f5f9",
        "theme_color": "#0f172a",
        "orientation": "any",
        "categories": ["finance", "lifestyle"],
        "icons": [
            {"src": "icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}
        ]
    }, indent=2, ensure_ascii=False)


def generate_sw(cache_ver):
    return f"""\
const CACHE = 'immo-bot-{cache_ver}';
const ASSETS = ['./index.html', './map.html', './icon.svg'];

self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
}});

self.addEventListener('activate', e => {{
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
}});

self.addEventListener('fetch', e => {{
  e.respondWith(
    fetch(e.request).then(resp => {{
      const clone = resp.clone();
      caches.open(CACHE).then(c => c.put(e.request, clone));
      return resp;
    }}).catch(() => caches.match(e.request))
  );
}});
"""


# ─── Chargement données ───────────────────────────────────────────────────────

def load_listings():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT id, listing_id, site, title, city, price, rooms, surface,
                        url, image_url, latitude, longitude, distance_km, created_at, notified,
                        available_from
                 FROM listings ORDER BY created_at DESC''')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def calc_stats(listings):
    if not listings:
        return {}
    prices   = [l['price']       for l in listings if l.get('price')   and l['price']   > 0]
    surfaces = [l['surface']     for l in listings if l.get('surface') and l['surface'] > 0]
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
        'avg_price':    round(sum(prices) / len(prices))     if prices   else 0,
        'min_price':    min(prices)                          if prices   else 0,
        'max_price':    max(prices)                          if prices   else 0,
        'avg_surface':  round(sum(surfaces) / len(surfaces)) if surfaces else 0,
        'avg_distance': round(sum(dists) / len(dists), 1)   if dists    else None,
        'by_site':      by_site,
        'avg_prix_m2':  round(sum(pm2) / len(pm2), 1)       if pm2      else 0,
    }


def _fmt(n):
    """Formater un entier avec séparateur milliers (espace insécable)."""
    if not n and n != 0:
        return '—'
    return f'{int(n):,}'.replace(',', '\u202f')


# ─── Page principale ──────────────────────────────────────────────────────────

def generate_index_html(listings, stats, generated_at):
    listings_json = json.dumps(listings, ensure_ascii=False, default=str)

    # Table qualité par site (D07)
    def _qual_row(site_name, lst, color):
        n       = len(lst)
        no_img  = sum(1 for l in lst if not l.get('image_url'))
        no_surf = sum(1 for l in lst if not l.get('surface'))
        no_gps  = sum(1 for l in lst if not l.get('latitude'))
        ok = lambda bad: '✅' if bad == 0 else f'<span style="color:#ef4444">⚠️ {bad}</span>'
        return (f'<tr><td><span class="sb" style="background:{color}">{site_name}</span></td>'
                f'<td class="text-center">{n}</td>'
                f'<td class="text-center">{ok(no_img)}</td>'
                f'<td class="text-center">{ok(no_surf)}</td>'
                f'<td class="text-center">{ok(no_gps)}</td></tr>')

    site_groups = {}
    for l in listings:
        s = l.get('site', '?')
        site_groups.setdefault(s, []).append(l)

    qual_rows = ''.join(
        _qual_row(s, lst, CHART_COLORS[i % len(CHART_COLORS)])
        for i, (s, lst) in enumerate(sorted(site_groups.items()))
    )
    qual_table = f'''
<div class="card mb-3">
  <div class="card-header">Qualité des données par site</div>
  <div class="card-body p-0">
    <table class="table table-sm mb-0" style="font-size:.78rem">
      <thead style="background:#1e293b;color:#94a3b8">
        <tr><th>Site</th><th class="text-center">N</th>
            <th class="text-center">Images</th>
            <th class="text-center">Surface</th>
            <th class="text-center">GPS</th></tr>
      </thead>
      <tbody>{qual_rows}</tbody>
    </table>
  </div>
</div>'''

    # Données graphiques
    by_site = stats.get('by_site', {})
    # Badges site pour info-bar (remplace le donut site)
    by_site_badges = ' '.join(
        f'<span class="sb" style="background:{CHART_COLORS[i % len(CHART_COLORS)]}">{s} {n}</span>'
        for i, (s, n) in enumerate(sorted(by_site.items()))
    )

    city_counts = Counter(l.get('city', '') for l in listings if l.get('city'))

    # Donut : top 8 villes (proportions)
    top8_donut   = city_counts.most_common(8)
    donut_labels = json.dumps([c[0] for c in top8_donut], ensure_ascii=False)
    donut_data   = json.dumps([c[1] for c in top8_donut])
    donut_colors = json.dumps(CHART_COLORS[:len(top8_donut)])

    # Barre horizontale : top 10 villes (cliquable → filtre tableau)
    top10 = list(reversed(city_counts.most_common(10)))
    city_labels = json.dumps([c[0] for c in top10], ensure_ascii=False)
    city_data   = json.dumps([c[1] for c in top10])

    pr = [0, 0, 0, 0, 0]
    for l in listings:
        p = l.get('price', 0) or 0
        if   p < 1500: pr[0] += 1
        elif p < 2000: pr[1] += 1
        elif p < 2500: pr[2] += 1
        elif p < 3000: pr[3] += 1
        else:          pr[4] += 1
    price_data = json.dumps(pr)

    # Options filtres — villes normalisées (dedup insensible à la casse)
    sites  = sorted(set(l.get('site', '') for l in listings if l.get('site')))
    _city_map = {}  # lowercase → forme canonique (première vue)
    for l in listings:
        c = (l.get('city') or '').strip()
        if c and c.lower() not in _city_map:
            _city_map[c.lower()] = c
    cities = sorted(_city_map.values(), key=str.lower)
    sites_opts  = '\n'.join(f'<option value="{s}">{s}</option>' for s in sites)
    cities_opts = '\n'.join(f'<option value="{c}">{c}</option>' for c in cities)

    geo_count = sum(1 for l in listings if l.get('latitude') and l.get('longitude'))

    t      = stats.get('total', 0)
    avg_p  = _fmt(stats.get('avg_price', 0))
    min_p  = _fmt(stats.get('min_price', 0))
    max_p  = _fmt(stats.get('max_price', 0))
    avg_s  = stats.get('avg_surface', 0)
    avg_m2 = stats.get('avg_prix_m2', 0)
    notif  = stats.get('notified', 0)

    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Immo Bot Luxembourg — Dashboard</title>
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#0f172a">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Immo Bot LU">
<link rel="apple-touch-icon" href="icon.svg">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.datatables.net/1.13.8/css/dataTables.bootstrap5.min.css" rel="stylesheet">
<style>
:root {{ --bg: #f1f5f9; }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); font-size: .875rem; font-family: "Segoe UI", system-ui, sans-serif; }}

/* Navbar */
.top-nav {{ background: #0f172a; height: 54px; display: flex; align-items: center;
  padding: 0 1.25rem; gap: 1rem; position: sticky; top: 0; z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,.4); }}
.top-nav .brand {{ color: #fff; font-weight: 700; font-size: 1rem; text-decoration: none; }}
.top-nav .upd {{ color: #64748b; font-size: .75rem; margin-left: auto; }}
.top-nav .map-btn {{ background: #3b82f6; color: #fff; border: none; border-radius: 6px;
  padding: .3rem .85rem; font-size: .8rem; font-weight: 600; text-decoration: none;
  transition: background .15s; }}
.top-nav .map-btn:hover {{ background: #2563eb; color: #fff; }}

/* KPI cards */
.kpi {{ border: none; border-left: 4px solid var(--c, #3b82f6);
  box-shadow: 0 1px 3px rgba(0,0,0,.08); border-radius: 10px; background: #fff;
  padding: 1rem 1.1rem; position: relative; overflow: hidden; }}
.kpi .val {{ font-size: 1.65rem; font-weight: 800; color: #0f172a; line-height: 1.15; }}
.kpi .lbl {{ font-size: .68rem; text-transform: uppercase; letter-spacing: .07em;
  color: #94a3b8; margin-top: .2rem; }}
.kpi .ico {{ position: absolute; right: .9rem; top: .75rem;
  font-size: 2rem; opacity: .1; line-height: 1; }}
.kpi .sub {{ font-size: .72rem; color: #64748b; margin-top: .25rem; }}

/* Cartes génériques */
.card {{ border: none; box-shadow: 0 1px 3px rgba(0,0,0,.08); border-radius: 10px; }}
.card-header {{ background: transparent; border-bottom: 1px solid #f1f5f9;
  font-size: .75rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .06em; color: #64748b; padding: .75rem 1rem; }}

/* Tableau */
table.dataTable thead th {{
  font-size: .7rem; text-transform: uppercase; letter-spacing: .05em;
  background: #1e293b !important; color: #94a3b8 !important;
  border-color: #334155 !important; white-space: nowrap;
}}
table.dataTable tbody tr:hover td {{ background: #eff6ff !important; }}
table.dataTable tbody td {{ vertical-align: middle; padding: .45rem .6rem; }}
.al {{ color: #3b82f6; text-decoration: none; font-weight: 500; }}
.al:hover {{ text-decoration: underline; }}
.pm2 {{ font-size: .7rem; color: #94a3b8; }}
.sb {{ font-size: .68rem; border-radius: 5px; padding: .15em .55em;
  font-weight: 700; color: #fff; white-space: nowrap; }}
.dbadge {{ border-radius: 5px; padding: .1em .5em; font-size: .68rem;
  font-weight: 700; color: #fff; white-space: nowrap; }}

/* Filtres */
.filter-lbl {{ font-size: .68rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .06em; color: #64748b; margin-bottom: .2rem; }}

/* Info bar */
.info-bar {{ display: flex; flex-wrap: wrap; align-items: center; gap: .5rem;
  font-size: .8rem; color: #64748b; margin-bottom: .75rem; }}
.info-bar strong {{ color: #0f172a; }}
</style>
</head>
<body>

<nav class="top-nav">
  <a href="#" class="brand">🏠 Immo Bot Luxembourg</a>
  <span class="upd">Mis à jour : {generated_at}</span>
  <a href="map.html" class="map-btn">🗺️ Carte ({geo_count})</a>
</nav>

<div class="container-fluid px-3 px-md-4 py-3">

<!-- ── KPI ── -->
<div class="row g-3 mb-3">
  <div class="col-6 col-md-2">
    <div class="kpi" style="--c:#3b82f6">
      <span class="ico">📋</span>
      <div class="val">{t}</div>
      <div class="lbl">Annonces</div>
      <div class="sub">{notif} notifiées</div>
    </div>
  </div>
  <div class="col-6 col-md-2">
    <div class="kpi" style="--c:#10b981">
      <span class="ico">💰</span>
      <div class="val">{avg_p} €</div>
      <div class="lbl">Prix moyen</div>
    </div>
  </div>
  <div class="col-6 col-md-2">
    <div class="kpi" style="--c:#06b6d4">
      <span class="ico">⬇️</span>
      <div class="val">{min_p} €</div>
      <div class="lbl">Prix min</div>
    </div>
  </div>
  <div class="col-6 col-md-2">
    <div class="kpi" style="--c:#f59e0b">
      <span class="ico">⬆️</span>
      <div class="val">{max_p} €</div>
      <div class="lbl">Prix max</div>
    </div>
  </div>
  <div class="col-6 col-md-2">
    <div class="kpi" style="--c:#8b5cf6">
      <span class="ico">📐</span>
      <div class="val">{avg_s} m²</div>
      <div class="lbl">Surface moy.</div>
    </div>
  </div>
  <div class="col-6 col-md-2">
    <div class="kpi" style="--c:#ec4899">
      <span class="ico">📊</span>
      <div class="val">{avg_m2} €</div>
      <div class="lbl">€/m² moyen</div>
    </div>
  </div>
</div>

<!-- ── SITES INFO-BAR ── -->
<div class="card mb-3 px-3 py-2" style="font-size:.8rem">
  <span class="text-secondary me-2" style="font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em">Sites actifs :</span>
  {by_site_badges}
</div>

<!-- ── QUALITE DONNEES ── -->
{qual_table}

<!-- ── GRAPHIQUES ── -->
<div class="row g-3 mb-3">
  <div class="col-md-4">
    <div class="card h-100">
      <div class="card-header">Répartition par ville</div>
      <div class="card-body d-flex align-items-center justify-content-center" style="min-height:230px">
        <canvas id="cSites"></canvas>
      </div>
    </div>
  </div>
  <div class="col-md-4">
    <div class="card h-100">
      <div class="card-header d-flex align-items-center justify-content-between">
        <span>Top 10 villes</span>
        <span style="font-size:.65rem;font-weight:400;color:#94a3b8;text-transform:none;letter-spacing:0">
          Cliquer pour filtrer
        </span>
      </div>
      <div class="card-body d-flex align-items-center" style="min-height:230px">
        <canvas id="cCities" style="cursor:pointer"></canvas>
      </div>
    </div>
  </div>
  <div class="col-md-4">
    <div class="card h-100">
      <div class="card-header">Distribution des prix</div>
      <div class="card-body d-flex align-items-center" style="min-height:230px">
        <canvas id="cPrices"></canvas>
      </div>
    </div>
  </div>
</div>

<!-- ── FILTRES ── -->
<div class="card mb-3">
  <div class="card-body py-2">
    <div class="row g-2 align-items-end">
      <div class="col-6 col-md-2">
        <div class="filter-lbl">Site</div>
        <select id="f-site" class="form-select form-select-sm">
          <option value="">Tous</option>
          {sites_opts}
        </select>
      </div>
      <div class="col-6 col-md-2">
        <div class="filter-lbl">Ville</div>
        <select id="f-city" class="form-select form-select-sm">
          <option value="">Toutes</option>
          {cities_opts}
        </select>
      </div>
      <div class="col-3 col-md-1">
        <div class="filter-lbl">Prix min</div>
        <input id="f-pmin" type="number" class="form-control form-control-sm" placeholder="1000" step="100">
      </div>
      <div class="col-3 col-md-1">
        <div class="filter-lbl">Prix max</div>
        <input id="f-pmax" type="number" class="form-control form-control-sm" placeholder="3000" step="100">
      </div>
      <div class="col-3 col-md-1">
        <div class="filter-lbl">Surface min</div>
        <input id="f-smin" type="number" class="form-control form-control-sm" placeholder="0">
      </div>
      <div class="col-3 col-md-1">
        <div class="filter-lbl">Pièces</div>
        <select id="f-rooms" class="form-select form-select-sm">
          <option value="">Toutes</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4+</option>
        </select>
      </div>
      <div class="col-12 col-md-auto d-flex gap-2">
        <button class="btn btn-sm" style="background:#3b82f6;color:#fff;font-weight:600"
                onclick="applyFilters()">Filtrer</button>
        <button class="btn btn-sm btn-outline-secondary" onclick="resetFilters()">Reset</button>
      </div>
      <div class="col-12 col-md-auto ms-auto d-flex align-items-center gap-2">
        <span class="text-muted small" id="cnt"></span>
        <button id="cmp-btn" class="btn btn-sm btn-warning" style="display:none"
                onclick="openCompare()">⚖️ Comparer (<span id="cmp-n">0</span>)</button>
      </div>
    </div>
  </div>
</div>

<!-- ── TABLEAU ── -->
<div class="card mb-4" style="overflow-x:auto">
  <table id="tbl" class="table table-sm table-hover table-bordered mb-0" style="width:100%">
    <thead>
      <tr>
        <th style="width:32px"><input type="checkbox" id="chk-all" onchange="toggleAll(this)"></th>
        <th>Site</th>
        <th>Ville</th>
        <th>Prix €</th>
        <th>m²</th>
        <th>€/m²</th>
        <th>Ch.</th>
        <th>Dist.</th>
        <th>Titre</th>
        <th>Date</th>
        <th>Dispo</th>
        <th>✉</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
</div>

</div><!-- /container -->

<!-- MODAL COMPARATEUR -->
<div class="modal fade" id="cmp-modal" tabindex="-1">
  <div class="modal-dialog modal-xl modal-dialog-scrollable">
    <div class="modal-content">
      <div class="modal-header" style="background:#0f172a;color:#fff">
        <h5 class="modal-title fw-bold">⚖️ Comparateur d'annonces</h5>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body p-2" id="cmp-body"></div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.8/js/dataTables.bootstrap5.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
const ALL = {listings_json};
let filtered = [...ALL];
let cmpSet   = new Set();
let dt;

const SITE_COL = {{
  'Athome.lu'   : '#3b82f6',
  'Immotop.lu'  : '#10b981',
  'Luxhome.lu'  : '#06b6d4',
  'VIVI.lu'     : '#f59e0b',
  'Nextimmo.lu' : '#8b5cf6',
  'Newimmo.lu'  : '#ef4444',
  'Unicorn.lu'  : '#64748b',
  'Remax.lu'    : '#ec4899',
  'Sigelux.lu'  : '#84cc16',
  'ImmoStar.lu' : '#f97316',
}};

function fmt(n)    {{ return n != null ? Number(n).toLocaleString('fr-FR') : '—'; }}
function trunc(s,n) {{ return s && s.length > n ? s.slice(0,n) + '…' : (s || '—'); }}
function dCol(d)   {{
  if (d == null) return '#94a3b8';
  return d < 2 ? '#10b981' : d < 5 ? '#3b82f6' : d < 10 ? '#f59e0b' : '#ef4444';
}}

function render(data) {{
  const tb = document.getElementById('tbody');
  tb.innerHTML = '';
  data.forEach(l => {{
    const pm2  = (l.price > 0 && l.surface > 0) ? Math.round(l.price / l.surface * 10) / 10 : '';
    const dist = l.distance_km != null
      ? `<span class="dbadge" style="background:${{dCol(l.distance_km)}}">${{l.distance_km.toFixed(1)}} km</span>`
      : '<span style="color:#94a3b8">—</span>';
    const sc = SITE_COL[l.site] || '#64748b';
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><input type="checkbox" class="cchk" value="${{l.id}}" onchange="togCmp(${{l.id}},this)"></td>
      <td><span class="sb" style="background:${{sc}}">${{l.site || '—'}}</span></td>
      <td>${{l.city || '—'}}</td>
      <td class="fw-bold">${{l.price ? fmt(l.price) + ' €' : '—'}}</td>
      <td>${{l.surface || '—'}}</td>
      <td class="pm2">${{pm2 ? pm2 + ' €' : '—'}}</td>
      <td>${{l.rooms || '—'}}</td>
      <td>${{dist}}</td>
      <td><a class="al" href="${{l.url}}" target="_blank" title="${{l.title}}">${{trunc(l.title, 55)}}</a></td>
      <td style="color:#94a3b8;font-size:.72rem">${{l.created_at ? l.created_at.slice(0,10) : '—'}}</td>
      <td style="color:#10b981;font-size:.72rem">${{l.available_from || ''}}</td>
      <td style="text-align:center">${{l.notified ? '✅' : ''}}</td>`;
    tb.appendChild(row);
  }});

  if (dt) dt.destroy();
  dt = $('#tbl').DataTable({{
    paging: true, pageLength: 25, ordering: true, order: [[3,'asc']], searching: true,
    language: {{ url: 'https://cdn.datatables.net/plug-ins/1.13.8/i18n/fr-FR.json' }},
    columnDefs: [{{ orderable: false, targets: [0, 8] }}]
  }});

  document.getElementById('chk-all').checked = false;
  const cnt = document.getElementById('cnt');
  if (cnt) cnt.textContent = `${{data.length}} annonce${{data.length > 1 ? 's' : ''}}`;
}}

function applyFilters() {{
  const site  = document.getElementById('f-site').value;
  const city  = document.getElementById('f-city').value;
  const pmin  = parseFloat(document.getElementById('f-pmin').value) || 0;
  const pmax  = parseFloat(document.getElementById('f-pmax').value) || Infinity;
  const smin  = parseFloat(document.getElementById('f-smin').value) || 0;
  const rooms = document.getElementById('f-rooms').value;
  filtered = ALL.filter(l => {{
    if (site && l.site !== site)   return false;
    if (city && l.city !== city)   return false;
    if (l.price < pmin || l.price > pmax) return false;
    if (smin > 0 && l.surface > 0 && l.surface < smin) return false;
    if (rooms) {{
      if (rooms === '4') {{ if (l.rooms < 4) return false; }}
      else               {{ if (l.rooms && l.rooms != +rooms) return false; }}
    }}
    return true;
  }});
  render(filtered);
}}

function resetFilters() {{
  ['f-site','f-city','f-rooms'].forEach(id => document.getElementById(id).value = '');
  ['f-pmin','f-pmax','f-smin'].forEach(id => document.getElementById(id).value = '');
  filtered = [...ALL];
  render(filtered);
}}

function togCmp(id, chk) {{
  chk.checked ? cmpSet.add(id) : cmpSet.delete(id);
  document.getElementById('cmp-n').textContent = cmpSet.size;
  document.getElementById('cmp-btn').style.display = cmpSet.size >= 2 ? '' : 'none';
}}
function toggleAll(chk) {{
  document.querySelectorAll('.cchk').forEach(c => {{
    c.checked = chk.checked;
    chk.checked ? cmpSet.add(+c.value) : cmpSet.delete(+c.value);
  }});
  document.getElementById('cmp-n').textContent = cmpSet.size;
  document.getElementById('cmp-btn').style.display = cmpSet.size >= 2 ? '' : 'none';
}}
function openCompare() {{
  const sel = ALL.filter(l => cmpSet.has(l.id));
  if (sel.length < 2) return;
  const fields = [
    ['Site',     l => l.site || '—'],
    ['Ville',    l => l.city || '—'],
    ['Prix',     l => l.price ? fmt(l.price) + ' €' : '—'],
    ['Surface',  l => l.surface ? l.surface + ' m²' : '—'],
    ['€/m²',    l => (l.price && l.surface) ? Math.round(l.price / l.surface * 10) / 10 + ' €' : '—'],
    ['Pièces',   l => l.rooms || '—'],
    ['Distance', l => l.distance_km != null ? l.distance_km.toFixed(1) + ' km' : '—'],
    ['Notifié',  l => l.notified ? '✅' : '❌'],
    ['Date',     l => l.created_at ? l.created_at.slice(0,10) : '—'],
    ['Lien',     l => `<a href="${{l.url}}" target="_blank" class="al">Voir →</a>`],
  ];
  let html = '<div style="overflow-x:auto"><table class="table table-sm table-bordered">'
           + '<thead class="table-dark"><tr><th>Critère</th>';
  sel.forEach(l => {{ html += `<th>${{trunc(l.title, 30)}}</th>`; }});
  html += '</tr></thead><tbody>';
  fields.forEach(([lb, fn]) => {{
    html += `<tr><td class="fw-semibold">${{lb}}</td>`;
    sel.forEach(l => {{ html += `<td>${{fn(l)}}</td>`; }});
    html += '</tr>';
  }});
  html += '</tbody></table></div>';
  document.getElementById('cmp-body').innerHTML = html;
  new bootstrap.Modal(document.getElementById('cmp-modal')).show();
}}

// ── Graphiques Chart.js ──
window.addEventListener('DOMContentLoaded', () => {{
  render(ALL);

  // Donut — répartition par ville (top 8)
  new Chart(document.getElementById('cSites'), {{
    type: 'doughnut',
    data: {{
      labels: {donut_labels},
      datasets: [{{ data: {donut_data}, backgroundColor: {donut_colors},
        borderWidth: 2, borderColor: '#f1f5f9' }}]
    }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ position: 'bottom', labels: {{ font: {{ size: 11 }}, boxWidth: 12, padding: 8 }} }}
      }}
    }}
  }});

  // Barre horizontale — top 10 villes (clic → filtre tableau)
  const CHART_CITIES = {city_labels};
  new Chart(document.getElementById('cCities'), {{
    type: 'bar',
    data: {{
      labels: CHART_CITIES,
      datasets: [{{
        data: {city_data},
        backgroundColor: '#3b82f6bb',
        borderColor: '#3b82f6',
        borderWidth: 1, borderRadius: 4
      }}]
    }},
    options: {{
      indexAxis: 'y', responsive: true,
      plugins: {{ legend: {{ display: false }} }},
      onHover: (e, el) => {{
        e.native.target.style.cursor = el.length ? 'pointer' : 'default';
      }},
      onClick: (e, el) => {{
        if (!el.length) return;
        const city = CHART_CITIES[el[0].index];
        const sel  = document.getElementById('f-city');
        if (sel.value === city) {{
          sel.value = '';
          resetFilters();
        }} else {{
          sel.value = city;
          applyFilters();
        }}
        // Scroll doux vers le tableau
        document.querySelector('.card.mb-4').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }},
      scales: {{
        x: {{ beginAtZero: true, ticks: {{ font: {{ size: 10 }} }} }},
        y: {{ ticks: {{ font: {{ size: 10 }} }} }}
      }}
    }}
  }});

  // Barre — distribution prix
  new Chart(document.getElementById('cPrices'), {{
    type: 'bar',
    data: {{
      labels: ['< 1 500 €', '1 500–2 000 €', '2 000–2 500 €', '2 500–3 000 €', '> 3 000 €'],
      datasets: [{{
        data: {price_data},
        backgroundColor: ['#10b981bb','#3b82f6bb','#f59e0bbb','#ef4444bb','#8b5cf6bb'],
        borderColor:     ['#10b981',  '#3b82f6',  '#f59e0b',  '#ef4444',  '#8b5cf6'],
        borderWidth: 1, borderRadius: 4
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        y: {{ beginAtZero: true, ticks: {{ font: {{ size: 10 }}, stepSize: 1 }} }},
        x: {{ ticks: {{ font: {{ size: 10 }} }} }}
      }}
    }}
  }});
}});

if ('serviceWorker' in navigator) {{
  navigator.serviceWorker.register('./sw.js').catch(() => {{}});
}}
</script>
</body>
</html>'''


# ─── Page carte ───────────────────────────────────────────────────────────────

def generate_map_html(listings, generated_at):
    geo = [l for l in listings if l.get('latitude') and l.get('longitude')]
    geo_json  = json.dumps(geo, ensure_ascii=False, default=str)
    geo_count = len(geo)

    sites      = sorted(set(l.get('site', '') for l in geo if l.get('site')))
    sites_opts = '\n'.join(f'<option value="{s}">{s}</option>' for s in sites)

    cities      = sorted(set(l.get('city', '') for l in geo if l.get('city')), key=str.lower)
    cities_opts = '\n'.join(f'<option value="{c}">{c}</option>' for c in cities)

    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Immo Bot LU — Carte</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" rel="stylesheet">
<link href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" rel="stylesheet">
<link href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" rel="stylesheet">
<style>
html, body {{ margin: 0; padding: 0; height: 100%; overflow: hidden;
  font-family: "Segoe UI", system-ui, sans-serif; }}
#map {{ height: calc(100vh - 52px); width: 100%; }}

.top-nav {{ background: #0f172a; height: 52px; display: flex; align-items: center;
  padding: 0 1.25rem; gap: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,.4); }}
.back-btn {{ color: #94a3b8; text-decoration: none; font-size: .82rem;
  display: flex; align-items: center; gap: .3rem; transition: color .15s; }}
.back-btn:hover {{ color: #fff; }}
.nav-title {{ color: #fff; font-weight: 700; }}
.nav-upd {{ color: #475569; font-size: .75rem; margin-left: auto; }}

#panel {{
  position: fixed; top: 62px; right: 12px; z-index: 1000;
  width: 230px;
  background: rgba(255,255,255,.96);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,.2);
  backdrop-filter: blur(10px);
  overflow: hidden;
}}
#panel .ph {{
  background: #0f172a; color: #fff;
  padding: .6rem .85rem; font-weight: 700; font-size: .82rem;
  display: flex; align-items: center; justify-content: space-between;
  cursor: pointer; user-select: none;
}}
#panel .ph .badge-geo {{
  background: #3b82f6; color: #fff; border-radius: 20px;
  padding: .1em .6em; font-size: .75rem; font-weight: 700;
}}
#panel .ph .toggle-icon {{
  font-size: .75rem; color: #94a3b8; transition: transform .2s;
  margin-left: .5rem;
}}
#panel.collapsed .ph .toggle-icon {{ transform: rotate(180deg); }}
#panel .pb {{ padding: .75rem .85rem; }}
#panel.collapsed .pb {{ display: none; }}
.filter-lbl {{
  font-size: .65rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: #94a3b8; margin-bottom: .2rem;
}}
.dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block;
  border: 1px solid rgba(0,0,0,.1); flex-shrink: 0; }}
.legend-row {{ display: flex; align-items: center; gap: .4rem;
  font-size: .75rem; color: #475569; padding: .1rem 0; }}

/* Stats rapides */
.qs {{ display: grid; grid-template-columns: 1fr 1fr; gap: .4rem; margin-bottom: .6rem; }}
.qs-item {{ background: #f8fafc; border-radius: 6px; padding: .35rem .5rem; text-align: center; }}
.qs-val {{ font-size: .95rem; font-weight: 800; color: #0f172a; }}
.qs-lbl {{ font-size: .6rem; text-transform: uppercase; letter-spacing: .05em; color: #94a3b8; }}
</style>
</head>
<body>

<nav class="top-nav">
  <a href="index.html" class="back-btn">← Dashboard</a>
  <span class="nav-title">🗺️ Carte des annonces</span>
  <span class="nav-upd">Mis à jour : {generated_at}</span>
</nav>

<div id="map"></div>

<div id="panel">
  <div class="ph" onclick="togglePanel()">
    <span>Annonces géolocalisées</span>
    <div style="display:flex;align-items:center;gap:.4rem">
      <span class="badge-geo" id="geo-count">{geo_count}</span>
      <span class="toggle-icon">▲</span>
    </div>
  </div>
  <div class="pb">

    <!-- Stats rapides -->
    <div class="qs" id="qs">
      <div class="qs-item">
        <div class="qs-val" id="qs-min">—</div>
        <div class="qs-lbl">Prix min</div>
      </div>
      <div class="qs-item">
        <div class="qs-val" id="qs-max">—</div>
        <div class="qs-lbl">Prix max</div>
      </div>
      <div class="qs-item">
        <div class="qs-val" id="qs-avg">—</div>
        <div class="qs-lbl">Prix moy.</div>
      </div>
      <div class="qs-item">
        <div class="qs-val" id="qs-cnt">—</div>
        <div class="qs-lbl">Visibles</div>
      </div>
    </div>

    <!-- Filtres -->
    <div style="border-top:1px solid #f1f5f9;padding-top:.6rem;margin-bottom:.6rem">
      <div class="filter-lbl">Ville</div>
      <select id="f-city" class="form-select form-select-sm mb-2">
        <option value="">Toutes les villes</option>
        {cities_opts}
      </select>
      <div class="filter-lbl">Site</div>
      <select id="f-site" class="form-select form-select-sm mb-2">
        <option value="">Tous les sites</option>
        {sites_opts}
      </select>
      <div class="filter-lbl">Distance max</div>
      <select id="f-dist" class="form-select form-select-sm mb-2">
        <option value="">Toutes distances</option>
        <option value="2">&lt; 2 km</option>
        <option value="5">&lt; 5 km</option>
        <option value="10">&lt; 10 km</option>
      </select>
      <div class="d-flex gap-2">
        <button class="btn btn-sm w-100 fw-semibold"
                style="background:#3b82f6;color:#fff;font-size:.78rem"
                onclick="applyFilters()">Appliquer</button>
        <button class="btn btn-sm btn-outline-secondary w-100"
                style="font-size:.78rem"
                onclick="resetFilters()">Reset</button>
      </div>
    </div>

    <!-- Légende -->
    <div style="border-top:1px solid #f1f5f9;padding-top:.6rem">
      <div class="filter-lbl mb-1">Légende — distance</div>
      <div class="legend-row"><span class="dot" style="background:#10b981"></span>&lt; 2 km du centre</div>
      <div class="legend-row"><span class="dot" style="background:#3b82f6"></span>2 – 5 km</div>
      <div class="legend-row"><span class="dot" style="background:#f59e0b"></span>5 – 10 km</div>
      <div class="legend-row"><span class="dot" style="background:#ef4444"></span>&gt; 10 km</div>
      <div class="legend-row"><span class="dot" style="background:#94a3b8"></span>Distance inconnue</div>
    </div>

  </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script>
const GEO = {geo_json};
let mapObj, clusterGroup;

function fmt(n) {{ return n != null ? Number(n).toLocaleString('fr-FR') : '—'; }}
function trunc(s,n) {{ return s && s.length > n ? s.slice(0,n) + '…' : (s || '—'); }}
function dCol(d) {{
  if (d == null) return '#94a3b8';
  return d < 2 ? '#10b981' : d < 5 ? '#3b82f6' : d < 10 ? '#f59e0b' : '#ef4444';
}}

function updateStats(data) {{
  const prices = data.map(l => l.price).filter(p => p > 0);
  const avg = prices.length ? Math.round(prices.reduce((a,b) => a+b,0) / prices.length) : null;
  document.getElementById('qs-min').textContent  = prices.length ? fmt(Math.min(...prices)) + ' €' : '—';
  document.getElementById('qs-max').textContent  = prices.length ? fmt(Math.max(...prices)) + ' €' : '—';
  document.getElementById('qs-avg').textContent  = avg ? fmt(avg) + ' €' : '—';
  document.getElementById('qs-cnt').textContent  = data.length;
  document.getElementById('geo-count').textContent = data.length;
}}

function buildMap(data) {{
  if (clusterGroup) {{ mapObj.removeLayer(clusterGroup); }}
  clusterGroup = L.markerClusterGroup({{
    maxClusterRadius: 40,
    iconCreateFunction: cluster => {{
      const n = cluster.getChildCount();
      const sz = n < 10 ? 32 : n < 50 ? 40 : 48;
      return L.divIcon({{
        html: `<div style="background:#3b82f6;color:#fff;border-radius:50%;
          width:${{sz}}px;height:${{sz}}px;display:flex;align-items:center;
          justify-content:center;font-weight:800;font-size:.8rem;
          box-shadow:0 2px 8px rgba(0,0,0,.35);border:2px solid #fff;">${{n}}</div>`,
        iconSize: [sz,sz], iconAnchor: [sz/2,sz/2], className: ''
      }});
    }}
  }});

  const bounds = [];
  data.forEach(l => {{
    const col = dCol(l.distance_km);
    const pm2 = (l.price > 0 && l.surface > 0) ? Math.round(l.price / l.surface) : null;
    const icon = L.divIcon({{
      html: `<div style="background:${{col}};width:14px;height:14px;border-radius:50%;
        border:2px solid #fff;box-shadow:0 1px 5px rgba(0,0,0,.4)"></div>`,
      iconSize: [14,14], iconAnchor: [7,7], className: ''
    }});
    const popup = `
      <div style="min-width:210px;font-size:.85rem;font-family:'Segoe UI',sans-serif">
        <div style="font-weight:700;color:#0f172a;margin-bottom:2px;font-size:.95rem">${{l.city || ''}}</div>
        <div style="font-size:1.15rem;color:#3b82f6;font-weight:800;margin-bottom:4px">
          ${{l.price ? fmt(l.price) + ' €' : '—'}}
        </div>
        <div style="font-size:.78rem;color:#64748b;margin-bottom:6px">
          ${{l.surface ? l.surface + ' m²' : ''}}
          ${{l.rooms ? ' · ' + l.rooms + ' ch.' : ''}}
          ${{pm2 ? ' · ' + pm2 + ' €/m²' : ''}}
        </div>
        ${{l.distance_km != null
          ? `<div style="font-size:.75rem;color:#94a3b8;margin-bottom:4px">${{l.distance_km.toFixed(1)}} km du centre</div>`
          : ''}}
        <div style="font-size:.78rem;color:#475569;margin-bottom:8px">${{trunc(l.title, 60)}}</div>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="font-size:.68rem;color:#94a3b8">${{l.site || ''}}</span>
          <a href="${{l.url}}" target="_blank"
             style="background:#3b82f6;color:#fff;text-decoration:none;border-radius:6px;
                    padding:4px 12px;font-size:.78rem;font-weight:700">
            Voir →
          </a>
        </div>
      </div>`;
    bounds.push([l.latitude, l.longitude]);
    L.marker([l.latitude, l.longitude], {{icon}})
      .bindPopup(popup, {{maxWidth: 260, className: ''}})
      .addTo(clusterGroup);
  }});

  clusterGroup.addTo(mapObj);
  if (bounds.length > 0) {{
    try {{ mapObj.fitBounds(bounds, {{padding: [30,30], maxZoom: 13}}); }} catch(e) {{}}
  }}
  updateStats(data);
}}

function applyFilters() {{
  const city = document.getElementById('f-city').value;
  const site = document.getElementById('f-site').value;
  const dist = parseFloat(document.getElementById('f-dist').value) || Infinity;
  const d = GEO.filter(l => {{
    if (city && l.city !== city) return false;
    if (site && l.site !== site) return false;
    if (dist < Infinity && l.distance_km != null && l.distance_km > dist) return false;
    return true;
  }});
  buildMap(d);
}}

function resetFilters() {{
  document.getElementById('f-city').value = '';
  document.getElementById('f-site').value = '';
  document.getElementById('f-dist').value = '';
  buildMap(GEO);
}}

function togglePanel() {{
  document.getElementById('panel').classList.toggle('collapsed');
}}

window.addEventListener('DOMContentLoaded', () => {{
  // Replié par défaut sur mobile (écran < 640px)
  if (window.innerWidth < 640) {{
    document.getElementById('panel').classList.add('collapsed');
  }}
  mapObj = L.map('map').setView([49.6116, 6.1319], 11);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© OpenStreetMap contributors', maxZoom: 19
  }}).addTo(mapObj);
  buildMap(GEO);
}});
</script>
</body>
</html>'''


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(DB_PATH):
        print(f"Erreur: {DB_PATH} introuvable"); sys.exit(1)

    OUT_DIR.mkdir(exist_ok=True)
    ARCHIVES_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)

    listings = load_listings()
    stats    = calc_stats(listings)
    now          = datetime.now()
    generated_at = now.strftime('%d/%m/%Y %H:%M')
    cache_ver    = now.strftime('%Y%m%d%H%M')

    # Page principale (sans carte)
    html_index = generate_index_html(listings, stats, generated_at)
    (OUT_DIR / 'index.html').write_text(html_index, encoding='utf-8')

    # Page carte
    geo_count = sum(1 for l in listings if l.get('latitude') and l.get('longitude'))
    html_map  = generate_map_html(listings, generated_at)
    (OUT_DIR / 'map.html').write_text(html_map, encoding='utf-8')

    # Fichiers PWA
    (OUT_DIR / 'manifest.json').write_text(generate_manifest(), encoding='utf-8')
    (OUT_DIR / 'sw.js').write_text(generate_sw(cache_ver), encoding='utf-8')
    (OUT_DIR / 'icon.svg').write_text(ICON_SVG, encoding='utf-8')

    # Archive du jour
    archive = now.strftime('%Y-%m-%d') + '.html'
    (ARCHIVES_DIR / archive).write_text(html_index, encoding='utf-8')

    # Export JSON
    (DATA_DIR / 'listings.json').write_text(
        json.dumps(listings, ensure_ascii=False, indent=2, default=str), encoding='utf-8'
    )

    print(f"Dashboard genere : {len(listings)} annonces")
    print(f"  dashboards/index.html  (sans carte)")
    print(f"  dashboards/map.html    ({geo_count} annonces geo)")
    print(f"  PWA : manifest.json + sw.js + icon.svg")


if __name__ == '__main__':
    main()
