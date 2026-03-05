# =============================================================================
# dashboard_generator.py — Generateur de donnees pour dashboard
# =============================================================================
# Lit listings.db, exporte les donnees en fichiers JS/JSON.
# ⚠️  NE RÉGÉNÈRE PAS les fichiers HTML (conserve les modifications manuelles!)
#
# Usage : python dashboard_generator.py
# Output :
#   dashboards/data/listings.js           — donnees annonces (variable JS)
#   dashboards/data/stats.js              — statistiques (variable JS)
#   dashboards/data/listings.json         — JSON pur (reutilisable)
#   dashboards/data/history/YYYY-MM-DD.json — archive JSON du jour
#   dashboards/manifest.json              — manifest PWA
#
# ✅ Les fichiers HTML (index.html, photos.html, etc.) sont gérés manuellement
#    et NE sont PAS régénérés pour conserver les corrections du jour!
#
# Zero dependance externe (stdlib Python uniquement)
# =============================================================================

import sqlite3
import json
import os
import re
import shutil
import hashlib
import urllib.request
from datetime import datetime
from database import db

# =============================================================================
# VERSION DU DASHBOARD — incrémenter manuellement à chaque release notable
# =============================================================================
DASHBOARD_VERSION = "2.7"

# Villes prioritaires — chargées depuis .env (fallback hardcodé)
import dotenv as _dotenv_module
_dotenv_module.load_dotenv()
PRIORITY_CITIES = [c.strip() for c in os.getenv(
    'PRIORITY_CITIES', 'Luxembourg,Belair,Gare,Merl,Bonnevoie,Bertrange,Mamer,Strassen'
).split(',') if c.strip()]

# Image compression settings
IMAGE_MAX_WIDTH = 400  # Max width for thumbnails
IMAGE_QUALITY = 75     # JPEG quality (1-100)
IMAGES_DIR = 'dashboards/images'

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  Pillow non disponible - images non compressées")


def normalize_city_name(city):
    """
    Normaliser les noms de villes pour éliminer les doublons.

    Problèmes résolus:
    - "Luxembourg-Gare" vs "Luxembourg Gare" → "Luxembourg-Gare"
    - "Luxembourg Neudorf" → "Luxembourg-Neudorf"
    - "Luxembourg-Centre ville" vs "Luxembourg-Centre Ville" → "Luxembourg-Centre"

    Format standard: Tirets entre mots, Majuscule initiale chaque mot
    """
    if not city or city == 'N/A':
        return city

    # Convertir tous les espaces en tirets
    city = city.strip().replace(' ', '-')

    # Normaliser majuscules: première lettre de chaque segment en majuscule
    parts = city.split('-')
    city = '-'.join(part.capitalize() for part in parts if part)

    # Cas spéciaux - harmonisation
    replacements = {
        # Luxembourg Centre variations
        'Luxembourg-Centre-Ville': 'Centre',
        'Luxembourg-Centre-Vill': 'Centre',  # Typo potentiel
        'Luxembourg-Centre': 'Centre',

        # Gasperich variations
        'Luxembourg-Gasperich-Cloche-D\'or': 'Gasperich',
        'Luxembourg-Gasperich-Cloche-D\'Or': 'Gasperich',

        # Brouch
        'Brouch-(mersch)': 'Brouch',
        'Brouch-(Mersch)': 'Brouch',

        # Weiler
        'Weiler-La-Tour': 'Weiler-La-Tour',
    }

    city = replacements.get(city, city)

    # Supprimer le préfixe "Luxembourg-" pour les quartiers de la ville
    # "Luxembourg-Belair" → "Belair", "Luxembourg-Kirchberg" → "Kirchberg"
    # Mais conserver "Luxembourg" seul (la ville entière)
    if '-' in city and city.lower().startswith('luxembourg-'):
        city = city[len('Luxembourg-'):]

    return city


