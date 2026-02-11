import logging
import random
from config import CITIES, MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class UnicornScraper:
    def scrape(self):
        logger.info("🦄 Simulation Unicorn.lu")
        
        if random.random() < 0.6:
            new_count = random.randint(0, 2)
        else:
            new_count = 0
        
        listings = []
        for i in range(new_count):
            city = random.choice(CITIES) if CITIES else 'Luxembourg'
            listing_id = random.randint(1000, 9999)
            
            listings.append({
                'listing_id': f'unicorn_{listing_id}',
                'site': 'Unicorn.lu',
                'title': f'Appartement {random.randint(1, 3)} pièces {city}',
                'city': city,
                'price': random.randint(1200, 1900),
                'rooms': random.randint(1, 3),
                'surface': random.randint(40, 90),
                'url': f'https://www.unicorn.lu/property/{listing_id}',
                'time_ago': random.choice(["Aujourd'hui", "Cette semaine"])
            })
        
        logger.info(f"✅ {len(listings)} annonces")
        return listings

unicorn_scraper = UnicornScraper()
