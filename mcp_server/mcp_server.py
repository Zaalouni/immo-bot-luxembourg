#!/usr/bin/env python3
# =============================================================================
# mcp_server.py — Serveur MCP principal pour Immo-Bot Luxembourg
# =============================================================================
#
# Expose 7 TOOLS et 4 RESOURCES via le Model Context Protocol (MCP).
#
# TOOLS (actions):
#   - search_listings      : Recherche d'annonces avec filtres multiples
#   - get_stats            : Statistiques globales du marché
#   - run_scraper          : Lancer un scraper spécifique à la demande
#   - analyze_market       : Analyse tendances marché sur N jours
#   - find_nearby          : Annonces dans un rayon géographique
#   - generate_dashboard   : Régénérer les dashboards statiques
#   - send_alert           : Envoyer alerte Telegram pour une annonce
#
# RESOURCES (données en lecture):
#   - listings://all       : Toutes les annonces actives
#   - listings://new       : Nouvelles annonces (dernières 24h)
#   - stats://current      : Statistiques temps réel
#   - history://YYYY-MM-DD : Archives journalières
#
# Usage:
#   python mcp_server/mcp_server.py          # Démarrage direct
#   python -m mcp_server.mcp_server          # Via module
#
# Config Claude Desktop (~/.config/claude/claude_desktop_config.json):
#   {
#     "mcpServers": {
#       "immo-bot-luxembourg": {
#         "command": "python",
#         "args": ["/home/user/immo-bot-luxembourg/mcp_server/mcp_server.py"]
#       }
#     }
#   }
# =============================================================================

import sys
import os
import asyncio
import logging

# Ajouter le dossier parent au PYTHONPATH pour importer database, config, etc.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Import des modules outils
from mcp_server.tools.search_tool import handle_search_listings
from mcp_server.tools.stats_tool import handle_get_stats
from mcp_server.tools.scraper_tool import handle_run_scraper, handle_list_scrapers
from mcp_server.tools.market_tool import handle_analyze_market, handle_detect_anomalies
from mcp_server.tools.geo_tool import handle_find_nearby, handle_geocode_city
from mcp_server.tools.dashboard_tool import handle_generate_dashboard
from mcp_server.tools.notify_tool import handle_send_alert, handle_test_connection

# Import des modules ressources
from mcp_server.resources.listings_resource import get_listings_all, get_listings_new, get_listings_by_site
from mcp_server.resources.stats_resource import get_stats_current, get_stats_by_city
from mcp_server.resources.history_resource import get_history_day

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("mcp_server.main")

# =============================================================================
# INITIALISATION DU SERVEUR MCP
# =============================================================================

server = Server("immo-bot-luxembourg")
server_version = "1.0.0"

