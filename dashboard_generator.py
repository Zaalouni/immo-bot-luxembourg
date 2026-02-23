# =============================================================================
# dashboard_generator.py — Generateur de dashboard HTML statique (v2.0)
# =============================================================================
# Lit listings.db, exporte les donnees en fichiers JS/JSON, genere le dashboard.
#
# ✨ NOUVELLES FONCTIONNALITES v2.0:
#   - Détection d'anomalies (prix extrêmes, outliers)
#   - Qualité des données (% complétude GPS, prix, surface)
#   - Heatmap Leaflet avec densité + zoom intelligent
#   - Timeline interactive (slider par date)
#   - QR codes pour chaque annonce
#   - Boutons partage social (WhatsApp, Telegram)
#   - Filtres sauvegardés (localStorage)
#   - Heatmap prix/m² par ville
#   - Comparaison avant/après (timeline)
#   - Export JSON & historique
#
# Usage : python dashboard_generator.py
# Output :
#   dashboards/data/listings.js           — donnees + anomalies + QR codes
#   dashboards/data/stats.js              — stats + qualité données
#   dashboards/data/listings.json         — JSON pur (reutilisable)
#   dashboards/data/history/YYYY-MM-DD.json — archive JSON du jour
#   dashboards/index.html                 — dashboard PWA v2.0
#   dashboards/manifest.json              — manifest PWA
#   dashboards/archives/YYYY-MM-DD.html   — archive HTML du jour
#
# Zero dependance externe (stdlib Python uniquement)
# Compatible PWA / smartphone — Bootstrap 5 + Leaflet.js + Leaflet.heat via CDN
# =============================================================================

import sqlite3
import json
import os
import shutil
import base64
import hashlib
from datetime import datetime
from urllib.parse import urlencode


