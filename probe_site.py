#!/usr/bin/env python3
# =============================================================================
# probe_site.py — Sonde de faisabilite scraping pour sites immobiliers LU
# =============================================================================
# Usage :
#   python probe_site.py https://www.logic-immo.lu/location-immobilier/luxembourg
#   python probe_site.py --all          → tester tous les sites de la liste
#   python probe_site.py --url URL      → tester une URL specifique
#
# Verdict :
#   FACILE   → HTTP + BeautifulSoup suffit, donnees visibles
#   MOYEN    → Headers specifiques ou JSON embarque, faisable sans Selenium
#   SELENIUM → JavaScript requis, Selenium/Playwright necessaire
#   BLOQUE   → Cloudflare, CAPTCHA ou acces refuse
# =============================================================================
import sys
import re
import time
import json
import argparse
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── Sites candidats a tester ────────────────────────────────────────────────

SITES_CANDIDATS = [
    # Portails
    ("Logic-Immo.lu",      "https://www.logic-immo.lu/location-immobilier/luxembourg.htm"),
    ("Properstar.lu",      "https://www.properstar.com/luxembourg/rent/apartment"),
    ("Lux-Residence.com",  "https://www.lux-residence.com/location"),
    # Agences
    ("ERA.lu",             "https://www.era.lu/fr/listings?transactionType=rent"),
    ("Engel-Voelkers.lu",  "https://www.engelvoelkers.com/lu/en/search/?q=&startIndex=0&businessArea=residential&weDo=tolet&subTypeName=&country=Luxembourg"),
    ("Bo-Immo.lu",         "https://www.bo-immo.lu/fr/a-louer"),
    ("LaCasa.lu",          "https://www.lacasa.lu/fr/annonces/location"),
    ("Immo365.lu",         "https://www.immo365.lu/location"),
    ("EasyFlat.lu",        "https://www.easyflat.lu/en/apartments"),
    # Deja evalues — ne pas retester
    # Century21.lu    → COMPLEXE (JS, authentification)
    # VIVI.lu         → deja scrape
    # Athome.lu       → deja scrape
]

# ─── Headers navigateur realiste ─────────────────────────────────────────────

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-LU,fr;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0',
}


def make_session():
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.mount('http://',  HTTPAdapter(max_retries=retry))
    session.headers.update(HEADERS)
    return session


# ─── Detections ───────────────────────────────────────────────────────────────

def detect_cloudflare(resp):
    """Detecter un challenge Cloudflare"""
    cf_headers = any(h in resp.headers for h in ['cf-ray', 'cf-cache-status', 'CF-Ray'])
    challenge   = any(k in resp.text for k in [
        'Checking your browser', 'cf-browser-verification',
        'challenge-platform', '__cf_chl', 'cloudflare',
        'jschl_vc', 'Just a moment'
    ])
    return cf_headers and challenge or (resp.status_code in (403, 429, 503) and challenge)


def detect_captcha(text):
    """Detecter un CAPTCHA"""
    return any(k in text.lower() for k in [
        'recaptcha', 'hcaptcha', 'g-recaptcha', 'data-sitekey',
        'captcha', 'robot', 'are you human'
    ])


def detect_framework(text):
    """Detecter le framework JS utilise"""
    frameworks = []
    if '__NEXT_DATA__'      in text: frameworks.append('Next.js')
    if '__NUXT__'           in text: frameworks.append('Nuxt.js')
    if 'react'              in text.lower() and 'root' in text: frameworks.append('React')
    if 'vue'                in text.lower(): frameworks.append('Vue')
    if 'angular'            in text.lower(): frameworks.append('Angular')
    if '__INITIAL_STATE__'  in text: frameworks.append('Redux/SSR')
    if 'window.__data'      in text: frameworks.append('SSR-data')
    return frameworks


def detect_json_embedded(text):
    """Detecter JSON embarque exploitable"""
    patterns = {
        '__NEXT_DATA__':     r'<script id="__NEXT_DATA__"[^>]*>({.{50,}})</script>',
        '__INITIAL_STATE__': r'__INITIAL_STATE__\s*=\s*({.{50,}});',
        'window.__data':     r'window\.__data\s*=\s*({.{50,}});',
        'window.props':      r'window\.props\s*=\s*({.{50,}});',
        'dataLayer':         r'dataLayer\.push\(({.{50,}})\)',
    }
    found = []
    for name, pattern in patterns.items():
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                found.append((name, data))
            except Exception:
                found.append((name, None))  # JSON invalide mais present
    return found


def extract_prices(text):
    """Extraire les prix (€) visibles dans le HTML"""
    prices = re.findall(r'(\d[\d\s\u202f\xa0]*)\s*[€$]', text)
    valid = []
    for p in prices:
        try:
            val = int(re.sub(r'\s', '', p))
            if 300 <= val <= 15000:
                valid.append(val)
        except ValueError:
            continue
    return sorted(set(valid))[:10]


