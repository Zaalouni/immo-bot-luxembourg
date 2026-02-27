# =============================================================================
# scrapers/nexvia_scraper.py — Scraper Nexvia.lu via HTML BeautifulSoup
# =============================================================================
# Methode : requete HTTP GET sur page de recherche, extraction HTML via BS4
# Pagination : page unique (lazy-load), scrape tous les listings statiques
# Images : extraction depuis data-lazyloadedstyle background-image
# Structure : <a class="listings-item-wrapper"> avec infos completes
# Instance globale : nexvia_scraper
# =============================================================================
import requests
import re
import time
import logging
import random
from bs4 import BeautifulSoup
from requests.exceptions import RequestException, Timeout, ConnectionError
from config import MAX_PRICE, MIN_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS, USER_AGENTS, SCRAPER_TIMEOUTS, SCRAPER_SLEEP_CONFIG, RETRY_CONFIG
from utils import validate_listing_data, retry_with_backoff

logger = logging.getLogger(__name__)

TIMEOUT = SCRAPER_TIMEOUTS.get('default', 30)  # Fallback 30s si config manque
SLEEP_BETWEEN_PAGES = SCRAPER_SLEEP_CONFIG.get('between_pages', (1, 2))

class NexviaScraperLu:
    def __init__(self):
        self.base_url = "https://www.nexvia.lu/fr/rent"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def scrape(self):
        """Scraper Nexvia.lu via HTML statique"""
        try:
            logger.debug(f"Scraping {self.base_url}...")

            # Requete HTTP
            headers = {
                'User-Agent': random.choice(USER_AGENTS) if USER_AGENTS else self.headers['User-Agent'],
                'Referer': 'https://www.nexvia.lu',
            }
            response = retry_with_backoff(
                lambda: requests.get(self.base_url, headers=headers, timeout=TIMEOUT, verify=True),
                max_attempts=RETRY_CONFIG.get('max_attempts', 3),
                base_delay=RETRY_CONFIG.get('base_delay', 1),
                backoff_multiplier=RETRY_CONFIG.get('backoff_multiplier', 2),
                logger_obj=logger
            )

            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code}")
                return None

            # Parser HTML avec BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            listings = []

            # Chercher tous les listings
            listing_elements = soup.find_all('a', class_='listings-item-wrapper')
            logger.debug(f"Found {len(listing_elements)} listing elements")

            for elem in listing_elements:
                try:
                    listing = self._parse_listing(elem)
                    if listing:
                        listings.append(listing)
                except (AttributeError, ValueError, TypeError) as e:
                    logger.debug(f"Error parsing listing: {type(e).__name__}: {e}")
                    continue

            logger.info(f"Total: {len(listings)} listings")
            return listings if listings else None

        except Exception as e:
            logger.error(f"Scraping error: {e}")
            return None

    def _parse_listing(self, elem):
        """Extraire les infos d'une annonce"""
        try:
            # URL
            url = elem.get('href', '').strip()
            if not url or not url.startswith('http'):
                return None

            # Extraire listing_id depuis l'URL
            match = re.search(r'/(\d+)/', url)
            listing_id = match.group(1) if match else None
            if not listing_id:
                return None

            # Localité + rue (titre combiné)
            city_elem = elem.find('div', class_='listings-item-city-neighborhood')
            street_elem = elem.find('div', class_='listings-item-street')

            city = city_elem.text.strip() if city_elem else 'N/A'
            street = street_elem.text.strip() if street_elem else ''
            title = f"{street}, {city}" if street else city

            # Prix : chercher dans listing-item-right-label ou fallback sur tous les textes
            price_text = ''
            price_label = elem.find('span', class_='listings-item-right-label')
            if price_label:
                price_text = price_label.get_text(strip=True)

            # Fallback : chercher le texte contenant EUR/month
            if not price_text:
                for text in elem.stripped_strings:
                    if 'EUR' in text or 'month' in text.lower() or (text.replace(' ', '').replace(',', '').isdigit() and len(text) > 3):
                        price_text = text
                        break

            # Parser prix (format: "1 200 EUR" ou "2 150 / month")
            price = self._extract_price(price_text)
            if price is None:
                price = 0

            # Chambres : premier nombre dans les infos
            rooms = 0
            rooms_text = ''
            for elem_info in elem.find_all(['span', 'div']):
                text = elem_info.get_text(strip=True)
                if text and text.isdigit() and 0 < int(text) < 10:
                    rooms = int(text)
                    break

            # Surface : chercher "sqm" ou "m²"
            surface = 0
            for text in elem.stripped_strings:
                if 'sqm' in text.lower() or 'm²' in text.lower():
                    # Extraire le nombre avant sqm/m²
                    num_match = re.search(r'(\d+(?:\s|\s?\.|\s?,)?\d*)\s*(?:sqm|m²)', text.lower())
                    if num_match:
                        surface_str = num_match.group(1).replace(' ', '').replace('.', '').replace(',', '.')
                        try:
                            surface = int(float(surface_str))
                        except (ValueError, TypeError):
                            pass
                    break

            # Image : depuis data-lazyloadedstyle du header
            image_url = None
            img_header = elem.find('div', class_='listings-item-header')
            if img_header:
                style_attr = img_header.get('data-lazyloadedstyle', '') or img_header.get('style', '')
                # Extraire URL depuis background-image
                img_match = re.search(r"url\('([^']+)'\)", style_attr)
                if img_match:
                    image_url = img_match.group(1)

            # Extraire ville depuis city (format: "Luxembourg - Cessange")
            city_parts = city.split(' - ')
            city_name = city_parts[-1].strip() if city_parts else city

            # Construire le listing
            listing = {
                'listing_id': f"nexvia_{listing_id}",
                'site': 'Nexvia',
                'title': title[:200],
                'city': city_name,
                'price': price,
                'rooms': rooms,
                'surface': surface,
                'url': url,
                'image_url': image_url,
                'latitude': None,
                'longitude': None,
                'distance_km': None,
                'time_ago': 'N/A',
                'full_text': title,
            }

            return validate_listing_data(listing)

        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None

    def _extract_price(self, text):
        """Extraire le prix depuis le texte"""
        if not text:
            return None

        # Nettoyer le texte
        text = text.replace('\xa0', ' ').replace('\u202f', ' ')

        # Pattern 1: Format ancien "1200 EUR" ou "1 200 EUR" ou "1.200 EUR"
        match = re.search(r'(\d+(?:\s|\.|\,)?\d*)\s*EUR', text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(' ', '').replace('.', '').replace(',', '')
            try:
                return int(float(price_str))
            except (ValueError, TypeError):
                pass

        # Pattern 2: Format nouveau "2 150 / month" ou "2150 /month"
        match = re.search(r'(\d+(?:\s|\.|\,)?\d*)\s*[/÷]\s*month', text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(' ', '').replace('.', '').replace(',', '')
            try:
                return int(float(price_str))
            except (ValueError, TypeError):
                pass

        return None


# Instance globale
nexvia_scraper = NexviaScraperLu()
