# =============================================================================
# data_processor.py — Traitement des données immobilières (v3.0)
# =============================================================================
# Module de logique métier pour le Dashboard PWA
# - Lecture SQLite
# - Calculs statistiques + qualité données + anomalies
# - Enrichissement métadonnées (QR codes, partage social)
# - Exports JSON/JS
#
# Zero dépendances externes (stdlib uniquement)
# =============================================================================

import sqlite3
import json
import os
from datetime import datetime
from urllib.parse import urlencode


def read_listings(db_path='listings.db'):
    """
    Lire toutes les annonces depuis la base de données SQLite.

    Args:
        db_path (str): Chemin vers la base listings.db (défaut: 'listings.db')

    Returns:
        list[dict]: Liste d'annonces enrichies avec price_m2 calculé

    Notes:
        - Calcule le prix/m² si price et surface disponibles
        - Retourne liste vide si DB n'existe pas ou est vide
    """
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
    """
    Calculer les statistiques globales avec qualité de données et détection d'anomalies.

    Args:
        listings (list[dict]): Liste d'annonces

    Returns:
        dict: Statistiques avec clés:
            - total, avg_price, min_price, max_price, avg_surface, cities
            - sites (dict par site)
            - by_city (list de villes avec stats)
            - by_price_range (dict de tranches de prix)
            - data_quality (complétude GPS/prix/surface)
            - anomalies (outliers IQR détectés)

    Notes:
        - Détection d'anomalies via IQR (quartiles)
        - Qualité = (GPS + prix + surface) / (total * 3)
        - Anomalies identifiées sur 5 max
    """
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

    # 🚨 Détection d'anomalies (IQR method)
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
    """
    Générer une URL QR code (via API QR Code externe gratuite).

    Args:
        text (str): Texte ou URL à encoder en QR code

    Returns:
        str: URL vers image PNG du QR code

    Notes:
        - Utilise API QR Server (https://qrserver.com)
        - Pas de dépendance externe (requête via URL)
        - Taille: 200x200 pixels
    """
    params = {
        'size': '200x200',
        'data': text,
        'format': 'png'
    }
    return f"https://api.qrserver.com/v1/create-qr-code/?{urlencode(params)}"


def enrich_listings_with_metadata(listings):
    """
    Enrichir les annonces avec QR codes, URLs de partage social et flags d'anomalies.

    Args:
        listings (list[dict]): Liste d'annonces (modifiée in-place)

    Returns:
        list[dict]: Même liste enrichie avec:
            - qr_code_url: URL vers QR code
            - share_urls: dict avec URLs WhatsApp, Telegram, Email
            - flags: list de warnings (prix-suspect, prix-eleve, surface-petite, pas-gps)

    Notes:
        - Modifie les listings in-place
        - Flags: prix < 500€, prix > 5000€, surface < 20m², pas de GPS
    """
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
    """
    Calculer la heatmap de prix/m² par ville pour visualisation Leaflet.

    Args:
        listings (list[dict]): Liste d'annonces enrichies

    Returns:
        list[dict]: Liste de villes avec:
            - city: nom de la ville
            - lat, lng: coordonnées GPS
            - avg_price_m2: prix moyen au m²
            - count: nombre d'annonces

    Notes:
        - Filtre les villes sans GPS ou sans price_m2
        - Agrégation par ville
    """
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
    """
    Créer les données de timeline (nombre d'annonces par date).

    Args:
        listings (list[dict]): Liste d'annonces

    Returns:
        list[dict]: Liste de points (date, count) triés chronologiquement

    Notes:
        - Agrégation par jour (format YYYY-MM-DD)
        - Utile pour visualiser l'évolution du marché
    """
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
    """
    Exporter les données en fichiers JS, JSON et archives.

    Args:
        listings (list[dict]): Liste d'annonces (sera enrichie in-place)
        stats (dict): Statistiques calculées
        data_dir (str): Répertoire d'export (crée les sous-dossiers)

    Returns:
        dict: site_colors (couleurs par site pour les graphiques)

    Output files:
        - data_dir/listings.js: Variable JS const LISTINGS
        - data_dir/stats.js: Variables JS STATS, SITE_COLORS, PRICE_HEATMAP, TIMELINE
        - data_dir/listings.json: JSON pur réutilisable
        - data_dir/history/YYYY-MM-DD.json: Archive JSON du jour

    Notes:
        - Crée les dossiers automatiquement
        - Enrichit listings avec métadonnées (QR codes, partage, flags)
        - Calcule heatmap prix/m² et timeline
    """
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
