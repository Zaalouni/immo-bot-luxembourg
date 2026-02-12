
# scrapers/nextimmo_scraper.py
# Scraper pour Nextimmo.lu — API JSON directe
import requests
import logging
from config import USER_AGENT, MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class NextimmoScraper:
    """Scraper Nextimmo.lu via API JSON"""

    def __init__(self):
        self.base_url = 'https://nextimmo.lu'
        # API JSON directe (country=1=Luxembourg, type=1=apartment, category=2=rent)
        self.api_url = 'https://nextimmo.lu/api/v2/properties'
        self.site_name = 'Nextimmo.lu'
        self.headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
            'Referer': 'https://nextimmo.lu/en/rent/apartment/luxembourg-country',
        }

    def scrape(self):
        """Scraper via API JSON"""
        listings = []

        try:
            logger.info(f"🔍 Scraping {self.site_name} (API JSON)...")

            params = {
                'country': 1,       # Luxembourg
                'type': 1,          # Apartment
                'category': 2,      # Rent
                'page': 1,
            }

            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=15)

            if response.status_code != 200:
                logger.warning(f"API HTTP {response.status_code}, fallback HTML...")
                return self._scrape_html()

            data = response.json()
            items = data.get('data', [])

            if not items:
                logger.warning("API retourne 0 résultats, fallback HTML...")
                return self._scrape_html()

            logger.info(f"   📊 API retourne {len(items)} annonces")

            for item in items[:20]:
                try:
                    listing = self._extract_from_json(item)
                    if listing and self._matches_criteria(listing):
                        listings.append(listing)
                except Exception as e:
                    logger.debug(f"Erreur extraction: {e}")
                    continue

            logger.info(f"✅ {len(listings)} annonces après filtrage")
            return listings

        except requests.RequestException as e:
            logger.error(f"❌ Erreur réseau {self.site_name}: {e}")
            return self._scrape_html()
        except Exception as e:
            logger.error(f"❌ Erreur {self.site_name}: {e}")
            return []

    def _extract_from_json(self, item):
        """Extraire depuis un objet JSON de l'API"""
        prop_id = item.get('id')
        if not prop_id:
            return None

        # Prix
        price_obj = item.get('price', {})
        price = 0
        if isinstance(price_obj, dict):
            price = int(price_obj.get('value', 0))
        elif isinstance(price_obj, (int, float)):
            price = int(price_obj)

        if price <= 0:
            return None

        # Surface
        area_obj = item.get('area', {})
        surface = 0
        if isinstance(area_obj, dict):
            surface = int(float(area_obj.get('value', 0)))
        elif isinstance(area_obj, (int, float)):
            surface = int(area_obj)

        # Chambres
        bedrooms = item.get('bedrooms', 0) or 0
        rooms = item.get('rooms', 0) or 0
        room_count = max(bedrooms, rooms)

        # Ville
        city_obj = item.get('city', {})
        city = 'Luxembourg'
        if isinstance(city_obj, dict):
            city = city_obj.get('name', 'Luxembourg')
        elif isinstance(city_obj, str):
            city = city_obj

        # Image
        pictures = item.get('pictures', {})
        image_url = None
        if isinstance(pictures, dict):
            thumbs = pictures.get('thumb', [])
            if thumbs and isinstance(thumbs, list):
                image_url = thumbs[0]

        # Titre
        title = item.get('title', '') or f"Appartement {city}"
        if not title or title == '':
            title = f"Appartement {room_count}ch {surface}m² {city}" if room_count > 0 else f"Appartement {city}"

        # URL
        url = f"{self.base_url}/en/details/{prop_id}"

        # GPS
        lat = item.get('latitude') or item.get('lat')
        lng = item.get('longitude') or item.get('lng')
        distance_km = None
        if lat and lng:
            try:
                from utils import haversine_distance
                from config import REFERENCE_LAT, REFERENCE_LNG
                distance_km = haversine_distance(REFERENCE_LAT, REFERENCE_LNG, float(lat), float(lng))
            except Exception:
                pass

        return {
            'listing_id': f'nextimmo_{prop_id}',
            'site': self.site_name,
            'title': str(title)[:200],
            'city': city,
            'price': price,
            'rooms': room_count,
            'surface': surface,
            'url': url,
            'image_url': image_url,
            'latitude': lat,
            'longitude': lng,
            'distance_km': distance_km,
            'time_ago': 'Récemment'
        }

    def _scrape_html(self):
        """Fallback: extraire depuis __NEXT_DATA__ dans le HTML"""
        import re
        import json

        try:
            url = f"{self.base_url}/en/rent/apartment/luxembourg-country"
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html',
            }, timeout=15)

            if response.status_code != 200:
                logger.warning(f"HTML fallback HTTP {response.status_code}")
                return []

            # Chercher __NEXT_DATA__
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', response.text, re.DOTALL)
            if not match:
                logger.warning("__NEXT_DATA__ non trouvé")
                return []

            next_data = json.loads(match.group(1))

            # Naviguer dans la structure
            fallback = next_data.get('props', {}).get('pageProps', {}).get('fallback', {})

            items = []
            for key, value in fallback.items():
                if 'properties' in key and isinstance(value, dict):
                    items = value.get('data', [])
                    break

            if not items:
                logger.warning("Aucune propriété dans __NEXT_DATA__")
                return []

            logger.info(f"   📊 __NEXT_DATA__ contient {len(items)} annonces")

            listings = []
            for item in items[:20]:
                try:
                    listing = self._extract_from_json(item)
                    if listing and self._matches_criteria(listing):
                        listings.append(listing)
                except Exception:
                    continue

            logger.info(f"✅ {len(listings)} annonces (HTML fallback)")
            return listings

        except Exception as e:
            logger.error(f"❌ HTML fallback: {e}")
            return []

    def _matches_criteria(self, listing):
        """Vérifier critères"""
        try:
            price = listing.get('price', 0)
            if price <= 0 or price > MAX_PRICE:
                return False
            rooms = listing.get('rooms', 0)
            if rooms > 0 and rooms < MIN_ROOMS:
                return False
            return True
        except Exception:
            return False

nextimmo_scraper = NextimmoScraper()
