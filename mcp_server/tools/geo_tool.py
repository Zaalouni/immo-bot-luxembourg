#!/usr/bin/env python3
# =============================================================================
# tools/geo_tool.py — Tools MCP: find_nearby + geocode_city
# =============================================================================
# Recherche géographique avec formule Haversine.
# Utilise le dictionnaire LUXEMBOURG_CITIES de utils.py (120+ villes).
#
# find_nearby:
#   - Accepte lat/lng OU city_name comme point central
#   - Calcule la distance Haversine pour chaque annonce
#   - Retourne les annonces dans le rayon donné, triées par distance
#
# geocode_city:
#   - Convertit un nom de ville en coordonnées GPS
#   - Utilise le dictionnaire local (pas d'API externe)
# =============================================================================

import sqlite3
import json
import os
import sys
import math
import logging

import mcp.types as types

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH  = os.path.join(BASE_DIR, "listings.db")

logger = logging.getLogger("mcp_server.tools.geo")


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculer distance en km entre 2 points GPS (formule Haversine)."""
    R = 6371.0
    lat1_r = math.radians(lat1)
    lng1_r = math.radians(lng1)
    lat2_r = math.radians(lat2)
    lng2_r = math.radians(lng2)
    dlat = lat2_r - lat1_r
    dlng = lng2_r - lng1_r
    a = math.sin(dlat / 2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def _get_city_coords(city_name: str) -> tuple[float, float] | None:
    """Obtenir les coordonnées GPS d'une ville via utils.py."""
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    try:
        from utils import geocode_city
        return geocode_city(city_name)
    except ImportError:
        logger.warning("utils.py introuvable — geocodage non disponible")
        return None


