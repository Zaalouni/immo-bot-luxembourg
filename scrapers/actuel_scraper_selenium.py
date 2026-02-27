# =============================================================================
# scrapers/actuel_scraper_selenium.py — Scraper Actuel.lu via Selenium
# =============================================================================
# Méthode : Selenium Firefox headless contourne Cloudflare
# URL base : https://www.actuel.lu/rechercher?k=location
# Annonces : <div class="annonce_bien"> avec tous les infos
#           - URL: <a href="...">
#           - Type: <div class="listing_nature">
#           - Ville: <div class="listing_ville">
#           - Chambres: <span>X Chambre(s)</span>
#           - Surface: <p>+/- XYZ m²</p>
#           - Prix: <p>XXXX €</p> + <span>Charges: YYY €</span>
#           - Image: background-image url('img/...')
# Pagination : ?paging=2, ?paging=3, etc.
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE,
#            EXCLUDED_WORDS, EXCLUDED_CITIES
# Instance globale : actuel_scraper_selenium
# =============================================================================
import logging
import re
import time
import random
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from config import MAX_PRICE, MIN_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS, EXCLUDED_CITIES, SCRAPER_TIMEOUTS, SCRAPER_SLEEP_CONFIG
from utils import validate_listing_data

logger = logging.getLogger(__name__)

MAX_PAGES = 3
TIMEOUT_SELENIUM = SCRAPER_TIMEOUTS.get('cloudflare', 60)
CLOUDFLARE_WAIT = SCRAPER_SLEEP_CONFIG.get('cloudflare_wait', 8)
SLEEP_BETWEEN_PAGES = SCRAPER_SLEEP_CONFIG.get('between_pages', (1, 2))


