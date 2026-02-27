#!/usr/bin/env python3
# =============================================================================
# test_all_scrapers.py — Test automatisé de tous les scrapers
# =============================================================================
# Usage:
#   python test_all_scrapers.py          # Tester tous les scrapers
#   python test_all_scrapers.py --quick  # Test rapide (timeout court)
#   python test_all_scrapers.py --only sigelux sothebys  # Tester seulement certains
#   python test_all_scrapers.py --verbose  # Afficher détails des annonces
# =============================================================================

import sys
import time
import argparse
from datetime import datetime

# Couleurs terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def color(text, col):
    return f"{col}{text}{Colors.END}"

# Configuration des scrapers à tester
SCRAPERS_CONFIG = [
    # (module_name, instance_name, display_name, type)
    # Type: 'http' = rapide, 'selenium' = lent

    # Scrapers existants
    ('athome_scraper_json', 'athome_scraper_json', 'Athome.lu', 'http'),
    ('immotop_scraper_real', 'immotop_scraper_real', 'Immotop.lu', 'http'),
    ('luxhome_scraper', 'luxhome_scraper', 'Luxhome.lu', 'http'),
    ('vivi_scraper_selenium', 'vivi_scraper_selenium', 'VIVI.lu', 'selenium'),
    ('newimmo_scraper_real', 'newimmo_scraper_real', 'Newimmo.lu', 'selenium'),
    ('unicorn_scraper_real', 'unicorn_scraper_real', 'Unicorn.lu', 'selenium'),
    ('wortimmo_scraper', 'wortimmo_scraper', 'Wortimmo.lu', 'selenium'),
    ('immoweb_scraper', 'immoweb_scraper', 'Immoweb.be', 'selenium'),
    ('nextimmo_scraper', 'nextimmo_scraper', 'Nextimmo.lu', 'http'),

    # Nouveaux scrapers (27/02/2026)
    ('sigelux_scraper', 'sigelux_scraper', 'Sigelux.lu', 'http'),
    ('sothebys_scraper', 'sothebys_scraper', 'Sothebys.lu', 'http'),
    ('ldhome_scraper', 'ldhome_scraper', 'LDHome.lu', 'http'),
    ('rockenbrod_scraper', 'rockenbrod_scraper', 'Rockenbrod.lu', 'http'),
    ('propertyinvest_scraper', 'propertyinvest_scraper', 'PropertyInvest.lu', 'http'),
    ('remax_scraper', 'remax_scraper', 'REMAX.lu', 'selenium'),

    # Scrapers copiés mais potentiellement non-fonctionnels
    ('actuel_scraper_selenium', 'actuel_scraper_selenium', 'Actuel.lu', 'selenium'),
    ('apropos_scraper', 'apropos_scraper', 'Apropos.lu', 'http'),
    ('floor_scraper', 'floor_scraper', 'Floor.lu', 'selenium'),
    ('home_pass_scraper', 'home_pass_scraper', 'HomePass.lu', 'http'),
    ('immostar_scraper', 'immostar_scraper', 'ImmoStar.lu', 'http'),
    ('nexvia_scraper', 'nexvia_scraper', 'Nexvia.lu', 'http'),
]

# Champs requis dans une annonce
REQUIRED_FIELDS = ['listing_id', 'site', 'title', 'price', 'url']
OPTIONAL_FIELDS = ['city', 'rooms', 'surface', 'image_url', 'latitude', 'longitude', 'distance_km']


