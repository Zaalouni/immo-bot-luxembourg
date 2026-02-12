#!/usr/bin/env python3
"""
Diagnostic rapide — teste chaque site et affiche la structure HTML/JSON
Usage: python diagnostic.py
"""
import requests
import re
import json

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'

def test_site(name, url, headers=None):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"URL:  {url}")
    print(f"{'='*60}")

    if not headers:
        headers = {'User-Agent': UA, 'Accept': 'text/html,application/json'}

    try:
        r = requests.get(url, headers=headers, timeout=15)
        print(f"  HTTP: {r.status_code}")
        print(f"  Taille: {len(r.text)} caractères")
        print(f"  Content-Type: {r.headers.get('Content-Type', '???')}")

        if r.status_code != 200:
            print(f"  ❌ ERREUR HTTP {r.status_code}")
            # Afficher les 500 premiers caractères pour debug
            print(f"  Body: {r.text[:500]}")
            return

        text = r.text

        # Chercher JSON embarqué
        if '__NEXT_DATA__' in text:
            print(f"  ✅ __NEXT_DATA__ trouvé!")
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                print(f"     Clés: {list(data.keys())}")
                props = data.get('props', {}).get('pageProps', {})
                print(f"     pageProps clés: {list(props.keys())[:10]}")

        if 'window.__INITIAL_STATE__' in text:
            print(f"  ✅ window.__INITIAL_STATE__ trouvé!")

        if 'window.classified' in text:
            print(f"  ✅ window.classified trouvé!")

        # Chercher les balises article
        articles = re.findall(r'<article[^>]*class="([^"]*)"', text)
        if articles:
            print(f"  📦 Articles trouvés: {len(articles)}")
            for cls in set(articles[:5]):
                print(f"     class=\"{cls}\"")

        # Chercher les cartes
        cards = re.findall(r'class="([^"]*(?:card|listing|property|result)[^"]*)"', text, re.I)
        if cards:
            unique = list(set(cards))[:10]
            print(f"  🃏 Classes card/listing/property: {len(cards)} ({len(unique)} uniques)")
            for cls in unique:
                print(f"     .{cls}")

        # Chercher les prix
        prices = re.findall(r'([\d\s\.]+)\s*€', text)
        if prices:
            print(f"  💰 Prix trouvés: {len(prices)}")
            for p in prices[:5]:
                print(f"     {p.strip()}€")

        # Chercher les liens d'annonces
        links = re.findall(r'href="(/[^"]*(?:detail|classified|property|annonce|listing)[^"]*)"', text, re.I)
        if links:
            unique_links = list(set(links))[:5]
            print(f"  🔗 Liens annonces: {len(links)} ({len(set(links))} uniques)")
            for l in unique_links:
                print(f"     {l}")

        # Chercher images
        imgs = re.findall(r'<img[^>]*src="(https?://[^"]+)"', text)
        if imgs:
            print(f"  🖼️ Images: {len(imgs)}")
            for img in imgs[:3]:
                print(f"     {img[:100]}")

        # Si rien trouvé, afficher un extrait
        if not articles and not cards and not prices:
            print(f"  ⚠️ Rien détecté! Premiers 1000 caractères:")
            print(f"  {text[:1000]}")

    except Exception as e:
        print(f"  ❌ ERREUR: {e}")


def test_nextimmo_api():
    print(f"\n{'='*60}")
    print(f"TEST: Nextimmo.lu API JSON")
    print(f"{'='*60}")

    try:
        r = requests.get('https://nextimmo.lu/api/v2/properties',
                         params={'country': 1, 'type': 1, 'category': 2, 'page': 1},
                         headers={'User-Agent': UA, 'Accept': 'application/json',
                                  'Referer': 'https://nextimmo.lu/en/rent/apartment/luxembourg-country'},
                         timeout=15)
        print(f"  HTTP: {r.status_code}")

        if r.status_code == 200:
            data = r.json()
            print(f"  Clés racine: {list(data.keys())}")
            items = data.get('data', [])
            print(f"  Annonces: {len(items)}")

            if items:
                item = items[0]
                print(f"  Premier item clés: {list(item.keys())}")
                print(f"  Premier item (résumé):")
                print(f"     id: {item.get('id')}")
                print(f"     price: {item.get('price')}")
                print(f"     area: {item.get('area')}")
                print(f"     bedrooms: {item.get('bedrooms')}")
                print(f"     rooms: {item.get('rooms')}")
                print(f"     city: {item.get('city')}")
                print(f"     title: {str(item.get('title', ''))[:80]}")
                print(f"     pictures: {item.get('pictures')}")
                print(f"     latitude: {item.get('latitude')}")
        else:
            print(f"  ❌ {r.text[:500]}")
    except Exception as e:
        print(f"  ❌ ERREUR: {e}")


if __name__ == '__main__':
    # Sites HTTP
    test_site("Athome.lu", "https://www.athome.lu/en/srp/?tr=rent&q=faee1a4a&loc=L2-luxembourg&ptypes=apartment&pmin=1000&pmax=2800")
    test_site("Immotop.lu", "https://www.immotop.lu/en/search-rent.html?rubric=apartment")
    test_site("Luxhome.lu", "https://www.luxhome.lu/en/rent/apartment")
    test_site("Wortimmo.lu", "https://www.wortimmo.lu/en/rent")
    test_site("Nextimmo.lu HTML", "https://nextimmo.lu/en/rent/apartment/luxembourg-country")
    test_nextimmo_api()

    # Immoweb (HTTP - probablement 403)
    test_site("Immoweb.be", "https://www.immoweb.be/en/search/apartment/for-rent?countries=LU&orderBy=newest")

    print(f"\n{'='*60}")
    print("TERMINÉ — copie le résultat complet ici")
    print(f"{'='*60}")