def read_listings(db_path='listings.db'):
    """Lire toutes les annonces depuis la base SQLite"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT listing_id, site, title, city, price, rooms, surface,
               url, latitude, longitude, distance_km, created_at, image_url
        FROM listings
        ORDER BY id DESC
    ''')

    listings = []
    for row in cursor.fetchall():
        listing = dict(row)

        # Normaliser le nom de ville
        if listing.get('city'):
            listing['city'] = normalize_city_name(listing['city'])

        # Calculer prix/m²
        if listing['price'] and listing['surface'] and listing['surface'] > 0:
            listing['price_m2'] = round(listing['price'] / listing['surface'], 1)
        else:
            listing['price_m2'] = None
        listings.append(listing)

    conn.close()
    return listings


def calc_stats(listings):
    """Calculer les statistiques globales"""
    if not listings:
        return {
            'total': 0, 'avg_price': 0, 'min_price': 0, 'max_price': 0,
            'avg_surface': 0, 'cities': 0, 'sites': {},
            'by_city': [], 'by_price_range': {}
        }

    prices = [l['price'] for l in listings if l['price'] and l['price'] > 0]
    surfaces = [l['surface'] for l in listings if l['surface'] and l['surface'] > 0]
    sites = {}
    cities = {}

    for l in listings:
        site = l['site'] or 'Inconnu'
        sites[site] = sites.get(site, 0) + 1

        # Normaliser le nom de ville (double sécurité si déjà fait dans read_listings)
        city = normalize_city_name(l['city']) if l.get('city') else 'N/A'

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

    return {
        'total': len(listings),
        'avg_price': int(sum(prices) / len(prices)) if prices else 0,
        'min_price': min(prices) if prices else 0,
        'max_price': max(prices) if prices else 0,
        'avg_surface': int(sum(surfaces) / len(surfaces)) if surfaces else 0,
        'cities': len(cities),
        'sites': sites,
        'by_city': by_city,
        'by_price_range': ranges
    }


def calculate_time_ago(date_str):
    """Calculer le temps écoulé depuis une date"""
    if not date_str:
        return "N/A"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        now = datetime.now()
        diff = now - dt.replace(tzinfo=None)
        if diff.days > 0:
            return f"{diff.days}j"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h"
        else:
            return f"{diff.seconds // 60}min"
    except:
        return "N/A"


def calculate_market_stats_detailed(listings, stats=None):
    """Calculer des stats marché détaillées"""
    if not listings:
        return {'price_distribution': {}, 'surface_distribution': {}, 'by_site': {}}

    stats = {
        'price_distribution': {'< 1500': 0, '1500-2000': 0, '2000-2500': 0, '> 2500': 0},
        'surface_distribution': {'< 50': 0, '50-80': 0, '80-100': 0, '> 100': 0},
        'by_site': {}
    }

    for l in listings:
        # Price distribution
        price = l.get('price', 0) or 0
        if price < 1500:
            stats['price_distribution']['< 1500'] += 1
        elif price < 2000:
            stats['price_distribution']['1500-2000'] += 1
        elif price < 2500:
            stats['price_distribution']['2000-2500'] += 1
        else:
            stats['price_distribution']['> 2500'] += 1

        # Surface distribution
        surface = l.get('surface', 0) or 0
        if surface < 50:
            stats['surface_distribution']['< 50'] += 1
        elif surface < 80:
            stats['surface_distribution']['50-80'] += 1
        elif surface < 100:
            stats['surface_distribution']['80-100'] += 1
        else:
            stats['surface_distribution']['> 100'] += 1

        # By site
        site = l.get('site', 'Inconnu')
        if site not in stats['by_site']:
            stats['by_site'][site] = 0
        stats['by_site'][site] += 1

    return stats


def download_and_compress_image(image_url, listing_id, images_dir=IMAGES_DIR):
    """
    Télécharger une image, la compresser et la sauvegarder localement.

    Args:
        image_url: URL de l'image source
        listing_id: ID de l'annonce (utilisé pour le nom de fichier)
        images_dir: Dossier de destination

    Returns:
        str: Chemin local relatif (ex: "images/athome_123.jpg") ou None si échec
    """
    if not image_url or not listing_id:
        return None

    # Filtrer les URLs non valides
    if 'badge' in image_url.lower() or 'logo' in image_url.lower() or 'placeholder' in image_url.lower():
        return None

    # Créer le dossier images si nécessaire
    os.makedirs(images_dir, exist_ok=True)

    # Nom du fichier basé sur listing_id
    safe_id = listing_id.replace('/', '_').replace('\\', '_')
    local_filename = f"{safe_id}.jpg"
    local_path = os.path.join(images_dir, local_filename)
    relative_path = f"images/{local_filename}"

    # Si l'image existe déjà, ne pas re-télécharger
    if os.path.exists(local_path):
        return relative_path

    try:
        # Télécharger l'image avec headers pour éviter blocage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': image_url.split('/')[0] + '//' + image_url.split('/')[2] + '/'
        }
        req = urllib.request.Request(image_url, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            image_data = response.read()

        if not image_data or len(image_data) < 1000:  # Image trop petite = probablement erreur
            return None

        # Compresser avec Pillow si disponible
        if PIL_AVAILABLE:
            from io import BytesIO
            img = Image.open(BytesIO(image_data))

            # Convertir en RGB si nécessaire (pour JPEG)
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')

            # Redimensionner si trop large
            if img.width > IMAGE_MAX_WIDTH:
                ratio = IMAGE_MAX_WIDTH / img.width
                new_height = int(img.height * ratio)
                img = img.resize((IMAGE_MAX_WIDTH, new_height), Image.LANCZOS)

            # Sauvegarder compressé
            img.save(local_path, 'JPEG', quality=IMAGE_QUALITY, optimize=True)
        else:
            # Sans Pillow, sauvegarder tel quel
            with open(local_path, 'wb') as f:
                f.write(image_data)

        return relative_path

    except Exception as e:
        # Silencieux - beaucoup d'images seront bloquées par hotlink protection
        return None


def cleanup_old_images(current_listing_ids, images_dir=IMAGES_DIR):
    """
    Supprimer les images des annonces qui n'existent plus.

    Args:
        current_listing_ids: Set des IDs d'annonces actuelles
        images_dir: Dossier des images

    Returns:
        int: Nombre d'images supprimées
    """
    if not os.path.exists(images_dir):
        return 0

    deleted_count = 0

    for filename in os.listdir(images_dir):
        if not filename.endswith('.jpg'):
            continue

        # Extraire l'ID de l'annonce du nom de fichier
        listing_id = filename.replace('.jpg', '')

        # Si l'annonce n'existe plus, supprimer l'image
        if listing_id not in current_listing_ids:
            try:
                os.remove(os.path.join(images_dir, filename))
                deleted_count += 1
            except Exception:
                pass

    return deleted_count


def process_images_for_listings(listings, images_dir=IMAGES_DIR):
    """
    Télécharger et compresser les images pour toutes les annonces.
    Met à jour les listings avec le chemin local.

    Args:
        listings: Liste des annonces
        images_dir: Dossier de destination

    Returns:
        tuple: (nombre téléchargées, nombre échecs)
    """
    downloaded = 0
    failed = 0

    print(f"\n📸 Traitement des images ({len(listings)} annonces)...")

    # Créer le set des IDs actuels pour le nettoyage
    current_ids = {l['listing_id'] for l in listings}

    # Nettoyer les anciennes images
    deleted = cleanup_old_images(current_ids, images_dir)
    if deleted > 0:
        print(f"   🗑️  {deleted} anciennes images supprimées")

    # Télécharger les nouvelles images
    for i, listing in enumerate(listings):
        if not listing.get('image_url'):
            continue

        local_path = download_and_compress_image(
            listing['image_url'],
            listing['listing_id'],
            images_dir
        )

        if local_path:
            listing['local_image'] = local_path
            downloaded += 1
        else:
            failed += 1

        # Afficher progression tous les 20
        if (i + 1) % 20 == 0:
            print(f"   ... {i + 1}/{len(listings)} traitées")

    print(f"   ✅ {downloaded} images téléchargées/compressées")
    if failed > 0:
        print(f"   ⚠️  {failed} images non accessibles (hotlink protection)")

    return downloaded, failed


def calc_anomalies(listings, stats):
    """Calculer les anomalies dans les annonces"""
    anomalies = []
    avg_price = stats['avg_price']
    prices = [l['price'] for l in listings if l['price'] and l['price'] > 0]

    if not prices:
        return anomalies

    # Prix moyen et écart-type pour détecter les outliers
    import statistics
    if len(prices) > 1:
        std_dev = statistics.stdev(prices)
    else:
        std_dev = 0

    for l in listings:
        reasons = []

        # Prix anormalement bas (< 50% du prix moyen)
        if l['price'] and l['price'] > 0 and avg_price > 0:
            if l['price'] < avg_price * 0.5:
                reasons.append(f"Prix bas: {l['price']}€ (moy: {avg_price}€)")

        # Prix anormalement haut (> 200% du prix moyen)
        if l['price'] and l['price'] > avg_price * 2:
            reasons.append(f"Prix élevé: {l['price']}€ (moy: {avg_price}€)")

        # Prix/m² anormal
        if l.get('price_m2'):
            if l['price_m2'] > 50:  # > 50€/m² est suspect pour une location
                reasons.append(f"Prix/m² élevé: {l['price_m2']}€/m²")
            elif l['price_m2'] < 5:  # < 5€/m² est très bas
                reasons.append(f"Prix/m² très bas: {l['price_m2']}€/m²")

        # Surface suspecte
        if l.get('surface'):
            if l['surface'] > 300:
                reasons.append(f"Surface très grande: {l['surface']}m²")
            elif l['surface'] < 15:
                reasons.append(f"Surface très petite: {l['surface']}m²")

        # Données manquantes importantes
        if not l.get('city') or l['city'] == 'N/A':
            reasons.append("Ville manquante")

        if reasons:
            anomalies.append({
                'listing_id': l['listing_id'],
                'title': l.get('title', ''),
                'city': l.get('city', 'N/A'),
                'price': l.get('price', 0),
                'surface': l.get('surface'),
                'site': l.get('site', ''),
                'url': l.get('url', ''),
                'reasons': reasons
            })

    return anomalies


def export_data(listings, stats, data_dir):
    """Exporter les donnees en fichiers JS + JSON + archive quotidienne"""
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'history'), exist_ok=True)
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    today = datetime.now().strftime('%Y-%m-%d')

    # listings.js
    listings_json = json.dumps(listings, ensure_ascii=False, indent=2, default=str)
    with open(os.path.join(data_dir, 'listings.js'), 'w', encoding='utf-8') as f:
        f.write(f'// Genere le {now_str}\n')
        f.write(f'// {len(listings)} annonces depuis listings.db\n')
        f.write(f'const LISTINGS = {listings_json};\n')

    # stats.js
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#2ECC71', '#E74C3C', '#3498DB']
    site_colors = {}
    for i, site in enumerate(stats['sites'].keys()):
        site_colors[site] = colors[i % len(colors)]

    stats_json = json.dumps(stats, ensure_ascii=False, indent=2)
    colors_json = json.dumps(site_colors, ensure_ascii=False, indent=2)
    with open(os.path.join(data_dir, 'stats.js'), 'w', encoding='utf-8') as f:
        f.write(f'// Genere le {now_str}\n')
        f.write(f'const STATS = {stats_json};\n')
        f.write(f'const SITE_COLORS = {colors_json};\n')

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
            'listings': listings
        }, f, ensure_ascii=False, indent=2, default=str)

    # anomalies.js - Détection automatique d'anomalies
    anomalies = calc_anomalies(listings, stats)
    anomalies_json = json.dumps(anomalies, ensure_ascii=False, indent=2, default=str)
    with open(os.path.join(data_dir, 'anomalies.js'), 'w', encoding='utf-8') as f:
        f.write(f'// Genere le {now_str}\n')
        f.write(f'// {len(anomalies)} anomalies detectees\n')
        f.write(f'const ANOMALIES = {anomalies_json};\n')

    # new-listings.json - Nouvelles annonces récentes (derniers 7 jours)
    from datetime import timedelta
    cutoff_date = datetime.now() - timedelta(days=7)
    new_listings = [
        l for l in listings
        if l.get('created_at') and datetime.strptime(l['created_at'][:10], '%Y-%m-%d') >= cutoff_date
    ]

    new_listings_data = {
        'generated_at': now_str,
        'total': len(new_listings),
        'anomalies_count': len([a for a in anomalies if a['listing_id'] in [l['listing_id'] for l in new_listings]]),
        'good_deals_count': len([l for l in new_listings if l.get('price', 0) > 0 and l.get('price', 0) < stats.get('avg_price', 0) * 0.7]),
        'high_price_count': len([l for l in new_listings if l.get('price', 0) > stats.get('avg_price', 0) * 1.5]),
        'market_stats': {},
        'listings': new_listings
    }

    with open(os.path.join(data_dir, 'new-listings.json'), 'w', encoding='utf-8') as f:
        json.dump(new_listings_data, f, ensure_ascii=False, indent=2, default=str)

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
    """Generer le HTML du dashboard PWA"""
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    colors = list(site_colors.values())

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

        /* Mobile */
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.1rem; }}
            .stat-value {{ font-size: 1.2rem; }}
            .stat-label {{ font-size: 0.6rem; }}
            .table {{ font-size: 0.7rem; }}
            .container-fluid {{ padding-left: 0.5rem; padding-right: 0.5rem; }}
            #map {{ height: 280px; }}
        }}
    </style>
</head>
<body>

<!-- Header -->
<div class="header">
    <div class="d-flex justify-content-between align-items-center">
        <div>
            <h1>ImmoLux Dashboard</h1>
            <small>Mis a jour le {now} — {stats['total']} annonces</small>
        </div>
        <div>
            <span class="listing-count">{stats['cities']} villes | {len(stats['sites'])} sites</span>
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

    <!-- Onglets -->
    <ul class="nav nav-tabs mb-2" role="tablist">
        <li class="nav-item">
            <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-table">Tableau</button>
        </li>
        <li class="nav-item">
            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-city">Par ville</button>
        </li>
        <li class="nav-item">
            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-price">Par prix</button>
        </li>
        <li class="nav-item">
            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-map">Carte</button>
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
                <div class="card-body p-0">
                    <div id="map"></div>
                </div>
            </div>
        </div>

    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-3">Aucune annonce</td></tr>';
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
document.querySelector('[data-bs-target="#tab-map"]').addEventListener('shown.bs.tab', () => {
    if (mapInit) return;
    mapInit = true;
    const withGPS = LISTINGS.filter(l => l.latitude && l.longitude);
    if (!withGPS.length) {
        document.getElementById('map').innerHTML = '<p class="text-center text-muted py-5">Aucune annonce avec coordonnees GPS</p>';
        return;
    }
    const map = L.map('map').setView([49.6116, 6.1319], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' }).addTo(map);
    withGPS.forEach(l => {
        const color = SITE_COLORS[l.site] || '#888';
        L.circleMarker([l.latitude, l.longitude], {
            radius: 7, fillColor: color, color: '#fff', weight: 2, fillOpacity: 0.85
        }).addTo(map).bindPopup(`
            <strong>${l.city || '\u2014'}</strong><br>
            ${fmt(l.price)}&euro; | ${l.rooms || '?'} ch. | ${l.surface || '?'} m&sup2;<br>
            <a href="${l.url}" target="_blank">Voir l'annonce</a>
        `);
    });
    map.fitBounds(withGPS.map(l => [l.latitude, l.longitude]), { padding: [30, 30] });
});

// --- Init ---
initFilters();
applyFilters();
renderCityView();
renderPriceView();
</script>
</body>
</html>'''

    return html


def sync_data_to_dashboard2(data_dir):
    """Sync data files to Dashboard2 (Vue app)"""
    dashboard2_data = 'dashboards2/public/data'

    try:
        # Create directory if it doesn't exist
        os.makedirs(dashboard2_data, exist_ok=True)

        # Files to sync
        files_to_sync = [
            'listings.js',
            'stats.js',
            'listings.json',
            'anomalies.js',
            'market-stats.js',
            'new-listings.json'
        ]

        # Copy files
        for filename in files_to_sync:
            src = os.path.join(data_dir, filename)
            dst = os.path.join(dashboard2_data, filename)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"  -> {dst}")

        print("✅ Dashboard2 data synced")
    except Exception as e:
        print(f"⚠️  Dashboard2 sync skipped: {e}")


def generate_version_js(data_dir, total_listings):
    """Générer data/version.js avec version, date de build et token de cache busting"""
    now = datetime.now()
    build_token = now.strftime("%Y%m%d-%H%M")
    built_at = now.strftime("%d/%m/%Y %H:%M")

    version_info = {
        "version": DASHBOARD_VERSION,
        "built_at": built_at,
        "build_token": build_token,
        "total_listings": total_listings
    }
    version_json = json.dumps(version_info, ensure_ascii=False, indent=2)
    priority_json = json.dumps(PRIORITY_CITIES, ensure_ascii=False)

    with open(os.path.join(data_dir, 'version.js'), 'w', encoding='utf-8') as f:
        f.write(f'// Genere le {built_at}\n')
        f.write(f'const VERSION_INFO = {version_json};\n')
        f.write(f'const PRIORITY_CITIES = {priority_json};\n')

    return build_token


def update_sw_cache_version(dashboards_dir, build_token):
    """Mettre à jour CACHE_NAME dans sw.js pour invalider le cache navigateur"""
    sw_path = os.path.join(dashboards_dir, 'sw.js')
    if not os.path.exists(sw_path):
        return

    with open(sw_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remplacer la ligne CACHE_NAME avec le nouveau build token
    new_content = re.sub(
        r"const CACHE_NAME = 'immo-lux-v[^']*';",
        f"const CACHE_NAME = 'immo-lux-v{build_token}';",
        content
    )
    # Mettre à jour aussi le commentaire de version en haut
    new_content = re.sub(
        r'// Version: [\d-]+',
        f'// Version: {build_token}',
        new_content
    )

    with open(sw_path, 'w', encoding='utf-8') as f:
        f.write(new_content)


def main():
    """Point d'entree principal"""
    print("Initialisation de la base de donnees...")
    # Initialize database (creates tables if they don't exist)
    db.init_db()

    print("Lecture de listings.db...")
    listings = read_listings()

    if not listings:
        print("Aucune annonce trouvee dans la base.")
        return

    stats = calc_stats(listings)
    today = datetime.now().strftime('%Y-%m-%d')
    dashboards_dir = 'dashboards'
    data_dir = os.path.join(dashboards_dir, 'data')
    images_dir = os.path.join(dashboards_dir, 'images')
    print(f"  {stats['total']} annonces, {stats['cities']} villes, {len(stats['sites'])} sites")

    # Creer les dossiers
    os.makedirs(os.path.join(dashboards_dir, 'archives'), exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)

    # Etape 0 : Télécharger et compresser les images
    if PIL_AVAILABLE:
        downloaded, failed = process_images_for_listings(listings, images_dir)
    else:
        print("\n⚠️  Pillow non disponible - images non téléchargées")

    # Etape 1 : exporter donnees JS + JSON + archive quotidienne
    site_colors = export_data(listings, stats, data_dir)
    print(f"  -> {data_dir}/listings.js")
    print(f"  -> {data_dir}/stats.js")
    print(f"  -> {data_dir}/listings.json")
    print(f"  -> {data_dir}/history/{today}.json")

    # Etape 1b : version.js + cache busting sw.js
    build_token = generate_version_js(data_dir, stats['total'])
    print(f"  -> {data_dir}/version.js (v{DASHBOARD_VERSION} token:{build_token})")
    update_sw_cache_version(dashboards_dir, build_token)
    print(f"  -> {dashboards_dir}/sw.js (cache version: {build_token})")

    # Etape 2 : manifest PWA
    generate_manifest(dashboards_dir)
    print(f"  -> {dashboards_dir}/manifest.json")

    # ⚠️  ETAPES 3 & 4 COMMENTÉES : Ne pas régénérer les fichiers HTML
    # Les fichiers HTML (index.html, photos.html, stats-by-city.html, etc.) sont gérés manuellement
    # et doivent conserver les modifications du jour (glasmorphism, dark mode, photos, transport info, etc.)
    #
    # Décommentez uniquement si vous voulez recréer les fichiers HTML depuis le modèle
    # (cela écrasera TOUTES les corrections manuelles!)
    #
    # # Etape 3 : HTML dashboard
    # html = generate_html(stats, site_colors)
    # index_path = os.path.join(dashboards_dir, 'index.html')
    # with open(index_path, 'w', encoding='utf-8') as f:
    #     f.write(html)
    # print(f"  -> {index_path}")

    # # Etape 4 : archive HTML du jour
    # archive_path = os.path.join(dashboards_dir, 'archives', f'{today}.html')
    # shutil.copy2(index_path, archive_path)
    # print(f"  -> {archive_path}")

    # ⚠️  Dashboard2 sync commentée : dossier supprimé (uniquement dashboards/ en use)
    # # Etape 5 : sync data to Dashboard2 (Vue app)
    # print("\nSync Dashboard2...")
    # sync_data_to_dashboard2(data_dir)

    # Compter les images locales
    local_images = sum(1 for l in listings if l.get('local_image'))

    print(f"\n✅ Données du dashboard générées avec succès!")
    print(f"📊 Les fichiers HTML manuels sont PRÉSERVÉS:")
    print(f"   - dashboards/index.html (avec glasmorphism + dark mode)")
    print(f"   - dashboards/photos.html (avec images + transport)")
    print(f"   - dashboards/stats-by-city.html (avec onglets + transport)")
    print(f"   - Et tous les autres fichiers HTML personnalisés")
    print(f"\n📈 Données exportées:")
    print(f"   ✅ listings.js (avec {stats['total']} annonces)")
    print(f"   ✅ stats.js")
    print(f"   ✅ version.js (v{DASHBOARD_VERSION} — token: {build_token})")
    print(f"   ✅ sw.js mis à jour (cache invalidé: {build_token})")
    print(f"   ✅ manifest.json")
    print(f"   📸 {local_images}/{stats['total']} images locales dans {images_dir}/")


# Aliases pour compatibilité avec tests
calculate_price_anomalies = calc_anomalies


if __name__ == '__main__':
    main()
