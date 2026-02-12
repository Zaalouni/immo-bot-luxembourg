
# scrapers/unicorn_scraper_real.py
# Scraper Unicorn.lu — URL corrigée /recherche/location/appartement
import logging
import re
from scrapers.selenium_template import SeleniumScraperBase
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

class UnicornScraperReal(SeleniumScraperBase):
    def __init__(self):
        super().__init__(
            site_name="Unicorn.lu",
            base_url="https://www.unicorn.lu",
            search_url="https://www.unicorn.lu/recherche/location/appartement"
        )

    def find_listings_elements(self, driver):
        """Trouver les éléments d'annonces"""
        # Unicorn utilise des <a> avec href /detail-XXXX-location-...
        selectors = [
            'a[href*="/detail-"][href*="-location-"]',
            'a[href*="/detail-"]',
            'article.property-item',
            '.property-card',
            '[class*="property"]',
        ]

        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(elements) >= 2:
                logger.info(f"Utilisation sélecteur: {selector} ({len(elements)} éléments)")
                return elements

        # Fallback
        return driver.find_elements(By.CSS_SELECTOR, 'a[href*="/detail-"]')

    def extract_listing_data(self, element):
        """Extraire données d'une annonce Unicorn"""
        try:
            # URL - l'élément lui-même est un <a>
            url = element.get_attribute('href') or ''
            if '/detail-' not in url:
                # Chercher un lien enfant
                try:
                    link = element.find_element(By.CSS_SELECTOR, 'a[href*="/detail-"]')
                    url = link.get_attribute('href') or ''
                except Exception:
                    return None

            if '/detail-' not in url or 'unicorn.lu' not in url:
                return None

            # ID depuis URL: /detail-9278-location-studio-...
            id_match = re.search(r'/detail-(\d+)', url)
            listing_id = id_match.group(1) if id_match else url.split('/')[-1]

            if not listing_id:
                return None

            # Texte complet
            text = element.text or ''
            if not text or len(text) < 5:
                return None

            lines = [l.strip() for l in text.split('\n') if l.strip()]

            # Titre (type de bien)
            title = lines[0] if lines else 'Annonce Unicorn.lu'

            # Prix - chercher "XXXX€" dans le texte
            price = 0
            for line in lines:
                if '€' in line and 'charge' not in line.lower():
                    price_digits = re.sub(r'[^\d]', '', line.split('€')[0])
                    if price_digits:
                        try:
                            p = int(price_digits)
                            if 100 < p < 100000:
                                price = p
                                break
                        except ValueError:
                            continue

            if price <= 0:
                return None

            # Chambres
            rooms = 0
            rooms_match = re.search(r'(\d+)\s*(?:chambre|pièce|room)', text, re.IGNORECASE)
            if rooms_match:
                rooms = int(rooms_match.group(1))

            # Surface
            surface = 0
            surface_match = re.search(r'(\d+)\s*m[²2]', text)
            if surface_match:
                surface = int(surface_match.group(1))

            # Ville depuis URL: /detail-9278-location-studio-esch-sur-alzette
            city = 'Luxembourg'
            # Extraire la dernière partie après le type
            url_parts = url.split('/')[-1]  # detail-9278-location-studio-esch-sur-alzette
            location_match = re.search(r'location-(?:appartement|studio|maison|penthouse|duplex|loft|bureau)-(.+)$', url_parts)
            if location_match:
                city = location_match.group(1).replace('-', ' ').title()

            # Filtrer
            from config import MAX_PRICE, MIN_ROOMS
            if price > MAX_PRICE or price < 500:
                return None
            if rooms > 0 and rooms < MIN_ROOMS:
                return None

            return {
                'listing_id': f'unicorn_{listing_id}',
                'site': 'Unicorn.lu',
                'title': str(title)[:200],
                'city': city,
                'price': price,
                'rooms': rooms,
                'surface': surface,
                'url': url,
                'time_ago': 'Récemment'
            }

        except Exception as e:
            logger.debug(f"Erreur extraction Unicorn: {e}")
            return None

unicorn_scraper_real = UnicornScraperReal()
