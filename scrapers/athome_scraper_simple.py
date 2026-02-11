
# scrapers/athome_scraper_simple.py - VERSION API
import requests
import logging
import time
import random
from config import MAX_PRICE, MIN_ROOMS, CITIES

logger = logging.getLogger(__name__)

class AthomeScraperSimple:
    """Scraper simplifié utilisant l'API JSON d'Athome"""

    def __init__(self):
        self.api_url = 'https://www.athome.lu/api/public/real-estate-ads'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Origin': 'https://www.athome.lu',
            'Referer': 'https://www.athome.lu/',
        }

    def scrape(self):
        """Scraper via API JSON"""
        listings = []

        try:
            logger.info("🔍 Scraping Athome.lu (via API)...")

            # Paramètres API
            params = {
                'transaction': 'RENT',
                'page': '1',
                'size': '50',
                'sort': 'DATE_DESC',
                'advertiserTypes': 'PRIVATE,PROFESSIONAL',
                'productTypes': 'APARTMENT,HOUSE',
            }

            # Ajouter filtres par ville si spécifiés
            if CITIES:
                for city in CITIES:
                    try:
                        city_listings = self._search_city(city, params.copy())
                        listings.extend(city_listings)
                        logger.info(f"   📍 {city}: {len(city_listings)} annonces")
                        time.sleep(random.uniform(2, 4))  # Délai entre villes
                    except Exception as e:
                        logger.error(f"   ❌ Erreur pour {city}: {e}")
                        continue
            else:
                # Recherche générale
                listings = self._search_city('', params)

            # Filtrer par nos critères
            filtered_listings = []
            for listing in listings:
                if self._matches_criteria(listing):
                    filtered_listings.append(listing)

            logger.info(f"✅ Athome.lu: {len(filtered_listings)} annonces valides")
            return filtered_listings

        except Exception as e:
            logger.error(f"❌ Erreur scraping API: {e}")
            return []

    def _search_city(self, city, params):
        """Rechercher pour une ville spécifique"""
        if city:
            params['location'] = city

        try:
            response = requests.get(
                self.api_url,
                params=params,
                headers=self.headers,
                timeout=30
            )

            if response.status_code != 200:
                logger.warning(f"   ⚠️  Code {response.status_code} pour {city}")
                return []

            data = response.json()

            listings = []
            for item in data.get('results', []):
                listing = self._parse_api_item(item)
                if listing:
                    listings.append(listing)

            return listings

        except Exception as e:
            logger.error(f"   ❌ Erreur API {city}: {e}")
            return []

    def _parse_api_item(self, item):
        """Parser un item de l'API"""
        try:
            # Informations de base
            listing_id = item.get('id', '')
            if not listing_id:
                return None

            title = item.get('title', {}).get('fr', '') or item.get('title', {}).get('en', '') or 'Sans titre'

            # Prix
            price_info = item.get('price', {})
            price = price_info.get('amount', 0) if isinstance(price_info, dict) else price_info

            # Localisation
            location = item.get('location', {})
            city = location.get('city', '') or location.get('locality', '')

            # Caractéristiques
            features = item.get('features', {})
            rooms = features.get('bedroomCount', 0)
            surface = features.get('livingArea', 0)

            # URL
            slug = item.get('slug', {}).get('fr', '') or item.get('slug', {}).get('en', '')
            url = f"https://www.athome.lu/annonce/{slug}" if slug else '#'

            return {
                'listing_id': f'athome_{listing_id}',
                'site': 'Athome.lu',
                'title': title[:100],
                'city': city,
                'price': int(price) if price else 0,
                'rooms': int(rooms) if rooms else 0,
                'surface': int(surface) if surface else 0,
                'url': url,
                'time_ago': 'récent'
            }

        except Exception as e:
            logger.debug(f"   ⚠️  Erreur parsing API item: {e}")
            return None

    def _matches_criteria(self, listing):
        """Vérifier critères"""
        try:
            price = listing.get('price', 0)
            if price > MAX_PRICE or price <= 0:
                return False

            rooms = listing.get('rooms', 0)
            if rooms < MIN_ROOMS:
                return False

            return True
        except:
            return False


# Remplacer l'ancienne instance
athome_scraper = AthomeScraperSimple()
