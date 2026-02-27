#!/usr/bin/env python3
# =============================================================================
# tools/search_tool.py — Tool MCP: search_listings
# =============================================================================
# Recherche d'annonces immobilières avec filtres multiples.
# Interroge directement listings.db via sqlite3.
#
# Paramètres acceptés:
#   price_min, price_max    : fourchette de prix (€/mois)
#   city                    : ville ou commune (LIKE partiel)
#   rooms_min, rooms_max    : nombre de chambres
#   surface_min             : surface minimum (m²)
#   site                    : site source (LIKE partiel)
#   max_distance_km         : distance max depuis référence GPS
#   only_new                : seulement annonces non-notifiées
#   sort_by                 : ordre de tri
#   limit                   : max résultats (1-100)
# =============================================================================

import sqlite3
import json
import os
import sys
import logging

import mcp.types as types

# Chemin vers la DB (parent du dossier mcp_server/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "listings.db")

logger = logging.getLogger("mcp_server.tools.search")


# Mapping des ordres de tri vers clauses SQL
SORT_MAP = {
    "price_asc":    "price ASC, created_at DESC",
    "price_desc":   "price DESC, created_at DESC",
    "distance_asc": "COALESCE(distance_km, 999) ASC, price ASC",
    "date_desc":    "created_at DESC",
    "surface_desc": "COALESCE(surface, 0) DESC, price ASC",
}


def _format_listing(row: tuple, columns: list[str]) -> dict:
    """Convertir une ligne DB en dictionnaire formaté."""
    listing = dict(zip(columns, row))

    # Formatage prix/m²
    price = listing.get("price", 0) or 0
    surface = listing.get("surface", 0) or 0
    if price > 0 and surface > 0:
        listing["price_per_m2"] = round(price / surface, 1)
    else:
        listing["price_per_m2"] = None

    # Formatage distance
    dist = listing.get("distance_km")
    if dist is not None:
        listing["distance_formatted"] = (
            "< 1 km" if dist < 1
            else f"{dist:.1f} km" if dist < 10
            else f"{int(dist)} km"
        )
    else:
        listing["distance_formatted"] = "N/A"

    return listing


