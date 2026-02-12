
# scrapers/wortimmo_scraper.py
# Scraper pour Wortimmo.lu (Luxemburger Wort immobilier)
# Les annonces sont chargées par AJAX → Selenium nécessaire
import logging
import re
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from config import MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class WortimmoScraper:
    """Scraper pour Wortimmo.lu via Selenium (contenu AJAX)"""

    def __init__(self):
        self.base_url = 'https://www.wortimmo.lu'
        self.search_url = 'https://www.wortimmo.lu/en/rent'
        self.site_name = 'Wortimmo.lu'

    def scrape(self):
        """Scraper les annonces de location"""
        listings = []
        driver = None

        try:
            logger.info(f"🔍 Scraping {self.site_name} (Selenium)...")

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            driver = webdriver.Firefox(options=options)
            driver.set_page_load_timeout(30)

            logger.info(f"   Chargement {self.search_url}")
            driver.get(self.search_url)

            import time
            time.sleep(8)

            # Accepter cookies si popup
            try:
                cookie_btns = driver.find_elements(By.CSS_SELECTOR,
                    '[id*="accept"], [class*="accept"], button[data-action="accept"]')
                if cookie_btns:
                    cookie_btns[0].click()
                    time.sleep(1)
            except Exception:
                pass

            # Scroll pour charger toutes les annonces
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight*2/3);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Chercher les cartes d'annonces
            # Wortimmo utilise des liens <a> avec images et prix dans serp-results-container
            cards = driver.find_elements(By.CSS_SELECTOR, '.serp-results-container-box a[href*="/en/rent/"]')
            if not cards:
                cards = driver.find_elements(By.CSS_SELECTOR, '.serp-results-container a[href*="/rent/"]')
            if not cards:
                cards = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/en/rent/"][href*="/property/"]')
            if not cards:
                # Fallback: tous les liens avec images wortimmo
                all_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/en/rent/"]')
                cards = [l for l in all_links if l.text.strip() and '€' in l.text]

            if not cards:
                # Dernier fallback: chercher divs avec prix
                page_source = driver.page_source
                logger.info(f"   Page source: {len(page_source)} chars")

                # Chercher pattern prix dans le HTML rendu
                price_links = re.findall(
                    r'href="(https?://www\.wortimmo\.lu/en/rent/[^"]+)"',
                    page_source
                )
                if not price_links:
                    price_links = re.findall(r'href="(/en/rent/[^"]+/property/\d+[^"]*)"', page_source)

                logger.info(f"   Liens rent trouvés dans source: {len(price_links)}")

                if price_links:
                    # Extraire depuis le HTML rendu
                    return self._extract_from_source(page_source, price_links)

            logger.info(f"   🔍 {len(cards)} cartes trouvées")

            for card in cards[:20]:
                try:
                    listing = self._extract_listing_selenium(card)
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

    def _extract_listing_selenium(self, card):
        """Extraire données d'une carte Selenium"""
        url = card.get_attribute('href') or ''
        if '/rent/' not in url:
            return None

        # ID depuis URL
        id_match = re.search(r'/property/(\d+)', url)
        if not id_match:
            id_match = re.search(r'/(\d{5,})', url)
        listing_id = id_match.group(1) if id_match else url.rstrip('/').split('/')[-1]

        if not listing_id or len(str(listing_id)) < 3:
            return None

        text = card.text or ''
        if not text:
            return None

        # Prix
        price = 0
        for line in text.split('\n'):
            if '€' in line:
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

        # Titre
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        title = lines[0] if lines else 'Annonce Wortimmo'

        # Chambres
        rooms = 0
        rooms_match = re.search(r'(\d+)\s*(?:chambre|pièce|room|bedroom|ch\.)', text, re.IGNORECASE)
        if rooms_match:
            rooms = int(rooms_match.group(1))

        # Surface
        surface = 0
        surface_match = re.search(r'(\d+)\s*m[²2]', text)
        if surface_match:
            surface = int(surface_match.group(1))

        # Ville depuis URL
        city = self._extract_city(url)

        # Image
        image_url = None
        try:
            img = card.find_element(By.CSS_SELECTOR, 'img')
            image_url = img.get_attribute('src') or img.get_attribute('data-src')
        except Exception:
            pass

        if not url.startswith('http'):
            url = self.base_url + url

        return {
            'listing_id': f'wortimmo_{listing_id}',
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

    def _extract_from_source(self, page_source, links):
        """Extraire depuis le HTML source rendu (fallback)"""
        listings = []
        seen_ids = set()

        for link_url in links[:20]:
            if link_url in seen_ids:
                continue
            seen_ids.add(link_url)

            full_url = link_url if link_url.startswith('http') else self.base_url + link_url

            # ID
            id_match = re.search(r'/property/(\d+)', link_url)
            if not id_match:
                id_match = re.search(r'/(\d{5,})', link_url)
            listing_id = id_match.group(1) if id_match else link_url.rstrip('/').split('/')[-1]

            # Chercher contexte autour du lien
            escaped_url = re.escape(link_url)
            context_match = re.search(
                rf'(.{{0,500}}){escaped_url}(.{{0,500}})',
                page_source, re.DOTALL
            )

            if not context_match:
                continue

            context = context_match.group(1) + context_match.group(2)
            context_text = re.sub(r'<[^>]+>', ' ', context)

            # Prix
            price = 0
            price_match = re.search(r'([\d\s\.]+)\s*€', context_text)
            if price_match:
                price_str = price_match.group(1).replace(' ', '').replace('.', '')
                try:
                    price = int(price_str)
                except ValueError:
                    pass

            if price <= 0 or price > 100000:
                continue

            # Ville
            city = self._extract_city(link_url)

            # Chambres
            rooms = 0
            rooms_match = re.search(r'(\d+)\s*(?:chambre|room|bedroom)', context_text, re.I)
            if rooms_match:
                rooms = int(rooms_match.group(1))

            # Surface
            surface = 0
            surface_match = re.search(r'(\d+)\s*m[²2]', context_text)
            if surface_match:
                surface = int(surface_match.group(1))

            listing = {
                'listing_id': f'wortimmo_{listing_id}',
                'site': self.site_name,
                'title': f'Annonce {city}',
                'city': city,
                'price': price,
                'rooms': rooms,
                'surface': surface,
                'url': full_url,
                'time_ago': 'Récemment'
            }

            if self._matches_criteria(listing):
                listings.append(listing)

        logger.info(f"✅ {len(listings)} annonces (source HTML)")
        return listings

    def _extract_city(self, url):
        """Extraire ville depuis URL Wortimmo"""
        # Pattern: /en/rent/TYPE/CITY/...
        parts = url.split('/')
        for i, part in enumerate(parts):
            if part == 'rent' and i + 2 < len(parts):
                city_slug = parts[i + 2]
                return city_slug.replace('-', ' ').title()
        return 'Luxembourg'

    def _matches_criteria(self, listing):
        """Vérifier critères"""
        try:
            if listing['price'] > MAX_PRICE or listing['price'] <= 0:
                return False
            rooms = listing.get('rooms', 0)
            if rooms > 0 and rooms < MIN_ROOMS:
                return False
            return True
        except Exception:
            return False

wortimmo_scraper = WortimmoScraper()
