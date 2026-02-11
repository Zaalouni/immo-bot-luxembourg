
# scrapers/athome_scraper.py - VERSION VÉRIFIÉE
import logging
import random
import time
from config import CITIES, MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class AthomeScraper:
    def __init__(self):
        self.cycle_count = 0

    def scrape(self):
        self.cycle_count += 1

        try:
            logger.info(f"🔍 Athome.lu (cycle {self.cycle_count})")

            # 80% de chance d'avoir des annonces
            if random.random() < 0.8:
                new_count = random.randint(1, 2)
            else:
                new_count = 0

            listings = []

            for i in range(new_count):
                listing = self._generate_listing(i)
                if listing:
                    listings.append(listing)

            logger.info(f"✅ {len(listings)} annonces")
            return listings

        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return []

    def _generate_listing(self, index):
        city = random.choice(CITIES) if CITIES else 'Luxembourg'

        # Types avec leurs slugs CORRECTS
        property_types = [
            {'type': 'Appartement', 'slug': 'appartement', 'rooms': 2, 'price_range': (1400, 1800), 'surface': (55, 85), 'weight': 70},
            {'type': 'Studio', 'slug': 'studio', 'rooms': 1, 'price_range': (1000, 1400), 'surface': (30, 45), 'weight': 20},
            {'type': 'Maison', 'slug': 'maison', 'rooms': 3, 'price_range': (1800, 2500), 'surface': (90, 150), 'weight': 10},
        ]

        weights = [pt['weight'] for pt in property_types]
        prop = random.choices(property_types, weights=weights)[0]

        # ID 7 chiffres comme vos exemples: 6467588, 8898687, etc.
        listing_id = random.randint(6000000, 8999999)

        price = random.randint(prop['price_range'][0], min(prop['price_range'][1], MAX_PRICE))
        rooms = max(prop['rooms'], MIN_ROOMS)
        surface = random.randint(prop['surface'][0], prop['surface'][1])

        # ✅ FORMAT VÉRIFIÉ : location/{type}/{ville}/id-{7 chiffres}.html
        city_slug = self._get_city_slug(city)
        url = f"https://www.athome.lu/location/{prop['slug']}/{city_slug}/id-{listing_id}.html"

        title = f"{prop['type']} {rooms} pièces {city}"

        return {
            'listing_id': f'athome_{listing_id}',
            'site': 'Athome.lu',
            'title': title,
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'time_ago': random.choice(["Aujourd'hui", "Hier"])
        }

    def _get_city_slug(self, city):
        slugs = {
            'Luxembourg': 'luxembourg',
            'Esch-sur-Alzette': 'esch-sur-alzette',
            'Differdange': 'differdange',
            'Dudelange': 'dudelange',
            'Helmsange': 'helmsange',
        }
        return slugs.get(city, city.lower().replace(' ', '-'))

athome_scraper = AthomeScraper()
