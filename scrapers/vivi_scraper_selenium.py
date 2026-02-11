
# scrapers/vivi_scraper_selenium.py
# Scraper RÉEL pour VIVI.lu avec Selenium
import logging
import re
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from config import MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class ViviScraperSelenium:
    def __init__(self):
        self.base_url = "https://www.vivi.lu"
        # Chercher appartements ET maisons
        self.search_urls = [
            f"{self.base_url}/fr/location/appartement",
            f"{self.base_url}/fr/location/maison"
        ]
        self.site_name = "VIVI.lu"

    def scrape(self):
        """Scraper VIVI.lu avec Selenium - Appartements + Maisons"""
        listings = []
        driver = None

        try:
            # Configuration Firefox headless
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            driver = webdriver.Firefox(options=options)
            driver.set_page_load_timeout(20)

            # Scraper appartements ET maisons
            for search_url in self.search_urls:
                try:
                    logger.info(f"Chargement {search_url}")
                    driver.get(search_url)

                    # Attendre chargement JavaScript
                    import time
                    time.sleep(8)

                    # Extraire cartes annonces
                    cards = driver.find_elements(By.CLASS_NAME, 'vivi-property')
                    logger.info(f"  Annonces trouvées: {len(cards)}")

                    for card in cards[:15]:  # Limiter à 15 par type
                        try:
                            listing = self._extract_listing(card)
                            if listing and self._matches_criteria(listing):
                                listings.append(listing)
                        except Exception as e:
                            logger.debug(f"  Erreur extraction: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"  Erreur URL {search_url}: {e}")
                    continue

            logger.info(f"✅ {len(listings)} annonces après filtrage")
            return listings

        except Exception as e:
            logger.error(f"❌ Scraping VIVI.lu: {e}")
            return []

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def _extract_listing(self, card):
        """Extraire données d'une carte annonce"""
        # URL et ID
        url = card.get_attribute('href')
        data_id = card.get_attribute('data-id')

        if not url or not data_id:
            return None

        # Texte complet
        text = card.text
        if not text:
            return None

        # Titre (première ligne)
        title = text.split('\n')[0].strip() if text else 'Annonce VIVI.lu'

        # Prix - Analyse ligne par ligne pour éviter capture chiffres parasites
        price = 0
        for line in text.split('\n'):
            if '€' in line:
                # Extraire tous les chiffres de cette ligne uniquement
                price_digits = re.sub(r'[^\d]', '', line)
                if price_digits:
                    try:
                        price = int(price_digits)
                        break  # Première ligne avec € trouvée
                    except ValueError:
                        continue

        if price <= 0:
            logger.debug(f"Prix non trouvé dans: {text[:100]}")
            return None

        # Chambres
        rooms = 1
        rooms_match = re.search(r'(\d+)\s*chambres?', text, re.IGNORECASE)
        if rooms_match:
            rooms = int(rooms_match.group(1))

        # Surface
        surface = 0
        surface_match = re.search(r'(\d+)\s*m[²2]', text)
        if surface_match:
            surface = int(surface_match.group(1))

        # Ville (extraire depuis URL)
        city = self._extract_city(url)

        return {
            'listing_id': f'vivi_{data_id}',
            'site': self.site_name,
            'title': title[:80],
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'time_ago': 'Récemment'
        }

    def _extract_city(self, url):
        """Extraire ville depuis URL"""
        # URL format: /propriete/lieu/TYPE/VILLE/titre/id
        # Index:      0  1  2  3  4  5   6    7      8     9
        parts = url.split('/')
        if len(parts) >= 8:
            city_slug = parts[7]  # Ville à l'index 7
            # Convertir slug en nom ville
            city = city_slug.replace('-', ' ').title()
            return city
        return 'Luxembourg'

    def _matches_criteria(self, listing):
        """Vérifier critères filtrage"""
        try:
            # Prix
            if listing['price'] > MAX_PRICE or listing['price'] <= 0:
                return False

            # Chambres
            if listing['rooms'] < MIN_ROOMS:
                return False

            return True
        except:
            return False

vivi_scraper_selenium = ViviScraperSelenium()