async def handle_find_nearby(args: dict) -> list[types.TextContent]:
    """Handler pour find_nearby — recherche géographique par rayon."""

    lat       = args.get("latitude")
    lng       = args.get("longitude")
    city_name = args.get("city_name", "").strip()
    radius_km = float(args.get("radius_km", 5.0))
    limit     = max(1, min(50, int(args.get("limit", 15))))

    # ---- Résoudre le point central ----
    center_label = ""
    if city_name and (lat is None or lng is None):
        coords = _get_city_coords(city_name)
        if coords:
            lat, lng = coords
            center_label = f"{city_name} ({lat:.4f}, {lng:.4f})"
        else:
            return [types.TextContent(
                type="text",
                text=f"Ville '{city_name}' non trouvée dans le dictionnaire luxembourgeois.\n"
                     "Essayez avec latitude/longitude explicites ou vérifiez l'orthographe."
            )]
    elif lat is not None and lng is not None:
        center_label = f"({lat:.4f}, {lng:.4f})"
    else:
        return [types.TextContent(
            type="text",
            text="Erreur: spécifiez soit 'city_name', soit 'latitude' + 'longitude'."
        )]

    if not os.path.exists(DB_PATH):
        return [types.TextContent(type="text", text=f"Erreur: DB introuvable à {DB_PATH}")]

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()

        # Récupérer toutes les annonces avec GPS
        cursor.execute("""
            SELECT listing_id, site, title, city, price, rooms, surface,
                   url, latitude, longitude, distance_km,
                   strftime('%d/%m/%Y', created_at) as added_date
            FROM listings
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """)
        rows = cursor.fetchall()
        conn.close()

    except sqlite3.Error as e:
        logger.error(f"Erreur DB geo: {e}")
        return [types.TextContent(type="text", text=f"Erreur base de données: {e}")]

    # ---- Calculer les distances ----
    results = []
    for row in rows:
        (lid, site, title, city, price, rooms, surface,
         url, row_lat, row_lng, stored_dist, added_date) = row

        try:
            dist = _haversine(float(lat), float(lng), float(row_lat), float(row_lng))
        except (ValueError, TypeError):
            continue

        if dist <= radius_km:
            results.append({
                "listing_id": lid,
                "site": site,
                "title": title,
                "city": city or "N/A",
                "price": price,
                "rooms": rooms,
                "surface": surface,
                "url": url,
                "latitude": row_lat,
                "longitude": row_lng,
                "distance_km": dist,
                "added_date": added_date
            })

    # Trier par distance
    results.sort(key=lambda x: x["distance_km"])
    results = results[:limit]

    # ---- Rapport ----
    lines = [
        f"=== ANNONCES À {radius_km} km DE {center_label} ===",
        f"Trouvées: {len(results)} annonces",
        ""
    ]

    if not results:
        lines.append(f"Aucune annonce dans un rayon de {radius_km} km.")
        lines.append("Essayez d'augmenter le rayon (radius_km).")
    else:
        for i, r in enumerate(results, 1):
            dist_str  = f"{r['distance_km']:.1f} km"
            surf_str  = f" | {r['surface']}m²" if r.get("surface") else ""
            rooms_str = f" | {r['rooms']}ch." if r.get("rooms") else ""
            price_m2  = ""
            if r.get("price", 0) > 0 and r.get("surface", 0) > 0:
                price_m2 = f" ({round(r['price']/r['surface'], 1)}€/m²)"

            lines.append(f"{i}. [{r['site'].upper()}] {r['title'][:55]}")
            lines.append(f"   📍 {r['city']} — {dist_str} du point central")
            lines.append(f"   💰 {r['price']}€/mois{price_m2}{surf_str}{rooms_str}")
            lines.append(f"   🔗 {r['url']}")
            lines.append(f"   ID: {r['listing_id']} | Ajouté: {r['added_date']}")
            lines.append("")

        # Stats
        prices = [r["price"] for r in results if r.get("price", 0) > 0]
        if prices:
            lines += [
                "--- Résumé ---",
                f"Prix moyen dans le rayon: {sum(prices) // len(prices)}€/mois",
                f"Prix min: {min(prices)}€ | max: {max(prices)}€",
            ]

    return [
        types.TextContent(type="text", text="\n".join(lines)),
        types.TextContent(
            type="text",
            text=f"\n--- JSON ---\n{json.dumps({'center': center_label, 'radius_km': radius_km, 'count': len(results), 'listings': results}, ensure_ascii=False, indent=2)}"
        )
    ]


async def handle_geocode_city(args: dict) -> list[types.TextContent]:
    """Handler pour geocode_city — convertir ville en GPS."""

    city_name = args.get("city_name", "").strip()
    if not city_name:
        return [types.TextContent(type="text", text="Erreur: 'city_name' requis.")]

    coords = _get_city_coords(city_name)

    if coords:
        lat, lng = coords
        lines = [
            f"=== GEOCODAGE: {city_name} ===",
            "",
            f"  Latitude:  {lat}",
            f"  Longitude: {lng}",
            "",
            f"  Google Maps: https://maps.google.com/?q={lat},{lng}",
            f"  OpenStreetMap: https://www.openstreetmap.org/?mlat={lat}&mlon={lng}",
        ]
        result = {"city": city_name, "latitude": lat, "longitude": lng, "found": True}
    else:
        lines = [
            f"=== GEOCODAGE: {city_name} ===",
            "",
            f"  Ville '{city_name}' non trouvée dans le dictionnaire.",
            "",
            "  Villes disponibles (exemples):",
            "  Luxembourg, Kirchberg, Belair, Gare, Eich, Limpertsberg,",
            "  Strassen, Bertrange, Mamer, Hesperange, Howald,",
            "  Esch-sur-Alzette, Bettembourg, Dudelange, ...",
        ]
        result = {"city": city_name, "found": False}

    return [
        types.TextContent(type="text", text="\n".join(lines)),
        types.TextContent(type="text", text=f"\n--- JSON ---\n{json.dumps(result, indent=2)}")
    ]
