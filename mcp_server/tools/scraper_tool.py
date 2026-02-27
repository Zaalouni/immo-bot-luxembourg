#!/usr/bin/env python3
# =============================================================================
# tools/scraper_tool.py — Tools MCP: run_scraper + list_scrapers
# =============================================================================
# Lancer un scraper à la demande via MCP.
# Importe dynamiquement le module scraper et appelle sa fonction principale.
#
# Scrapers supportés (correspondance nom → fichier):
#   athome      → scrapers/athome_scraper_json.py     → scrape()
#   immotop     → scrapers/immotop_scraper_real.py    → scrape()
#   luxhome     → scrapers/luxhome_scraper.py         → scrape()
#   vivi        → scrapers/vivi_scraper_selenium.py   → scrape()
#   newimmo     → scrapers/newimmo_scraper_real.py    → scrape()
#   nextimmo    → scrapers/nextimmo_scraper.py        → scrape()
#   unicorn     → scrapers/unicorn_scraper_real.py    → scrape()
#   wortimmo    → scrapers/wortimmo_scraper.py        → scrape()
#   immoweb     → scrapers/immoweb_scraper.py         → scrape()
#   sigelux     → scrapers/sigelux_scraper.py         → scrape()
#   sothebys    → scrapers/sothebys_scraper.py        → scrape()
#   remax       → scrapers/remax_scraper.py           → scrape()
#   floor       → scrapers/floor_scraper.py           → scrape()
#   apropos     → scrapers/apropos_scraper.py         → scrape()
#   ldhome      → scrapers/ldhome_scraper.py          → scrape()
#   immostar    → scrapers/immostar_scraper.py        → scrape()
#   nexvia      → scrapers/nexvia_scraper.py          → scrape()
#   propertyinvest → scrapers/propertyinvest_scraper.py → scrape()
#   rockenbrod  → scrapers/rockenbrod_scraper.py      → scrape()
#   homepass    → scrapers/home_pass_scraper.py       → scrape()
# =============================================================================

import os
import sys
import json
import importlib
import logging
import sqlite3
import asyncio
from datetime import datetime

import mcp.types as types

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "listings.db")

logger = logging.getLogger("mcp_server.tools.scraper")


# Registre des scrapers disponibles
SCRAPER_REGISTRY = {
    "athome":        ("scrapers.athome_scraper_json",    "scrape"),
    "immotop":       ("scrapers.immotop_scraper_real",   "scrape"),
    "luxhome":       ("scrapers.luxhome_scraper",        "scrape"),
    "vivi":          ("scrapers.vivi_scraper_selenium",  "scrape"),
    "newimmo":       ("scrapers.newimmo_scraper_real",   "scrape"),
    "nextimmo":      ("scrapers.nextimmo_scraper",       "scrape"),
    "unicorn":       ("scrapers.unicorn_scraper_real",   "scrape"),
    "wortimmo":      ("scrapers.wortimmo_scraper",       "scrape"),
    "immoweb":       ("scrapers.immoweb_scraper",        "scrape"),
    "sigelux":       ("scrapers.sigelux_scraper",        "scrape"),
    "sothebys":      ("scrapers.sothebys_scraper",       "scrape"),
    "remax":         ("scrapers.remax_scraper",          "scrape"),
    "floor":         ("scrapers.floor_scraper",          "scrape"),
    "apropos":       ("scrapers.apropos_scraper",        "scrape"),
    "ldhome":        ("scrapers.ldhome_scraper",         "scrape"),
    "immostar":      ("scrapers.immostar_scraper",       "scrape"),
    "nexvia":        ("scrapers.nexvia_scraper",         "scrape"),
    "propertyinvest":("scrapers.propertyinvest_scraper", "scrape"),
    "rockenbrod":    ("scrapers.rockenbrod_scraper",     "scrape"),
    "homepass":      ("scrapers.home_pass_scraper",      "scrape"),
    "actuel":        ("scrapers.actuel_scraper_selenium","scrape"),
}


