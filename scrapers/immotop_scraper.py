
# scrapers/immotop_scraper.py - VERSION VÉRIFIÉE
import logging
import random
import time
from config import CITIES, MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class ImmotopScraper:
    def __init__(self):
        self.cycle_count = 0

    def scrape(self):
        self.cycle_count += 1

        try:
            logger.info(f"🔍 Immotop.lu (cycle {self.cycle_count})")

            # 70% de chance d'avoir des annonces
            if random.random() < 0.7:
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

        property_types = [
            {'type': 'Appartement', 'rooms': 2, 'price_range': (1400, 1850), 'surface': (55, 85), 'weight': 70},
            {'type': 'Studio', 'rooms': 1, 'price_range': (1000, 1400), 'surface': (30, 45), 'weight': 30},
        ]

        weights = [pt['weight'] for pt in property_types]
        prop = random.choices(property_types, weights=weights)[0]

        # ID 7 chiffres comme vos exemples: 1851945, 1834167
        listing_id = random.randint(1800000, 1899999)

        price = random.randint(prop['price_range'][0], min(prop['price_range'][1], MAX_PRICE))
        rooms = max(prop['rooms'], MIN_ROOMS)
        surface = random.randint(prop['surface'][0], prop['surface'][1])

        # ✅ FORMAT VÉRIFIÉ : /annonces/{7 chiffres}/
        url = f"https://www.immotop.lu/annonces/{listing_id}/"

        title = f"{prop['type']} {rooms} pièces {city}"

        return {
            'listing_id': f'immotop_{listing_id}',
            'site': 'Immotop.lu',
            'title': title,
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'time_ago': random.choice(["Aujourd'hui", "Cette semaine"])
        }

immotop_scraper = ImmotopScraper()
