#!/usr/bin/env python3
# =============================================================================
# debug_broken_scrapers.py — Diagnostic des scrapers non-fonctionnels
# =============================================================================
# Analyse détaillée des scrapers qui retournent 0 résultats pour identifier
# la cause et proposer des solutions.
#
# Usage:
#   python debug_broken_scrapers.py              # Tester tous
#   python debug_broken_scrapers.py --only luxhome unicorn  # Tester certains
#   python debug_broken_scrapers.py --save       # Sauvegarder les pages HTML
# =============================================================================

import sys
import time
import argparse
import requests
import re
import os
from datetime import datetime
from urllib.parse import urlparse

# Couleurs terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'

def color(text, col):
    return f"{col}{text}{Colors.END}"

# Configuration des scrapers à diagnostiquer
BROKEN_SCRAPERS = {
    'luxhome': {
        'name': 'Luxhome.lu',
        'module': 'luxhome_scraper',
        'instance': 'luxhome_scraper',
        'url': 'https://www.luxhome.lu/recherche/?status%5B%5D=location',
        'type': 'http',
        'issue': 'Erreur DNS/connexion',
    },
    'unicorn': {
        'name': 'Unicorn.lu',
        'module': 'unicorn_scraper_real',
        'instance': 'unicorn_scraper_real',
        'url': 'https://www.unicorn.lu/fr/louer',
        'type': 'selenium',
        'issue': 'CAPTCHA / 0 résultats',
    },
    'wortimmo': {
        'name': 'Wortimmo.lu',
        'module': 'wortimmo_scraper',
        'instance': 'wortimmo_scraper',
        'url': 'https://www.wortimmo.lu/fr/louer',
        'type': 'selenium',
        'issue': 'Cloudflare / 0 résultats',
    },
    'immoweb': {
        'name': 'Immoweb.be',
        'module': 'immoweb_scraper',
        'instance': 'immoweb_scraper',
        'url': 'https://www.immoweb.be/fr/recherche/appartement/a-louer/luxembourg/province',
        'type': 'selenium',
        'issue': 'CAPTCHA / 0 résultats',
    },
    'actuel': {
        'name': 'Actuel.lu',
        'module': 'actuel_scraper_selenium',
        'instance': 'actuel_scraper_selenium',
        'url': 'https://www.actuel.lu/fr/louer',
        'type': 'selenium',
        'issue': '0 résultats',
    },
    'apropos': {
        'name': 'Apropos.lu',
        'module': 'apropos_scraper',
        'instance': 'apropos_scraper',
        'url': 'https://www.apropos.lu/fr/louer',
        'type': 'http',
        'issue': '0 résultats',
    },
    'floor': {
        'name': 'Floor.lu',
        'module': 'floor_scraper',
        'instance': 'floor_scraper',
        'url': 'https://www.floor.lu/fr/louer',
        'type': 'selenium',
        'issue': '0 résultats',
    },
    'homepass': {
        'name': 'HomePass.lu',
        'module': 'home_pass_scraper',
        'instance': 'home_pass_scraper',
        'url': 'https://www.home-pass.lu/location',
        'type': 'http',
        'issue': '0 résultats',
    },
    'immostar': {
        'name': 'ImmoStar.lu',
        'module': 'immostar_scraper',
        'instance': 'immostar_scraper',
        'url': 'https://www.immostar.lu/fr/louer',
        'type': 'http',
        'issue': 'Erreur geocode_city',
    },
    'nexvia': {
        'name': 'Nexvia.lu',
        'module': 'nexvia_scraper',
        'instance': 'nexvia_scraper',
        'url': 'https://www.nexvia.lu/fr/location',
        'type': 'http',
        'issue': '0 résultats',
    },
}

# Headers pour les requêtes HTTP
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


def check_dns(url):
    """Vérifie si le domaine est résolvable."""
    import socket
    try:
        domain = urlparse(url).netloc
        socket.gethostbyname(domain)
        return True, None
    except socket.gaierror as e:
        return False, str(e)


