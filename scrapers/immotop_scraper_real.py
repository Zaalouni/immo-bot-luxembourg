# =============================================================================
# scrapers/immotop_scraper_real.py — Scraper Immotop.lu via HTML regex
# =============================================================================
# Methode : requete HTTP GET sur la page de recherche, extraction des annonces
#           par regex sur le HTML (prix, URL, ID, titre)
# Images : extraction des data-src images associees aux IDs d'annonces
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS
# Limite : 20 annonces max par cycle
# Instance globale : immotop_scraper_real
# =============================================================================
import requests
import re
import logging
from config import MAX_PRICE, MIN_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS

logger = logging.getLogger(__name__)

class ImmotopScraperReal:
    def __init__(self):
        self.base_url = "https://www.immotop.lu"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def scrape(self):
        try:
            url = f"{self.base_url}/location-maisons-appartements/luxembourg-pays/?criterio=rilevanza"
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code}")
                return []
            
            html = response.text
            
            # Pattern : prix + URL + titre
            pattern = r'<span>€?\s*([\d\s\u202f]+)/mois</span>.*?<a href="(https://www\.immotop\.lu/annonces/(\d+)/)"[^>]*title="([^"]+)"'
            matches = re.findall(pattern, html, re.DOTALL)
            
            logger.info(f"Annonces trouvées: {len(matches)}")

            # Extraire images par ID d'annonce
            image_map = {}
            img_matches = re.findall(r'data-src="(https://[^"]*immotop[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)"[^>]*?(?:annonces/(\d+)|data-id="(\d+))', html, re.IGNORECASE)
            if not img_matches:
                # Fallback: chercher img src proche des liens
                img_matches2 = re.findall(r'<img[^>]+src="(https://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"[^>]*>.*?annonces/(\d+)/', html, re.DOTALL)
                for img_url, img_id in img_matches2[:30]:
                    if img_id not in image_map:
                        image_map[img_id] = img_url

            for img_url, id1, id2 in img_matches[:30]:
                img_id = id1 or id2
                if img_id and img_id not in image_map:
                    image_map[img_id] = img_url

            listings = []
            for price_text, url_annonce, id_val, title in matches[:20]:
                # Nettoyer prix (enlever espaces normaux + insécables)
                price_clean = price_text.replace(' ', '').replace('\u202f', '').replace(',', '')
                
                try:
                    price = int(price_clean)
                except ValueError:
                    logger.debug(f"Prix invalide: {price_text}")
                    continue
                
                # Filtrer prix
                if price < MIN_PRICE or price > MAX_PRICE or price <= 0:
                    continue

                # Extraire chambres
                rooms_match = re.search(r'(\d+)\s*chambre', title, re.IGNORECASE)
                rooms = int(rooms_match.group(1)) if rooms_match else 0

                if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                    continue

                # Surface
                surface_match = re.search(r'(\d+)\s*m[²2]', title)
                surface = int(surface_match.group(1)) if surface_match else 0

                if surface > 0 and surface < MIN_SURFACE:
                    continue

                # Mots exclus
                title_lower = title.lower()
                if any(w.strip().lower() in title_lower for w in EXCLUDED_WORDS if w.strip()):
                    continue
                
                # Ville (dernier élément après virgule)
                parts = title.split(',')
                city = parts[-1].strip() if len(parts) > 1 else 'Luxembourg'
                
                listing = {
                    'listing_id': f'immotop_{id_val}',
                    'site': 'Immotop.lu',
                    'title': title[:70],
                    'city': city,
                    'price': price,
                    'rooms': rooms,
                    'surface': surface,
                    'url': url_annonce,
                    'image_url': image_map.get(id_val),
                    'time_ago': 'Récemment'
                }
                listings.append(listing)
            
            logger.info(f"✅ {len(listings)} annonces après filtrage")
            return listings
            
        except Exception as e:
            logger.error(f"❌ Scraping: {e}")
            import traceback
            traceback.print_exc()
            return []

immotop_scraper_real = ImmotopScraperReal()
