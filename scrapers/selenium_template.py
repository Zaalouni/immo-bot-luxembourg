
# =============================================================================
# scrapers/selenium_template.py — Classe de base pour scrapers Selenium
# =============================================================================
# Classe SeleniumScraperBase heritee par : newimmo, unicorn (+ override scrape)
# Fonctionnalites :
#   - setup_driver() : Firefox headless en priorite, fallback Chrome si absent
#   - parse_price(text) : extrait prix depuis texte ("1 250 €" → 1250)
#   - parse_rooms(text) : extrait nombre de chambres
#   - parse_surface(text) : extrait surface (gere decimales : "52.00 m2")
#   - scrape() : methode generique (find_listings_elements → extract_listing_data)
#
# Les sous-classes doivent implementer :
#   - find_listings_elements(driver) → liste d'elements Selenium
#   - extract_listing_data(element) → dict listing ou None
# =============================================================================
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
        """Configurer le driver Selenium (Firefox, fallback Chrome)"""
        PAGE_LOAD_TIMEOUT = 30  # secondes max pour charger une page
        # Firefox en priorité
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            driver = webdriver.Firefox(options=options)
            driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            return driver
        except Exception as e:
            logger.warning(f"Firefox indisponible ({e}), tentative Chrome...")
        # Fallback Chrome
        try:
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            chrome_opts = ChromeOptions()
            chrome_opts.add_argument('--headless')
            chrome_opts.add_argument('--no-sandbox')
            chrome_opts.add_argument('--disable-dev-shm-usage')
            driver = webdriver.Chrome(options=chrome_opts)
            driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            return driver
        except Exception as e2:
            logger.error(f"Aucun navigateur disponible: {e2}")
            raise

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
        """Extraire la surface — gère 52.00 m², 52,5 m², 52 m²"""
        if not surface_text:
            return 0
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', surface_text)
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
