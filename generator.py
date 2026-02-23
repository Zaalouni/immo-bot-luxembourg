# =============================================================================
# generator.py — Orchestrateur principal du Dashboard PWA (v3.0)
# =============================================================================
# Point d'entrée centralisé pour la génération complète du dashboard
# Coordonne: données → stats → exports → HTML/PWA
#
# Utilise les modules modulaires:
# - data_processor: logique métier (read, stats, exports)
# - template_generator: génération templates (HTML, manifest)
#
# =============================================================================

import os
import shutil
from datetime import datetime

# Importer les modules de logique
from data_processor import (
    read_listings,
    calc_stats,
    export_data
)

# Importer les modules de template
from template_generator import (
    generate_manifest,
    generate_html
)


def main():
    """
    Point d'entrée principal - orchestre la génération complète du dashboard.

    Workflow:
        1. Lire les annonces depuis SQLite
        2. Calculer les statistiques
        3. Exporter les données (JS, JSON, archives)
        4. Générer manifest PWA
        5. Générer HTML complet
        6. Créer archives HTML quotidiennes

    Output:
        dashboards/
        ├── index.html                    [PWA principale]
        ├── manifest.json                 [PWA metadata]
        ├── data/
        │   ├── listings.js              [Annonces JS]
        │   ├── stats.js                 [Stats JS]
        │   ├── listings.json            [Annonces JSON]
        │   └── history/YYYY-MM-DD.json  [Archive JSON]
        └── archives/YYYY-MM-DD.html    [Archive HTML]

    Returns:
        None (génère les fichiers)
    """
    print("🚀 Génération Dashboard PWA v3.0")
    print("=" * 60)

    # Étape 0 : Lecture des données
    print("📖 Lecture de listings.db...")
    listings = read_listings()

    if not listings:
        print("❌ Aucune annonce trouvee dans la base.")
        print("   Lancez d'abord le bot pour générer des données")
        return

    # Étape 1 : Calcul des stats
    print("📊 Calcul des statistiques...")
    stats = calc_stats(listings)
    today = datetime.now().strftime('%Y-%m-%d')
    dashboards_dir = 'dashboards'
    data_dir = os.path.join(dashboards_dir, 'data')
    print(f"   {stats['total']} annonces")
    print(f"   {stats['cities']} villes")
    print(f"   {len(stats['sites'])} sites")
    print(f"   Qualité données: {stats.get('data_quality', {}).get('completeness', 0)}%")
    if stats.get('anomalies', {}).get('count', 0) > 0:
        print(f"   ⚠️  {stats['anomalies']['count']} anomalies détectées")

    # Créer les dossiers
    os.makedirs(os.path.join(dashboards_dir, 'archives'), exist_ok=True)

    # Étape 1 : Exporter données JS + JSON + archive quotidienne
    print("\n📁 Export des données...")
    site_colors = export_data(listings, stats, data_dir)
    print(f"   ✅ {data_dir}/listings.js")
    print(f"   ✅ {data_dir}/stats.js")
    print(f"   ✅ {data_dir}/listings.json")
    print(f"   ✅ {data_dir}/history/{today}.json")

    # Étape 2 : Générer manifest PWA
    print("\n📦 Génération manifest PWA...")
    generate_manifest(dashboards_dir)
    print(f"   ✅ {dashboards_dir}/manifest.json")

    # Étape 3 : Générer HTML dashboard
    print("\n🎨 Génération HTML dashboard...")
    html = generate_html(stats, site_colors)
    index_path = os.path.join(dashboards_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"   ✅ {index_path}")

    # Étape 4 : Créer archive HTML du jour
    print("\n📦 Archivage...")
    archive_path = os.path.join(dashboards_dir, 'archives', f'{today}.html')
    shutil.copy2(index_path, archive_path)
    print(f"   ✅ {archive_path}")

    print("\n" + "=" * 60)
    print("✅ Dashboard généré avec succès !")
    print(f"📍 Ouvrir : file://{os.path.abspath(index_path)}")
    print("=" * 60)


if __name__ == '__main__':
    main()