def check_http_access(url, timeout=15):
    """Vérifie l'accès HTTP basique au site."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return {
            'accessible': True,
            'status_code': response.status_code,
            'content_length': len(response.content),
            'final_url': response.url,
            'redirected': response.url != url,
            'content_type': response.headers.get('Content-Type', ''),
            'server': response.headers.get('Server', 'Unknown'),
            'html': response.text[:50000],  # Garder les premiers 50KB
        }
    except requests.exceptions.SSLError as e:
        return {'accessible': False, 'error': f'SSL Error: {str(e)[:100]}'}
    except requests.exceptions.ConnectionError as e:
        return {'accessible': False, 'error': f'Connection Error: {str(e)[:100]}'}
    except requests.exceptions.Timeout:
        return {'accessible': False, 'error': 'Timeout'}
    except Exception as e:
        return {'accessible': False, 'error': f'{type(e).__name__}: {str(e)[:100]}'}


def detect_protection(html):
    """Détecte les protections anti-bot dans le HTML."""
    protections = []
    html_lower = html.lower()

    # Cloudflare
    if 'cloudflare' in html_lower or 'cf-ray' in html_lower or 'cf_clearance' in html_lower:
        protections.append('Cloudflare')
    if 'checking your browser' in html_lower:
        protections.append('Cloudflare Browser Check')
    if 'challenge-platform' in html_lower:
        protections.append('Cloudflare Challenge')

    # CAPTCHA
    if 'captcha' in html_lower or 'recaptcha' in html_lower:
        protections.append('CAPTCHA')
    if 'g-recaptcha' in html_lower:
        protections.append('Google reCAPTCHA')
    if 'hcaptcha' in html_lower:
        protections.append('hCaptcha')

    # Autres protections
    if 'access denied' in html_lower:
        protections.append('Access Denied')
    if 'bot detection' in html_lower or 'bot-detection' in html_lower:
        protections.append('Bot Detection')
    if 'please enable javascript' in html_lower:
        protections.append('JavaScript Required')
    if 'rate limit' in html_lower or 'too many requests' in html_lower:
        protections.append('Rate Limiting')

    return protections


def detect_listings_in_html(html):
    """Cherche des patterns d'annonces dans le HTML."""
    patterns = {
        'price_patterns': [
            r'(\d{1,3}[.,]?\d{3})\s*€',
            r'€\s*(\d{1,3}[.,]?\d{3})',
            r'(\d{1,3}[.,]?\d{3})\s*EUR',
            r'price["\']?\s*[:=]\s*["\']?(\d+)',
        ],
        'room_patterns': [
            r'(\d+)\s*chambre',
            r'(\d+)\s*ch\b',
            r'(\d+)\s*bedroom',
            r'rooms?["\']?\s*[:=]\s*["\']?(\d+)',
        ],
        'surface_patterns': [
            r'(\d+)\s*m[²2]',
            r'(\d+)\s*sqm',
            r'surface["\']?\s*[:=]\s*["\']?(\d+)',
        ],
        'listing_indicators': [
            r'class=["\'][^"\']*listing[^"\']*["\']',
            r'class=["\'][^"\']*property[^"\']*["\']',
            r'class=["\'][^"\']*annonce[^"\']*["\']',
            r'class=["\'][^"\']*bien[^"\']*["\']',
            r'class=["\'][^"\']*card[^"\']*["\']',
            r'data-listing',
            r'data-property',
        ],
    }

    results = {}
    for pattern_type, patterns_list in patterns.items():
        count = 0
        for pattern in patterns_list:
            matches = re.findall(pattern, html, re.IGNORECASE)
            count += len(matches)
        results[pattern_type] = count

    return results


def test_scraper_import(module_name, instance_name):
    """Teste l'import du scraper."""
    try:
        module = __import__(f'scrapers.{module_name}', fromlist=[instance_name])
        scraper = getattr(module, instance_name, None)
        if scraper is None:
            return False, f"Instance '{instance_name}' non trouvée"
        if not hasattr(scraper, 'scrape'):
            return False, "Méthode scrape() non trouvée"
        return True, scraper
    except ImportError as e:
        return False, f"ImportError: {str(e)[:100]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:100]}"


def test_scraper_execution(scraper, timeout=120):
    """Teste l'exécution du scraper."""
    try:
        start = time.time()
        results = scraper.scrape()
        elapsed = time.time() - start

        if results is None:
            return {'success': False, 'count': 0, 'time': elapsed, 'error': 'Returned None'}

        return {
            'success': len(results) > 0,
            'count': len(results),
            'time': elapsed,
            'sample': results[0] if results else None,
            'error': None
        }
    except Exception as e:
        return {
            'success': False,
            'count': 0,
            'time': time.time() - start if 'start' in dir() else 0,
            'error': f"{type(e).__name__}: {str(e)[:200]}"
        }


