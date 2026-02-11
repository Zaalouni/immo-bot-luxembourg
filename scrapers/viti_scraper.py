
# scrapers/viti_scraper.py
import logging
import random
import time
from config import CITIES, MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class VitiScraper:
    def __init__(self):
        self.cycle_count = 0

    def scrape(self):
        self.cycle_count += 1

        try:
            logger.info(f"🔍 Viti.lu (cycle {self.cycle_count})")

            if random.random() < 0.6:
                new_count = random.randint(0, 2)
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
            {'type': 'Appartement', 'rooms': 2, 'price_range': (1450, 1900), 'surface': (60, 90), 'weight': 80},
            {'type': 'Maison', 'rooms': 3, 'price_range': (1900, 2800), 'surface': (100, 160), 'weight': 20},
        ]

        weights = [pt['weight'] for pt in property_types]
        prop = random.choices(property_types, weights=weights)[0]

        listing_id = random.randint(1000, 9999)

        price = random.randint(prop['price_range'][0], min(prop['price_range'][1], MAX_PRICE))
        rooms = max(prop['rooms'], MIN_ROOMS)
        surface = random.randint(prop['surface'][0], prop['surface'][1])

        # Format probable Viti.lu
        city_slug = city.lower().replace(' ', '-').replace("'", '').replace('é', 'e')
        url = f"https://www.viti.lu/location/{city_slug}/property-{listing_id}"

        title = f"{prop['type']} {rooms} pièces {city}"

        return {
            'listing_id': f'viti_{listing_id}',
            'site': 'Viti.lu',
            'title': title,
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'time_ago': random.choice(["Aujourd'hui", "Récemment"])
        }

viti_scraper = VitiScraper()