async def handle_search_listings(args: dict) -> list[types.TextContent]:
    """Handler principal pour search_listings."""

    # --- Extraire et valider les paramètres ---
    price_min      = max(0, int(args.get("price_min", 0)))
    price_max      = min(999999, int(args.get("price_max", 999999)))
    city           = args.get("city", "").strip()
    rooms_min      = args.get("rooms_min")
    rooms_max      = args.get("rooms_max")
    surface_min    = args.get("surface_min")
    site           = args.get("site", "").strip()
    max_dist       = args.get("max_distance_km")
    only_new       = bool(args.get("only_new", False))
    sort_by        = args.get("sort_by", "date_desc")
    limit          = max(1, min(100, int(args.get("limit", 20))))

    if not os.path.exists(DB_PATH):
        return [types.TextContent(
            type="text",
            text=f"Erreur: Base de données introuvable à {DB_PATH}"
        )]

    # --- Construction de la requête SQL ---
    conditions = []
    params = []

    # Filtre prix
    if price_min > 0:
        conditions.append("price >= ?")
        params.append(price_min)
    if price_max < 999999:
        conditions.append("price <= ?")
        params.append(price_max)

    # Filtre ville (recherche partielle insensible à la casse)
    if city:
        conditions.append("LOWER(city) LIKE ?")
        params.append(f"%{city.lower()}%")

    # Filtre chambres
    if rooms_min is not None:
        conditions.append("(rooms IS NULL OR rooms = 0 OR rooms >= ?)")
        params.append(int(rooms_min))
    if rooms_max is not None:
        conditions.append("(rooms IS NULL OR rooms = 0 OR rooms <= ?)")
        params.append(int(rooms_max))

    # Filtre surface
    if surface_min is not None:
        conditions.append("(surface IS NULL OR surface = 0 OR surface >= ?)")
        params.append(int(surface_min))

    # Filtre site
    if site:
        conditions.append("LOWER(site) LIKE ?")
        params.append(f"%{site.lower()}%")

    # Filtre distance GPS
    if max_dist is not None:
        conditions.append("(distance_km IS NULL OR distance_km <= ?)")
        params.append(float(max_dist))

    # Filtre nouvelles annonces seulement
    if only_new:
        conditions.append("notified = 0")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    order_clause = SORT_MAP.get(sort_by, "created_at DESC")

    query = f"""
        SELECT
            id, listing_id, site, title, city, price, rooms, surface,
            url, latitude, longitude, distance_km,
            strftime('%d/%m/%Y %H:%M', created_at) as created_at,
            notified
        FROM listings
        {where_clause}
        ORDER BY {order_clause}
        LIMIT ?
    """
    params.append(limit)

    # --- Exécution de la requête ---
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur DB search: {e}")
        return [types.TextContent(type="text", text=f"Erreur base de données: {e}")]

    # --- Formatage des résultats ---
    if not rows:
        # Construire un message informatif avec les filtres appliqués
        filters_desc = []
        if price_min > 0 or price_max < 999999:
            filters_desc.append(f"prix {price_min}-{price_max}€")
        if city:
            filters_desc.append(f"ville '{city}'")
        if rooms_min:
            filters_desc.append(f">= {rooms_min} chambres")
        if surface_min:
            filters_desc.append(f">= {surface_min}m²")
        filter_str = ", ".join(filters_desc) if filters_desc else "aucun filtre"

        return [types.TextContent(
            type="text",
            text=f"Aucune annonce trouvée avec ces critères ({filter_str}).\n"
                 f"Essayez d'élargir les filtres ou de vérifier l'orthographe de la ville."
        )]

    listings = [_format_listing(row, columns) for row in rows]

    # --- Construction du rapport texte ---
    lines = [
        f"=== RECHERCHE IMMOBILIÈRE — {len(listings)} résultat(s) ===",
        f"(Triés par: {sort_by}, Limite: {limit})",
        ""
    ]

    for i, l in enumerate(listings, 1):
        price_m2 = f" ({l['price_per_m2']}€/m²)" if l.get("price_per_m2") else ""
        dist_info = f" | {l['distance_formatted']}" if l.get("distance_km") is not None else ""
        surface_info = f" | {l['surface']}m²" if l.get("surface") else ""
        rooms_info = f" | {l['rooms']} ch." if l.get("rooms") else ""
        new_flag = " [NOUVEAU]" if not l.get("notified") else ""

        lines.append(f"{i}. [{l['site'].upper()}]{new_flag} {l['title']}")
        lines.append(f"   📍 {l['city']}{dist_info}")
        lines.append(f"   💰 {l['price']}€/mois{price_m2}{surface_info}{rooms_info}")
        lines.append(f"   🔗 {l['url']}")
        lines.append(f"   🕐 Ajouté le {l['created_at']}")
        lines.append(f"   ID: {l['listing_id']}")
        lines.append("")

    # Résumé statistique
    prices = [l["price"] for l in listings if l.get("price", 0) > 0]
    if prices:
        avg_price = sum(prices) // len(prices)
        lines.append(f"--- Résumé ({len(listings)} annonces) ---")
        lines.append(f"Prix moyen: {avg_price}€/mois")
        lines.append(f"Prix min:   {min(prices)}€/mois")
        lines.append(f"Prix max:   {max(prices)}€/mois")

    # Ajouter aussi le JSON brut pour usage programmatique
    result_text = "\n".join(lines)
    result_json = json.dumps({"count": len(listings), "listings": listings}, ensure_ascii=False, indent=2)

    return [
        types.TextContent(type="text", text=result_text),
        types.TextContent(type="text", text=f"\n--- JSON (usage programmatique) ---\n{result_json}")
    ]
