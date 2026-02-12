#!/usr/bin/env python3
"""
Diagnostic V2 — teste les VRAIES URLs des scrapers
Usage: python diagnostic_v2.py
"""
import requests
import re
import json

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
H = {'User-Agent': UA}

def sep(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ============================================================
# 1. ATHOME.LU — window.__INITIAL_STATE__
# ============================================================
sep("1. ATHOME.LU")
try:
    url = "https://www.athome.lu/en/srp/?tr=rent&q=faee1a4a&loc=L2-luxembourg&ptypes=apartment&pmin=1000&pmax=2800"
    r = requests.get(url, headers=H, timeout=15)
    print(f"  HTTP: {r.status_code}, Taille: {len(r.text)}")
    if r.status_code == 200:
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*</script>', r.text, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            # Trouver les annonces
            results = None
            for key in data:
                val = data[key]
                if isinstance(val, dict):
                    for k2 in val:
                        if isinstance(val[k2], list) and len(val[k2]) > 0:
                            if isinstance(val[k2][0], dict) and 'id' in val[k2][0]:
                                results = val[k2]
                                print(f"  Trouvé dans data['{key}']['{k2}']: {len(results)} items")
                                break
                if results:
                    break

            if not results:
                # Chercher autrement
                print(f"  Clés racine: {list(data.keys())[:15]}")
                for key in data:
                    v = data[key]
                    if isinstance(v, dict):
                        print(f"    data['{key}'] clés: {list(v.keys())[:10]}")
            else:
                item = results[0]
                print(f"  Premier item clés: {list(item.keys())}")
                print(f"    id: {item.get('id')}")
                print(f"    price: {item.get('price')}")
                print(f"    title: {str(item.get('title',''))[:80]}")
                print(f"    rooms: {item.get('rooms')}")
                print(f"    bedroom_count: {item.get('bedroom_count')}")
                print(f"    surface: {item.get('surface')}")
                print(f"    city: {item.get('city')}")
                print(f"    photos: {str(item.get('photos',''))[:100]}")
        else:
            print("  ❌ __INITIAL_STATE__ non trouvé!")
except Exception as e:
    print(f"  ❌ ERREUR: {e}")

# ============================================================
# 2. IMMOTOP.LU — regex HTML
# ============================================================
sep("2. IMMOTOP.LU")
try:
    url = "https://www.immotop.lu/location-maisons-appartements/luxembourg-pays/?criterio=rilevanza"
    r = requests.get(url, headers=H, timeout=15)
    print(f"  HTTP: {r.status_code}, Taille: {len(r.text)}")
    if r.status_code == 200:
        # Pattern du scraper
        pattern = r'<span>€?\s*([\d\s\u202f]+)/mois</span>.*?<a href="(https://www\.immotop\.lu/annonces/(\d+)/)"[^>]*title="([^"]+)"'
        matches = re.findall(pattern, r.text, re.DOTALL)
        print(f"  Pattern scraper: {len(matches)} matches")
        if matches:
            for m in matches[:3]:
                print(f"    Prix: {m[0].strip()}, ID: {m[2]}, Titre: {m[3][:60]}")
        else:
            # Chercher des prix manuellement
            prices = re.findall(r'([\d\s\u202f]+)\s*/\s*mois', r.text)
            print(f"  Prix /mois trouvés: {len(prices)}")
            # Chercher des liens annonces
            links = re.findall(r'href="(https://www\.immotop\.lu/annonces/\d+/)"', r.text)
            print(f"  Liens annonces: {len(links)}")
            if links:
                for l in links[:3]:
                    print(f"    {l}")
            # Classes CSS
            cards = re.findall(r'class="([^"]*(?:listing|annonce|result|item|card)[^"]*)"', r.text, re.I)
            if cards:
                unique = list(set(cards))[:8]
                print(f"  Classes CSS: {unique}")
    elif r.status_code == 404:
        print("  ❌ URL 404! Testons des alternatives...")
        for alt_url in [
            "https://www.immotop.lu/location-appartements/luxembourg-pays/",
            "https://www.immotop.lu/en/location-maisons-appartements/luxembourg-pays/",
            "https://www.immotop.lu/fr/location-maisons-appartements/luxembourg-pays/",
            "https://www.immotop.lu/louer/",
            "https://www.immotop.lu/en/rent/",
        ]:
            try:
                r2 = requests.get(alt_url, headers=H, timeout=10, allow_redirects=True)
                print(f"    {alt_url} → HTTP {r2.status_code} (taille: {len(r2.text)})")
                if r2.status_code == 200:
                    prices = re.findall(r'([\d\s\u202f]+)\s*€', r2.text)
                    print(f"      Prix €: {len(prices)}")
                    break
            except Exception:
                print(f"    {alt_url} → ERREUR")
except Exception as e:
    print(f"  ❌ ERREUR: {e}")

# ============================================================
# 3. LUXHOME.LU — regex JSON embarqué
# ============================================================
sep("3. LUXHOME.LU")
try:
    url = "https://www.luxhome.lu/recherche/?status%5B%5D=location"
    r = requests.get(url, headers=H, timeout=15)
    print(f"  HTTP: {r.status_code}, Taille: {len(r.text)}")
    if r.status_code == 200:
        # Pattern du scraper
        pattern = r'\{\s*"title":"([^"]+)",\s*"propertyType":"([^"]+)",\s*"price":"([^"]+)",\s*"url":"([^"]+)",\s*"id":(\d+)'
        matches = re.findall(pattern, r.text, re.DOTALL)
        print(f"  Pattern scraper: {len(matches)} matches")
        if matches:
            for m in matches[:3]:
                print(f"    Titre: {m[0][:50]}, Type: {m[1]}, Prix: {m[2]}, ID: {m[4]}")
        else:
            # Chercher JSON brut
            json_matches = re.findall(r'"title":"([^"]{5,50})".*?"price":"([^"]*)"', r.text)
            print(f"  JSON title+price: {len(json_matches)}")
    elif r.status_code == 404:
        print("  ❌ URL 404! Testons des alternatives...")
        for alt_url in [
            "https://www.luxhome.lu/recherche/?status[]=location",
            "https://www.luxhome.lu/en/search/?status[]=rental",
            "https://www.luxhome.lu/fr/recherche/?status[]=location",
            "https://www.luxhome.lu/louer/",
            "https://www.luxhome.lu/",
        ]:
            try:
                r2 = requests.get(alt_url, headers=H, timeout=10, allow_redirects=True)
                print(f"    {alt_url} → HTTP {r2.status_code} (taille: {len(r2.text)})")
                if r2.status_code == 200 and len(r2.text) > 10000:
                    prices = re.findall(r'"price":"([^"]*)"', r2.text)
                    print(f"      Prix JSON: {len(prices)}")
                    if prices:
                        break
            except Exception:
                print(f"    {alt_url} → ERREUR")
except Exception as e:
    print(f"  ❌ ERREUR: {e}")

# ============================================================
# 4. WORTIMMO.LU — structure HTML détaillée
# ============================================================
sep("4. WORTIMMO.LU")
try:
    url = "https://www.wortimmo.lu/en/rent"
    r = requests.get(url, headers=H, timeout=15)
    print(f"  HTTP: {r.status_code}, Taille: {len(r.text)}")
    if r.status_code == 200:
        html = r.text

        # Trouver la structure des résultats
        # Chercher le conteneur principal
        container = re.search(r'<div[^>]*class="[^"]*serp-results[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)

        # Chercher les liens d'annonces (détail)
        detail_links = re.findall(r'href="(/en/[^"]*(?:detail|property|ad|listing|rent/[^"]+/\d+)[^"]*)"', html, re.I)
        if not detail_links:
            detail_links = re.findall(r'href="(/en/rent/[^"]*)"', html, re.I)
        if not detail_links:
            detail_links = re.findall(r'href="(/[^"]*\d{5,}[^"]*)"', html)

        print(f"  Liens détail: {len(detail_links)} ({len(set(detail_links))} uniques)")
        for l in list(set(detail_links))[:5]:
            print(f"    {l}")

        # Extraire un bloc type annonce (autour d'un prix)
        # Chercher les blocs avec prix + lien
        blocks = re.findall(r'(<a[^>]*href="(/en/[^"]*)"[^>]*>.*?</a>)', html, re.DOTALL)
        print(f"  Blocs <a>: {len(blocks)}")

        # Chercher les div avec images d'annonces
        img_blocks = re.findall(r'<div[^>]*>.*?<img[^>]*src="(https://static\.wortimmo[^"]*)"[^>]*/?>.*?</div>', html, re.DOTALL)
        print(f"  Images wortimmo: {len(img_blocks)}")

        # Chercher la structure autour des prix
        price_context = re.findall(r'(.{0,200})([\d\s\.]+)\s*€(.{0,200})', html)
        print(f"  Contextes prix: {len(price_context)}")
        if price_context:
            # Afficher le 6ème contexte (les 5 premiers sont probablement des filtres)
            for i, ctx in enumerate(price_context[5:8], 6):
                before = re.sub(r'<[^>]+>', ' ', ctx[0]).strip()[-80:]
                after = re.sub(r'<[^>]+>', ' ', ctx[2]).strip()[:80]
                print(f"  Prix #{i}: ...{before} [{ctx[1].strip()}€] {after}...")

        # Chercher JSON embarqué
        json_data = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        if json_data:
            print(f"  JSON-LD: {len(json_data)} blocs")
            for jd in json_data[:2]:
                try:
                    d = json.loads(jd)
                    print(f"    Type: {d.get('@type', '???')}")
                except:
                    pass

        # Extraire une carte complète
        # Pattern: div avec href + image + prix
        card_pattern = re.compile(
            r'<a\s+href="(/en/rent/[^"]+)"[^>]*>.*?'
            r'<img[^>]*src="([^"]*)".*?'
            r'([\d\s\.]+)\s*€',
            re.DOTALL
        )
        cards = card_pattern.findall(html)
        print(f"  Cartes (lien+img+prix): {len(cards)}")
        if cards:
            for c in cards[:3]:
                print(f"    URL: {c[0][:60]}, Prix: {c[2].strip()}€")

        # Essayer pattern plus large
        any_links = re.findall(r'href="(/en/rent/[^"]*\d[^"]*)"', html)
        print(f"  Liens /en/rent/ avec chiffres: {len(any_links)} ({len(set(any_links))} uniques)")
        for l in list(set(any_links))[:5]:
            print(f"    {l}")

        # Afficher un morceau HTML autour d'une image wortimmo
        img_pos = html.find('static.wortimmo.lu')
        if img_pos > 0:
            snippet = html[max(0,img_pos-500):img_pos+500]
            # Nettoyer
            snippet_clean = re.sub(r'\s+', ' ', snippet)
            print(f"\n  📋 HTML autour première image:")
            print(f"  {snippet_clean[:800]}")

except Exception as e:
    print(f"  ❌ ERREUR: {e}")

# ============================================================
# 5. NEXTIMMO.LU API — déjà confirmé OK
# ============================================================
sep("5. NEXTIMMO.LU API (déjà OK)")
print("  ✅ Confirmé fonctionnel (API JSON + __NEXT_DATA__)")

# ============================================================
# 6. IMMOWEB.BE — HTTP 403 confirmé
# ============================================================
sep("6. IMMOWEB.BE (Selenium requis)")
print("  ❌ HTTP 403 confirmé — Selenium obligatoire")

print(f"\n{'='*60}")
print("TERMINÉ — copie le résultat ici")
print(f"{'='*60}")
