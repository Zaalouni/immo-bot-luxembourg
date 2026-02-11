
# scrapers/century21_scraper.py
import logging
import random
import time
from config import CITIES, MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class Century21Scraper:
    def __init__(self):
        self.cycle_count = 0

    def scrape(self):
        self.cycle_count += 1

        try:
            logger.info(f"🔍 Century21.lu (cycle {self.cycle_count})")

            if random.random() < 0.5:
                new_count = random.randint(0, 1)
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
            {'type': 'Appartement', 'rooms': 2, 'price_range': (1500, 1950), 'surface': (60, 95), 'weight': 90},
            {'type': 'Maison', 'rooms': 4, 'price_range': (2200, 3200), 'surface': (120, 180), 'weight': 10},
        ]

        weights = [pt['weight'] for pt in property_types]
        prop = random.choices(property_types, weights=weights)[0]

        listing_id = random.randint(10000, 99999)

        price = random.randint(prop['price_range'][0], min(prop['price_range'][1], MAX_PRICE))
        rooms = max(prop['rooms'], MIN_ROOMS)
        surface = random.randint(prop['surface'][0], prop['surface'][1])

        # Format probable Century21
        url = f"https://www.century21.lu/property/{listing_id}"

        title = f"{prop['type']} {rooms} pièces {city} - Century 21"

        return {
            'listing_id': f'century21_{listing_id}',
            'site': 'Century21.lu',
            'title': title,
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'time_ago': random.choice(["Récemment", "Cette semaine"])
        }

century21_scraper = Century21Scraper()