def test_scraper(module_name, instance_name, display_name, scraper_type, timeout=120, verbose=False):
    """
    Teste un scraper et retourne les résultats.

    Returns:
        dict: {
            'name': str,
            'status': 'ok' | 'error' | 'empty' | 'import_error',
            'count': int,
            'time': float,
            'error': str | None,
            'sample': dict | None,
            'validation': dict
        }
    """
    result = {
        'name': display_name,
        'module': module_name,
        'type': scraper_type,
        'status': 'unknown',
        'count': 0,
        'time': 0,
        'error': None,
        'sample': None,
        'validation': {
            'has_required_fields': False,
            'has_valid_price': False,
            'has_valid_url': False,
            'missing_fields': [],
        }
    }

    # 1. Test d'import
    try:
        module = __import__(f'scrapers.{module_name}', fromlist=[instance_name])
        scraper = getattr(module, instance_name, None)

        if scraper is None:
            result['status'] = 'import_error'
            result['error'] = f"Instance '{instance_name}' non trouvée dans le module"
            return result

        if not hasattr(scraper, 'scrape'):
            result['status'] = 'import_error'
            result['error'] = "Méthode scrape() non trouvée"
            return result

    except ImportError as e:
        result['status'] = 'import_error'
        result['error'] = str(e)[:100]
        return result
    except Exception as e:
        result['status'] = 'import_error'
        result['error'] = f"{type(e).__name__}: {str(e)[:80]}"
        return result

    # 2. Test d'exécution
    try:
        start_time = time.time()
        listings = scraper.scrape()
        elapsed = time.time() - start_time
        result['time'] = round(elapsed, 2)

        if listings is None:
            result['status'] = 'empty'
            result['count'] = 0
            return result

        result['count'] = len(listings)

        if len(listings) == 0:
            result['status'] = 'empty'
            return result

        # 3. Validation de la structure
        sample = listings[0]
        result['sample'] = sample

        # Vérifier les champs requis
        missing = [f for f in REQUIRED_FIELDS if f not in sample or not sample[f]]
        result['validation']['missing_fields'] = missing
        result['validation']['has_required_fields'] = len(missing) == 0

        # Vérifier le prix
        price = sample.get('price', 0)
        result['validation']['has_valid_price'] = isinstance(price, (int, float)) and price > 0

        # Vérifier l'URL
        url = sample.get('url', '')
        result['validation']['has_valid_url'] = url.startswith('http')

        # Statut final
        if result['validation']['has_required_fields'] and result['validation']['has_valid_price']:
            result['status'] = 'ok'
        else:
            result['status'] = 'warning'

        return result

    except Exception as e:
        result['status'] = 'error'
        result['error'] = f"{type(e).__name__}: {str(e)[:100]}"
        result['time'] = round(time.time() - start_time, 2) if 'start_time' in dir() else 0
        return result


def print_result(result, verbose=False):
    """Affiche le résultat d'un test de scraper."""
    name = result['name']
    status = result['status']
    count = result['count']
    elapsed = result['time']
    scraper_type = result.get('type', 'http')

    # Icône de type
    type_icon = "🌐" if scraper_type == 'http' else "🖥️"

    # Statut avec couleur
    if status == 'ok':
        status_str = color("✅ OK", Colors.GREEN)
        count_str = color(f"{count} annonces", Colors.GREEN)
    elif status == 'empty':
        status_str = color("⚠️  VIDE", Colors.YELLOW)
        count_str = color("0 annonces", Colors.YELLOW)
    elif status == 'warning':
        status_str = color("⚠️  WARN", Colors.YELLOW)
        count_str = color(f"{count} annonces", Colors.YELLOW)
    elif status == 'import_error':
        status_str = color("❌ IMPORT", Colors.RED)
        count_str = color("-", Colors.RED)
    else:
        status_str = color("❌ ERROR", Colors.RED)
        count_str = color("-", Colors.RED)

    # Ligne principale
    print(f"{type_icon} {name:<20} {status_str:<20} {count_str:<18} ({elapsed:.1f}s)")

    # Erreur si présente
    if result['error']:
        print(f"   {color('→ ' + result['error'], Colors.RED)}")

    # Champs manquants
    if result['validation']['missing_fields']:
        missing = ', '.join(result['validation']['missing_fields'])
        print(f"   {color('→ Champs manquants: ' + missing, Colors.YELLOW)}")

    # Mode verbose: afficher un exemple
    if verbose and result['sample']:
        sample = result['sample']
        print(f"   {color('Exemple:', Colors.CYAN)}")
        print(f"      Titre: {sample.get('title', 'N/A')[:50]}")
        print(f"      Prix: {sample.get('price', 'N/A')}€")
        print(f"      Ville: {sample.get('city', 'N/A')}")
        print(f"      Surface: {sample.get('surface', 'N/A')}m²")
        print(f"      URL: {sample.get('url', 'N/A')[:60]}...")