def extract_listing_links(text, base_url):
    """Extraire les liens d'annonces depuis le HTML"""
    domain = urlparse(base_url).netloc
    # Patterns typiques pour les liens d'annonces immobilieres
    patterns = [
        r'href="(/[^"]*(?:location|louer|rent|annonce|listing|bien|property|appartement)[^"]*)"',
        r'href="(https?://' + re.escape(domain) + r'/[^"]*(?:location|rent|annonce|listing)[^"]*)"',
    ]
    links = set()
    for p in patterns:
        for m in re.findall(p, text, re.IGNORECASE):
            if len(m) > 10 and not m.endswith(('.css', '.js', '.png', '.jpg')):
                links.add(m)
    return list(links)[:5]


def count_keywords(text):
    """Compter les mots-cles immobiliers dans le HTML"""
    keywords = {
        'prix_eur':  len(re.findall(r'\d+\s*€', text)),
        'chambre':   len(re.findall(r'chambre|bedroom|Zimmer', text, re.I)),
        'surface':   len(re.findall(r'\d+\s*m[²2]', text)),
        'louer':     len(re.findall(r'louer|location|rent|mieten', text, re.I)),
        'annonce':   len(re.findall(r'annonce|listing|property|bien', text, re.I)),
    }
    return keywords


def is_spa_empty(text, kw):
    """Determiner si la page est un SPA sans contenu (JS requis)"""
    content_size = len(text)
    has_content  = any(v > 2 for v in kw.values())
    has_root_div = bool(re.search(r'<div\s+id=["\'](?:app|root|__nuxt)["\']', text))
    return has_root_div and not has_content and content_size < 30000


# ─── Verdict ─────────────────────────────────────────────────────────────────

def compute_verdict(status, is_cf, is_captcha, kw, frameworks, json_found, is_spa, prices):
    """Calculer le verdict final"""

    if status in (403, 429) or is_cf:
        return 'BLOQUE', '⛔'
    if status == 404:
        return 'INTROUVABLE', '❓'
    if status >= 500:
        return 'ERREUR SERVEUR', '❌'
    if is_captcha:
        return 'BLOQUE (CAPTCHA)', '⛔'
    if is_spa:
        return 'SELENIUM', '🔴'
    if prices and kw.get('prix_eur', 0) > 3:
        if json_found:
            return 'FACILE (JSON)', '🟢'
        return 'FACILE (HTML)', '🟢'
    if json_found:
        return 'MOYEN (JSON embarque)', '🟡'
    if frameworks and not prices:
        return 'SELENIUM', '🔴'
    if kw.get('louer', 0) > 5 or kw.get('annonce', 0) > 5:
        return 'MOYEN', '🟡'
    return 'INCERTAIN', '❓'


# ─── Probe principal ──────────────────────────────────────────────────────────

def probe(site_name, url, session, verbose=False):
    """Analyser un site et retourner un rapport"""
    print(f"\n{'─'*60}")
    print(f"  🔍 {site_name}")
    print(f"     {url}")
    print(f"{'─'*60}")

    result = {
        'site': site_name,
        'url':  url,
        'status': None,
        'verdict': 'ERREUR',
        'emoji':   '❌',
    }

    try:
        t0   = time.time()
        resp = session.get(url, timeout=20, allow_redirects=True)
        elapsed = round(time.time() - t0, 1)

        status     = resp.status_code
        final_url  = resp.url
        text       = resp.text
        size_kb    = round(len(text) / 1024, 1)

        result['status'] = status

        print(f"  HTTP {status} | {size_kb} KB | {elapsed}s")
        if final_url != url:
            print(f"  Redirige → {final_url}")

        # Detections
        is_cf      = detect_cloudflare(resp)
        is_captcha = detect_captcha(text)
        frameworks = detect_framework(text)
        json_found = detect_json_embedded(text)
        kw         = count_keywords(text)
        prices     = extract_prices(text)
        links      = extract_listing_links(text, url)
        is_spa     = is_spa_empty(text, kw)

        # Affichage detections
        if is_cf:      print(f"  ⛔ Cloudflare detecte")
        if is_captcha: print(f"  ⛔ CAPTCHA detecte")
        if is_spa:     print(f"  🔴 SPA vide (JS requis)")
        if frameworks: print(f"  🔧 Framework : {', '.join(frameworks)}")
        if json_found: print(f"  📦 JSON embarque : {', '.join(n for n,_ in json_found)}")

        print(f"  📊 Mots-cles : €={kw['prix_eur']} ch={kw['chambre']} m²={kw['surface']} location={kw['louer']}")

        if prices:
            print(f"  💰 Prix trouves : {prices[:5]}")
        if links:
            print(f"  🔗 Liens annonces ({len(links)}) : {links[0][:80]}")

        # Verdict
        verdict, emoji = compute_verdict(
            status, is_cf, is_captcha, kw, frameworks, json_found, is_spa, prices
        )
        result.update({'verdict': verdict, 'emoji': emoji,
                       'frameworks': frameworks, 'json': [n for n,_ in json_found],
                       'prices': prices, 'links': links, 'keywords': kw})

        print(f"\n  {emoji} VERDICT : {verdict}")

        # Recommandation
        reco = {
            'FACILE (JSON)':       '→ requests + json.loads()  — scraper HTTP simple',
            'FACILE (HTML)':       '→ requests + BeautifulSoup — scraper HTTP simple',
            'MOYEN (JSON embarque)':'→ requests + extraction regex JSON embarque',
            'MOYEN':               '→ requests avec headers + BeautifulSoup',
            'SELENIUM':            '→ Selenium Firefox headless requis',
            'BLOQUE':              '→ Cloudflare / 403 — contournement difficile',
            'BLOQUE (CAPTCHA)':    '→ CAPTCHA — contournement tres difficile',
            'INTROUVABLE':         '→ URL incorrecte ou page inexistante',
            'ERREUR SERVEUR':      '→ Serveur en erreur, reessayer plus tard',
            'INCERTAIN':           '→ Analyser manuellement le site',
        }
        print(f"  {reco.get(verdict, '')}")

    except requests.exceptions.ConnectionError:
        print(f"  ❌ Connexion impossible (site hors ligne ou URL invalide)")
        result['verdict'] = 'HORS LIGNE'
        result['emoji']   = '❌'
    except requests.exceptions.Timeout:
        print(f"  ❌ Timeout (>20s)")
        result['verdict'] = 'TIMEOUT'
        result['emoji']   = '❌'
    except Exception as e:
        print(f"  ❌ Erreur : {str(e)[:80]}")

    return result