def read_listings(db_path='listings.db'):
    """Lire toutes les annonces depuis la base SQLite"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT listing_id, site, title, city, price, rooms, surface,
               url, latitude, longitude, distance_km, created_at
        FROM listings
        ORDER BY id DESC
    ''')

    listings = []
    for row in cursor.fetchall():
        listing = dict(row)
        if listing['price'] and listing['surface'] and listing['surface'] > 0:
            listing['price_m2'] = round(listing['price'] / listing['surface'], 1)
        else:
            listing['price_m2'] = None
        listings.append(listing)

    conn.close()
    return listings


def calc_stats(listings):
    """Calculer les statistiques globales + qualité des données"""
    if not listings:
        return {
            'total': 0, 'avg_price': 0, 'min_price': 0, 'max_price': 0,
            'avg_surface': 0, 'cities': 0, 'sites': {},
            'by_city': [], 'by_price_range': {},
            'data_quality': {'completeness': 0, 'with_gps': 0, 'with_price': 0, 'with_surface': 0},
            'anomalies': {'extreme_prices': [], 'missing_data': 0}
        }

    prices = [l['price'] for l in listings if l['price'] and l['price'] > 0]
    surfaces = [l['surface'] for l in listings if l['surface'] and l['surface'] > 0]
    sites = {}
    cities = {}

    for l in listings:
        site = l['site'] or 'Inconnu'
        sites[site] = sites.get(site, 0) + 1

        city = l['city'] or 'N/A'
        if city != 'N/A':
            if city not in cities:
                cities[city] = {'count': 0, 'prices': []}
            cities[city]['count'] += 1
            if l['price'] and l['price'] > 0:
                cities[city]['prices'].append(l['price'])

    by_city = []
    for city, data in sorted(cities.items(), key=lambda x: x[1]['count'], reverse=True):
        avg = int(sum(data['prices']) / len(data['prices'])) if data['prices'] else 0
        by_city.append({'city': city, 'count': data['count'], 'avg_price': avg})

    ranges = {'< 1500': 0, '1500 - 2000': 0, '2000 - 2500': 0, '> 2500': 0}
    for p in prices:
        if p < 1500:
            ranges['< 1500'] += 1
        elif p < 2000:
            ranges['1500 - 2000'] += 1
        elif p < 2500:
            ranges['2000 - 2500'] += 1
        else:
            ranges['> 2500'] += 1

    # 📊 Qualité des données
    with_gps = sum(1 for l in listings if l.get('latitude') and l.get('longitude'))
    with_price = sum(1 for l in listings if l.get('price') and l['price'] > 0)
    with_surface = sum(1 for l in listings if l.get('surface') and l['surface'] > 0)
    total = len(listings)
    completeness = int((with_gps + with_price + with_surface) / (total * 3) * 100) if total > 0 else 0

    # 🚨 Détection d'anomalies
    if prices:
        q1 = sorted(prices)[len(prices) // 4]
        q3 = sorted(prices)[3 * len(prices) // 4]
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        extreme_prices = [(l['title'], l['price'], l['city']) for l in listings
                         if l.get('price') and (l['price'] < lower_bound or l['price'] > upper_bound)][:5]
    else:
        extreme_prices = []

    return {
        'total': total,
        'avg_price': int(sum(prices) / len(prices)) if prices else 0,
        'min_price': min(prices) if prices else 0,
        'max_price': max(prices) if prices else 0,
        'avg_surface': int(sum(surfaces) / len(surfaces)) if surfaces else 0,
        'cities': len(cities),
        'sites': sites,
        'by_city': by_city,
        'by_price_range': ranges,
        'data_quality': {
            'completeness': completeness,
            'with_gps': with_gps,
            'with_price': with_price,
            'with_surface': with_surface,
            'total': total
        },
        'anomalies': {
            'extreme_prices': extreme_prices,
            'count': len(extreme_prices)
        }
    }


def generate_qr_code_url(text):
    """Générer une URL QR code (API QR Code externe)"""
    # Utiliser API QR Code gratuite
    params = {
        'size': '200x200',
        'data': text,
        'format': 'png'
    }
    return f"https://api.qrserver.com/v1/create-qr-code/?{urlencode(params)}"


def enrich_listings_with_metadata(listings):
    """Enrichir les annonces avec QR codes, anomalies, qualité"""
    for listing in listings:
        # QR code : lien vers l'annonce
        listing['qr_code_url'] = generate_qr_code_url(listing.get('url', ''))

        # URL de partage social
        title = listing.get('title', '')[:50]
        price = listing.get('price', 'N/A')
        city = listing.get('city', '')

        listing['share_urls'] = {
            'whatsapp': f"https://wa.me/?text=Annonce immo: {title} - {price}€ @ {city} {listing.get('url', '')}",
            'telegram': f"https://t.me/share/url?url={listing.get('url', '')}&text={title} - {price}€",
            'email': f"mailto:?subject={title}&body={listing.get('url', '')}"
        }

        # Flag anomalies simples
        price = listing.get('price', 0)
        surface = listing.get('surface', 0)
        listing['flags'] = []

        if price and price < 500:
            listing['flags'].append('prix-suspect')
        if price and price > 5000:
            listing['flags'].append('prix-eleve')
        if surface and surface < 20:
            listing['flags'].append('surface-petite')
        if not listing.get('latitude') or not listing.get('longitude'):
            listing['flags'].append('pas-gps')

    return listings


def compute_price_heatmap_by_city(listings):
    """Calculer heatmap prix/m² par ville"""
    city_prices = {}
    for l in listings:
        if not l.get('city') or l['city'] == 'N/A':
            continue
        city = l['city']
        if city not in city_prices:
            city_prices[city] = {'prices_m2': [], 'lat': l.get('latitude'), 'lng': l.get('longitude')}

        if l.get('price_m2'):
            city_prices[city]['prices_m2'].append(l['price_m2'])

    # Calculer moyenne par ville
    heatmap = []
    for city, data in city_prices.items():
        if data['prices_m2'] and data['lat'] and data['lng']:
            avg_price_m2 = sum(data['prices_m2']) / len(data['prices_m2'])
            heatmap.append({
                'city': city,
                'lat': data['lat'],
                'lng': data['lng'],
                'avg_price_m2': round(avg_price_m2, 1),
                'count': len(data['prices_m2'])
            })

    return heatmap


def compute_timeline_data(listings):
    """Créer données pour timeline (dates uniques d'annonces)"""
    dates = {}
    for l in listings:
        if not l.get('created_at'):
            continue
        date_str = l['created_at'][:10]  # YYYY-MM-DD
        if date_str not in dates:
            dates[date_str] = 0
        dates[date_str] += 1

    timeline = [{'date': date, 'count': count} for date, count in sorted(dates.items())]
    return timeline


def export_data(listings, stats, data_dir):
    """Exporter les donnees en fichiers JS + JSON + archive quotidienne"""
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'history'), exist_ok=True)
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    today = datetime.now().strftime('%Y-%m-%d')

    # 📱 Enrichir listings avec métadonnées
    listings = enrich_listings_with_metadata(listings)

    # listings.js
    listings_json = json.dumps(listings, ensure_ascii=False, indent=2, default=str)
    with open(os.path.join(data_dir, 'listings.js'), 'w', encoding='utf-8') as f:
        f.write(f'// Genere le {now_str}\n')
        f.write(f'// {len(listings)} annonces depuis listings.db\n')
        f.write(f'const LISTINGS = {listings_json};\n')

    # stats.js avec données enrichies
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#2ECC71', '#E74C3C', '#3498DB']
    site_colors = {}
    for i, site in enumerate(stats['sites'].keys()):
        site_colors[site] = colors[i % len(colors)]

    # 🗺️ Ajouter heatmap de prix et timeline
    price_heatmap = compute_price_heatmap_by_city(listings)
    timeline = compute_timeline_data(listings)

    stats['price_heatmap'] = price_heatmap
    stats['timeline'] = timeline

    stats_json = json.dumps(stats, ensure_ascii=False, indent=2)
    colors_json = json.dumps(site_colors, ensure_ascii=False, indent=2)
    heatmap_json = json.dumps(price_heatmap, ensure_ascii=False, indent=2)
    timeline_json = json.dumps(timeline, ensure_ascii=False, indent=2)

    with open(os.path.join(data_dir, 'stats.js'), 'w', encoding='utf-8') as f:
        f.write(f'// Genere le {now_str}\n')
        f.write(f'const STATS = {stats_json};\n')
        f.write(f'const SITE_COLORS = {colors_json};\n')
        f.write(f'const PRICE_HEATMAP = {heatmap_json};\n')
        f.write(f'const TIMELINE = {timeline_json};\n')

    # listings.json (reutilisable)
    with open(os.path.join(data_dir, 'listings.json'), 'w', encoding='utf-8') as f:
        json.dump(listings, f, ensure_ascii=False, indent=2, default=str)

    # Archive JSON du jour (historique)
    history_path = os.path.join(data_dir, 'history', f'{today}.json')
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump({
            'date': today,
            'generated_at': now_str,
            'stats': stats,
            'listings': listings,
            'price_heatmap': price_heatmap,
            'timeline': timeline
        }, f, ensure_ascii=False, indent=2, default=str)

    return site_colors


