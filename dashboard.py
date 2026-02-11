
# dashboard.py - Dashboard console pour monitoring
import sqlite3
import os
from datetime import datetime, timedelta
import json

def get_stats():
    """Obtenir les statistiques complètes"""
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()

    stats = {}

    # Statistiques globales
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT site) as sites_count,
            COUNT(DISTINCT city) as cities_count,
            AVG(price) as avg_price,
            MIN(price) as min_price,
            MAX(price) as max_price,
            SUM(CASE WHEN notified = 1 THEN 1 ELSE 0 END) as notified_count
        FROM listings
    """)

    row = cursor.fetchone()
    stats['total'] = row[0] or 0
    stats['sites_count'] = row[1] or 0
    stats['cities_count'] = row[2] or 0
    stats['avg_price'] = int(row[3]) if row[3] else 0
    stats['min_price'] = row[4] or 0
    stats['max_price'] = row[5] or 0
    stats['notified_count'] = row[6] or 0

    # Statistiques par site
    cursor.execute("""
        SELECT site, COUNT(*) as count, AVG(price) as avg_price
        FROM listings
        GROUP BY site
        ORDER BY count DESC
    """)

    stats['by_site'] = []
    for site, count, avg_price in cursor.fetchall():
        stats['by_site'].append({
            'site': site,
            'count': count,
            'avg_price': int(avg_price) if avg_price else 0
        })

    # Statistiques par ville
    cursor.execute("""
        SELECT city, COUNT(*) as count, AVG(price) as avg_price
        FROM listings
        WHERE city != 'N/A'
        GROUP BY city
        ORDER BY count DESC
        LIMIT 10
    """)

    stats['by_city'] = []
    for city, count, avg_price in cursor.fetchall():
        stats['by_city'].append({
            'city': city,
            'count': count,
            'avg_price': int(avg_price) if avg_price else 0
        })

    # Dernières 24 heures
    cursor.execute("""
        SELECT COUNT(*)
        FROM listings
        WHERE datetime(created_at) > datetime('now', '-1 day')
    """)
    stats['last_24h'] = cursor.fetchone()[0] or 0

    # Dernières annonces
    cursor.execute("""
        SELECT site, title, price, city, rooms, surface, url, created_at
        FROM listings
        ORDER BY id DESC
        LIMIT 10
    """)

    stats['recent_listings'] = []
    for row in cursor.fetchall():
        stats['recent_listings'].append({
            'site': row[0],
            'title': row[1],
            'price': row[2],
            'city': row[3],
            'rooms': row[4],
            'surface': row[5],
            'url': row[6],
            'created_at': row[7]
        })

    conn.close()
    return stats

def show_dashboard(export_json=False):
    """Afficher le dashboard dans la console"""
    if not os.path.exists('listings.db'):
        print("❌ Base de données non trouvée")
        print("   Lancez d'abord le bot pour générer des données")
        return

    stats = get_stats()

    if export_json:
        # Exporter en JSON
        with open('dashboard_stats.json', 'w') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"✅ Statistiques exportées dans dashboard_stats.json")
        return

    # Affichage console
    print("\n" + "="*80)
    print("📊 DASHBOARD BOT IMMOBILIER LUXEMBOURG")
    print("="*80)
    print(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    # Section 1: Vue d'ensemble
    print("\n📈 VUE D'ENSEMBLE")
    print("-"*40)
    print(f"🏠 Annonces totales: {stats['total']:,}".replace(',', ' '))
    print(f"📨 Notifiées: {stats['notified_count']:,}".replace(',', ' '))
    print(f"🌐 Sites différents: {stats['sites_count']}")
    print(f"📍 Villes couvertes: {stats['cities_count']}")
    print(f"📈 Dernières 24h: {stats['last_24h']}")
    print(f"💰 Prix moyen: {stats['avg_price']:,}€".replace(',', ' '))
    print(f"   Min: {stats['min_price']:,}€ | Max: {stats['max_price']:,}€".replace(',', ' '))

    # Section 2: Par site
    print("\n🏢 RÉPARTITION PAR SITE")
    print("-"*40)
    for site_data in stats['by_site']:
        percentage = (site_data['count'] / stats['total'] * 100) if stats['total'] > 0 else 0
        bar = '█' * int(percentage / 5)  # Barre de progression
        print(f"   {site_data['site']:20} {site_data['count']:4} annonces {bar}")
        print(f"       Prix moyen: {site_data['avg_price']:,}€".replace(',', ' '))

    # Section 3: Par ville
    print("\n📍 TOP VILLES")
    print("-"*40)
    for city_data in stats['by_city'][:5]:
        print(f"   {city_data['city']:20} {city_data['count']:4} annonces")
        print(f"       Prix moyen: {city_data['avg_price']:,}€".replace(',', ' '))

    # Section 4: Dernières annonces
    print("\n🆕 DERNIÈRES ANNONCES")
    print("-"*40)
    for i, listing in enumerate(stats['recent_listings'][:5], 1):
        print(f"   {i}. {listing['site']}")
        print(f"      {listing['title'][:50]}...")
        print(f"      💰 {listing['price']:,}€ | 🛏️ {listing['rooms']} | 📍 {listing['city']}".replace(',', ' '))
        print(f"      🕐 {listing['created_at'][:16]}")
        print()

    print("="*80)
    print("💡 Commandes: python dashboard.py [--json|--html|--csv]")
    print("="*80)

def export_html():
    """Exporter le dashboard en HTML"""
    stats = get_stats()

    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Bot Immobilier Luxembourg</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .chart {{ background: white; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
        .badge {{ background: #3498db; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Dashboard Bot Immobilier Luxembourg</h1>
            <p>🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{stats['total']:,}</div>
                <div>Annonces totales</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['sites_count']}</div>
                <div>Sites surveillés</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['cities_count']}</div>
                <div>Villes couvertes</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['avg_price']:,}€</div>
                <div>Prix moyen</div>
            </div>
        </div>

        <div class="chart">
            <h2>🏢 Répartition par site</h2>
            <table>
                <tr>
                    <th>Site</th>
                    <th>Annonces</th>
                    <th>Pourcentage</th>
                    <th>Prix moyen</th>
                </tr>
    """

    for site_data in stats['by_site']:
        percentage = (site_data['count'] / stats['total'] * 100) if stats['total'] > 0 else 0
        html += f"""
                <tr>
                    <td>{site_data['site']}</td>
                    <td>{site_data['count']}</td>
                    <td>{percentage:.1f}%</td>
                    <td>{site_data['avg_price']:,}€</td>
                </tr>
        """

    html += """
            </table>
        </div>

        <div class="chart">
            <h2>📍 Top villes</h2>
            <table>
                <tr>
                    <th>Ville</th>
                    <th>Annonces</th>
                    <th>Prix moyen</th>
                </tr>
    """

    for city_data in stats['by_city'][:10]:
        html += f"""
                <tr>
                    <td>{city_data['city']}</td>
                    <td>{city_data['count']}</td>
                    <td>{city_data['avg_price']:,}€</td>
                </tr>
        """

    html += """
            </table>
        </div>

        <div class="chart">
            <h2>🆕 Dernières annonces</h2>
            <table>
                <tr>
                    <th>Site</th>
                    <th>Titre</th>
                    <th>Prix</th>
                    <th>Ville</th>
                    <th>Date</th>
                </tr>
    """

    for listing in stats['recent_listings'][:10]:
        html += f"""
                <tr>
                    <td><span class="badge">{listing['site']}</span></td>
                    <td>{listing['title'][:50]}...</td>
                    <td>{listing['price']:,}€</td>
                    <td>{listing['city']}</td>
                    <td>{listing['created_at'][:16]}</td>
                </tr>
        """

    html += """
            </table>
        </div>

        <div style="text-align: center; margin: 40px 0; color: #7f8c8d; font-size: 0.9em;">
            <p>🤖 Généré automatiquement par le Bot Immobilier Luxembourg</p>
            <p>🔄 Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
    """

    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Dashboard HTML généré: dashboard.html")
    print(f"   Ouvrez dans votre navigateur: file://{os.path.abspath('dashboard.html')}")

def export_csv():
    """Exporter les données en CSV"""
    import csv

    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()

    # Récupérer toutes les annonces
    cursor.execute("""
        SELECT site, title, city, price, rooms, surface, url, created_at, notified
        FROM listings
        ORDER BY id DESC
    """)

    with open('listings_export.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Site', 'Titre', 'Ville', 'Prix (€)', 'Chambres', 'Surface (m²)', 'URL', 'Date ajout', 'Notifiée'])

        for row in cursor.fetchall():
            writer.writerow(row)

    conn.close()
    print(f"✅ Données exportées en CSV: listings_export.csv")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Dashboard Bot Immobilier')
    parser.add_argument('--json', action='store_true', help='Exporter en JSON')
    parser.add_argument('--html', action='store_true', help='Générer dashboard HTML')
    parser.add_argument('--csv', action='store_true', help='Exporter en CSV')

    args = parser.parse_args()

    if args.json:
        show_dashboard(export_json=True)
    elif args.html:
        export_html()
    elif args.csv:
        export_csv()
    else:
        show_dashboard()