def print_summary(results):
    """Affiche le résumé des tests."""
    total = len(results)
    ok = sum(1 for r in results if r['status'] == 'ok')
    empty = sum(1 for r in results if r['status'] == 'empty')
    warning = sum(1 for r in results if r['status'] == 'warning')
    error = sum(1 for r in results if r['status'] in ('error', 'import_error'))

    total_listings = sum(r['count'] for r in results)
    total_time = sum(r['time'] for r in results)

    print(f"\n{'='*60}")
    print(color("📊 RÉSUMÉ DES TESTS", Colors.BOLD))
    print(f"{'='*60}")
    print(f"   Total scrapers testés: {total}")
    print(f"   {color('✅ Fonctionnels:', Colors.GREEN)} {ok}")
    print(f"   {color('⚠️  Vides:', Colors.YELLOW)} {empty}")
    print(f"   {color('⚠️  Warnings:', Colors.YELLOW)} {warning}")
    print(f"   {color('❌ Erreurs:', Colors.RED)} {error}")
    print(f"   📈 Total annonces: {total_listings}")
    print(f"   ⏱️  Temps total: {total_time:.1f}s")

    # Liste des scrapers fonctionnels
    working = [r['name'] for r in results if r['status'] == 'ok']
    if working:
        print(f"\n{color('Scrapers fonctionnels:', Colors.GREEN)}")
        for name in working:
            print(f"   ✅ {name}")

    # Liste des scrapers en erreur
    failed = [(r['name'], r['error']) for r in results if r['status'] in ('error', 'import_error')]
    if failed:
        print(f"\n{color('Scrapers en erreur:', Colors.RED)}")
        for name, err in failed:
            print(f"   ❌ {name}: {err[:50] if err else 'Erreur inconnue'}")


def main():
    parser = argparse.ArgumentParser(description='Test automatisé des scrapers')
    parser.add_argument('--quick', action='store_true', help='Test rapide (timeout court)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Afficher détails des annonces')
    parser.add_argument('--only', nargs='+', help='Tester seulement ces scrapers (par nom)')
    parser.add_argument('--http-only', action='store_true', help='Tester seulement les scrapers HTTP (plus rapides)')
    parser.add_argument('--selenium-only', action='store_true', help='Tester seulement les scrapers Selenium')
    parser.add_argument('--list', action='store_true', help='Lister les scrapers disponibles')

    args = parser.parse_args()

    # Lister les scrapers
    if args.list:
        print(f"\n{'='*60}")
        print("📋 SCRAPERS DISPONIBLES")
        print(f"{'='*60}")
        for module, instance, name, stype in SCRAPERS_CONFIG:
            type_icon = "🌐" if stype == 'http' else "🖥️"
            print(f"   {type_icon} {name:<20} ({module})")
        return

    # Filtrer les scrapers à tester
    scrapers_to_test = SCRAPERS_CONFIG.copy()

    if args.only:
        # Filtrer par nom (insensible à la casse)
        only_lower = [o.lower() for o in args.only]
        scrapers_to_test = [
            s for s in scrapers_to_test
            if any(o in s[2].lower() or o in s[0].lower() for o in only_lower)
        ]

    if args.http_only:
        scrapers_to_test = [s for s in scrapers_to_test if s[3] == 'http']

    if args.selenium_only:
        scrapers_to_test = [s for s in scrapers_to_test if s[3] == 'selenium']

    timeout = 60 if args.quick else 120

    # Header
    print(f"\n{'='*60}")
    print(color(f"🧪 TEST DES SCRAPERS — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BOLD))
    print(f"{'='*60}")
    print(f"   Scrapers à tester: {len(scrapers_to_test)}")
    print(f"   Mode: {'rapide' if args.quick else 'complet'}")
    print(f"   Verbose: {'oui' if args.verbose else 'non'}")
    print(f"{'='*60}\n")

    # Exécuter les tests
    results = []

    for i, (module, instance, name, stype) in enumerate(scrapers_to_test):
        # Pause entre les scrapers (éviter le rate limiting)
        if i > 0:
            time.sleep(2)

        print(f"[{i+1}/{len(scrapers_to_test)}] Test de {name}...")
        result = test_scraper(module, instance, name, stype, timeout=timeout, verbose=args.verbose)
        results.append(result)
        print_result(result, verbose=args.verbose)
        print()

    # Résumé
    print_summary(results)

    # Code de sortie
    errors = sum(1 for r in results if r['status'] in ('error', 'import_error'))
    sys.exit(1 if errors > 0 else 0)


if __name__ == '__main__':
    main()