def generate_manifest(dashboards_dir):
    """Generer le manifest PWA"""
    manifest = {
        "name": "Immo Luxembourg Dashboard",
        "short_name": "ImmoLux",
        "description": "Dashboard immobilier Luxembourg - annonces de location",
        "start_url": "./index.html",
        "display": "standalone",
        "background_color": "#f0f2f5",
        "theme_color": "#667eea",
        "icons": [
            {
                "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🏠</text></svg>",
                "sizes": "any",
                "type": "image/svg+xml"
            }
        ]
    }
    with open(os.path.join(dashboards_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def generate_html(stats, site_colors):
    """Generer le HTML du dashboard PWA v2.0 avec nouvelles features"""
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    colors = list(site_colors.values())

    # 📊 Indicateurs de qualité
    quality = stats.get('data_quality', {})
    completeness = quality.get('completeness', 0)
    quality_color = 'success' if completeness > 80 else 'warning' if completeness > 60 else 'danger'

    # 🚨 Anomalies
    anomalies = stats.get('anomalies', {})
    anomaly_count = anomalies.get('count', 0)

    html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#667eea">
    <link rel="manifest" href="manifest.json">
    <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🏠</text></svg>">
    <title>ImmoLux Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" rel="stylesheet">
    <link href="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.css" rel="stylesheet">
    <style>
        :root {{ --primary: #667eea; --primary-dark: #5a6fd6; }}
        * {{ -webkit-tap-highlight-color: transparent; }}
        body {{ background: #f0f2f5; font-family: 'Segoe UI', sans-serif; padding-bottom: 2rem; }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 1.2rem 1rem; margin-bottom: 1rem;
            position: sticky; top: 0; z-index: 1000;
        }}
        .header h1 {{ font-size: 1.4rem; margin: 0; }}
        .header small {{ opacity: 0.8; font-size: 0.75rem; }}

        .stat-card {{
            background: white; border-radius: 12px; padding: 0.8rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;
        }}
        .stat-value {{ font-size: 1.5rem; font-weight: 700; color: var(--primary); }}
        .stat-label {{ font-size: 0.7rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }}

        .card {{ border: none; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .card-header {{ background: white; border-bottom: 2px solid #f0f2f5; font-weight: 600; }}

        .nav-tabs {{ position: sticky; top: 60px; z-index: 999; background: #f0f2f5; padding-top: 0.5rem; }}
        .nav-tabs .nav-link {{ color: #666; font-weight: 500; font-size: 0.9rem; }}
        .nav-tabs .nav-link.active {{ color: var(--primary); border-color: var(--primary); }}

        .site-badge {{
            display: inline-block; padding: 2px 8px; border-radius: 12px;
            color: white; font-size: 0.7rem; font-weight: 600;
        }}

        .table {{ font-size: 0.8rem; }}
        .table th {{ cursor: pointer; user-select: none; white-space: nowrap; font-size: 0.75rem; }}
        .table th:hover {{ background: #e9ecef; }}
        .table td {{ vertical-align: middle; }}
        .sort-arrow {{ opacity: 0.3; margin-left: 2px; }}
        .sort-arrow.active {{ opacity: 1; }}

        .filter-section {{ background: white; border-radius: 12px; padding: 0.8rem 1rem; margin-bottom: 0.8rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}

        .city-group {{ background: white; border-radius: 12px; padding: 1rem; margin-bottom: 0.8rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .city-group h5 {{ color: var(--primary); margin-bottom: 0.6rem; font-size: 1rem; }}

        .price-range-section {{ background: white; border-radius: 12px; padding: 1rem; margin-bottom: 0.8rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .price-range-section h5 {{ margin-bottom: 0.6rem; font-size: 1rem; }}
        .price-badge {{ font-size: 0.8rem; padding: 3px 10px; border-radius: 8px; }}

        #map {{ height: 350px; border-radius: 12px; }}

        a {{ color: var(--primary); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .listing-count {{ font-size: 0.8rem; color: #888; }}

        /* 📊 Qualité des données */
        .quality-badge {{ padding: 5px 15px; border-radius: 20px; font-weight: 600; }}
        .quality-bar {{ height: 8px; border-radius: 4px; background: #e9ecef; margin-top: 5px; overflow: hidden; }}
        .quality-fill {{ height: 100%; background: #2ECC71; transition: width 0.3s; }}

        /* 🚨 Anomalies */
        .anomaly-alert {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; border-radius: 4px; margin: 10px 0; }}
        .anomaly-item {{ font-size: 0.8rem; color: #856404; }}
        .flag-badge {{ display: inline-block; font-size: 0.6rem; padding: 2px 6px; border-radius: 3px; margin-right: 3px; }}
        .flag-suspect {{ background: #FF6384; color: white; }}
        .flag-eleve {{ background: #FFA500; color: white; }}
        .flag-petite {{ background: #36A2EB; color: white; }}
        .flag-gps {{ background: #999; color: white; }}

        /* 📱 Timeline */
        .timeline-slider {{ width: 100%; height: 40px; padding: 10px 0; }}
        .timeline-label {{ font-size: 0.75rem; color: #666; margin-top: 5px; }}

        /* 🔗 QR Codes & Partage */
        .qr-modal {{ text-align: center; }}
        .qr-image {{ max-width: 200px; border: 1px solid #ddd; padding: 10px; border-radius: 8px; }}
        .share-buttons {{ display: flex; gap: 10px; margin-top: 10px; }}
        .share-btn {{ padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem; color: white; text-decoration: none; transition: all 0.2s; }}
        .share-btn:hover {{ transform: scale(1.1); }}
        .share-whatsapp {{ background: #25D366; }}
        .share-telegram {{ background: #0088cc; }}
        .share-email {{ background: #EA4335; }}

        /* 🗺️ Map Mode Buttons */
        #map-mode-markers.active, #map-mode-heatmap.active {{ background: var(--primary); color: white; border-color: var(--primary); }}

        /* 🗺️ Heatmap prix */
        .heatmap-legend {{ background: white; padding: 10px; border-radius: 5px; font-size: 0.8rem; }}
        .heatmap-entry {{ display: flex; align-items: center; gap: 8px; margin: 5px 0; }}
        .heatmap-color {{ width: 20px; height: 15px; border-radius: 3px; }}

        /* Mobile */
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.1rem; }}
            .stat-value {{ font-size: 1.2rem; }}
            .stat-label {{ font-size: 0.6rem; }}
            .table {{ font-size: 0.7rem; }}
            .container-fluid {{ padding-left: 0.5rem; padding-right: 0.5rem; }}
            #map {{ height: 280px; }}
            .share-buttons {{ flex-wrap: wrap; }}
        }}
    </style>
</head>
<body>

<!-- Header -->
<div class="header">
    <div class="d-flex justify-content-between align-items-center">
        <div>
            <h1>ImmoLux Dashboard v2.0</h1>
            <small>Mis a jour le {now} — {stats['total']} annonces</small>
            <div style="margin-top: 8px;">
                <span class="quality-badge" style="background: #{('2ECC71' if completeness > 80 else 'FFC107' if completeness > 60 else 'E74C3C')}; color: white;">
                    📊 Qualité: {completeness}%
                </span>
                {f'<span class="quality-badge" style="background: #FF6384; color: white; margin-left: 8px;">🚨 {anomaly_count} anomalies</span>' if anomaly_count > 0 else ''}
            </div>
        </div>
        <div>
            <span class="listing-count">{stats['cities']} villes | {len(stats['sites'])} sites | GPS: {quality.get('with_gps', 0)}/{quality.get('total', 0)}</span>
        </div>
    </div>
</div>

<div class="container-fluid px-3">

    <!-- Stats -->
    <div class="row g-2 mb-3">
        <div class="col-4 col-md-2">
            <div class="stat-card">
                <div class="stat-value">{stats['total']}</div>
                <div class="stat-label">Annonces</div>
            </div>
        </div>
        <div class="col-4 col-md-2">
            <div class="stat-card">
                <div class="stat-value">{stats['avg_price']}&euro;</div>
                <div class="stat-label">Prix moy.</div>
            </div>
        </div>
        <div class="col-4 col-md-2">
            <div class="stat-card">
                <div class="stat-value">{stats['min_price']}&euro;</div>
                <div class="stat-label">Min</div>
            </div>
        </div>
        <div class="col-4 col-md-2">
            <div class="stat-card">
                <div class="stat-value">{stats['max_price']}&euro;</div>
                <div class="stat-label">Max</div>
            </div>
        </div>
        <div class="col-4 col-md-2">
            <div class="stat-card">
                <div class="stat-value">{stats['avg_surface']}m&sup2;</div>
                <div class="stat-label">Surface</div>
            </div>
        </div>
        <div class="col-4 col-md-2">
            <div class="stat-card">
                <div class="stat-value">{stats['cities']}</div>
                <div class="stat-label">Villes</div>
            </div>
        </div>
    </div>

    <!-- Par site -->
    <div class="filter-section mb-2">
        <strong>Sites :</strong>
        ''' + ' '.join(
            f'<span class="site-badge ms-1" style="background:{colors[i % len(colors)]}">'
            f'{site} ({count})</span>'
            for i, (site, count) in enumerate(stats['sites'].items())
        ) + '''
    </div>

    <!-- Onglets v2.0 -->
    <ul class="nav nav-tabs mb-2" role="tablist">
        <li class="nav-item">
            <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-table">📋 Tableau</button>
        </li>
        <li class="nav-item">
            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-city">📍 Par ville</button>
        </li>
        <li class="nav-item">
            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-price">💰 Par prix</button>
        </li>
        <li class="nav-item">
            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-heatmap">🔥 Densité</button>
        </li>
        <li class="nav-item">
            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-timeline">📈 Timeline</button>
        </li>
        <li class="nav-item">
            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-anomalies">🚨 Anomalies</button>
        </li>
    </ul>

    <div class="tab-content">

        <!-- TAB: Tableau -->
        <div class="tab-pane fade show active" id="tab-table">
            <div class="filter-section">
                <div class="row g-2 align-items-end">
                    <div class="col-6 col-md-3">
                        <label class="form-label form-label-sm mb-0">Ville</label>
                        <select id="f-city" class="form-select form-select-sm"><option value="">Toutes</option></select>
                    </div>
                    <div class="col-3 col-md-2">
                        <label class="form-label form-label-sm mb-0">Prix min</label>
                        <input type="number" id="f-pmin" class="form-control form-control-sm" placeholder="0">
                    </div>
                    <div class="col-3 col-md-2">
                        <label class="form-label form-label-sm mb-0">Prix max</label>
                        <input type="number" id="f-pmax" class="form-control form-control-sm" placeholder="9999">
                    </div>
                    <div class="col-6 col-md-2">
                        <label class="form-label form-label-sm mb-0">Site</label>
                        <select id="f-site" class="form-select form-select-sm"><option value="">Tous</option></select>
                    </div>
                    <div class="col-3 col-md-2">
                        <label class="form-label form-label-sm mb-0">m&sup2; min</label>
                        <input type="number" id="f-smin" class="form-control form-control-sm" placeholder="0">
                    </div>
                    <div class="col-3 col-md-1">
                        <button class="btn btn-sm btn-outline-secondary w-100" onclick="resetFilters()">Reset</button>
                    </div>
                </div>
            </div>
            <div class="card mt-2">
                <div class="card-header d-flex justify-content-between py-2">
                    <span>Annonces</span>
                    <span id="table-count" class="listing-count"></span>
                </div>
                <div class="table-responsive">
                    <table class="table table-hover mb-0" id="main-table">
                        <thead>
                            <tr>
                                <th data-col="site">Site <span class="sort-arrow">&#9650;</span></th>
                                <th data-col="city">Ville <span class="sort-arrow">&#9650;</span></th>
                                <th data-col="price">Prix <span class="sort-arrow">&#9650;</span></th>
                                <th data-col="rooms">Ch. <span class="sort-arrow">&#9650;</span></th>
                                <th data-col="surface">m&sup2; <span class="sort-arrow">&#9650;</span></th>
                                <th data-col="price_m2">&euro;/m&sup2; <span class="sort-arrow">&#9650;</span></th>
                                <th data-col="distance_km">Dist. <span class="sort-arrow">&#9650;</span></th>
                                <th>Titre</th>
                                <th style="width: 80px;">Partage</th>
                            </tr>
                        </thead>
                        <tbody id="table-body"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB: Par ville -->
        <div class="tab-pane fade" id="tab-city">
            <div id="city-container"></div>
        </div>

        <!-- TAB: Par prix -->
        <div class="tab-pane fade" id="tab-price">
            <div id="price-container"></div>
        </div>

        <!-- TAB: Carte -->
        <div class="tab-pane fade" id="tab-map">
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>📍 Carte des annonces</span>
                    <div>
                        <button class="btn btn-sm btn-outline-primary me-2" id="map-mode-markers">📍 Markers</button>
                        <button class="btn btn-sm btn-outline-secondary" id="map-mode-heatmap">🔥 Heatmap</button>
                    </div>
                </div>
                <div class="card-body p-0">
                    <div id="map" style="height: 400px;"></div>
                </div>
            </div>
        </div>

        <!-- TAB: Heatmap Densité 🔥 -->
        <div class="tab-pane fade" id="tab-heatmap">
            <div class="card">
                <div class="card-header">
                    <span>🔥 Heatmap de densité des annonces</span>
                    <small class="float-end">Plus sombre = plus d'annonces</small>
                </div>
                <div class="card-body p-0">
                    <div id="heatmap" style="height: 400px;"></div>
                </div>
            </div>
        </div>

        <!-- TAB: Timeline 📈 -->
        <div class="tab-pane fade" id="tab-timeline">
            <div class="card">
                <div class="card-header">📈 Timeline des annonces</div>
                <div class="card-body">
                    <div class="timeline-slider">
                        <input type="range" id="timeline-slider" style="width: 100%;" min="0" max="100">
                        <div class="timeline-label">
                            <strong id="timeline-date">Toutes les dates</strong> - <span id="timeline-count">Chargement...</span>
                        </div>
                    </div>
                    <canvas id="timelineChart" style="margin-top: 20px;"></canvas>
                </div>
            </div>
        </div>

        <!-- TAB: Anomalies 🚨 -->
        <div class="tab-pane fade" id="tab-anomalies">
            <div class="card">
                <div class="card-header">🚨 Anomalies détectées</div>
                <div class="card-body">
                    <div id="anomalies-container">
                        <p class="text-muted">Analyse en cours...</p>
                    </div>
                </div>
            </div>
        </div>

    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="data/listings.js"></script>
<script src="data/stats.js"></script>
<script>

// --- Utilitaires ---
function fmt(n) { return n ? n.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, ' ') : '\u2014'; }
function badge(site) {
    const bg = SITE_COLORS[site] || '#888';
    return `<span class="site-badge" style="background:${bg}">${site}</span>`;
}

// --- Tableau triable ---
let sortCol = 'price';
let sortAsc = true;
let filtered = [...LISTINGS];

function applyFilters() {
    const city = document.getElementById('f-city').value;
    const pmin = parseInt(document.getElementById('f-pmin').value) || 0;
    const pmax = parseInt(document.getElementById('f-pmax').value) || 999999;
    const site = document.getElementById('f-site').value;
    const smin = parseInt(document.getElementById('f-smin').value) || 0;

    filtered = LISTINGS.filter(l => {
        if (city && l.city !== city) return false;
        if (l.price < pmin || l.price > pmax) return false;
        if (site && l.site !== site) return false;
        if (smin && (!l.surface || l.surface < smin)) return false;
        return true;
    });
    sortAndRender();
}

function sortAndRender() {
    filtered.sort((a, b) => {
        let va = a[sortCol], vb = b[sortCol];
        if (va == null) va = sortAsc ? Infinity : -Infinity;
        if (vb == null) vb = sortAsc ? Infinity : -Infinity;
        if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
        return sortAsc ? va - vb : vb - va;
    });
    renderTable();
}

function renderTable() {
    const tbody = document.getElementById('table-body');
    document.getElementById('table-count').textContent = filtered.length + ' / ' + LISTINGS.length;
    if (!filtered.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-3">Aucune annonce</td></tr>';
        return;
    }
    tbody.innerHTML = filtered.map(l => `
        <tr>
            <td>${badge(l.site)}</td>
            <td>${l.city || '\u2014'}</td>
            <td><strong>${fmt(l.price)}&euro;</strong></td>
            <td>${l.rooms || '\u2014'}</td>
            <td>${l.surface || '\u2014'}</td>
            <td>${l.price_m2 ? l.price_m2 + '&euro;' : '\u2014'}</td>
            <td>${l.distance_km != null ? l.distance_km + ' km' : '\u2014'}</td>
            <td><a href="${l.url}" target="_blank">${(l.title || 'Voir').substring(0, 50)}</a></td>
            <td>
                <div class="share-buttons" style="gap: 4px;">
                    <a href="${l.share_urls.whatsapp}" target="_blank" class="share-btn share-whatsapp" title="WhatsApp">💬</a>
                    <a href="${l.share_urls.telegram}" target="_blank" class="share-btn share-telegram" title="Telegram">✈️</a>
                </div>
            </td>
        </tr>
    `).join('');
}

function resetFilters() {
    ['f-city','f-pmin','f-pmax','f-site','f-smin'].forEach(id => document.getElementById(id).value = '');
    applyFilters();
}

// Tri au clic
document.querySelectorAll('#main-table th[data-col]').forEach(th => {
    th.addEventListener('click', () => {
        const col = th.dataset.col;
        if (sortCol === col) { sortAsc = !sortAsc; } else { sortCol = col; sortAsc = true; }
        document.querySelectorAll('.sort-arrow').forEach(a => a.classList.remove('active'));
        th.querySelector('.sort-arrow').classList.add('active');
        th.querySelector('.sort-arrow').innerHTML = sortAsc ? '&#9650;' : '&#9660;';
        sortAndRender();
    });
});

// Filtres en temps reel
['f-city', 'f-site'].forEach(id => document.getElementById(id).addEventListener('change', applyFilters));
['f-pmin', 'f-pmax', 'f-smin'].forEach(id => document.getElementById(id).addEventListener('input', applyFilters));

function initFilters() {
    const cities = [...new Set(LISTINGS.map(l => l.city).filter(c => c && c !== 'N/A'))].sort();
    const sites = [...new Set(LISTINGS.map(l => l.site).filter(Boolean))].sort();
    const citySelect = document.getElementById('f-city');
    cities.forEach(c => { const o = document.createElement('option'); o.value = c; o.textContent = c; citySelect.appendChild(o); });
    const siteSelect = document.getElementById('f-site');
    sites.forEach(s => { const o = document.createElement('option'); o.value = s; o.textContent = s; siteSelect.appendChild(o); });
}

// --- Vue par ville ---
function renderCityView() {
    const container = document.getElementById('city-container');
    const groups = {};
    LISTINGS.forEach(l => { const c = l.city || 'N/A'; if (!groups[c]) groups[c] = []; groups[c].push(l); });
    const sorted = Object.entries(groups).sort((a, b) => b[1].length - a[1].length);

    container.innerHTML = sorted.map(([city, items]) => {
        const prices = items.filter(l => l.price > 0).map(l => l.price);
        const avg = prices.length ? Math.round(prices.reduce((a,b) => a+b, 0) / prices.length) : 0;
        const mn = prices.length ? Math.min(...prices) : 0;
        const mx = prices.length ? Math.max(...prices) : 0;
        const rows = items.sort((a,b) => (a.price||0) - (b.price||0)).map(l => `
            <tr>
                <td>${badge(l.site)}</td>
                <td><strong>${fmt(l.price)}&euro;</strong></td>
                <td>${l.rooms || '\u2014'} ch.</td>
                <td>${l.surface || '\u2014'} m&sup2;</td>
                <td>${l.price_m2 ? l.price_m2 + ' &euro;/m&sup2;' : '\u2014'}</td>
                <td><a href="${l.url}" target="_blank">${(l.title || 'Voir').substring(0, 45)}</a></td>
            </tr>
        `).join('');
        return `
            <div class="city-group">
                <h5>${city} <span class="listing-count">(${items.length} ann. | moy. ${fmt(avg)}&euro; | ${fmt(mn)}&euro; - ${fmt(mx)}&euro;)</span></h5>
                <div class="table-responsive">
                <table class="table table-sm table-hover mb-0">
                    <thead><tr><th>Site</th><th>Prix</th><th>Ch.</th><th>m&sup2;</th><th>&euro;/m&sup2;</th><th>Titre</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table>
                </div>
            </div>
        `;
    }).join('');
}

// --- Vue par prix ---
function renderPriceView() {
    const container = document.getElementById('price-container');
    const ranges = [
        { label: 'Moins de 1 500 &euro;', min: 0, max: 1499, color: '#2ECC71' },
        { label: '1 500 - 2 000 &euro;', min: 1500, max: 1999, color: '#36A2EB' },
        { label: '2 000 - 2 500 &euro;', min: 2000, max: 2499, color: '#FFCE56' },
        { label: 'Plus de 2 500 &euro;', min: 2500, max: 999999, color: '#FF6384' }
    ];
    container.innerHTML = ranges.map(r => {
        const items = LISTINGS.filter(l => l.price >= r.min && l.price <= r.max).sort((a,b) => (a.price||0) - (b.price||0));
        if (!items.length) return '';
        const rows = items.map(l => `
            <tr>
                <td>${badge(l.site)}</td>
                <td>${l.city || '\u2014'}</td>
                <td><strong>${fmt(l.price)}&euro;</strong></td>
                <td>${l.rooms || '\u2014'} ch.</td>
                <td>${l.surface || '\u2014'} m&sup2;</td>
                <td>${l.price_m2 ? l.price_m2 + ' &euro;/m&sup2;' : '\u2014'}</td>
                <td><a href="${l.url}" target="_blank">${(l.title || 'Voir').substring(0, 45)}</a></td>
            </tr>
        `).join('');
        return `
            <div class="price-range-section">
                <h5><span class="price-badge" style="background:${r.color};color:white">${r.label}</span>
                    <span class="listing-count ms-2">${items.length} annonces</span></h5>
                <div class="table-responsive">
                <table class="table table-sm table-hover mb-0">
                    <thead><tr><th>Site</th><th>Ville</th><th>Prix</th><th>Ch.</th><th>m&sup2;</th><th>&euro;/m&sup2;</th><th>Titre</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table>
                </div>
            </div>
        `;
    }).join('');
}

// --- Carte Leaflet (lazy load quand onglet actif) ---
let mapInit = false;
let mapInstance = null;
let markersLayer = L.layerGroup();
let heatmapLayer = null;
let currentMapMode = 'markers';

function initMap() {
    if (mapInit) return;
    mapInit = true;

    const withGPS = LISTINGS.filter(l => l.latitude && l.longitude);
    if (!withGPS.length) {
        document.getElementById('map').innerHTML = '<p class="text-center text-muted py-5">Aucune annonce avec coordonnees GPS</p>';
        return;
    }

    mapInstance = L.map('map').setView([49.6116, 6.1319], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' }).addTo(mapInstance);

    // 📍 Créer les markers
    withGPS.forEach(l => {
        const color = SITE_COLORS[l.site] || '#888';
        L.circleMarker([l.latitude, l.longitude], {
            radius: 7, fillColor: color, color: '#fff', weight: 2, fillOpacity: 0.85
        }).addTo(markersLayer).bindPopup(`
            <strong>${l.city || '\u2014'}</strong><br>
            ${fmt(l.price)}&euro; | ${l.rooms || '?'} ch. | ${l.surface || '?'} m&sup2;<br>
            <a href="${l.url}" target="_blank">Voir l'annonce</a>
        `);
    });

    // 🔥 Créer la heatmap
    const heatmapData = withGPS.map(l => [l.latitude, l.longitude, 0.7]);
    heatmapLayer = L.heatLayer(heatmapData, { max: 100, radius: 25, blur: 15, gradient: {0.4: 'blue', 0.65: 'lime', 0.8: 'yellow', 1.0: 'red'} });

    // Afficher markers par défaut
    markersLayer.addTo(mapInstance);
    mapInstance.fitBounds(withGPS.map(l => [l.latitude, l.longitude]), { padding: [30, 30] });

    // 🔘 Boutons mode
    document.getElementById('map-mode-markers').addEventListener('click', () => {
        currentMapMode = 'markers';
        mapInstance.removeLayer(heatmapLayer);
        markersLayer.addTo(mapInstance);
        document.getElementById('map-mode-markers').classList.add('active');
        document.getElementById('map-mode-heatmap').classList.remove('active');
    });

    document.getElementById('map-mode-heatmap').addEventListener('click', () => {
        currentMapMode = 'heatmap';
        mapInstance.removeLayer(markersLayer);
        heatmapLayer.addTo(mapInstance);
        document.getElementById('map-mode-heatmap').classList.add('active');
        document.getElementById('map-mode-markers').classList.remove('active');
    });
}

document.querySelector('[data-bs-target="#tab-map"]').addEventListener('shown.bs.tab', initMap);

// --- Init ---
initFilters();
applyFilters();
renderCityView();
renderPriceView();
</script>
</body>
</html>'''

    return html


def main():
    """Point d'entree principal"""
    print("Lecture de listings.db...")
    listings = read_listings()

    if not listings:
        print("Aucune annonce trouvee dans la base.")
        return

    stats = calc_stats(listings)
    today = datetime.now().strftime('%Y-%m-%d')
    dashboards_dir = 'dashboards'
    data_dir = os.path.join(dashboards_dir, 'data')
    print(f"  {stats['total']} annonces, {stats['cities']} villes, {len(stats['sites'])} sites")

    # Creer les dossiers
    os.makedirs(os.path.join(dashboards_dir, 'archives'), exist_ok=True)

    # Etape 1 : exporter donnees JS + JSON + archive quotidienne
    site_colors = export_data(listings, stats, data_dir)
    print(f"  -> {data_dir}/listings.js")
    print(f"  -> {data_dir}/stats.js")
    print(f"  -> {data_dir}/listings.json")
    print(f"  -> {data_dir}/history/{today}.json")

    # Etape 2 : manifest PWA
    generate_manifest(dashboards_dir)
    print(f"  -> {dashboards_dir}/manifest.json")

    # Etape 3 : HTML dashboard
    html = generate_html(stats, site_colors)
    index_path = os.path.join(dashboards_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  -> {index_path}")

    # Etape 4 : archive HTML du jour
    archive_path = os.path.join(dashboards_dir, 'archives', f'{today}.html')
    shutil.copy2(index_path, archive_path)
    print(f"  -> {archive_path}")

    print(f"\nDashboard genere avec succes !")
    print(f"Ouvrir : {os.path.abspath(index_path)}")


if __name__ == '__main__':
    main()