# ─── Rapport final ────────────────────────────────────────────────────────────

def print_summary(results):
    """Afficher le tableau recapitulatif"""
    print(f"\n\n{'='*70}")
    print(f"  RAPPORT FINAL — {len(results)} sites testes")
    print(f"{'='*70}")
    print(f"  {'Site':<22} {'Verdict':<30} {'Framework'}")
    print(f"  {'─'*22} {'─'*30} {'─'*20}")
    for r in results:
        fw  = ', '.join(r.get('frameworks', [])) or '—'
        print(f"  {r['site']:<22} {r['emoji']} {r['verdict']:<27} {fw}")

    # Grouper par verdict
    facile   = [r for r in results if 'FACILE'   in r['verdict']]
    moyen    = [r for r in results if 'MOYEN'    in r['verdict']]
    selenium = [r for r in results if 'SELENIUM' in r['verdict']]
    bloque   = [r for r in results if 'BLOQUE'   in r['verdict'] or r['verdict'] in ('HORS LIGNE','TIMEOUT')]

    print(f"\n  🟢 Facile  ({len(facile)})  : {', '.join(r['site'] for r in facile) or 'aucun'}")
    print(f"  🟡 Moyen   ({len(moyen)})  : {', '.join(r['site'] for r in moyen) or 'aucun'}")
    print(f"  🔴 Selenium({len(selenium)}): {', '.join(r['site'] for r in selenium) or 'aucun'}")
    print(f"  ⛔ Bloque  ({len(bloque)}) : {', '.join(r['site'] for r in bloque) or 'aucun'}")
    print(f"{'='*70}\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Sonde de faisabilite scraping — sites immobiliers Luxembourg',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python probe_site.py --all
  python probe_site.py --url https://www.logic-immo.lu/location-immobilier/luxembourg.htm
  python probe_site.py --url https://www.era.lu/fr/listings?transactionType=rent
        """
    )
    parser.add_argument('--all', action='store_true',
                        help='Tester tous les sites de la liste')
    parser.add_argument('--url', type=str, default=None,
                        help='Tester une URL specifique')
    parser.add_argument('url_positional', nargs='?',
                        help='URL a tester (argument positionnel)')
    args = parser.parse_args()

    session = make_session()

    if args.all:
        print(f"\n🔍 Test de {len(SITES_CANDIDATS)} sites candidats...\n")
        results = []
        for i, (name, url) in enumerate(SITES_CANDIDATS, 1):
            results.append(probe(name, url, session))
            if i < len(SITES_CANDIDATS):
                time.sleep(2)  # delai poli entre requetes
        print_summary(results)

    elif args.url or args.url_positional:
        url = args.url or args.url_positional
        name = urlparse(url).netloc.replace('www.', '')
        probe(name, url, session)

    else:
        parser.print_help()
        print(f"\nSites preconfigures ({len(SITES_CANDIDATS)}) :")
        for name, url in SITES_CANDIDATS:
            print(f"  {name:<22} {url}")


if __name__ == '__main__':
    main()