def _count_listings_for_site(site_name: str) -> int:
    """Compter le nombre d'annonces en DB pour un site."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM listings WHERE LOWER(site) LIKE ?", (f"%{site_name}%",))
        count = cursor.fetchone()[0] or 0
        conn.close()
        return count
    except Exception:
        return 0


def _save_listings_to_db(listings: list, dry_run: bool) -> tuple[int, int]:
    """
    Sauvegarder les annonces dans la DB.
    Retourne (new_count, duplicate_count).
    """
    if dry_run or not listings:
        return 0, 0

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        new_count = 0
        dup_count = 0

        for listing in listings:
            listing_id = listing.get("listing_id", "")
            if not listing_id:
                continue

            # Vérifier si déjà en DB
            cursor.execute("SELECT id FROM listings WHERE listing_id = ?", (listing_id,))
            if cursor.fetchone():
                dup_count += 1
                continue

            # Insérer
            try:
                cursor.execute("""
                    INSERT INTO listings
                    (listing_id, site, title, city, price, rooms, surface, url, latitude, longitude, distance_km)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    listing_id,
                    listing.get("site", "unknown"),
                    listing.get("title", "")[:200],
                    listing.get("city", ""),
                    listing.get("price", 0),
                    listing.get("rooms", 0),
                    listing.get("surface", 0),
                    listing.get("url", ""),
                    listing.get("latitude"),
                    listing.get("longitude"),
                    listing.get("distance_km"),
                ))
                new_count += 1
            except sqlite3.IntegrityError:
                dup_count += 1

        conn.commit()
        conn.close()
        return new_count, dup_count

    except Exception as e:
        logger.error(f"Erreur sauvegarde DB: {e}")
        return 0, 0


async def handle_run_scraper(args: dict) -> list[types.TextContent]:
    """Handler pour run_scraper — lancer un ou tous les scrapers."""

    scraper_name = args.get("scraper_name", "").strip().lower()
    dry_run = bool(args.get("dry_run", False))

    if not scraper_name:
        return [types.TextContent(
            type="text",
            text="Erreur: paramètre 'scraper_name' requis. "
                 f"Scrapers disponibles: {', '.join(sorted(SCRAPER_REGISTRY.keys()))}, all"
        )]

    # Ajouter le parent au path pour les imports
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    # Mode "all" — lancer tous les scrapers
    if scraper_name == "all":
        return await _run_all_scrapers(dry_run)

    # Vérifier que le scraper existe
    if scraper_name not in SCRAPER_REGISTRY:
        return [types.TextContent(
            type="text",
            text=f"Scraper '{scraper_name}' inconnu.\n"
                 f"Disponibles: {', '.join(sorted(SCRAPER_REGISTRY.keys()))}, all"
        )]

    return await _run_single_scraper(scraper_name, dry_run)


