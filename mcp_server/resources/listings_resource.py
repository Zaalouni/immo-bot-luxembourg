#!/usr/bin/env python3
# =============================================================================
# resources/listings_resource.py — Resources MCP: listings://
# =============================================================================
# Expose les annonces immobilières sous forme de ressources MCP en lecture seule.
#
# Resources:
#   listings://all      → Toutes les annonces (JSON)
#   listings://new      → Nouvelles annonces < 24h (JSON)
#   listings://by-site  → Annonces regroupées par site (JSON)
# =============================================================================

import sqlite3
import json
import os
import logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH  = os.path.join(BASE_DIR, "listings.db")

logger = logging.getLogger("mcp_server.resources.listings")


def _row_to_dict(row: tuple, columns: list) -> dict:
    """Convertir une ligne SQLite en dictionnaire."""
    d = dict(zip(columns, row))
    # Ajouter prix/m²
    price   = d.get("price", 0) or 0
    surface = d.get("surface", 0) or 0
    d["price_per_m2"] = round(price / surface, 1) if price > 0 and surface > 0 else None
    return d


async def get_listings_all() -> str:
    """Retourner toutes les annonces actives en JSON."""
    if not os.path.exists(DB_PATH):
        return json.dumps({"error": f"DB introuvable: {DB_PATH}"})

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                listing_id, site, title, city, price, rooms, surface,
                url, latitude, longitude, distance_km,
                strftime('%Y-%m-%dT%H:%M:%S', created_at) as created_at,
                notified
            FROM listings
            ORDER BY created_at DESC
        """)
        rows    = cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        conn.close()

        listings = [_row_to_dict(r, columns) for r in rows]
        return json.dumps({
            "resource":   "listings://all",
            "count":      len(listings),
            "generated":  datetime.now().isoformat(),
            "listings":   listings
        }, ensure_ascii=False, indent=2)

    except sqlite3.Error as e:
        logger.error(f"Erreur listings_all: {e}")
        return json.dumps({"error": str(e)})


async def get_listings_new() -> str:
    """Retourner les annonces des dernières 24h en JSON."""
    if not os.path.exists(DB_PATH):
        return json.dumps({"error": f"DB introuvable: {DB_PATH}"})

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                listing_id, site, title, city, price, rooms, surface,
                url, latitude, longitude, distance_km,
                strftime('%Y-%m-%dT%H:%M:%S', created_at) as created_at,
                notified
            FROM listings
            WHERE created_at >= datetime('now', '-1 day')
            ORDER BY created_at DESC
        """)
        rows    = cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        conn.close()

        listings = [_row_to_dict(r, columns) for r in rows]
        return json.dumps({
            "resource":   "listings://new",
            "period":     "dernières 24h",
            "count":      len(listings),
            "generated":  datetime.now().isoformat(),
            "listings":   listings
        }, ensure_ascii=False, indent=2)

    except sqlite3.Error as e:
        logger.error(f"Erreur listings_new: {e}")
        return json.dumps({"error": str(e)})


async def get_listings_by_site() -> str:
    """Retourner les annonces regroupées par site en JSON."""
    if not os.path.exists(DB_PATH):
        return json.dumps({"error": f"DB introuvable: {DB_PATH}"})

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()

        # Récupérer tous les sites
        cursor.execute("SELECT DISTINCT site FROM listings ORDER BY site")
        sites = [row[0] for row in cursor.fetchall()]

        by_site = {}
        total   = 0

        for site in sites:
            cursor.execute("""
                SELECT
                    listing_id, title, city, price, rooms, surface, url,
                    strftime('%Y-%m-%dT%H:%M:%S', created_at) as created_at,
                    notified
                FROM listings
                WHERE site = ?
                ORDER BY created_at DESC
            """, (site,))
            rows    = cursor.fetchall()
            columns = [d[0] for d in cursor.description]
            listings = [dict(zip(columns, r)) for r in rows]

            prices = [l["price"] for l in listings if l.get("price", 0) > 0]
            by_site[site] = {
                "count":      len(listings),
                "avg_price":  round(sum(prices) / len(prices), 0) if prices else 0,
                "min_price":  min(prices) if prices else 0,
                "max_price":  max(prices) if prices else 0,
                "listings":   listings
            }
            total += len(listings)

        conn.close()

        return json.dumps({
            "resource":   "listings://by-site",
            "total":      total,
            "sites":      len(sites),
            "generated":  datetime.now().isoformat(),
            "by_site":    by_site
        }, ensure_ascii=False, indent=2)

    except sqlite3.Error as e:
        logger.error(f"Erreur listings_by_site: {e}")
        return json.dumps({"error": str(e)})
