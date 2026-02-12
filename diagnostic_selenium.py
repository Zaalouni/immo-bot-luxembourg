#!/usr/bin/env python3
"""
Diagnostic Selenium — teste Wortimmo, Immoweb, Unicorn
Usage: python diagnostic_selenium.py
"""
import re
import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By

def setup():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    driver = webdriver.Firefox(options=options)
    driver.set_page_load_timeout(60)
    return driver

def sep(t):
    print(f"\n{'='*60}")
    print(f"  {t}")
    print(f"{'='*60}")

# ============================================================
# 1. WORTIMMO
# ============================================================
sep("1. WORTIMMO.LU (Selenium)")
driver = None
try:
    driver = setup()
    driver.get("https://www.wortimmo.lu/en/rent")
    time.sleep(10)

    # Scroll
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)

    src = driver.page_source
    print(f"  Page source: {len(src)} chars")

    # Chercher liens rent
    rent_links = re.findall(r'href="(/en/rent/[^"]*)"', src)
    print(f"  Liens /en/rent/: {len(rent_links)} ({len(set(rent_links))} uniques)")
    for l in list(set(rent_links))[:8]:
        print(f"    {l}")

    # Chercher liens property
    prop_links = re.findall(r'href="([^"]*property[^"]*)"', src, re.I)
    print(f"  Liens property: {len(prop_links)}")
    for l in list(set(prop_links))[:5]:
        print(f"    {l}")

    # Chercher prix dans le HTML rendu (pas dans les filtres)
    # Les filtres sont dans des <select>, les vrais prix sont ailleurs
    price_contexts = []
    for m in re.finditer(r'([\d\s\.]+)\s*€', src):
        # Vérifier que ce n'est pas dans un <option> ou <select>
        start = max(0, m.start() - 200)
        before = src[start:m.start()]
        if '<option' not in before and '<select' not in before:
            price_contexts.append((m.group().strip(), before[-50:]))

    print(f"  Prix hors filtres: {len(price_contexts)}")
    for p, ctx in price_contexts[:5]:
        ctx_clean = re.sub(r'<[^>]+>', ' ', ctx).strip()[-40:]
        print(f"    {p} — contexte: ...{ctx_clean}")

    # Chercher les éléments avec images wortimmo
    img_elems = driver.find_elements(By.CSS_SELECTOR, 'img[src*="static.wortimmo"]')
    print(f"  Images wortimmo: {len(img_elems)}")
    if img_elems:
        # Trouver le parent commun
        for img in img_elems[:3]:
            parent = img.find_element(By.XPATH, './..')
            grandparent = parent.find_element(By.XPATH, './..')
            ggp = grandparent.find_element(By.XPATH, './..')
            print(f"    img parent: <{parent.tag_name} class='{parent.get_attribute('class')}'>")
            print(f"    grandparent: <{grandparent.tag_name} class='{grandparent.get_attribute('class')}'>")
            print(f"    great-grandparent: <{ggp.tag_name} class='{ggp.get_attribute('class')}'>")
            # Texte du grand-parent
            gp_text = grandparent.text[:200] if grandparent.text else '(vide)'
            print(f"    text: {gp_text}")
            break

    # Chercher tous les <a> avec texte contenant €
    a_with_price = driver.find_elements(By.XPATH, "//a[contains(., '€')]")
    print(f"  <a> avec €: {len(a_with_price)}")
    for a in a_with_price[:3]:
        href = a.get_attribute('href') or ''
        txt = (a.text or '')[:100]
        print(f"    href={href[:60]} text={txt}")

except Exception as e:
    print(f"  ❌ ERREUR: {e}")
finally:
    if driver:
        driver.quit()

# ============================================================
# 2. UNICORN
# ============================================================
sep("2. UNICORN.LU (Selenium)")
driver = None
try:
    driver = setup()
    driver.get("https://www.unicorn.lu/recherche/location/appartement")
    time.sleep(8)

    src = driver.page_source
    print(f"  Page source: {len(src)} chars")

    # Liens detail
    detail_links = re.findall(r'href="([^"]*detail-\d+[^"]*)"', src)
    print(f"  Liens detail-: {len(detail_links)} ({len(set(detail_links))} uniques)")
    for l in list(set(detail_links))[:5]:
        print(f"    {l}")

    # Elements avec Selenium
    cards = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/detail-"]')
    print(f"  <a> detail: {len(cards)}")
    for c in cards[:3]:
        txt = (c.text or '')[:150]
        href = c.get_attribute('href') or ''
        print(f"    href={href}")
        print(f"    text={txt}")

except Exception as e:
    print(f"  ❌ ERREUR: {e}")
finally:
    if driver:
        driver.quit()

# ============================================================
# 3. IMMOWEB (timeout test)
# ============================================================
sep("3. IMMOWEB.BE (Selenium)")
driver = None
try:
    driver = setup()
    print("  Chargement (timeout 60s)...")
    driver.get("https://www.immoweb.be/en/search/apartment/for-rent?countries=LU&orderBy=newest")
    time.sleep(10)

    src = driver.page_source
    print(f"  Page source: {len(src)} chars")

    # Vérifier si Datadome/challenge
    if 'Please enable JS' in src or 'captcha' in src.lower() or len(src) < 5000:
        print("  ❌ Datadome/Captcha détecté!")
        print(f"  Contenu: {src[:300]}")
    else:
        # Chercher annonces
        classified = re.findall(r'href="([^"]*classified[^"]*)"', src)
        print(f"  Liens classified: {len(classified)}")
        cards = driver.find_elements(By.CSS_SELECTOR, '.search-results__item, article')
        print(f"  Cards: {len(cards)}")

except Exception as e:
    print(f"  ❌ ERREUR: {e}")
finally:
    if driver:
        driver.quit()

print(f"\n{'='*60}")
print("TERMINÉ")
print(f"{'='*60}")