# =============================================================================
# LISTE DES TOOLS DISPONIBLES
# =============================================================================

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Retourne la liste de tous les outils disponibles."""
    return [
        # --- Tool 1: search_listings ---
        types.Tool(
            name="search_listings",
            description=(
                "Rechercher des annonces immobilières au Luxembourg avec filtres avancés. "
                "Interroge la base de données SQLite en temps réel. "
                "Supporte filtrage par prix, ville, chambres, surface, distance GPS, et site source."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "price_min": {
                        "type": "integer",
                        "description": "Prix minimum en euros/mois (ex: 1000)",
                        "default": 0
                    },
                    "price_max": {
                        "type": "integer",
                        "description": "Prix maximum en euros/mois (ex: 2500)",
                        "default": 999999
                    },
                    "city": {
                        "type": "string",
                        "description": "Ville ou commune (ex: Luxembourg, Esch, Kirchberg)"
                    },
                    "rooms_min": {
                        "type": "integer",
                        "description": "Nombre minimum de chambres (ex: 2)"
                    },
                    "rooms_max": {
                        "type": "integer",
                        "description": "Nombre maximum de chambres (ex: 4)"
                    },
                    "surface_min": {
                        "type": "integer",
                        "description": "Surface minimum en m² (ex: 70)"
                    },
                    "site": {
                        "type": "string",
                        "description": "Site source (ex: athome, immotop, vivi, nextimmo)"
                    },
                    "max_distance_km": {
                        "type": "number",
                        "description": "Distance maximum depuis le point de référence (km)"
                    },
                    "only_new": {
                        "type": "boolean",
                        "description": "Seulement les annonces non-notifiées (nouvelles)",
                        "default": False
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["price_asc", "price_desc", "distance_asc", "date_desc", "surface_desc"],
                        "description": "Tri des résultats",
                        "default": "date_desc"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Nombre maximum de résultats (1-100)",
                        "default": 20
                    }
                }
            }
        ),

        # --- Tool 2: get_stats ---
        types.Tool(
            name="get_stats",
            description=(
                "Obtenir les statistiques complètes du marché immobilier. "
                "Inclut: totaux, prix moyens/min/max, prix/m², répartition par site, "
                "répartition par ville, et métriques de distance GPS."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "include_by_site": {
                        "type": "boolean",
                        "description": "Inclure la répartition par site source",
                        "default": True
                    },
                    "include_by_city": {
                        "type": "boolean",
                        "description": "Inclure la répartition par ville",
                        "default": True
                    },
                    "include_price_ranges": {
                        "type": "boolean",
                        "description": "Inclure la distribution par tranche de prix",
                        "default": True
                    }
                }
            }
        ),

        # --- Tool 3: run_scraper ---
        types.Tool(
            name="run_scraper",
            description=(
                "Lancer un scraper spécifique à la demande pour récupérer de nouvelles annonces. "
                "Scrapers disponibles: athome, immotop, luxhome, vivi, newimmo, nextimmo, "
                "unicorn, wortimmo, immoweb, sigelux, sothebys, remax, floor, et plus. "
                "Utiliser 'all' pour lancer tous les scrapers."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "scraper_name": {
                        "type": "string",
                        "description": "Nom du scraper à lancer (ex: athome, all)",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Mode test: scraper sans sauvegarder en DB",
                        "default": False
                    }
                },
                "required": ["scraper_name"]
            }
        ),

        # --- Tool 4: list_scrapers ---
        types.Tool(
            name="list_scrapers",
            description=(
                "Lister tous les scrapers disponibles avec leur statut "
                "(actif/inactif) et statistiques (dernière exécution, nombre d'annonces)."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),

        # --- Tool 5: analyze_market ---
        types.Tool(
            name="analyze_market",
            description=(
                "Analyser les tendances du marché immobilier sur une période donnée. "
                "Compare avec les archives historiques (dashboards/data/history/). "
                "Retourne: évolution des prix, villes en croissance, opportunités."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "period_days": {
                        "type": "integer",
                        "description": "Période d'analyse en jours (1-90)",
                        "default": 7
                    },
                    "focus_city": {
                        "type": "string",
                        "description": "Analyser spécifiquement une ville"
                    },
                    "include_opportunities": {
                        "type": "boolean",
                        "description": "Inclure les annonces sous la moyenne (opportunités)",
                        "default": True
                    }
                }
            }
        ),

        # --- Tool 6: detect_anomalies ---
        types.Tool(
            name="detect_anomalies",
            description=(
                "Détecter les anomalies dans la base de données: "
                "prix aberrants, doublons potentiels, données manquantes, "
                "annonces très chères ou très bon marché vs la moyenne."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "threshold_percent": {
                        "type": "number",
                        "description": "Seuil de déviation en % pour considérer comme anomalie",
                        "default": 30
                    }
                }
            }
        ),

        # --- Tool 7: find_nearby ---
        types.Tool(
            name="find_nearby",
            description=(
                "Trouver les annonces dans un rayon géographique autour d'un point GPS. "
                "Utilise la formule Haversine. Peut aussi chercher autour d'une ville nommée."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude du point central (ex: 49.6116)"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude du point central (ex: 6.1319)"
                    },
                    "city_name": {
                        "type": "string",
                        "description": "Nom de ville comme point central (alternative à lat/lng)"
                    },
                    "radius_km": {
                        "type": "number",
                        "description": "Rayon de recherche en km",
                        "default": 5.0
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Nombre maximum de résultats",
                        "default": 15
                    }
                }
            }
        ),

        # --- Tool 8: geocode_city ---
        types.Tool(
            name="geocode_city",
            description=(
                "Convertir un nom de ville luxembourgeoise en coordonnées GPS (lat, lng). "
                "Utilise le dictionnaire local de 120+ villes/localités du Luxembourg."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "Nom de la ville (ex: Esch-sur-Alzette, Kirchberg)"
                    }
                },
                "required": ["city_name"]
            }
        ),

        # --- Tool 9: generate_dashboard ---
        types.Tool(
            name="generate_dashboard",
            description=(
                "Régénérer les fichiers des dashboards statiques (listings.js, stats.js, etc.). "
                "Lance dashboard_generator.py qui exporte la DB vers dashboards/data/. "
                "Retourne le nombre de fichiers générés et les métriques."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "include_archive": {
                        "type": "boolean",
                        "description": "Créer une archive journalière dans history/",
                        "default": True
                    }
                }
            }
        ),

        # --- Tool 10: send_alert ---
        types.Tool(
            name="send_alert",
            description=(
                "Envoyer une notification Telegram pour une ou plusieurs annonces spécifiques. "
                "Utile pour alerter manuellement sur des opportunités détectées. "
                "Format: photo + description + lien + prix."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "listing_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Liste des listing_id à notifier (ex: ['athome_12345'])"
                    },
                    "message": {
                        "type": "string",
                        "description": "Message personnalisé à ajouter à la notification"
                    }
                },
                "required": ["listing_ids"]
            }
        ),

        # --- Tool 11: test_connection ---
        types.Tool(
            name="test_connection",
            description=(
                "Tester la connexion Telegram: vérifier que le bot est actif "
                "et que les chats sont accessibles. "
                "Utile pour diagnostiquer les problèmes de notification."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


# =============================================================================
# DISPATCHER DES TOOLS
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Dispatcher principal — route vers le handler approprié."""
    logger.info(f"Tool appelé: {name} avec args: {list(arguments.keys())}")

    try:
        if name == "search_listings":
            return await handle_search_listings(arguments)
        elif name == "get_stats":
            return await handle_get_stats(arguments)
        elif name == "run_scraper":
            return await handle_run_scraper(arguments)
        elif name == "list_scrapers":
            return await handle_list_scrapers(arguments)
        elif name == "analyze_market":
            return await handle_analyze_market(arguments)
        elif name == "detect_anomalies":
            return await handle_detect_anomalies(arguments)
        elif name == "find_nearby":
            return await handle_find_nearby(arguments)
        elif name == "geocode_city":
            return await handle_geocode_city(arguments)
        elif name == "generate_dashboard":
            return await handle_generate_dashboard(arguments)
        elif name == "send_alert":
            return await handle_send_alert(arguments)
        elif name == "test_connection":
            return await handle_test_connection(arguments)
        else:
            return [types.TextContent(
                type="text",
                text=f"Erreur: outil inconnu '{name}'. "
                     f"Outils disponibles: search_listings, get_stats, run_scraper, "
                     f"list_scrapers, analyze_market, detect_anomalies, find_nearby, "
                     f"geocode_city, generate_dashboard, send_alert, test_connection"
            )]
    except Exception as e:
        logger.error(f"Erreur dans tool {name}: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=f"Erreur lors de l'exécution de {name}: {str(e)}"
        )]


