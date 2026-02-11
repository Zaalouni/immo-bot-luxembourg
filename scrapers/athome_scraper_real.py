import requests
import re
import logging
from config import MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class AthomeScraperReal:
    def __init__(self):
        self.base_url = "https://www.athome.lu"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def scrape(self):
        try:
            url = f"{self.base_url}/location"
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code}")
                return []
            
            html = response.text
            
            # Extraire blocs annonces complets
            pattern = r'"id":(\d{7,}).*?"price":\{[^}]*"value":(\d+).*?"description":"([^"]*)".*?"permalink":\{[^}]*"fr":"([^"]+)"'
            matches = re.findall(pattern, html, re.DOTALL)
            
            logger.info(f"Annonces trouvées: {len(matches)}")
            
            listings = []
            for id_val, price, description, url_path in matches[:10]:
                price_int = int(price)
                
                # Filtrer prix
                if price_int > MAX_PRICE or price_int <= 0:
                    continue
                
                # Extraire chambres depuis description
                rooms_match = re.search(r'(\d+)\s*chambres?', description, re.IGNORECASE)
                rooms = int(rooms_match.group(1)) if rooms_match else 1
                
                # Filtrer chambres
                if rooms < MIN_ROOMS:
                    continue
                
                # Extraire surface depuis description (optionnel)
                surface_match = re.search(r'(\d+)\s*m[²2]', description)
                surface = int(surface_match.group(1)) if surface_match else 0
                
                # Décoder URL
                url_clean = url_path.replace('\\u002F', '/')
                
                # Extraire ville depuis URL
                city = self._extract_city(url_clean)
                
                # Titre depuis description (max 50 chars)
                title = description[:50].strip() + ('...' if len(description) > 50 else '')
                
                listing = {
                    'listing_id': f'athome_{id_val}',
                    'site': 'Athome.lu',
                    'title': title,
                    'city': city,
                    'price': price_int,
                    'rooms': rooms,
                    'surface': surface,
                    'url': f"{self.base_url}{url_clean}",
                    'time_ago': 'Récemment'
                }
                listings.append(listing)
            
            logger.info(f"✅ {len(listings)} annonces après filtrage")
            return listings
            
        except Exception as e:
            logger.error(f"❌ Scraping: {e}")
            return []
    
    def _extract_city(self, url_path):
        parts = url_path.split('/')
        if len(parts) >= 4:
            city = parts[3].replace('-', ' ').title()
            return city
        return 'Luxembourg'

athome_scraper_real = AthomeScraperReal()
