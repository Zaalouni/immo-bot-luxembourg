#!/usr/bin/env python3
# =============================================================================
# diagnostic_locations.py — Diagnostic des localisations/distances
# =============================================================================
# Lance chaque scraper et affiche pour chaque annonce :
#   - ville extraite, GPS (lat/lng), distance calculee
#   - compare avec le point de reference config.py
# Permet d'identifier : villes mal parsees, GPS absent/faux, distances incorrectes
#
# Usage : python diagnostic_locations.py
# =============================================================================
import sys
import logging

# Reduire le bruit des logs
logging.basicConfig(level=logging.WARNING)

from config import (
    REFERENCE_LAT, REFERENCE_LNG, REFERENCE_NAME, MAX_DISTANCE,
    MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE
)
from utils import haversine_distance

def print_header():
    print("=" * 80)
    print("DIAGNOSTIC LOCALISATIONS — Immo-Bot Luxembourg")
    print("=" * 80)
    print(f"\nPoint de reference : {REFERENCE_NAME}")
    print(f"  Coordonnees      : {REFERENCE_LAT}, {REFERENCE_LNG}")
    print(f"  Distance max     : {MAX_DISTANCE} km")
    print(f"\nFiltres actifs :")
    print(f"  Prix     : {MIN_PRICE}-{MAX_PRICE} EUR")
    print(f"  Chambres : {MIN_ROOMS}-{MAX_ROOMS}")
    print(f"  Surface  : >= {MIN_SURFACE} m2")
    print()

    # Verifier que le point de reference est coherent (Luxembourg)
    if not (49.4 < REFERENCE_LAT < 49.9 and 5.7 < REFERENCE_LNG < 6.5):
        print("!!! ATTENTION : le point de reference ne semble PAS au Luxembourg !!!")
        print(f"    Attendu : lat 49.4-49.9, lng 5.7-6.5")
        print(f"    Actuel  : lat {REFERENCE_LAT}, lng {REFERENCE_LNG}")
        print()


def test_scraper(name, scraper):
    """Tester un scraper et afficher les details de localisation"""
    print(f"\n{'─' * 80}")
    print(f"SCRAPER : {name}")
    print(f"{'─' * 80}")

    try:
        listings = scraper.scrape()
    except Exception as e:
        print(f"  ERREUR : {e}")
        return

    if not listings:
        print(f"  Aucune annonce retournee")
        return

    # Enrichir GPS par geocodage ville
    from utils import enrich_listing_gps
    enriched = 0
    for l in listings:
        had_gps = l.get('latitude') is not None
        enrich_listing_gps(l)
        if not had_gps and l.get('latitude') is not None:
            enriched += 1

    print(f"  {len(listings)} annonces retournees ({enriched} geocodees par ville)\n")

    # Compteurs
    avec_gps = 0
    sans_gps = 0
    geocoded = 0
    distances_ok = 0
    distances_trop_loin = 0
    villes_vides = 0

    print(f"  {'Prix':>7} | {'Ville':<25} | {'Lat':>9} | {'Lng':>9} | {'Dist':>7} | {'Src':<7} | {'Statut':<10} | ID")
    print(f"  {'─'*7}─┼─{'─'*25}─┼─{'─'*9}─┼─{'─'*9}─┼─{'─'*7}─┼─{'─'*7}─┼─{'─'*10}─┼─{'─'*20}")

    for l in listings:
        price = l.get('price', 0)
        city = l.get('city', '')
        lat = l.get('latitude')
        lng = l.get('longitude')
        dist = l.get('distance_km')
        lid = l.get('listing_id', '?')
        gps_src = l.get('gps_source', 'scraper')  # 'scraper' ou 'geocode'

        # Convertir lat/lng en float (certains scrapers retournent des strings)
        try:
            lat = float(lat) if lat else None
        except (ValueError, TypeError):
            lat = None
        try:
            lng = float(lng) if lng else None
        except (ValueError, TypeError):
            lng = None
        try:
            dist = float(dist) if dist is not None else None
        except (ValueError, TypeError):
            dist = None

        # Recalculer la distance si GPS dispo (verifier coherence)
        recalc = None
        if lat and lng:
            try:
                recalc = haversine_distance(REFERENCE_LAT, REFERENCE_LNG, lat, lng)
            except:
                pass

        # Statut
        if not city or city.strip() in ('', 'N/A', 'Luxembourg'):
            ville_status = 'VILLE?'
            if not city or city.strip() in ('', 'N/A'):
                villes_vides += 1
        else:
            ville_status = ''

        if lat and lng:
            avec_gps += 1
            if gps_src == 'geocode':
                geocoded += 1
            if recalc is not None:
                if recalc <= MAX_DISTANCE:
                    distances_ok += 1
                    gps_status = 'OK'
                else:
                    distances_trop_loin += 1
                    gps_status = 'LOIN'
            else:
                gps_status = 'ERR'
        else:
            sans_gps += 1
            gps_status = 'NO GPS'

        # Verifier coherence distance scraper vs recalculee
        coherence = ''
        if dist is not None and recalc is not None:
            ecart = abs(dist - recalc)
            if ecart > 2:  # Plus de 2 km d'ecart
                coherence = f' ECART={ecart:.1f}km!'

        status = f"{gps_status} {ville_status}{coherence}".strip()

        lat_str = f"{lat:.4f}" if lat else "   N/A  "
        lng_str = f"{lng:.4f}" if lng else "   N/A  "
        dist_str = f"{dist:.1f}km" if dist is not None else "  N/A  "
        src_str = f"{gps_src:<7}" if lat else "       "

        print(f"  {price:>7} | {str(city)[:25]:<25} | {lat_str:>9} | {lng_str:>9} | {dist_str:>7} | {src_str} | {status:<10} | {lid}")

    # Resume
    print(f"\n  RESUME {name}:")
    print(f"    Avec GPS    : {avec_gps}/{len(listings)} (dont {geocoded} geocodes par ville)")
    print(f"    Sans GPS    : {sans_gps}/{len(listings)}")
    print(f"    Dist OK     : {distances_ok} (<= {MAX_DISTANCE}km)")
    print(f"    Dist LOIN   : {distances_trop_loin} (> {MAX_DISTANCE}km)")
    print(f"    Ville vide  : {villes_vides}")


