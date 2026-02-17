
# =============================================================================
# scrapers/vivi_scraper_selenium.py — Scraper VIVI.lu via Selenium
# =============================================================================
# Methode : Selenium Firefox headless, charge la page de recherche,
#           scroll pour charger les cartes, extrait prix/chambres/surface
#           depuis le texte de chaque carte <a>
# Images : extraction <img> src/data-src depuis chaque carte
# full_text : stocke le texte complet pour filtrage mots exclus
# Ville : extraite depuis l'URL (/location/type/VILLE)
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS
# Instance globale : vivi_scraper_selenium
# =============================================================================
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

            import time
            MAX_PAGES = 3
            seen_ids = set()

            # Scraper appartements ET maisons avec pagination
            for search_url in self.search_urls:
                for page_num in range(1, MAX_PAGES + 1):
                    try:
                        page_url = f"{search_url}?page={page_num}" if page_num > 1 else search_url
                        logger.info(f"Chargement {page_url}")
                        driver.get(page_url)

                        # Attendre chargement JavaScript
                        time.sleep(8)

                        # Extraire cartes annonces
                        cards = driver.find_elements(By.CLASS_NAME, 'vivi-property')
                        logger.info(f"  Page {page_num}: {len(cards)} annonces")

                        if not cards:
                            break

                        new_count = 0
                        for card in cards:
                            try:
                                listing = self._extract_listing(card)
                                if listing and self._matches_criteria(listing):
                                    lid = listing['listing_id']
                                    if lid not in seen_ids:
                                        seen_ids.add(lid)
                                        listings.append(listing)
                                        new_count += 1
                            except Exception as e:
                                logger.debug(f"  Erreur extraction: {e}")
                                continue

                        if new_count == 0:
                            break

                    except Exception as e:
                        logger.warning(f"  Erreur page {page_num} {search_url}: {e}")
                        break

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

        # Chambres (0 = inconnu, pas 1 par défaut)
        rooms = 0
        rooms_match = re.search(r'(\d+)\s*chambres?', text, re.IGNORECASE)
        if rooms_match:
            rooms = int(rooms_match.group(1))

        # Surface
        surface = 0
        surface_match = re.search(r'(\d+)\s*m[²2]', text)
        if surface_match:
            surface = int(surface_match.group(1))

        # Image
        image_url = None
        try:
            img_elem = card.find_element(By.CSS_SELECTOR, 'img')
            image_url = img_elem.get_attribute('src') or img_elem.get_attribute('data-src')
        except Exception:
            pass

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
            'image_url': image_url,
            'full_text': text,
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
        """Vérifier critères filtrage complets"""
        try:
            from config import MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS

            price = listing.get('price', 0)
            if price <= 0 or price < MIN_PRICE or price > MAX_PRICE:
                return False

            rooms = listing.get('rooms', 0) or 0
            if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                return False

            surface = listing.get('surface', 0) or 0
            if surface > 0 and surface < MIN_SURFACE:
                return False

            # Vérifier mots exclus dans titre ET texte complet
            check_text = (str(listing.get('title', '')) + ' ' + str(listing.get('full_text', ''))).lower()
            if any(w.strip().lower() in check_text for w in EXCLUDED_WORDS if w.strip()):
                return False

            return True
        except Exception:
            return False

vivi_scraper_selenium = ViviScraperSelenium()
