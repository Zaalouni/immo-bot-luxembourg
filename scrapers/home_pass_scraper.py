# =============================================================================
# scrapers/home_pass_scraper.py — Scraper Home-Pass.lu via JSON propertiesMapData
# =============================================================================
# Methode : requete HTTP GET, extraction de la variable JS propertiesMapData
#           (array JSON embarque dans le HTML par WordPress RealHomes theme)
# Chaque objet contient : title, price, url, id, thumb, lat, lng
# Ville : extraite du prefixe du titre (ex: "BERTRANGE – Appartement...")
# GPS : lat/lng disponibles directement dans le JSON
# Pagination : /page/N/ jusqu'a MAX_PAGES
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS
# Instance globale : home_pass_scraper
# =============================================================================
import requests
import re
import json
import time
import logging
from config import MAX_PRICE, MIN_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS

logger = logging.getLogger(__name__)


class HomePassScraper:
    def __init__(self):
        self.base_url = "https://www.home-pass.lu"
        self.search_url = f"{self.base_url}/property-status/for-rent/"
        self.site_name = "Home-Pass.lu"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'fr-LU,fr;q=0.9',
        }

    def scrape(self):
        """Scraper Home-Pass.lu — locations uniquement via propertiesMapData JSON"""
        listings = []
        seen_ids = set()
        MAX_PAGES = 5

        try:
            for page_num in range(1, MAX_PAGES + 1):
                url = self.search_url if page_num == 1 else f"{self.search_url}page/{page_num}/"
                logger.info(f"[Home-Pass] Chargement page {page_num}: {url}")

                resp = requests.get(url, headers=self.headers, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"  HTTP {resp.status_code} — arret pagination")
                    break

                html = resp.text

                # Extraire le JSON de la variable JS propertiesMapData
                match = re.search(r'var propertiesMapData\s*=\s*(\[.*?\]);', html, re.DOTALL)
                if not match:
                    logger.info(f"  Aucune propertiesMapData trouvee (page {page_num})")
                    break

                try:
                    data = json.loads(match.group(1))
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"  JSON invalide: {e}")
                    break

                if not data:
                    logger.info(f"  propertiesMapData vide — fin pagination")
                    break

                logger.info(f"  Page {page_num}: {len(data)} annonces")
                new_count = 0

                for item in data:
                    prop_id = str(item.get('id', ''))
                    if not prop_id or prop_id in seen_ids:
                        continue
                    seen_ids.add(prop_id)

                    listing = self._extract_listing(item)
                    if listing:
                        listings.append(listing)
                        new_count += 1

                if new_count == 0:
                    logger.info(f"  Aucune nouvelle annonce — fin pagination")
                    break

                if page_num < MAX_PAGES:
                    time.sleep(1)

        except Exception as e:
            logger.error(f"❌ Scraping Home-Pass.lu: {e}")

        logger.info(f"✅ Home-Pass.lu: {len(listings)} annonces apres filtrage")
        return listings

    def _extract_listing(self, item):
        """Extraire et filtrer une annonce depuis un objet propertiesMapData"""
        try:
            title = (item.get('title') or '').strip()
            url = (item.get('url') or '').strip()
            prop_id = str(item.get('id') or '')
            thumb = item.get('thumb') or None
            lat = item.get('lat') or None
            lng = item.get('lng') or None

            if not url or not prop_id:
                return None

            # Prix : " 1.580.000€ " ou "1 250 €" → entier
            price_raw = item.get('price') or ''
            price_digits = re.sub(r'[^\d]', '', price_raw)
            if not price_digits:
                return None
            price = int(price_digits)

            if price <= 0 or price < MIN_PRICE or price > MAX_PRICE:
                return None

            # Ville depuis prefixe du titre : "BERTRANGE – ..." ou "Howald – ..."
            city = 'Luxembourg'
            # Format majuscules : "BERTRANGE – ..." ou "LUX-VILLE – ..."
            city_match = re.match(r'^([A-Z][A-Z\-]+)\s*[–\-]', title)
            if city_match:
                city = city_match.group(1).replace('-', ' ').title()
            else:
                # Format titre case : "Howald – ..."
                city_match2 = re.match(r'^([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\s*[–\-]', title)
                if city_match2:
                    city = city_match2.group(1)

            # Chambres depuis titre
            rooms = 0
            rooms_match = re.search(r'(\d+)\s*chambre', title, re.IGNORECASE)
            if rooms_match:
                rooms = int(rooms_match.group(1))

            if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                return None

            # Surface depuis titre
            surface = 0
            surface_match = re.search(r'(\d+)\s*m[²2]', title)
            if surface_match:
                surface = int(surface_match.group(1))

            if surface > 0 and surface < MIN_SURFACE:
                return None

            # Mots exclus
            check = title.lower()
            if any(w.strip().lower() in check for w in EXCLUDED_WORDS if w.strip()):
                return None

            return {
                'listing_id': f'homepass_{prop_id}',
                'site': self.site_name,
                'title': title[:80],
                'city': city,
                'price': price,
                'rooms': rooms,
                'surface': surface,
                'url': url,
                'image_url': thumb,
                'latitude': float(lat) if lat else None,
                'longitude': float(lng) if lng else None,
                'time_ago': 'Récemment',
                'full_text': title,
            }

        except Exception as e:
            logger.debug(f"  Erreur extraction Home-Pass item: {e}")
            return None


home_pass_scraper = HomePassScraper()
