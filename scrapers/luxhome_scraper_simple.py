
# scrapers/luxhome_scraper_simple.py - CORRIGÉ
import logging
import time  # AJOUTER CETTE LIGNE
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
import re
from config import MAX_PRICE, MIN_ROOMS, CITIES

logger = logging.getLogger(__name__)

class LuxhomeScraperSimple:
    def __init__(self):
        self.site_name = "Luxhome.lu"
        self.base_url = "https://www.luxhome.lu"
        self.search_url = "https://www.luxhome.lu/louer"

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
        digits = re.findall(r'[\d\s]+', price_text.replace('.', '').replace(',', ''))
        if digits:
            try:
                return int(''.join(digits[0].split()))
            except:
                return 0
        return 0

    def scrape(self):
        driver = None
        try:
            driver = self.setup_driver()
            logger.info(f"🟡 Début scraping {self.site_name}")
            logger.info(f"📡 URL: {self.search_url}")

            driver.get(self.search_url)
            time.sleep(8)  # Attendre plus longtemps

            # Prendre un screenshot pour debug
            driver.save_screenshot('/tmp/luxhome_screenshot.png')
            logger.info("📸 Screenshot: /tmp/luxhome_screenshot.png")

            # Chercher des éléments avec texte '€'
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), '€')]")
            logger.info(f"💰 Éléments avec '€': {len(elements)}")

            # Voir les 5 premiers éléments
            for i, elem in enumerate(elements[:5]):
                text = elem.text.strip()
                if text and len(text) < 100:
                    logger.info(f"  {i+1}. {text}")

            # Chercher des liens
            links = driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"🔗 Liens totaux: {len(links)}")

            # Chercher des titres h2, h3
            titles = driver.find_elements(By.TAG_NAME, "h2") + driver.find_elements(By.TAG_NAME, "h3")
            logger.info(f"📰 Titres (h2/h3): {len(titles)}")

            for i, title in enumerate(titles[:3]):
                if title.text.strip():
                    logger.info(f"  Titre {i+1}: {title.text[:50]}...")

            # Retourner des données de test
            return [
                {
                    'listing_id': 'luxhome_test_1',
                    'site': 'Luxhome.lu',
                    'title': 'Appartement test Luxembourg',
                    'city': 'Luxembourg',
                    'price': 1800,
                    'rooms': 3,
                    'surface': 75,
                    'url': 'https://www.luxhome.lu/test',
                    'time_ago': 'Récemment'
                }
            ]

        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
        finally:
            if driver:
                driver.quit()

# Instance à importer
luxhome_scraper_simple = LuxhomeScraperSimple()