def diagnose_scraper(key, config, save_html=False):
    """Diagnostic complet d'un scraper."""
    print(f"\n{'='*70}")
    print(color(f"🔍 DIAGNOSTIC: {config['name']}", Colors.BOLD))
    print(f"{'='*70}")
    print(f"   URL: {config['url']}")
    print(f"   Type: {config['type']}")
    print(f"   Problème connu: {config['issue']}")
    print()

    diagnosis = {
        'name': config['name'],
        'dns_ok': False,
        'http_ok': False,
        'import_ok': False,
        'scraper_ok': False,
        'protections': [],
        'recommendations': [],
    }

    # 1. Test DNS
    print(color("1. Test DNS...", Colors.CYAN))
    dns_ok, dns_error = check_dns(config['url'])
    diagnosis['dns_ok'] = dns_ok
    if dns_ok:
        print(f"   {color('✅ DNS OK', Colors.GREEN)}")
    else:
        print(f"   {color('❌ DNS FAILED', Colors.RED)}: {dns_error}")
        diagnosis['recommendations'].append("Vérifier si le domaine existe encore ou a changé")
        return diagnosis

    # 2. Test HTTP
    print(color("2. Test HTTP...", Colors.CYAN))
    http_result = check_http_access(config['url'])

    if http_result.get('accessible'):
        diagnosis['http_ok'] = True
        print(f"   {color('✅ HTTP OK', Colors.GREEN)}")
        print(f"      Status: {http_result['status_code']}")
        print(f"      Taille: {http_result['content_length']} bytes")
        print(f"      Serveur: {http_result['server']}")
        if http_result['redirected']:
            print(f"      Redirigé vers: {http_result['final_url']}")

        # Détecter les protections
        protections = detect_protection(http_result['html'])
        diagnosis['protections'] = protections
        if protections:
            print(f"   {color('⚠️  Protections détectées:', Colors.YELLOW)} {', '.join(protections)}")

        # Chercher des annonces dans le HTML
        listings_found = detect_listings_in_html(http_result['html'])
        print(f"   {color('📊 Patterns trouvés dans HTML:', Colors.BLUE)}")
        print(f"      Prix: {listings_found['price_patterns']}")
        print(f"      Chambres: {listings_found['room_patterns']}")
        print(f"      Surface: {listings_found['surface_patterns']}")
        print(f"      Indicateurs listing: {listings_found['listing_indicators']}")

        # Sauvegarder le HTML si demandé
        if save_html:
            debug_dir = 'debug_html'
            os.makedirs(debug_dir, exist_ok=True)
            filename = f"{debug_dir}/{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(http_result['html'])
            print(f"   {color('💾 HTML sauvegardé:', Colors.MAGENTA)} {filename}")

        # Recommandations basées sur les protections
        if 'Cloudflare' in protections or 'Cloudflare Challenge' in protections:
            diagnosis['recommendations'].append("Utiliser Selenium avec undetected-chromedriver")
            diagnosis['recommendations'].append("Ajouter des délais aléatoires entre requêtes")
            diagnosis['recommendations'].append("Utiliser cloudscraper au lieu de requests")
        if 'CAPTCHA' in protections or 'Google reCAPTCHA' in protections:
            diagnosis['recommendations'].append("CAPTCHA détecté - scraping difficile")
            diagnosis['recommendations'].append("Essayer avec Selenium + délais longs")
            diagnosis['recommendations'].append("Considérer un service de résolution CAPTCHA")
        if 'JavaScript Required' in protections:
            diagnosis['recommendations'].append("Passer de HTTP à Selenium (JavaScript requis)")
        if listings_found['listing_indicators'] == 0:
            diagnosis['recommendations'].append("Les sélecteurs CSS peuvent avoir changé")
            diagnosis['recommendations'].append("Analyser le HTML sauvegardé pour trouver les nouveaux sélecteurs")
    else:
        print(f"   {color('❌ HTTP FAILED', Colors.RED)}: {http_result.get('error')}")
        diagnosis['recommendations'].append("Site inaccessible - vérifier l'URL")
        return diagnosis

    # 3. Test Import
    print(color("3. Test Import scraper...", Colors.CYAN))
    import_ok, scraper_or_error = test_scraper_import(config['module'], config['instance'])
    diagnosis['import_ok'] = import_ok

    if import_ok:
        print(f"   {color('✅ Import OK', Colors.GREEN)}")
        scraper = scraper_or_error
    else:
        print(f"   {color('❌ Import FAILED', Colors.RED)}: {scraper_or_error}")
        diagnosis['recommendations'].append(f"Corriger l'erreur d'import: {scraper_or_error}")
        return diagnosis

    # 4. Test Exécution
    print(color("4. Test Exécution scraper...", Colors.CYAN))
    exec_result = test_scraper_execution(scraper)
    diagnosis['scraper_ok'] = exec_result['success']

    if exec_result['success']:
        print(f"   {color('✅ Scraper OK', Colors.GREEN)}")
        print(f"      Annonces: {exec_result['count']}")
        print(f"      Temps: {exec_result['time']:.1f}s")
        if exec_result['sample']:
            print(f"      Exemple: {exec_result['sample'].get('title', 'N/A')[:50]}")
    else:
        print(f"   {color('❌ Scraper FAILED', Colors.RED)}")
        print(f"      Annonces: {exec_result['count']}")
        print(f"      Temps: {exec_result['time']:.1f}s")
        if exec_result['error']:
            print(f"      Erreur: {exec_result['error']}")

            # Recommandations basées sur l'erreur
            if 'geocode_city' in exec_result['error']:
                diagnosis['recommendations'].append("Corriger la gestion de geocode_city() quand elle retourne None")
            if 'NoneType' in exec_result['error']:
                diagnosis['recommendations'].append("Ajouter des vérifications None dans le code")
            if 'timeout' in exec_result['error'].lower():
                diagnosis['recommendations'].append("Augmenter le timeout Selenium")

    # Résumé
    print(color("\n📋 RÉSUMÉ:", Colors.BOLD))
    print(f"   DNS: {'✅' if diagnosis['dns_ok'] else '❌'}")
    print(f"   HTTP: {'✅' if diagnosis['http_ok'] else '❌'}")
    print(f"   Import: {'✅' if diagnosis['import_ok'] else '❌'}")
    print(f"   Scraper: {'✅' if diagnosis['scraper_ok'] else '❌'}")

    if diagnosis['recommendations']:
        print(color("\n💡 RECOMMANDATIONS:", Colors.YELLOW))
        for i, rec in enumerate(diagnosis['recommendations'], 1):
            print(f"   {i}. {rec}")

    return diagnosis


