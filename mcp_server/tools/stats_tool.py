#!/usr/bin/env python3
# =============================================================================
# tools/stats_tool.py — Tool MCP: get_stats
# =============================================================================
# Statistiques complètes du marché immobilier en temps réel.
# Lit directement la DB SQLite.
#
# Métriques retournées:
#   - Total annonces, nouvelles, notifiées
#   - Prix moyen/min/max/médian
#   - Prix moyen/m²
#   - Répartition par site (nombre + %)
#   - Répartition par ville (top 10)
#   - Tranches de prix
#   - Distance GPS moyenne/min
# =============================================================================

import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta

import mcp.types as types

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "listings.db")

logger = logging.getLogger("mcp_server.tools.stats")


async def handle_get_stats(args: dict) -> list[types.TextContent]:
    """Handler pour get_stats — statistiques complètes du marché."""

    include_by_site    = bool(args.get("include_by_site", True))
    include_by_city    = bool(args.get("include_by_city", True))
    include_price_ranges = bool(args.get("include_price_ranges", True))

    if not os.path.exists(DB_PATH):
        return [types.TextContent(type="text", text=f"Erreur: DB introuvable à {DB_PATH}")]

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()

        # ---- Totaux ----
        cursor.execute("SELECT COUNT(*) FROM listings")
        total = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM listings WHERE notified = 0")
        new_count = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM listings WHERE notified = 1")
        notified_count = cursor.fetchone()[0] or 0

        # ---- Annonces dernières 24h ----
        cursor.execute("""
            SELECT COUNT(*) FROM listings
            WHERE created_at >= datetime('now', '-1 day')
        """)
        last_24h = cursor.fetchone()[0] or 0

        # ---- Annonces derniers 7j ----
        cursor.execute("""
            SELECT COUNT(*) FROM listings
            WHERE created_at >= datetime('now', '-7 days')
        """)
        last_7d = cursor.fetchone()[0] or 0

        # ---- Statistiques prix ----
        cursor.execute("""
            SELECT
                AVG(price), MIN(price), MAX(price), COUNT(DISTINCT city)
            FROM listings
            WHERE price > 0
        """)
        price_row = cursor.fetchone()
        avg_price = round(price_row[0], 0) if price_row[0] else 0
        min_price = price_row[1] or 0
        max_price = price_row[2] or 0
        city_count = price_row[3] or 0

        # ---- Médiane des prix ----
        cursor.execute("SELECT price FROM listings WHERE price > 0 ORDER BY price")
        prices_all = [row[0] for row in cursor.fetchall()]
        if prices_all:
            n = len(prices_all)
            if n % 2 == 0:
                median_price = (prices_all[n//2 - 1] + prices_all[n//2]) / 2
            else:
                median_price = prices_all[n//2]
        else:
            median_price = 0

        # ---- Prix/m² ----
        cursor.execute("""
            SELECT AVG(CAST(price AS REAL) / surface)
            FROM listings
            WHERE price > 0 AND surface > 0
        """)
        avg_price_m2_row = cursor.fetchone()
        avg_price_m2 = round(avg_price_m2_row[0], 1) if avg_price_m2_row[0] else None

        # ---- Surface moyenne ----
        cursor.execute("SELECT AVG(surface) FROM listings WHERE surface > 0")
        avg_surface_row = cursor.fetchone()
        avg_surface = round(avg_surface_row[0], 0) if avg_surface_row[0] else None

        # ---- Distance GPS ----
        cursor.execute("""
            SELECT AVG(distance_km), MIN(distance_km), COUNT(*)
            FROM listings WHERE distance_km IS NOT NULL
        """)
        dist_row = cursor.fetchone()
        avg_dist = round(dist_row[0], 1) if dist_row[0] else None
        min_dist = round(dist_row[1], 1) if dist_row[1] else None
        gps_count = dist_row[2] or 0

        # ---- Par site ----
        by_site = {}
        if include_by_site:
            cursor.execute("""
                SELECT site, COUNT(*), AVG(price)
                FROM listings
                GROUP BY site
                ORDER BY COUNT(*) DESC
            """)
            for row in cursor.fetchall():
                by_site[row[0]] = {
                    "count": row[1],
                    "percent": round(row[1] / total * 100, 1) if total > 0 else 0,
                    "avg_price": round(row[2], 0) if row[2] else 0
                }

        # ---- Par ville (top 15) ----
        by_city = {}
        if include_by_city:
            cursor.execute("""
                SELECT city, COUNT(*), AVG(price), MIN(price), MAX(price)
                FROM listings
                WHERE city IS NOT NULL AND city != ''
                GROUP BY city
                ORDER BY COUNT(*) DESC
                LIMIT 15
            """)
            for row in cursor.fetchall():
                by_city[row[0]] = {
                    "count": row[1],
                    "avg_price": round(row[2], 0) if row[2] else 0,
                    "min_price": row[3] or 0,
                    "max_price": row[4] or 0
                }

        # ---- Tranches de prix ----
        price_ranges = {}
        if include_price_ranges:
            ranges = [
                ("< 1500€", "price < 1500"),
                ("1500-2000€", "price >= 1500 AND price < 2000"),
                ("2000-2500€", "price >= 2000 AND price < 2500"),
                ("> 2500€", "price >= 2500"),
            ]
            for label, condition in ranges:
                cursor.execute(f"SELECT COUNT(*) FROM listings WHERE {condition} AND price > 0")
                count = cursor.fetchone()[0] or 0
                price_ranges[label] = {
                    "count": count,
                    "percent": round(count / total * 100, 1) if total > 0 else 0
                }

        conn.close()

        # ---- Construction du rapport texte ----
        lines = [
            "=" * 55,
            "  STATISTIQUES MARCHÉ IMMOBILIER LUXEMBOURG",
            f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "=" * 55,
            "",
            "--- TOTAUX ---",
            f"  Total annonces:     {total}",
            f"  Nouvelles:          {new_count}  (non notifiées)",
            f"  Notifiées:          {notified_count}",
            f"  Ajoutées 24h:       {last_24h}",
            f"  Ajoutées 7 jours:   {last_7d}",
            f"  Villes couvertes:   {city_count}",
            "",
            "--- PRIX ---",
            f"  Moyen:   {int(avg_price)}€/mois",
            f"  Médian:  {int(median_price)}€/mois",
            f"  Min:     {int(min_price)}€/mois",
            f"  Max:     {int(max_price)}€/mois",
        ]

        if avg_price_m2:
            lines.append(f"  Prix/m²: {avg_price_m2}€/m²")
        if avg_surface:
            lines.append(f"  Surface moy.: {int(avg_surface)}m²")

        if avg_dist is not None:
            lines += [
                "",
                "--- GPS ---",
                f"  Distance moy.:  {avg_dist} km",
                f"  Distance min:   {min_dist} km",
                f"  Annonces GPS:   {gps_count}/{total}",
            ]

        if price_ranges:
            lines += ["", "--- TRANCHES DE PRIX ---"]
            for label, data in price_ranges.items():
                bar = "#" * int(data["percent"] / 5)
                lines.append(f"  {label:<12} {data['count']:>3} annonces ({data['percent']:>5.1f}%) {bar}")

        if by_site:
            lines += ["", "--- PAR SITE ---"]
            for site_name, data in by_site.items():
                lines.append(
                    f"  {site_name:<20} {data['count']:>3} ann. "
                    f"({data['percent']:>5.1f}%) | moy. {int(data['avg_price'])}€"
                )

        if by_city:
            lines += ["", "--- TOP VILLES (par nombre) ---"]
            for city_name, data in by_city.items():
                lines.append(
                    f"  {city_name:<20} {data['count']:>3} ann. "
                    f"| moy. {int(data['avg_price'])}€ "
                    f"(min {int(data['min_price'])}€ - max {int(data['max_price'])}€)"
                )

        lines += ["", "=" * 55]

        # JSON complet
        stats_json = {
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "new": new_count,
            "notified": notified_count,
            "last_24h": last_24h,
            "last_7d": last_7d,
            "city_count": city_count,
            "price": {
                "avg": int(avg_price),
                "median": int(median_price),
                "min": int(min_price),
                "max": int(max_price),
                "avg_per_m2": avg_price_m2
            },
            "avg_surface": avg_surface,
            "gps": {
                "avg_distance_km": avg_dist,
                "min_distance_km": min_dist,
                "gps_count": gps_count
            },
            "by_site": by_site,
            "by_city": by_city,
            "price_ranges": price_ranges
        }

        return [
            types.TextContent(type="text", text="\n".join(lines)),
            types.TextContent(
                type="text",
                text=f"\n--- JSON complet ---\n{json.dumps(stats_json, ensure_ascii=False, indent=2)}"
            )
        ]

    except sqlite3.Error as e:
        logger.error(f"Erreur DB stats: {e}")
        return [types.TextContent(type="text", text=f"Erreur base de données: {e}")]