# =============================================================================
# LISTE DES RESOURCES DISPONIBLES
# =============================================================================

@server.list_resources()
async def list_resources() -> list[types.Resource]:
    """Retourne la liste de toutes les ressources disponibles."""
    return [
        types.Resource(
            uri="listings://all",
            name="Toutes les annonces",
            description="Toutes les annonces actives dans la base de données SQLite",
            mimeType="application/json"
        ),
        types.Resource(
            uri="listings://new",
            name="Nouvelles annonces (24h)",
            description="Annonces ajoutées dans les dernières 24 heures",
            mimeType="application/json"
        ),
        types.Resource(
            uri="listings://by-site",
            name="Annonces par site",
            description="Annonces regroupées par site source (athome, immotop, etc.)",
            mimeType="application/json"
        ),
        types.Resource(
            uri="stats://current",
            name="Statistiques actuelles",
            description="Snapshot des statistiques de marché en temps réel",
            mimeType="application/json"
        ),
        types.Resource(
            uri="stats://by-city",
            name="Statistiques par ville",
            description="Prix moyen, min, max et nombre d'annonces par ville",
            mimeType="application/json"
        ),
        types.Resource(
            uri="history://today",
            name="Archive aujourd'hui",
            description="Archive JSON de la journée en cours (depuis dashboards/data/history/)",
            mimeType="application/json"
        ),
    ]


# =============================================================================
# DISPATCHER DES RESOURCES
# =============================================================================

@server.read_resource()
async def read_resource(uri: str) -> str:
    """Dispatcher ressources — route vers le handler approprié."""
    logger.info(f"Resource demandée: {uri}")

    try:
        if uri == "listings://all":
            return await get_listings_all()
        elif uri == "listings://new":
            return await get_listings_new()
        elif uri == "listings://by-site":
            return await get_listings_by_site()
        elif uri == "stats://current":
            return await get_stats_current()
        elif uri == "stats://by-city":
            return await get_stats_by_city()
        elif uri.startswith("history://"):
            date_str = uri.replace("history://", "")
            return await get_history_day(date_str)
        else:
            return f'{{"error": "Resource inconnue: {uri}"}}'
    except Exception as e:
        logger.error(f"Erreur resource {uri}: {e}", exc_info=True)
        return f'{{"error": "{str(e)}"}}'


# =============================================================================
# POINT D'ENTREE PRINCIPAL
# =============================================================================

async def main():
    """Démarrage du serveur MCP via stdio."""
    logger.info("=" * 60)
    logger.info(f"Immo-Bot Luxembourg MCP Server v{server_version}")
    logger.info("=" * 60)
    logger.info(f"Répertoire de travail: {os.getcwd()}")
    logger.info(f"Python: {sys.version.split()[0]}")
    logger.info("Transport: stdio")
    logger.info("=" * 60)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
