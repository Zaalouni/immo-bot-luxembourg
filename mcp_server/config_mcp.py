#!/usr/bin/env python3
# =============================================================================
# config_mcp.py — Configuration du serveur MCP Immo-Bot Luxembourg
# =============================================================================
# Variables de configuration propres au serveur MCP.
# Ne remplace PAS config.py du bot principal.
# =============================================================================

import os
from pathlib import Path

# Répertoire racine du projet
BASE_DIR = Path(__file__).parent.parent.resolve()

# Chemins principaux
DB_PATH          = BASE_DIR / "listings.db"
DASHBOARD_DIR    = BASE_DIR / "dashboards"
DATA_DIR         = DASHBOARD_DIR / "data"
HISTORY_DIR      = DATA_DIR / "history"
GENERATOR_SCRIPT = BASE_DIR / "dashboard_generator.py"

# Configuration MCP Server
MCP_SERVER_NAME    = "immo-bot-luxembourg"
MCP_SERVER_VERSION = "1.0.0"
MCP_TRANSPORT      = "stdio"   # "stdio" ou "http"
MCP_HTTP_HOST      = "127.0.0.1"
MCP_HTTP_PORT      = 8765

# Limites de sécurité
MAX_SEARCH_RESULTS = 100     # Max résultats par recherche
MAX_SCRAPER_TIMEOUT = 120    # Timeout max scraper (secondes)
MAX_HISTORY_DAYS   = 90      # Max jours d'historique analysables

# Logging
LOG_LEVEL = os.getenv("MCP_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Couleurs des sites pour les dashboards (héritées du projet)
SITE_COLORS = {
    "athome":        "#667eea",
    "immotop":       "#f093fb",
    "luxhome":       "#4facfe",
    "vivi":          "#43e97b",
    "newimmo":       "#fa709a",
    "nextimmo":      "#fccb90",
    "unicorn":       "#a18cd1",
    "wortimmo":      "#fda085",
    "immoweb":       "#f5576c",
    "sigelux":       "#4481eb",
    "sothebys":      "#0f2027",
    "remax":         "#e52d27",
    "floor":         "#614385",
    "apropos":       "#02aab0",
    "ldhome":        "#e44d26",
    "immostar":      "#11998e",
    "nexvia":        "#f7971e",
    "propertyinvest":"#2980b9",
    "rockenbrod":    "#8e44ad",
    "homepass":      "#16a085",
    "actuel":        "#d35400",
}

# Tranches de prix pour les statistiques
PRICE_RANGES = [
    ("< 1500€",   0,    1499),
    ("1500-2000€", 1500, 1999),
    ("2000-2500€", 2000, 2499),
    ("> 2500€",   2500, 999999),
]


def get_config_summary() -> dict:
    """Retourner un résumé de la configuration MCP."""
    return {
        "server_name":    MCP_SERVER_NAME,
        "version":        MCP_SERVER_VERSION,
        "transport":      MCP_TRANSPORT,
        "db_path":        str(DB_PATH),
        "db_exists":      DB_PATH.exists(),
        "history_dir":    str(HISTORY_DIR),
        "history_exists": HISTORY_DIR.exists(),
        "generator_exists": GENERATOR_SCRIPT.exists(),
        "max_search_results": MAX_SEARCH_RESULTS,
        "max_scraper_timeout": MAX_SCRAPER_TIMEOUT,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_config_summary(), indent=2))