class ActuelScraperSelenium:
    """Scraper Actuel.lu via Selenium (contourne Cloudflare)"""

    def __init__(self):
        self.base_url = "https://www.actuel.lu"
        self.list_url = f"{self.base_url}/rechercher?k=location"
        self.site_name = "Actuel.lu"

    def scrape(self):
        """Scraper Actuel.lu avec Selenium — locations"""
        listings = []
        driver = None

        try:
            # Configuration Firefox headless
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            driver = webdriver.Firefox(options=options)
            driver.set_page_load_timeout(TIMEOUT_SELENIUM)

            seen_ids = set()

            for page_num in range(1, MAX_PAGES + 1):
                # Page 1: URL base, pages suivantes: ?paging=N
                if page_num == 1:
                    url = self.list_url
                else:
                    url = f"{self.list_url}&paging={page_num}"

                logger.info(f"[Actuel.lu] Chargement page {page_num}: {url}")

                try:
                    driver.get(url)
                    # Attendre le chargement Cloudflare et JS (config centralisée)
                    time.sleep(CLOUDFLARE_WAIT)
                except TimeoutException:
                    logger.warning(f"  Timeout Selenium page {page_num}")
                    break
                except Exception as e:
                    logger.warning(f"  Erreur chargement page {page_num}: {type(e).__name__}")
                    break

                # Extraire les annonces
                try:
                    annonces = driver.find_elements(By.CLASS_NAME, 'annonce_bien')
                    logger.info(f"  Page {page_num}: {len(annonces)} annonces trouvées")

                    if not annonces:
                        break

                    new_count = 0
                    for annonce in annonces:
                        try:
                            listing = self._extract_listing(annonce)
                            if listing:
                                lid = listing['listing_id']
                                if lid not in seen_ids:
                                    seen_ids.add(lid)
                                    if self._matches_criteria(listing):
                                        try:
                                            validated = validate_listing_data(listing)
                                            listings.append(validated)
                                            new_count += 1
                                        except (ValueError, KeyError) as ve:
                                            logger.debug(f"  Validation échouée: {ve}")
                        except StaleElementReferenceException:
                            # Element became stale, skip
                            logger.debug(f"  Element stale, skip")
                            continue
                        except Exception as e:
                            logger.debug(f"  Erreur extraction annonce: {type(e).__name__}")
                            continue

                    logger.info(f"  Page {page_num}: {new_count} nouvelles annonces après filtrage")

                    if new_count == 0:
                        break

                    if page_num < MAX_PAGES:
                        # Sleep aléatoire entre pages
                        sleep_min, sleep_max = SLEEP_BETWEEN_PAGES
                        sleep_delay = random.uniform(sleep_min, sleep_max)
                        time.sleep(sleep_delay)

                except (TimeoutException, Exception) as e:
                    logger.warning(f"  Erreur parsing page {page_num}: {type(e).__name__}")
                    break

            logger.info(f"✅ Actuel.lu: {len(listings)} annonces apres filtrage")
            return listings

        except Exception as e:
            logger.error(f"❌ Scraping Actuel.lu: {e}")
            return []

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def _extract_listing(self, annonce_elem):
        """Extraire données d'une annonce"""
        try:
            # Ref depuis l'ID du div: "bien_listing5762" → "5762"
            elem_id = annonce_elem.get_attribute('id')
            ref_match = re.search(r'bien_listing(\d+)', elem_id)
            if not ref_match:
                return None
            ref = ref_match.group(1)

            # URL depuis le lien <a href="...">
            link_elem = annonce_elem.find_element(By.TAG_NAME, 'a')
            href = link_elem.get_attribute('href') or ''
            if not href:
                return None

            # URL complète
            if href.startswith('http'):
                full_url = href
            else:
                full_url = f"{self.base_url}/{href}"

            # Type: <div class="listing_nature">
            try:
                type_elem = annonce_elem.find_element(By.CLASS_NAME, 'listing_nature')
                prop_type = type_elem.text.strip()
            except (NoSuchElementException, AttributeError, StaleElementReferenceException):
                prop_type = 'Appartement'

            # Ville: <div class="listing_ville">
            try:
                ville_elem = annonce_elem.find_element(By.CLASS_NAME, 'listing_ville')
                city = ville_elem.text.strip()
            except (NoSuchElementException, AttributeError, StaleElementReferenceException):
                city = 'Luxembourg'

            # Titre
            title = f"{prop_type} — {city}"

            # Chambres: chercher <span>X Chambre(s)</span>
            rooms = 0
            try:
                all_text = annonce_elem.text
                rooms_match = re.search(r'(\d+)\s*Chambre\(s\)', all_text, re.IGNORECASE)
                if rooms_match:
                    rooms = int(rooms_match.group(1))
            except (ValueError, AttributeError, StaleElementReferenceException):
                rooms = 0

            # Surface: chercher <p>+/- XYZ m²</p>
            surface = 0
            try:
                all_text = annonce_elem.text
                surface_match = re.search(r'\+/?-?\s*([\d\.]+)\s*m[²2]', all_text)
                if surface_match:
                    surface = int(float(surface_match.group(1).replace(',', '.')))
            except (ValueError, AttributeError, StaleElementReferenceException):
                surface = 0

            # Prix: chercher <p>XXXX €</p>
            price = 0
            try:
                all_text = annonce_elem.text
                # Chercher le premier nombre suivi de € (pas dans "Charges")
                price_lines = all_text.split('\n')
                for line in price_lines:
                    if '€' in line and 'Charges' not in line:
                        price_match = re.search(r'([\d\s\.]+)\s*€', line)
                        if price_match:
                            price_str = re.sub(r'[^\d]', '', price_match.group(1))
                            if price_str:
                                price = int(price_str)
                                break
            except (ValueError, AttributeError, StaleElementReferenceException):
                price = 0

            if price <= 0:
                return None

            # Image: chercher style="background: url('img/...')"
            image_url = None
            try:
                img_div = annonce_elem.find_element(By.CSS_SELECTOR, 'div[style*="background"]')
                style = img_div.get_attribute('style') or ''
                img_match = re.search(r"url\('([^']+)'\)", style)
                if img_match:
                    img_path = img_match.group(1)
                    # Convertir "img/5762_1.jpg" en URL complète
                    if not img_path.startswith('http'):
                        image_url = f"{self.base_url}/{img_path}"
                    else:
                        image_url = img_path
            except (NoSuchElementException, AttributeError, StaleElementReferenceException):
                pass

            # Full text pour filtrage mots exclus
            text = annonce_elem.text.lower()

            return {
                'listing_id': f'actuel_{ref}',
                'site': self.site_name,
                'title': title[:80],
                'city': city,
                'price': price,
                'rooms': rooms,
                'surface': surface,
                'url': full_url,
                'image_url': image_url,
                'time_ago': 'Récemment',
                'full_text': text[:300],
            }

        except Exception as e:
            logger.debug(f"  Erreur extraction: {e}")
            return None

    def _matches_criteria(self, listing):
        """Vérifier critères filtrage"""
        try:
            # Prix
            price = listing.get('price', 0)
            if price <= 0 or price < MIN_PRICE or price > MAX_PRICE:
                return False

            # Chambres
            rooms = listing.get('rooms', 0) or 0
            if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                return False

            # Surface
            surface = listing.get('surface', 0) or 0
            if surface > 0 and surface < MIN_SURFACE:
                return False

            # Villes exclues
            if EXCLUDED_CITIES:
                city_check = listing.get('city', '').lower().strip()
                if city_check and any(excl in city_check or city_check in excl for excl in EXCLUDED_CITIES):
                    return False

            # Mots exclus
            check_text = (str(listing.get('title', '')) + ' ' + str(listing.get('full_text', ''))).lower()
            if any(w.strip().lower() in check_text for w in EXCLUDED_WORDS if w.strip()):
                return False

            return True
        except Exception:
            return False


actuel_scraper_selenium = ActuelScraperSelenium()
