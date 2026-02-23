# =============================================================================
# scrapers/immotop_scraper_real.py — Scraper Immotop.lu via HTML regex
# =============================================================================
# Methode : requete HTTP GET sur la page de recherche, extraction des annonces
#           par regex sur le HTML (prix, URL, ID, titre)
# Pagination : pages 1..MAX_PAGES, accumule HTML pour images
# Images : extraction des data-src images associees aux IDs d'annonces
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS
# Instance globale : immotop_scraper_real
# =============================================================================
import requests
import re
import time
import logging
import random
from config import MAX_PRICE, MIN_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS, USER_AGENTS
from utils import validate_listing_data

logger = logging.getLogger(__name__)

class ImmotopScraperReal:
    def __init__(self):
        self.base_url = "https://www.immotop.lu"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def scrape(self):
        try:
            MAX_PAGES = 5
            base_search = f"{self.base_url}/location-maisons-appartements/luxembourg-pays/?criterio=rilevanza"

            all_matches = []
            seen_ids = set()
            combined_html = ''

            for page_num in range(1, MAX_PAGES + 1):
                url = f"{base_search}&page={page_num}" if page_num > 1 else base_search
                # Rotation User-Agent
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Referer': self.base_url,
                }
                response = requests.get(url, headers=headers, timeout=15)

                if response.status_code != 200:
                    break

                html = response.text

                # Security: Limite taille réponse pour éviter ReDoS
                if len(html) > 10_000_000:  # 10MB max
                    logger.warning(f"Response trop volumineux ({len(html)/1e6:.1f}MB), skip page")
                    break

                combined_html += '\n' + html

                # Pattern : prix + URL + titre (bounded regex pour éviter ReDoS)
                # title="([^"]{1,500})" limite la capture à 500 chars
                pattern = r'<span>€?\s*([\d\s\u202f]+)/mois</span>.*?<a href="(https://www\.immotop\.lu/annonces/(\d+)/)"[^>]*title="([^"]{1,500})"'
                matches = re.findall(pattern, html, re.DOTALL)
                logger.info(f"  Page {page_num}: {len(matches)} annonces")

                if not matches:
                    break

                new_count = 0
                for m in matches:
                    id_val = m[2]
                    if id_val not in seen_ids:
                        seen_ids.add(id_val)
                        all_matches.append(m)
                        new_count += 1

                if new_count == 0:
                    break

                if page_num < MAX_PAGES:
                    time.sleep(1)

            logger.info(f"Annonces totales: {len(all_matches)}")

            # Extraire images par ID d'annonce depuis tout le HTML accumule
            image_map = {}
            img_matches = re.findall(r'data-src="(https://[^"]*immotop[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)"[^>]*?(?:annonces/(\d+)|data-id="(\d+))', combined_html, re.IGNORECASE)
            if not img_matches:
                # Fallback: chercher img src proche des liens
                img_matches2 = re.findall(r'<img[^>]+src="(https://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"[^>]*>.*?annonces/(\d+)/', combined_html, re.DOTALL)
                for img_url, img_id in img_matches2:
                    if img_id not in image_map:
                        image_map[img_id] = img_url

            for img_url, id1, id2 in img_matches:
                img_id = id1 or id2
                if img_id and img_id not in image_map:
                    image_map[img_id] = img_url

            listings = []
            for price_text, url_annonce, id_val, title in all_matches:
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
                # Valider avant ajout
                try:
                    validated = validate_listing_data(listing)
                    listings.append(validated)
                except (ValueError, KeyError) as ve:
                    logger.debug(f"Validation échouée: {ve}")
            
            logger.info(f"✅ {len(listings)} annonces après filtrage")
            return listings
            
        except Exception as e:
            logger.error(f"❌ Scraping: {e}")
            return []

immotop_scraper_real = ImmotopScraperReal()
