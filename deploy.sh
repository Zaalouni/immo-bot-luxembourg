#!/bin/bash
# =============================================================================
# deploy.sh — Scrape + genere dashboard + push vers GitHub Pages
# =============================================================================
# Usage (depuis le serveur Linux) :
#   chmod +x deploy.sh
#   ./deploy.sh           # scrape + dashboard + git push
#   ./deploy.sh --no-scrape  # dashboard + git push seulement
#
# Cron (toutes les 2h) :
#   0 */2 * * * cd /chemin/vers/immo-bot-luxembourg && ./deploy.sh >> logs/deploy.log 2>&1
# =============================================================================

set -e
cd "$(dirname "$0")"

DATE=$(date '+%Y-%m-%d %H:%M')
echo "=== Deploy $DATE ==="

# Etape 1 : Scraping (sauf si --no-scrape)
if [ "$1" != "--no-scrape" ]; then
    echo "[1/3] Scraping..."
    python3 main.py || echo "WARN: scraping termine avec erreurs"
else
    echo "[1/3] Scraping ignore (--no-scrape)"
fi

# Etape 2 : Generer le dashboard
echo "[2/3] Generation dashboard..."
python3 dashboard_generator.py

# Etape 3 : Git push du dossier dashboards
echo "[3/3] Git push..."
git add dashboards/
git commit -m "dashboard: mise a jour $DATE" || echo "Rien a commiter"
git push origin main

echo "=== Deploy termine ==="
echo "Dashboard visible sur : https://zaalouni.github.io/immo-bot-luxembourg/dashboards/"
