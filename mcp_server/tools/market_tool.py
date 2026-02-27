#!/usr/bin/env python3
# =============================================================================
# tools/market_tool.py — Tools MCP: analyze_market + detect_anomalies
# =============================================================================
# Analyse des tendances du marché immobilier sur une période donnée.
# Compare les données actuelles avec les archives historiques JSON.
# Détecte les anomalies de prix (outliers statistiques).
# =============================================================================

import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

import mcp.types as types

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH  = os.path.join(BASE_DIR, "listings.db")
HISTORY_DIR = os.path.join(BASE_DIR, "dashboards", "data", "history")

logger = logging.getLogger("mcp_server.tools.market")


def _load_history(date_str: str) -> dict | None:
    """Charger une archive historique depuis dashboards/data/history/YYYY-MM-DD.json."""
    path = os.path.join(HISTORY_DIR, f"{date_str}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _get_available_history_dates() -> list[str]:
    """Lister toutes les dates disponibles dans l'historique."""
    if not os.path.exists(HISTORY_DIR):
        return []
    dates = []
    for fname in sorted(os.listdir(HISTORY_DIR)):
        if fname.endswith(".json") and len(fname) == 15:  # YYYY-MM-DD.json
            dates.append(fname[:-5])
    return sorted(dates)


async def handle_analyze_market(args: dict) -> list[types.TextContent]:
    """Handler pour analyze_market — tendances et comparaison temporelle."""

    period_days  = max(1, min(90, int(args.get("period_days", 7))))
    focus_city   = args.get("focus_city", "").strip()
    include_opps = bool(args.get("include_opportunities", True))

    if not os.path.exists(DB_PATH):
        return [types.TextContent(type="text", text=f"Erreur: DB introuvable à {DB_PATH}")]

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()

        today = datetime.now().date()

        # ---- Données actuelles ----
        base_query = "FROM listings WHERE price > 0"
        if focus_city:
            base_query += f" AND LOWER(city) LIKE '%{focus_city.lower()}%'"

        cursor.execute(f"SELECT COUNT(*), AVG(price), MIN(price), MAX(price) {base_query}")
        current_row = cursor.fetchone()
        current_total = current_row[0] or 0
        current_avg   = round(current_row[1] or 0, 0)
        current_min   = current_row[2] or 0
        current_max   = current_row[3] or 0

        # ---- Nouvelles annonces dans la période ----
        cursor.execute(f"""
            SELECT COUNT(*), AVG(price)
            {base_query}
            AND created_at >= datetime('now', '-{period_days} days')
        """)
        period_row = cursor.fetchone()
        period_count = period_row[0] or 0
        period_avg   = round(period_row[1] or 0, 0)

        # ---- Évolution par ville (sur la période) ----
        cursor.execute(f"""
            SELECT city, COUNT(*), AVG(price), MIN(price)
            FROM listings
            WHERE price > 0
            AND created_at >= datetime('now', '-{period_days} days')
            {'AND LOWER(city) LIKE \'%' + focus_city.lower() + '%\'' if focus_city else ''}
            GROUP BY city
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        city_period = cursor.fetchall()

        # ---- Par site (sur la période) ----
        cursor.execute(f"""
            SELECT site, COUNT(*)
            FROM listings
            WHERE created_at >= datetime('now', '-{period_days} days')
            GROUP BY site
            ORDER BY COUNT(*) DESC
        """)
        site_period = cursor.fetchall()

        # ---- Annonces par jour (sur la période) ----
        cursor.execute(f"""
            SELECT DATE(created_at), COUNT(*)
            FROM listings
            WHERE created_at >= datetime('now', '-{period_days} days')
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at) DESC
        """)
        daily_counts = cursor.fetchall()

        # ---- Opportunités (prix < 80% de la moyenne) ----
        opportunities = []
        if include_opps and current_avg > 0:
            threshold = current_avg * 0.80
            cursor.execute(f"""
                SELECT listing_id, title, city, price, surface, rooms, url
                {base_query}
                AND price <= ?
                ORDER BY price ASC
                LIMIT 10
            """, (threshold,))
            opportunities = cursor.fetchall()

        conn.close()

        # ---- Comparaison avec l'historique ----
        history_comparison = []
        available_dates = _get_available_history_dates()

        if available_dates:
            for days_back in [1, 3, 7, 14, 30]:
                if days_back <= period_days or days_back == 1:
                    target_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
                    hist_data = _load_history(target_date)
                    if hist_data:
                        hist_total = hist_data.get("total", 0)
                        hist_avg   = hist_data.get("avg_price", 0)
                        delta_total = current_total - hist_total
                        delta_avg   = current_avg - hist_avg if hist_avg else 0
                        history_comparison.append({
                            "days_back": days_back,
                            "date": target_date,
                            "total": hist_total,
                            "avg_price": hist_avg,
                            "delta_total": delta_total,
                            "delta_avg_price": delta_avg
                        })

        # ---- Construction du rapport ----
        title = f"ANALYSE MARCHÉ — {'Ville: ' + focus_city if focus_city else 'Luxembourg complet'}"
        lines = [
            "=" * 60,
            f"  {title}",
            f"  Période: {period_days} jour(s) | {today.strftime('%d/%m/%Y')}",
            "=" * 60,
            "",
            "--- SITUATION ACTUELLE ---",
            f"  Total annonces:  {current_total}",
            f"  Prix moyen:      {int(current_avg)}€/mois",
            f"  Prix min:        {int(current_min)}€/mois",
            f"  Prix max:        {int(current_max)}€/mois",
            "",
            f"--- ACTIVITÉ (derniers {period_days} jours) ---",
            f"  Nouvelles annonces: {period_count}",
        ]

        if period_count > 0:
            lines.append(f"  Prix moyen (période): {int(period_avg)}€/mois")
            avg_per_day = round(period_count / period_days, 1)
            lines.append(f"  Rythme: {avg_per_day} annonces/jour")

        if daily_counts:
            lines += ["", "--- ANNONCES PAR JOUR ---"]
            for day, count in daily_counts[:7]:
                bar = "█" * min(count, 20)
                lines.append(f"  {day}  {count:>3}  {bar}")

        if city_period:
            lines += ["", f"--- VILLES ACTIVES (derniers {period_days}j) ---"]
            for city, count, avg, min_p in city_period:
                lines.append(
                    f"  {(city or 'N/A'):<22} {count:>3} nouvelles | moy. {int(avg or 0)}€"
                )

        if site_period:
            lines += ["", f"--- SITES ACTIFS (derniers {period_days}j) ---"]
            for site, count in site_period:
                lines.append(f"  {site:<22} {count:>3} nouvelles annonces")

        if history_comparison:
            lines += ["", "--- ÉVOLUTION HISTORIQUE ---"]
            for comp in history_comparison:
                d = comp["days_back"]
                sign_total = "+" if comp["delta_total"] >= 0 else ""
                sign_avg   = "+" if comp["delta_avg_price"] >= 0 else ""
                lines.append(
                    f"  vs {d}j: annonces {sign_total}{comp['delta_total']:+d}, "
                    f"prix moy. {sign_avg}{int(comp['delta_avg_price']):+d}€"
                )

        if opportunities:
            threshold = int(current_avg * 0.80)
            lines += [
                "",
                f"--- OPPORTUNITÉS (< {threshold}€, soit < 80% de la moyenne) ---"
            ]
            for lid, title, city, price, surf, rooms, url in opportunities:
                surf_str  = f" | {surf}m²" if surf else ""
                rooms_str = f" | {rooms}ch." if rooms else ""
                lines.append(f"  {price}€{surf_str}{rooms_str} — {city}")
                lines.append(f"    {title[:50]}")
                lines.append(f"    {url}")
                lines.append("")

        if available_dates:
            lines += [
                "",
                f"Archives disponibles: {len(available_dates)} jours",
                f"De {available_dates[0]} à {available_dates[-1]}"
            ]

        lines.append("=" * 60)

        # JSON
        result_data = {
            "period_days": period_days,
            "focus_city": focus_city or None,
            "current": {
                "total": current_total,
                "avg_price": int(current_avg),
                "min_price": int(current_min),
                "max_price": int(current_max)
            },
            "period_activity": {
                "new_listings": period_count,
                "avg_price": int(period_avg),
                "daily_counts": [{"date": d, "count": c} for d, c in daily_counts]
            },
            "history_comparison": history_comparison,
            "opportunities_count": len(opportunities)
        }

        return [
            types.TextContent(type="text", text="\n".join(lines)),
            types.TextContent(
                type="text",
                text=f"\n--- JSON ---\n{json.dumps(result_data, ensure_ascii=False, indent=2)}"
            )
        ]

    except sqlite3.Error as e:
        logger.error(f"Erreur DB market: {e}")
        return [types.TextContent(type="text", text=f"Erreur base de données: {e}")]


async def handle_detect_anomalies(args: dict) -> list[types.TextContent]:
    """Handler pour detect_anomalies — détecter prix aberrants, doublons, données manquantes."""

    threshold_pct = float(args.get("threshold_percent", 30))

    if not os.path.exists(DB_PATH):
        return [types.TextContent(type="text", text=f"Erreur: DB introuvable à {DB_PATH}")]

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()

        # ---- Statistiques de base ----
        cursor.execute("SELECT AVG(price), AVG(surface) FROM listings WHERE price > 0")
        base_row = cursor.fetchone()
        avg_price   = base_row[0] or 0
        avg_surface = base_row[1] or 0

        threshold_factor = threshold_pct / 100
        high_price_threshold = avg_price * (1 + threshold_factor)
        low_price_threshold  = avg_price * (1 - threshold_factor)

        anomalies = {
            "prix_tres_eleves": [],
            "prix_tres_bas":    [],
            "surface_zero":     [],
            "pas_de_gps":       [],
            "doublons_potentiels": [],
            "urls_manquantes":  []
        }

        # ---- Prix très élevés ----
        cursor.execute("""
            SELECT listing_id, site, city, price, surface, url
            FROM listings
            WHERE price > ? AND price > 0
            ORDER BY price DESC LIMIT 10
        """, (high_price_threshold,))
        for row in cursor.fetchall():
            anomalies["prix_tres_eleves"].append({
                "listing_id": row[0], "site": row[1], "city": row[2],
                "price": row[3], "surface": row[4], "url": row[5],
                "deviation_pct": round((row[3] - avg_price) / avg_price * 100, 1)
            })

        # ---- Prix très bas ----
        cursor.execute("""
            SELECT listing_id, site, city, price, surface, url
            FROM listings
            WHERE price < ? AND price > 0
            ORDER BY price ASC LIMIT 10
        """, (low_price_threshold,))
        for row in cursor.fetchall():
            anomalies["prix_tres_bas"].append({
                "listing_id": row[0], "site": row[1], "city": row[2],
                "price": row[3], "surface": row[4], "url": row[5],
                "deviation_pct": round((row[3] - avg_price) / avg_price * 100, 1)
            })

        # ---- Surface = 0 ou NULL ----
        cursor.execute("SELECT COUNT(*) FROM listings WHERE surface IS NULL OR surface = 0")
        anomalies["surface_zero"] = cursor.fetchone()[0] or 0

        # ---- Pas de GPS ----
        cursor.execute("SELECT COUNT(*) FROM listings WHERE latitude IS NULL OR longitude IS NULL")
        anomalies["pas_de_gps"] = cursor.fetchone()[0] or 0

        # ---- Doublons potentiels (même prix + ville) ----
        cursor.execute("""
            SELECT price, city, COUNT(*) as cnt
            FROM listings
            WHERE price > 0
            GROUP BY price, city
            HAVING cnt > 1
            ORDER BY cnt DESC
            LIMIT 10
        """)
        for row in cursor.fetchall():
            anomalies["doublons_potentiels"].append({
                "price": row[0], "city": row[1], "count": row[2]
            })

        # ---- URLs manquantes ou invalides ----
        cursor.execute("""
            SELECT COUNT(*) FROM listings
            WHERE url IS NULL OR url = '' OR url = '#'
        """)
        anomalies["urls_manquantes"] = cursor.fetchone()[0] or 0

        conn.close()

        # ---- Rapport ----
        lines = [
            "=" * 55,
            "  DÉTECTION D'ANOMALIES — Immo-Bot Luxembourg",
            f"  Seuil: ±{threshold_pct}% (moyenne: {int(avg_price)}€)",
            "=" * 55,
            ""
        ]

        # Prix élevés
        if anomalies["prix_tres_eleves"]:
            lines += [f"--- PRIX TRÈS ÉLEVÉS (> {int(high_price_threshold)}€) ---"]
            for a in anomalies["prix_tres_eleves"]:
                lines.append(
                    f"  {a['price']}€ ({a['deviation_pct']:+.0f}%) — "
                    f"{a['city']} [{a['site']}] | {a['listing_id']}"
                )
            lines.append("")

        # Prix bas
        if anomalies["prix_tres_bas"]:
            lines += [f"--- PRIX TRÈS BAS (< {int(low_price_threshold)}€) ---"]
            for a in anomalies["prix_tres_bas"]:
                lines.append(
                    f"  {a['price']}€ ({a['deviation_pct']:+.0f}%) — "
                    f"{a['city']} [{a['site']}] | {a['listing_id']}"
                )
            lines.append("")

        # Données manquantes
        lines += [
            "--- DONNÉES MANQUANTES ---",
            f"  Surface inconnue:   {anomalies['surface_zero']} annonces",
            f"  GPS manquant:       {anomalies['pas_de_gps']} annonces",
            f"  URLs invalides:     {anomalies['urls_manquantes']} annonces",
            ""
        ]

        # Doublons
        if anomalies["doublons_potentiels"]:
            lines += ["--- DOUBLONS POTENTIELS (même prix + ville) ---"]
            for d in anomalies["doublons_potentiels"]:
                lines.append(f"  {d['price']}€ à {d['city']}: {d['count']} annonces similaires")
            lines.append("")

        total_anomalies = (
            len(anomalies["prix_tres_eleves"]) +
            len(anomalies["prix_tres_bas"]) +
            len(anomalies["doublons_potentiels"])
        )
        lines += [
            "=" * 55,
            f"TOTAL ANOMALIES: {total_anomalies} détectées",
            f"  Prix aberrants: {len(anomalies['prix_tres_eleves'])} hauts, {len(anomalies['prix_tres_bas'])} bas",
            f"  Doublons: {len(anomalies['doublons_potentiels'])} groupes",
        ]

        return [
            types.TextContent(type="text", text="\n".join(lines)),
            types.TextContent(
                type="text",
                text=f"\n--- JSON ---\n{json.dumps(anomalies, ensure_ascii=False, indent=2)}"
            )
        ]

    except sqlite3.Error as e:
        logger.error(f"Erreur DB anomalies: {e}")
        return [types.TextContent(type="text", text=f"Erreur base de données: {e}")]