async def _run_single_scraper(scraper_name: str, dry_run: bool) -> list[types.TextContent]:
    """Lancer un seul scraper."""
    module_path, func_name = SCRAPER_REGISTRY[scraper_name]
    start_time = datetime.now()
    mode_label = "[DRY RUN]" if dry_run else "[LIVE]"

    lines = [
        f"=== SCRAPER: {scraper_name.upper()} {mode_label} ===",
        f"Démarrage: {start_time.strftime('%H:%M:%S')}",
        ""
    ]

    try:
        # Import dynamique du module scraper
        module = importlib.import_module(module_path)
        scrape_func = getattr(module, func_name)

        # Lancer le scraper dans un thread (peut être bloquant)
        loop = asyncio.get_event_loop()
        listings = await loop.run_in_executor(None, scrape_func)

        if listings is None:
            listings = []

        elapsed = (datetime.now() - start_time).total_seconds()

        lines.append(f"Annonces trouvées: {len(listings)}")
        lines.append(f"Temps d'exécution: {elapsed:.1f}s")
        lines.append("")

        if listings:
            # Sauvegarder en DB (si pas dry_run)
            new_count, dup_count = _save_listings_to_db(listings, dry_run)
            lines.append(f"Nouvelles en DB:  {new_count}")
            lines.append(f"Doublons:         {dup_count}")
            lines.append("")

            if dry_run:
                lines.append("[DRY RUN] — Aucune annonce sauvegardée")
                lines.append("")

            # Aperçu des 5 premières annonces
            lines.append("--- Aperçu (5 premières) ---")
            for i, l in enumerate(listings[:5], 1):
                price = l.get("price", 0)
                city  = l.get("city", "N/A")
                surf  = l.get("surface", "?")
                rooms = l.get("rooms", "?")
                title = l.get("title", "")[:60]
                lines.append(
                    f"{i}. {title}\n"
                    f"   {city} | {price}€ | {surf}m² | {rooms}ch."
                )
        else:
            lines.append("Aucune annonce récupérée.")

    except ImportError as e:
        lines.append(f"Erreur import module '{module_path}': {e}")
        lines.append("Vérifiez que le fichier scraper existe dans scrapers/")
    except AttributeError as e:
        lines.append(f"Fonction '{func_name}' introuvable dans '{module_path}': {e}")
    except Exception as e:
        lines.append(f"Erreur scraper: {type(e).__name__}: {e}")
        logger.error(f"Erreur scraper {scraper_name}: {e}", exc_info=True)

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _run_all_scrapers(dry_run: bool) -> list[types.TextContent]:
    """Lancer tous les scrapers séquentiellement."""
    mode_label = "[DRY RUN]" if dry_run else "[LIVE]"
    start_time = datetime.now()

    lines = [
        f"=== LANCEMENT DE TOUS LES SCRAPERS {mode_label} ===",
        f"Démarrage: {start_time.strftime('%H:%M:%S')}",
        f"Scrapers: {len(SCRAPER_REGISTRY)}",
        ""
    ]

    total_found = 0
    total_new = 0
    results = {}

    for scraper_name in sorted(SCRAPER_REGISTRY.keys()):
        module_path, func_name = SCRAPER_REGISTRY[scraper_name]
        scraper_start = datetime.now()

        try:
            if BASE_DIR not in sys.path:
                sys.path.insert(0, BASE_DIR)

            module = importlib.import_module(module_path)
            scrape_func = getattr(module, func_name)

            loop = asyncio.get_event_loop()
            listings = await loop.run_in_executor(None, scrape_func)

            if listings is None:
                listings = []

            new_count, _ = _save_listings_to_db(listings, dry_run)
            elapsed = (datetime.now() - scraper_start).total_seconds()

            results[scraper_name] = {"found": len(listings), "new": new_count, "elapsed": elapsed, "status": "OK"}
            total_found += len(listings)
            total_new += new_count

            lines.append(f"✓ {scraper_name:<20} {len(listings):>3} trouvées, {new_count:>3} nouvelles ({elapsed:.1f}s)")

        except ImportError:
            results[scraper_name] = {"found": 0, "new": 0, "elapsed": 0, "status": "IMPORT_ERROR"}
            lines.append(f"✗ {scraper_name:<20} Import error")
        except Exception as e:
            results[scraper_name] = {"found": 0, "new": 0, "elapsed": 0, "status": f"ERROR: {type(e).__name__}"}
            lines.append(f"✗ {scraper_name:<20} {type(e).__name__}: {str(e)[:50]}")

    elapsed_total = (datetime.now() - start_time).total_seconds()
    lines += [
        "",
        "=" * 50,
        f"TOTAL: {total_found} annonces trouvées, {total_new} nouvelles",
        f"Durée totale: {elapsed_total:.1f}s",
    ]
    if dry_run:
        lines.append("[DRY RUN] — Aucune annonce sauvegardée en DB")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def handle_list_scrapers(args: dict) -> list[types.TextContent]:
    """Handler pour list_scrapers — liste tous les scrapers avec statut."""

    lines = [
        "=== SCRAPERS DISPONIBLES ===",
        f"Total: {len(SCRAPER_REGISTRY)} scrapers",
        ""
    ]

    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    scrapers_info = []

    for name in sorted(SCRAPER_REGISTRY.keys()):
        module_path, func_name = SCRAPER_REGISTRY[name]
        module_file = module_path.replace(".", "/") + ".py"
        full_path = os.path.join(BASE_DIR, module_file)

        # Vérifier si le fichier existe
        file_exists = os.path.exists(full_path)

        # Compter les annonces en DB pour ce site
        db_count = _count_listings_for_site(name)

        status = "✓ actif" if file_exists else "✗ fichier manquant"

        scrapers_info.append({
            "name": name,
            "module": module_path,
            "file_exists": file_exists,
            "db_count": db_count,
            "status": status
        })

        lines.append(f"  {name:<20} {status:<20} DB: {db_count:>3} annonces")

    lines += [
        "",
        "Usage: run_scraper avec scraper_name='<nom>' ou 'all'",
        "Exemple: run_scraper(scraper_name='athome')",
        "Exemple: run_scraper(scraper_name='all', dry_run=True)"
    ]

    result_json = json.dumps({"scrapers": scrapers_info, "total": len(scrapers_info)}, indent=2)

    return [
        types.TextContent(type="text", text="\n".join(lines)),
        types.TextContent(type="text", text=f"\n--- JSON ---\n{result_json}")
    ]
