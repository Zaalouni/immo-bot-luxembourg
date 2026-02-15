
# =============================================================================
# scrapers/immoweb_scraper.py — Scraper Immoweb.be section Luxembourg
# =============================================================================
# Methode : Selenium Firefox headless (Immoweb bloque les requetes HTTP → 403)
# Cible : section Luxembourg du site belge Immoweb.be
# Instance globale : immoweb_scraper
# =============================================================================
import logging
import re
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from config import MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class ImmowebScraper:
    """Scraper pour Immoweb.be — annonces Luxembourg via Selenium"""

    def __init__(self):
        self.base_url = 'https://www.immoweb.be'
        self.search_url = 'https://www.immoweb.be/en/search/apartment/for-rent?countries=LU&orderBy=newest'
        self.site_name = 'Immoweb.be'

    def scrape(self):
        """Scraper Immoweb.be avec Selenium"""
        listings = []
        driver = None

        try:
            logger.info(f"🔍 Scraping {self.site_name} (Selenium)...")

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            driver = webdriver.Firefox(options=options)
            driver.set_page_load_timeout(60)

            logger.info(f"   Chargement {self.search_url}")
            driver.get(self.search_url)

            import time
            time.sleep(8)

            # Accepter cookies si popup
            try:
                cookie_btn = driver.find_elements(By.CSS_SELECTOR, '[data-testid="uc-accept-all-button"], .didomi-continue-without-agreeing, #uc-btn-accept-banner')
                if cookie_btn:
                    cookie_btn[0].click()
                    time.sleep(2)
            except Exception:
                pass

            # Scroll pour charger plus
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Méthode 1: Chercher JSON dans page source (window.classified ou hydration)
            page_source = driver.page_source
            json_listings = self._extract_from_json(page_source)
            if json_listings:
                logger.info(f"✅ {len(json_listings)} annonces (JSON)")
                return json_listings

            # Méthode 2: Sélecteurs CSS Immoweb
            cards = driver.find_elements(By.CSS_SELECTOR, '.search-results__item')
            if not cards:
                cards = driver.find_elements(By.CSS_SELECTOR, '[class*="search-results"] article')
            if not cards:
                cards = driver.find_elements(By.CSS_SELECTOR, 'article[id^="classified_"]')
            if not cards:
                cards = driver.find_elements(By.CSS_SELECTOR, 'article')

            logger.info(f"   🔍 {len(cards)} cartes trouvées")

            for card in cards[:20]:
                try:
                    listing = self._extract_listing(card)
                    if listing and self._matches_criteria(listing):
                        listings.append(listing)
                except Exception as e:
                    logger.debug(f"   Erreur extraction: {e}")
                    continue

            logger.info(f"✅ {len(listings)} annonces après filtrage")
            return listings

        except Exception as e:
            logger.error(f"❌ Scraping {self.site_name}: {e}")
            return []

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _extract_from_json(self, page_source):
        """Extraire annonces depuis JSON embarqué dans la page"""
        import json

        listings = []

        # Chercher iw-search hydration data
        match = re.search(r'<iw-search[^>]*:results-storage="(\[.*?\])"', page_source, re.DOTALL)
        if match:
            try:
                import html
                json_str = html.unescape(match.group(1))
                items = json.loads(json_str)
                logger.info(f"   📊 iw-search contient {len(items)} annonces")
                for item in items[:20]:
                    listing = self._parse_json_item(item)
                    if listing and self._matches_criteria(listing):
                        listings.append(listing)
                return listings if listings else None
            except Exception as e:
                logger.debug(f"   iw-search parse error: {e}")

        # Chercher window.dataLayer ou __NEXT_DATA__
        for pattern in [
            r'window\.__NEXT_DATA__\s*=\s*(\{.*?\})\s*;?\s*</script>',
            r'"results"\s*:\s*(\[.*?\])\s*[,}]',
        ]:
            match = re.search(pattern, page_source, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    items = data if isinstance(data, list) else data.get('props', {}).get('pageProps', {}).get('results', [])
                    if items:
                        logger.info(f"   📊 JSON contient {len(items)} annonces")
                        for item in items[:20]:
                            listing = self._parse_json_item(item)
                            if listing and self._matches_criteria(listing):
                                listings.append(listing)
                        return listings if listings else None
                except Exception:
                    continue

        return None

    def _parse_json_item(self, item):
        """Parser un item JSON Immoweb"""
        try:
            listing_id = item.get('id', '')
            if not listing_id:
                return None

            # Prix
            price = 0
            price_obj = item.get('price', {})
            if isinstance(price_obj, dict):
                price = int(price_obj.get('mainValue', 0) or 0)
            elif isinstance(price_obj, (int, float)):
                price = int(price_obj)

            if price <= 0:
                return None

            # Propriété
            prop = item.get('property', {}) or {}

            # Titre
            title = prop.get('title', '') or item.get('title', '') or 'Appartement'

            # Ville
            location = prop.get('location', {}) or {}
            city = location.get('locality', '') or location.get('city', '') or 'Luxembourg'

            # Chambres
            rooms = int(prop.get('bedroomCount', 0) or 0)

            # Surface
            surface = int(prop.get('netHabitableSurface', 0) or 0)

            # Image
            media = item.get('media', {}) or {}
            pictures = media.get('pictures', []) or []
            image_url = pictures[0].get('smallUrl', '') if pictures else None

            # URL
            url = f'{self.base_url}/en/classified/{listing_id}'

            # GPS
            lat = location.get('latitude')
            lng = location.get('longitude')
            distance_km = None
            if lat and lng:
                try:
                    from utils import haversine_distance
                    from config import REFERENCE_LAT, REFERENCE_LNG
                    distance_km = haversine_distance(REFERENCE_LAT, REFERENCE_LNG, float(lat), float(lng))
                except Exception:
                    pass

            return {
                'listing_id': f'immoweb_{listing_id}',
                'site': self.site_name,
                'title': str(title)[:200],
                'city': str(city),
                'price': price,
                'rooms': rooms,
                'surface': surface,
                'url': url,
                'image_url': image_url,
                'latitude': lat,
                'longitude': lng,
                'distance_km': distance_km,
                'time_ago': 'Récemment'
            }
        except Exception as e:
            logger.debug(f"JSON item error: {e}")
            return None

    def _extract_listing(self, card):
        """Extraire données d'une carte Selenium"""
        try:
            # URL et ID
            link = None
            try:
                link = card.find_element(By.CSS_SELECTOR, '.card__title-link, a[href*="/classified/"]')
            except Exception:
                try:
                    link = card.find_element(By.CSS_SELECTOR, 'a')
                except Exception:
                    return None

            if not link:
                return None

            url = link.get_attribute('href') or ''
            if '/classified/' not in url:
                return None

            # ID depuis URL
            id_match = re.search(r'/(\d+)(?:\?|$)', url)
            listing_id = id_match.group(1) if id_match else url.rstrip('/').split('/')[-1]

            # Titre
            title = link.get_attribute('aria-label') or ''
            if not title:
                try:
                    title_elem = card.find_element(By.CSS_SELECTOR, 'h2, [class*="title"]')
                    title = title_elem.text
                except Exception:
                    title = 'Appartement'

            # Texte complet de la carte
            text = card.text or ''

            # Prix
            price = 0
            for line in text.split('\n'):
                if '€' in line:
                    price_digits = re.sub(r'[^\d]', '', line.split('€')[0])
                    if price_digits:
                        try:
                            price = int(price_digits)
                            if 100 < price < 100000:
                                break
                        except ValueError:
                            continue

            if price <= 0:
                return None

            # Chambres
            rooms = 0
            rooms_match = re.search(r'(\d+)\s*(?:bedroom|chambre|ch\.)', text, re.IGNORECASE)
            if rooms_match:
                rooms = int(rooms_match.group(1))

            # Surface
            surface = 0
            surface_match = re.search(r'(\d+)\s*m[²2]', text)
            if surface_match:
                surface = int(surface_match.group(1))

            # Ville
            city = 'Luxembourg'
            city_match = re.search(
                r'\b(Luxembourg|Esch|Differdange|Dudelange|Mersch|Ettelbruck|Diekirch|Wiltz|Clervaux|Remich|Grevenmacher|Arlon|Strassen|Bertrange|Hesperange)\b',
                text, re.IGNORECASE
            )
            if city_match:
                city = city_match.group(1).title()

            # Image
            image_url = None
            try:
                img = card.find_element(By.CSS_SELECTOR, 'img')
                image_url = img.get_attribute('src')
            except Exception:
                pass

            return {
                'listing_id': f'immoweb_{listing_id}',
                'site': self.site_name,
                'title': str(title)[:200],
                'city': city,
                'price': price,
                'rooms': rooms,
                'surface': surface,
                'url': url,
                'image_url': image_url,
                'time_ago': 'Récemment'
            }

        except Exception as e:
            logger.debug(f"Erreur extraction carte: {e}")
            return None

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

immoweb_scraper = ImmowebScraper()
