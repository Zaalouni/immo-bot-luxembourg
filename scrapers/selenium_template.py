
# scrapers/selenium_template.py
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import logging
from config import MAX_PRICE, MIN_ROOMS, MIN_SURFACE

logger = logging.getLogger(__name__)

class SeleniumScraperBase:
    def __init__(self, site_name, base_url, search_url):
        self.site_name = site_name
        self.base_url = base_url
        self.search_url = search_url

    def setup_driver(self):
        """Configurer le driver Selenium"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        return webdriver.Firefox(options=options)

    def parse_price(self, price_text):
        """Extraire le prix d'un texte"""
        if not price_text:
            return 0
        # Chercher tous les chiffres
        digits = re.findall(r'[\d\s]+', price_text.replace('.', '').replace(',', ''))
        if digits:
            try:
                return int(''.join(digits[0].split()))
            except:
                return 0
        return 0

    def parse_rooms(self, rooms_text):
        """Extraire le nombre de pièces"""
        if not rooms_text:
            return 0
        # Chercher explicitement "N chambres/pièces/rooms"
        match = re.search(r'(\d+)\s*(?:pièces|chambres|rooms|ch\.)', rooms_text, re.IGNORECASE)
        if match:
            val = int(match.group(1))
            if val < 20:  # Sanity check
                return val
        # Détection basique
        if 'studio' in rooms_text.lower():
            return 1
        return 0

    def parse_surface(self, surface_text):
        """Extraire la surface"""
        if not surface_text:
            return 0
        match = re.search(r'(\d+(?:,\d+)?)\s*m²', surface_text)
        if match:
            try:
                return int(float(match.group(1).replace(',', '.')))
            except:
                return 0
        return 0

    def extract_listing_data(self, element):
        """À implémenter pour chaque site - extraire données d'une annonce"""
        raise NotImplementedError

    def find_listings_elements(self, driver):
        """À implémenter - trouver les éléments des annonces"""
        raise NotImplementedError

    def scrape(self):
        """Méthode principale de scraping"""
        driver = None
        try:
            driver = self.setup_driver()
            logger.info(f"🟡 {self.site_name}: Chargement {self.search_url}")
            driver.get(self.search_url)

            # Attendre que la page soit chargée
            time.sleep(5)

            # Faire défiler pour charger plus d'annonces
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

            # Trouver les annonces
            listings_elements = self.find_listings_elements(driver)
            logger.info(f"🔍 {self.site_name}: {len(listings_elements)} éléments trouvés")

            # Extraire les données
            listings = []
            for elem in listings_elements:
                try:
                    listing_data = self.extract_listing_data(elem)
                    if listing_data:
                        listings.append(listing_data)
                except Exception as e:
                    logger.debug(f"Erreur extraction: {e}")
                    continue

            logger.info(f"✅ {self.site_name}: {len(listings)} annonces valides")
            return listings

        except Exception as e:
            logger.error(f"❌ {self.site_name}: Erreur scraping - {e}")
            return []
        finally:
            if driver:
                driver.quit()
