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

source venv/bin/activate


python3 main.py --once


RANDOM=$RANDOM

PYTHONIOENCODING=utf-8 python3 dashboard_generator.py

RANDOM=$RANDOM

# Etape 2 : Generer le dashboard
echo "[2/3] Generation dashboard..."
#python3 dashboard_generator.py
# Etape 3 : Git push du dossier dashboards
echo "[3/3] Git push..."
git add dashboards/
git commit -m "dashboard: mise a jour $RANDOM" || echo "Rien a commiter"
git push --force origin main









RANDOM=$RANDOM

# Etape 2 : Generer le dashboard
echo "[2/3] Generation dashboard..."
#python3 dashboard_generator.py
# Etape 3 : Git push du dossier dashboards
echo "[3/3] Git push..."
git add dashboards2/
git commit -m "dashboard2: mise a jour $RANDOM" || echo "Rien a commiter"
git push --force origin main






echo "=== Deploy termine ==="
echo "Dashboard visible sur : https://zaalouni.github.io/immo-bot-luxembourg/dashboards/"
