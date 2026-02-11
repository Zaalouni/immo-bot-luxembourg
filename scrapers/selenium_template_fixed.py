
# scrapers/selenium_template_fixed.py
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
import time
import re
import logging
from config import MAX_PRICE, MIN_ROOMS, CITIES  # IMPORT CORRIGÉ

logger = logging.getLogger(__name__)

class SeleniumScraperFixed:
    def __init__(self, site_name, base_url, search_url):
        self.site_name = site_name
        self.base_url = base_url
        self.search_url = search_url

    def setup_driver(self):
        """Configurer le driver Selenium"""
        options = Options()
        options.add_argument('--headless')
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
        """À implémenter dans chaque scraper"""
        raise NotImplementedError
