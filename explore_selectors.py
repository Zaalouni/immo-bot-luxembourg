from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import time
import re

def explore_site(url, site_name):
    """Explorer un site et trouver les sélecteurs potentiels"""
    print(f"\n=== Exploration de {site_name} ===")
    
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Firefox(options=options)
    
    try:
        driver.get(url)
        time.sleep(8)
        
        # Sauvegarder le HTML pour analyse
        filename = f"/tmp/{site_name}_rendered.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"✅ HTML sauvegardé: {filename}")
        
        # Analyser les classes communes
        html = driver.page_source
        
        # Chercher les classes qui pourraient être des annonces
        classes = re.findall(r'class="([^"]+)"', html)
        
        # Compter les occurrences de chaque classe
        from collections import Counter
        class_counter = Counter()
        
        for class_list in classes:
            for cls in class_list.split():
                class_counter[cls] += 1
        
        print("\nClasses les plus fréquentes:")
        for cls, count in class_counter.most_common(20):
            if count > 5 and len(cls) > 2:
                print(f"  .{cls}: {count} fois")
        
        # Chercher des mots-clés liés aux annonces
        keywords = ['property', 'listing', 'card', 'item', 'annonce', 'offer', 'result']
        print("\nClasses avec mots-clés annonces:")
        for cls in class_counter:
            if any(keyword in cls.lower() for keyword in keywords):
                print(f"  .{cls}: {class_counter[cls]} fois")
        
        # Chercher des prix
        price_elements = driver.find_elements_by_xpath("//*[contains(text(), '€') or contains(text(), 'EUR')]")
        print(f"\nÉléments avec prix trouvés: {len(price_elements)}")
        if price_elements:
            print("Exemple de prix:")
            for elem in price_elements[:3]:
                text = elem.text[:50]
                if text.strip():
                    print(f"  - {text}")
        
    finally:
        driver.quit()

# Explorer les 4 sites
sites = [
    ("Luxhome", "https://www.luxhome.lu/louer"),
    ("VIVI", "https://www.vivi.lu/search"),
    ("Newimmo", "https://www.newimmo.lu/fr/louer/"),
    ("Unicorn", "https://www.unicorn.lu/recherche/location")
]

for site_name, url in sites:
    explore_site(url, site_name)
