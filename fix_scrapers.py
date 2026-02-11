import os
import glob

# Trouver tous les fichiers scraper_real
scraper_files = glob.glob('scrapers/*_scraper_real.py')

for file_path in scraper_files:
    print(f"Correction de {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remplacer l'import de MIN_SURFACE
    if 'from config import' in content:
        # Remplacer l'import complet
        new_content = content.replace(
            'from config import MAX_PRICE, MIN_ROOMS, MIN_SURFACE',
            'from config import MAX_PRICE, MIN_ROOMS'
        ).replace(
            'from config import MAX_PRICE, MIN_ROOMS, MIN_SURFACE, CITIES',
            'from config import MAX_PRICE, MIN_ROOMS, CITIES'
        ).replace(
            'from config import MAX_PRICE, MIN_ROOMS, MIN_SURFACE, CITIES, USER_AGENT',
            'from config import MAX_PRICE, MIN_ROOMS, CITIES, USER_AGENT'
        )
        
        # Remplacer également les références à MIN_SURFACE dans le code
        new_content = new_content.replace('surface < MIN_SURFACE', 'surface < 40')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✅ {file_path} corrigé")

print("Correction terminée !")
