
# scrapers/newimmo_scraper_real.py
import logging
import re
from scrapers.selenium_template import SeleniumScraperBase
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

class NewimmoScraperReal(SeleniumScraperBase):
    def __init__(self):
        super().__init__(
            site_name="Newimmo.lu",
            base_url="https://www.newimmo.lu",
            search_url="https://www.newimmo.lu/louer"
        )

    def find_listings_elements(self, driver):
        """Trouver les éléments d'annonces"""
        selectors = [
            'article.property-item',
            '.property-card',
            '.listing-item',
            '[class*="property"]',
            '[class*="listing"]',
            'div[class*="card"]'
        ]

        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(elements) > 3:
                logger.info(f"Utilisation sélecteur: {selector}")
                return elements

        return driver.find_elements(By.CSS_SELECTOR, 'article, div[class]')

    def extract_listing_data(self, element):
        """Extraire données d'une annonce Newimmo"""
        try:
            # URL
            link_elem = element.find_element(By.CSS_SELECTOR, 'a')
            url = link_elem.get_attribute('href')
            if not url or 'newimmo.lu' not in url:
                return None

            # ID depuis URL (gérer les URLs qui finissent par /)
            url_clean = url.rstrip('/')
            listing_id = url_clean.split('/')[-1].split('?')[0]
            if not listing_id:
                listing_id = str(abs(hash(url)))[:10]

            # Titre
            try:
                title_elem = element.find_element(By.CSS_SELECTOR, 'h2, h3, [class*="title"]')
                title = title_elem.text
            except Exception:
                title = element.text[:100]

            # Prix
            price = 0
            price_elems = element.find_elements(By.XPATH, ".//*[contains(text(), '€')]")
            for price_elem in price_elems:
                price_text = price_elem.text
                parsed_price = self.parse_price(price_text)
                if parsed_price > price:
                    price = parsed_price

            # Pièces et surface
            rooms = 0
            surface = 0
            text_content = element.text

            # Surface d'abord (pour éviter que parse_rooms capture "33" de "33 m²")
            # Gère "52.00 m²", "52 m²", "52m2"
            surface_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', text_content)
            if surface_match:
                surface = int(float(surface_match.group(1).replace(',', '.')))
            else:
                surface = self.parse_surface(text_content)

            # Chambres (exclure les chiffres suivis de m²)
            rooms_match = re.search(r'(\d+)\s*(?:pièces|chambres|rooms|ch\.)', text_content, re.IGNORECASE)
            if rooms_match:
                # Vérifier que ce n'est pas la surface
                matched_num = int(rooms_match.group(1))
                if matched_num != surface and matched_num < 20:
                    rooms = matched_num

            # Ville
            city = "Luxembourg"
            city_match = re.search(r'\b(Luxembourg|Esch|Differdange|Dudelange|Mersch|Walferdange|Bertrange|Strassen|Howald|Hesperange|Mamer)\b', text_content, re.IGNORECASE)
            if city_match:
                city = city_match.group(1)

            # Filtrer selon config
            from config import MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS
            if price < MIN_PRICE or price > MAX_PRICE:
                return None
            if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                return None
            if surface > 0 and surface < MIN_SURFACE:
                return None
            # Vérifier mots exclus dans titre ET texte complet
            check_text = (title + ' ' + text_content).lower()
            if any(w.strip().lower() in check_text for w in EXCLUDED_WORDS if w.strip()):
                return None

            return {
                'listing_id': f'newimmo_{listing_id}',
                'site': 'Newimmo.lu',
                'title': title[:200],
                'city': city,
                'price': price,
                'rooms': rooms,
                'surface': surface,
                'url': url,
                'time_ago': 'Récemment'
            }

        except Exception as e:
            logger.debug(f"Erreur extraction Newimmo: {e}")
            return None

# Instance à importer
newimmo_scraper_real = NewimmoScraperReal()