def main():
    parser = argparse.ArgumentParser(description='Diagnostic des scrapers non-fonctionnels')
    parser.add_argument('--only', nargs='+', help='Tester seulement ces scrapers')
    parser.add_argument('--save', action='store_true', help='Sauvegarder les pages HTML')
    parser.add_argument('--list', action='store_true', help='Lister les scrapers à diagnostiquer')

    args = parser.parse_args()

    if args.list:
        print(f"\n{'='*60}")
        print("📋 SCRAPERS NON-FONCTIONNELS À DIAGNOSTIQUER")
        print(f"{'='*60}")
        for key, config in BROKEN_SCRAPERS.items():
            print(f"   {key:<12} {config['name']:<20} ({config['issue']})")
        return

    # Filtrer les scrapers à tester
    scrapers_to_test = BROKEN_SCRAPERS
    if args.only:
        only_lower = [o.lower() for o in args.only]
        scrapers_to_test = {k: v for k, v in BROKEN_SCRAPERS.items()
                           if any(o in k.lower() or o in v['name'].lower() for o in only_lower)}

    print(f"\n{'='*70}")
    print(color(f"🔧 DIAGNOSTIC SCRAPERS NON-FONCTIONNELS", Colors.BOLD))
    print(f"{'='*70}")
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Scrapers à analyser: {len(scrapers_to_test)}")
    print(f"   Sauvegarder HTML: {'Oui' if args.save else 'Non'}")

    # Exécuter les diagnostics
    results = {}
    for key, config in scrapers_to_test.items():
        results[key] = diagnose_scraper(key, config, save_html=args.save)
        time.sleep(2)  # Pause entre les tests

    # Résumé final
    print(f"\n{'='*70}")
    print(color("📊 RÉSUMÉ FINAL", Colors.BOLD))
    print(f"{'='*70}")

    working = [k for k, v in results.items() if v['scraper_ok']]
    fixable = [k for k, v in results.items() if v['http_ok'] and not v['scraper_ok']]
    blocked = [k for k, v in results.items() if not v['http_ok']]

    print(f"\n{color('✅ Fonctionnels:', Colors.GREEN)} {len(working)}")
    for k in working:
        print(f"   - {BROKEN_SCRAPERS[k]['name']}")

    print(f"\n{color('🔧 Réparables (HTTP OK mais scraper KO):', Colors.YELLOW)} {len(fixable)}")
    for k in fixable:
        print(f"   - {BROKEN_SCRAPERS[k]['name']}")
        for rec in results[k]['recommendations'][:2]:
            print(f"     → {rec}")

    print(f"\n{color('❌ Bloqués (HTTP KO):', Colors.RED)} {len(blocked)}")
    for k in blocked:
        print(f"   - {BROKEN_SCRAPERS[k]['name']}")
        if results[k]['protections']:
            print(f"     → Protections: {', '.join(results[k]['protections'])}")


if __name__ == '__main__':
    main()
