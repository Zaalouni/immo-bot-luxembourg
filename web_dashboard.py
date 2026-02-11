
# web_dashboard.py - Dashboard web avec Flask
from flask import Flask, render_template, jsonify, request
import sqlite3
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)

def get_db_stats():
    """Obtenir les statistiques depuis la base de données"""
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()

    stats = {}

    # Statistiques globales
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT site) as sites,
            COUNT(DISTINCT city) as cities,
            AVG(price) as avg_price,
            MIN(price) as min_price,
            MAX(price) as max_price
        FROM listings
    """)
    row = cursor.fetchone()

    stats['total'] = row[0] or 0
    stats['sites'] = row[1] or 0
    stats['cities'] = row[2] or 0
    stats['avg_price'] = int(row[3]) if row[3] else 0
    stats['min_price'] = row[4] or 0
    stats['max_price'] = row[5] or 0

    # Dernières 24h
    cursor.execute("""
        SELECT COUNT(*)
        FROM listings
        WHERE datetime(created_at) > datetime('now', '-1 day')
    """)
    stats['last_24h'] = cursor.fetchone()[0] or 0

    # Par site
    cursor.execute("""
        SELECT site, COUNT(*) as count
        FROM listings
        GROUP BY site
        ORDER BY count DESC
    """)
    stats['by_site'] = [{'site': site, 'count': count} for site, count in cursor.fetchall()]

    # Par ville
    cursor.execute("""
        SELECT city, COUNT(*) as count, AVG(price) as avg_price
        FROM listings
        WHERE city != 'N/A'
        GROUP BY city
        ORDER BY count DESC
        LIMIT 10
    """)
    stats['by_city'] = [{'city': city, 'count': count, 'avg_price': int(avg_price) if avg_price else 0}
                       for city, count, avg_price in cursor.fetchall()]

    # Dernières annonces
    cursor.execute("""
        SELECT id, site, title, city, price, rooms, surface, url, created_at
        FROM listings
        ORDER BY id DESC
        LIMIT 20
    """)

    stats['recent_listings'] = []
    for row in cursor.fetchall():
        stats['recent_listings'].append({
            'id': row[0],
            'site': row[1],
            'title': row[2],
            'city': row[3],
            'price': row[4],
            'rooms': row[5],
            'surface': row[6],
            'url': row[7],
            'created_at': row[8],
            'price_formatted': f"{row[4]:,}€".replace(',', ' ')
        })

    conn.close()
    return stats

@app.route('/')
def index():
    """Page principale du dashboard"""
    stats = get_db_stats()
    return render_template('dashboard.html',
                         stats=stats,
                         now=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))

@app.route('/api/stats')
def api_stats():
    """API pour les statistiques (JSON)"""
    stats = get_db_stats()
    return jsonify(stats)

@app.route('/api/listings')
def api_listings():
    """API pour les annonces"""
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()

    # Paramètres de pagination/filtre
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page

    site_filter = request.args.get('site', '')
    city_filter = request.args.get('city', '')

    # Construire la requête
    query = "SELECT * FROM listings WHERE 1=1"
    params = []

    if site_filter:
        query += " AND site = ?"
        params.append(site_filter)

    if city_filter:
        query += " AND city = ?"
        params.append(city_filter)

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    cursor.execute(query, params)

    listings = []
    columns = [description[0] for description in cursor.description]

    for row in cursor.fetchall():
        listing = dict(zip(columns, row))
        listing['price_formatted'] = f"{listing['price']:,}€".replace(',', ' ')
        listings.append(listing)

    # Total count
    count_query = "SELECT COUNT(*) FROM listings WHERE 1=1"
    count_params = []

    if site_filter:
        count_query += " AND site = ?"
        count_params.append(site_filter)

    if city_filter:
        count_query += " AND city = ?"
        count_params.append(city_filter)

    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        'listings': listings,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@app.route('/api/sites')
def api_sites():
    """API pour la liste des sites"""
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT site FROM listings ORDER BY site")
    sites = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(sites)

@app.route('/api/cities')
def api_cities():
    """API pour la liste des villes"""
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT city FROM listings WHERE city != 'N/A' ORDER BY city")
    cities = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(cities)

if __name__ == '__main__':
    # Créer le dossier templates si nécessaire
    os.makedirs('templates', exist_ok=True)

    # Créer le template HTML
    with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
        f.write("""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Bot Immobilier</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8f9fa; color: #333; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; text-align: center; }
        .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .stat-card { background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .stat-value { font-size: 2.5rem; font-weight: bold; color: #667eea; }
        .stat-label { font-size: 0.9rem; color: #6c757d; text-transform: uppercase; letter-spacing: 1px; }
        .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .chart-container { background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .listings-table { background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #f8f9fa; padding: 1rem; text-align: left; font-weight: 600; border-bottom: 2px solid #dee2e6; }
        td { padding: 1rem; border-bottom: 1px solid #dee2e6; }
        tr:hover { background: #f8f9fa; }
        .site-badge { background: #667eea; color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; }
        .loading { text-align: center; padding: 2rem; font-size: 1.2rem; color: #6c757d; }
        .filters { background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }
        .filter-group { display: inline-block; margin-right: 1rem; }
        select { padding: 0.5rem; border: 1px solid #dee2e6; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏠 Dashboard Bot Immobilier Luxembourg</h1>
        <p>Surveillance du marché immobilier en temps réel</p>
        <p id="last-update">🕐 Dernière mise à jour: {{ now }}</p>
    </div>

    <div class="container">
        <!-- Filtres -->
        <div class="filters">
            <div class="filter-group">
                <label>Site: </label>
                <select id="site-filter">
                    <option value="">Tous les sites</option>
                </select>
            </div>
            <div class="filter-group">
                <label>Ville: </label>
                <select id="city-filter">
                    <option value="">Toutes les villes</option>
                </select>
            </div>
            <button onclick="loadListings()">🔍 Filtrer</button>
        </div>

        <!-- Statistiques -->
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ stats.total|intcomma }}</div>
                <div class="stat-label">Annonces totales</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.sites }}</div>
                <div class="stat-label">Sites surveillés</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.cities }}</div>
                <div class="stat-label">Villes couvertes</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.avg_price|intcomma }}€</div>
                <div class="stat-label">Prix moyen</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.last_24h }}</div>
                <div class="stat-label">Dernières 24h</div>
            </div>
        </div>

        <!-- Graphiques -->
        <div class="charts-grid">
            <div class="chart-container">
                <h3>📊 Répartition par site</h3>
                <canvas id="sitesChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>📍 Top villes</h3>
                <canvas id="citiesChart"></canvas>
            </div>
        </div>

        <!-- Tableau des annonces -->
        <div class="listings-table">
            <h3 style="padding: 1.5rem; margin: 0;">🆕 Dernières annonces</h3>
            <div id="listings-container">
                <table>
                    <thead>
                        <tr>
                            <th>Site</th>
                            <th>Titre</th>
                            <th>Ville</th>
                            <th>Prix</th>
                            <th>Chambres</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody id="listings-body">
                        {% for listing in stats.recent_listings %}
                        <tr>
                            <td><span class="site-badge">{{ listing.site }}</span></td>
                            <td><a href="{{ listing.url }}" target="_blank">{{ listing.title }}</a></td>
                            <td>{{ listing.city }}</td>
                            <td>{{ listing.price_formatted }}</td>
                            <td>{{ listing.rooms }}</td>
                            <td>{{ listing.created_at[:16] }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            <div id="pagination" style="padding: 1rem; text-align: center;"></div>
        </div>
    </div>

    <script>
        // Formatter les nombres avec séparateurs
        function intcomma(x) {
            return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
        }

        // Initialiser les graphiques
        function initCharts() {
            // Graphique sites
            const sitesCtx = document.getElementById('sitesChart').getContext('2d');
            new Chart(sitesCtx, {
                type: 'doughnut',
                data: {
                    labels: {{ stats.by_site|map(attribute='site')|list|tojson }},
                    datasets: [{
                        data: {{ stats.by_site|map(attribute='count')|list|tojson }},
                        backgroundColor: [
                            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });

            // Graphique villes
            const citiesCtx = document.getElementById('citiesChart').getContext('2d');
            new Chart(citiesCtx, {
                type: 'bar',
                data: {
                    labels: {{ stats.by_city|map(attribute='city')|list|tojson }},
                    datasets: [{
                        label: 'Nombre d\'annonces',
                        data: {{ stats.by_city|map(attribute='count')|list|tojson }},
                        backgroundColor: '#667eea'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }

        // Charger les filtres
        async function loadFilters() {
            const [sites, cities] = await Promise.all([
                fetch('/api/sites').then(r => r.json()),
                fetch('/api/cities').then(r => r.json())
            ]);

            const siteSelect = document.getElementById('site-filter');
            const citySelect = document.getElementById('city-filter');

            sites.forEach(site => {
                const option = document.createElement('option');
                option.value = site;
                option.textContent = site;
                siteSelect.appendChild(option);
            });

            cities.forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                option.textContent = city;
                citySelect.appendChild(option);
            });
        }

        // Charger les annonces avec pagination
        async function loadListings(page = 1) {
            const site = document.getElementById('site-filter').value;
            const city = document.getElementById('city-filter').value;

            const url = `/api/listings?page=${page}&site=${site}&city=${city}`;
            const response = await fetch(url);
            const data = await response.json();

            // Mettre à jour le tableau
            const tbody = document.getElementById('listings-body');
            tbody.innerHTML = '';

            data.listings.forEach(listing => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><span class="site-badge">${listing.site}</span></td>
                    <td><a href="${listing.url}" target="_blank">${listing.title}</a></td>
                    <td>${listing.city}</td>
                    <td>${listing.price_formatted}</td>
                    <td>${listing.rooms}</td>
                    <td>${listing.created_at.slice(0, 16)}</td>
                `;
                tbody.appendChild(row);
            });

            // Mettre à jour la pagination
            const pagination = document.getElementById('pagination');
            pagination.innerHTML = '';

            for (let i = 1; i <= data.total_pages; i++) {
                const button = document.createElement('button');
                button.textContent = i;
                button.style.margin = '0 5px';
                button.style.padding = '5px 10px';
                button.style.border = i === page ? '2px solid #667eea' : '1px solid #ddd';
                button.onclick = () => loadListings(i);
                pagination.appendChild(button);
            }
        }

        // Actualiser automatiquement
        function startAutoRefresh() {
            setInterval(() => {
                fetch('/api/stats')
                    .then(r => r.json())
                    .then(stats => {
                        document.getElementById('last-update').textContent =
                            `🕐 Dernière mise à jour: ${new Date().toLocaleString('fr-FR')}`;

                        // Mettre à jour les stats
                        document.querySelectorAll('.stat-value')[0].textContent = intcomma(stats.total);
                        document.querySelectorAll('.stat-value')[3].textContent = intcomma(stats.avg_price) + '€';
                        document.querySelectorAll('.stat-value')[4].textContent = stats.last_24h;
                    });
            }, 30000); // Toutes les 30 secondes
        }

        // Initialisation
        document.addEventListener('DOMContentLoaded', () => {
            initCharts();
            loadFilters();
            loadListings();
            startAutoRefresh();
        });
    </script>
</body>
</html>
        """)

    # Démarrer le serveur
    print("🌐 Dashboard web démarré sur http://localhost:5000")
    print("📊 Ouvrez votre navigateur et allez sur: http://localhost:5000")
    print("🛑 Pour arrêter: Ctrl+C")

    app.run(host='0.0.0.0', port=5000, debug=False)
