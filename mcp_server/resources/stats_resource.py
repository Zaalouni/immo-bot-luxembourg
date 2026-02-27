#!/usr/bin/env python3
# =============================================================================
# resources/stats_resource.py — Resources MCP: stats://
# =============================================================================
# Statistiques du marché immobilier en lecture seule.
#
# Resources:
#   stats://current   → Snapshot statistiques temps réel (JSON)
#   stats://by-city   → Stats par ville: prix moy/min/max, nb annonces (JSON)
# =============================================================================

import sqlite3
import json
import os
import logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH  = os.path.join(BASE_DIR, "listings.db")

logger = logging.getLogger("mcp_server.resources.stats")


async def get_stats_current() -> str:
    """Retourner les statistiques actuelles du marché en JSON."""
    if not os.path.exists(DB_PATH):
        return json.dumps({"error": f"DB introuvable: {DB_PATH}"})

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*), COUNT(CASE WHEN notified=0 THEN 1 END) FROM listings")
        row = cursor.fetchone()
        total, new_count = row[0] or 0, row[1] or 0

        cursor.execute("""
            SELECT AVG(price), MIN(price), MAX(price),
                   AVG(surface), COUNT(DISTINCT city)
            FROM listings WHERE price > 0
        """)
        pr = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) FROM listings
            WHERE created_at >= datetime('now', '-1 day')
        """)
        last_24h = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*) FROM listings
            WHERE created_at >= datetime('now', '-7 days')
        """)
        last_7d = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT AVG(CAST(price AS REAL)/surface)
            FROM listings WHERE price > 0 AND surface > 0
        """)
        ppm2 = cursor.fetchone()[0]

        cursor.execute("SELECT site, COUNT(*) FROM listings GROUP BY site ORDER BY COUNT(*) DESC")
        by_site = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("""
            SELECT price FROM listings WHERE price > 0 ORDER BY price
        """)
        prices = [r[0] for r in cursor.fetchall()]
        median = 0
        if prices:
            n = len(prices)
            median = prices[n//2] if n % 2 else (prices[n//2-1] + prices[n//2]) / 2

        conn.close()

        stats = {
            "resource":     "stats://current",
            "generated":    datetime.now().isoformat(),
            "total":        total,
            "new":          new_count,
            "notified":     total - new_count,
            "last_24h":     last_24h,
            "last_7d":      last_7d,
            "city_count":   int(pr[4]) if pr[4] else 0,
            "price": {
                "avg":        round(pr[0], 0) if pr[0] else 0,
                "median":     round(median, 0),
                "min":        int(pr[1]) if pr[1] else 0,
                "max":        int(pr[2]) if pr[2] else 0,
                "avg_per_m2": round(ppm2, 1) if ppm2 else None
            },
            "avg_surface":  round(pr[3], 0) if pr[3] else None,
            "by_site":      by_site
        }
        return json.dumps(stats, ensure_ascii=False, indent=2)

    except sqlite3.Error as e:
        logger.error(f"Erreur stats_current: {e}")
        return json.dumps({"error": str(e)})


async def get_stats_by_city() -> str:
    """Retourner les statistiques par ville en JSON."""
    if not os.path.exists(DB_PATH):
        return json.dumps({"error": f"DB introuvable: {DB_PATH}"})

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                city,
                COUNT(*) as count,
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                AVG(surface) as avg_surface,
                AVG(distance_km) as avg_distance
            FROM listings
            WHERE city IS NOT NULL AND city != '' AND price > 0
            GROUP BY city
            ORDER BY COUNT(*) DESC
        """)
        rows    = cursor.fetchall()
        columns = ["city","count","avg_price","min_price","max_price","avg_surface","avg_distance"]
        conn.close()

        cities = []
        for row in rows:
            d = dict(zip(columns, row))
            d["avg_price"]    = round(d["avg_price"] or 0, 0)
            d["min_price"]    = int(d["min_price"] or 0)
            d["max_price"]    = int(d["max_price"] or 0)
            d["avg_surface"]  = round(d["avg_surface"] or 0, 0) if d["avg_surface"] else None
            d["avg_distance"] = round(d["avg_distance"] or 0, 1) if d["avg_distance"] else None
            cities.append(d)

        return json.dumps({
            "resource":   "stats://by-city",
            "count":      len(cities),
            "generated":  datetime.now().isoformat(),
            "cities":     cities
        }, ensure_ascii=False, indent=2)

    except sqlite3.Error as e:
        logger.error(f"Erreur stats_by_city: {e}")
        return json.dumps({"error": str(e)})