def main():
    print_header()

    # Charger les scrapers (meme methode que main.py)
    scrapers = []

    try:
        from scrapers.athome_scraper_json import athome_scraper_json
        scrapers.append(('Athome.lu', athome_scraper_json))
    except ImportError as e:
        print(f"  Skip Athome: {e}")

    try:
        from scrapers.immotop_scraper_real import immotop_scraper_real
        scrapers.append(('Immotop.lu', immotop_scraper_real))
    except ImportError as e:
        print(f"  Skip Immotop: {e}")

    try:
        from scrapers.luxhome_scraper import luxhome_scraper
        scrapers.append(('Luxhome.lu', luxhome_scraper))
    except ImportError as e:
        print(f"  Skip Luxhome: {e}")

    try:
        from scrapers.vivi_scraper_selenium import vivi_scraper_selenium
        scrapers.append(('VIVI.lu', vivi_scraper_selenium))
    except ImportError as e:
        print(f"  Skip VIVI: {e}")

    try:
        from scrapers.newimmo_scraper_real import newimmo_scraper_real
        scrapers.append(('Newimmo.lu', newimmo_scraper_real))
    except ImportError as e:
        print(f"  Skip Newimmo: {e}")

    try:
        from scrapers.unicorn_scraper_real import unicorn_scraper_real
        scrapers.append(('Unicorn.lu', unicorn_scraper_real))
    except ImportError as e:
        print(f"  Skip Unicorn: {e}")

    try:
        from scrapers.wortimmo_scraper import wortimmo_scraper
        scrapers.append(('Wortimmo.lu', wortimmo_scraper))
    except ImportError as e:
        print(f"  Skip Wortimmo: {e}")

    try:
        from scrapers.immoweb_scraper import immoweb_scraper
        scrapers.append(('Immoweb.be', immoweb_scraper))
    except ImportError as e:
        print(f"  Skip Immoweb: {e}")

    try:
        from scrapers.nextimmo_scraper import nextimmo_scraper
        scrapers.append(('Nextimmo.lu', nextimmo_scraper))
    except ImportError as e:
        print(f"  Skip Nextimmo: {e}")

    print(f"\n{len(scrapers)} scrapers charges\n")

    for name, scraper in scrapers:
        try:
            test_scraper(name, scraper)
        except Exception as e:
            print(f"\n  ERREUR FATALE {name}: {e}")

    # Resume global
    print(f"\n{'=' * 80}")
    print("FIN DIAGNOSTIC")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
