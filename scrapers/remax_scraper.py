# =============================================================================
# scrapers/remax_scraper.py — Scraper RE/MAX.lu via Selenium
# =============================================================================
# Methode : Selenium + DOM rendu (React/MUI, besoin JS execution)
# URL     : https://www.remax.lu/listings?TransactionTypeUID=260 (location)
# Liens   : <a href="/fr-lu/mandats-de-vente/{type}/a-louer/{city}/{id}">
# Prix    : span.card-first-price ("2.100 €")
# Rooms/Surface : extraits depuis le texte de la carte (ordre : rooms, surface)
# Pagination : &page=N jusqu'a 5 pages
# Types acceptes : appartement, maison, duplex, loft, studio, penthouse, villa
# Instance globale : remax_scraper
# =============================================================================
import re
import time
import logging
from scrapers.selenium_template import SeleniumScraperBase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from filters import matches_criteria

logger = logging.getLogger(__name__)

SEARCH_URL    = 'https://www.remax.lu/listings?TransactionTypeUID=260'
ALLOWED_TYPES = {'appartement', 'maison', 'duplex', 'loft', 'studio', 'penthouse', 'villa'}
MAX_PAGES     = 5
WAIT_REACT    = 12  # secondes pour le rendu React


class RemaxScraper(SeleniumScraperBase):

    def __init__(self):
        super().__init__(
            site_name="Remax.lu",
            base_url="https://www.remax.lu",
            search_url=SEARCH_URL
        )

    # ── helpers ──────────────────────────────────────────────────────────────

    def _parse_remax_price(self, text):
        """Extraire le prix depuis '2.100 € mensuellement' ou '1 800 €'"""
        if not text:
            return 0
        cleaned = text.replace('.', '').replace('\xa0', '').replace(' ', '')
        m = re.search(r'(\d+)', cleaned)
        if m:
            try:
                val = int(m.group(1))
                if 200 <= val <= 50000:
                    return val
            except ValueError:
                pass
        return 0

    def _parse_city_from_url(self, href):
        """Extraire la ville depuis l'URL
        /fr-lu/mandats-de-vente/appartement/a-louer/luxembourg/slug → Luxembourg"""
        m = re.search(r'/a-louer/([^/]+)/', href)
        if m:
            return m.group(1).replace('-', ' ').title()
        return 'Luxembourg'

    def _parse_type_from_url(self, href):
        """Extraire le type de bien depuis l'URL"""
        m = re.search(r'/mandats-de-vente/([^/]+)/', href)
        return m.group(1) if m else ''

    def _parse_listing_id(self, href):
        """Extraire l'ID depuis la fin de l'URL
        .../luxembourg/280221031-193 → remax_280221031-193
        .../luxembourg/rue-de-cessange-315-1321/ → remax_rue-de-cessange-315-1321"""
        parts = href.rstrip('/').split('/')
        slug = parts[-1] if parts else 'unknown'
        return f"remax_{slug}"

    def _extract_rooms_surface(self, card_element):
        """Extraire rooms et surface depuis le texte de la carte.
        Structure RE/MAX : prix, rooms, bathrooms, floor, surface, type, city"""
        rooms   = 0
        surface = 0
        try:
            # Essayer les selectors CSS d'abord
            for sel in ['[class*="room"]', '[class*="chambre"]', '[class*="bed"]']:
                try:
                    el = card_element.find_element(By.CSS_SELECTOR, sel)
                    m = re.search(r'(\d+)', el.text)
                    if m:
                        val = int(m.group(1))
                        if 0 < val <= 15:
                            rooms = val
                            break
                except NoSuchElementException:
                    continue

            for sel in ['[class*="surface"]', '[class*="area"]', '[class*="m2"]', '[class*="sqm"]']:
                try:
                    el = card_element.find_element(By.CSS_SELECTOR, sel)
                    m = re.search(r'(\d+(?:[.,]\d+)?)', el.text)
                    if m:
                        val = int(float(m.group(1).replace(',', '.')))
                        if 10 <= val <= 2000:
                            surface = val
                            break
                except NoSuchElementException:
                    continue

            # Fallback : parser le texte brut de la carte
            if rooms == 0 or surface == 0:
                full_text = card_element.text
                # Supprimer le prix (ex: "2.100 € mensuellement")
                text_clean = re.sub(r'[\d\.,\s]+€[^\n]*', '', full_text)
                # Chercher tous les nombres
                numbers = [int(float(n.replace(',', '.')))
                           for n in re.findall(r'\b(\d+(?:[.,]\d+)?)\b', text_clean)]
                numbers = [n for n in numbers if n > 0]

                for n in numbers:
                    if rooms == 0 and 1 <= n <= 15:
                        rooms = n
                for n in reversed(numbers):
                    if surface == 0 and 20 <= n <= 2000:
                        surface = n

        except Exception as e:
            logger.debug(f"Erreur extraction rooms/surface: {e}")

        return rooms, surface

    def _extract_image_from_ancestors(self, driver, link):
        """Chercher l'image dans les ancetres du <a> — sur Remax React l'image
        est dans un div parent/frere du lien, pas a l'interieur du <a>."""
        try:
            # Remonter jusqu'a 4 niveaux dans le DOM
            for xpath in ['..', '../..', '../../..', '../../../..']:
                try:
                    ancestor = link.find_element(By.XPATH, xpath)
                    # background-image CSS
                    for el in ancestor.find_elements(By.CSS_SELECTOR, '[style*="background-image"]'):
                        style = el.get_attribute('style') or ''
                        m = re.search(r'url\(["\']?(https?://[^"\')\s]+)["\']?\)', style)
                        if m and 'placeholder' not in m.group(1) and 'data:' not in m.group(1):
                            return m.group(1)
                    # <img> dans l'ancetre
                    for img in ancestor.find_elements(By.CSS_SELECTOR, 'img'):
                        for attr in ['data-src', 'data-lazy-src', 'src']:
                            val = img.get_attribute(attr) or ''
                            if (val.startswith('http') and not val.startswith('data:')
                                    and not val.endswith('.svg') and 'placeholder' not in val):
                                return val
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _extract_image(self, card_element):
        """Fallback : chercher image directement dans l'element (utilise si pas de driver disponible)"""
        try:
            for img in card_element.find_elements(By.CSS_SELECTOR, 'img'):
                for attr in ['data-src', 'data-lazy-src', 'src']:
                    val = img.get_attribute(attr) or ''
                    if val.startswith('http') and not val.startswith('data:') and not val.endswith('.svg'):
                        return val
            for el in card_element.find_elements(By.CSS_SELECTOR, '[style*="background-image"]'):
                style = el.get_attribute('style') or ''
                m = re.search(r'url\(["\']?(https?://[^"\')\s]+)["\']?\)', style)
                if m:
                    return m.group(1)
        except Exception:
            pass
        return None

    # ── scrape principal ──────────────────────────────────────────────────────

    def scrape(self):
        driver = None
        try:
            driver = self.setup_driver()
            all_listings = {}   # url → listing dict (dedup)
            cookies_done = False

            for page_num in range(1, MAX_PAGES + 1):
                page_url = f"{SEARCH_URL}&page={page_num}" if page_num > 1 else SEARCH_URL
                logger.info(f"🟡 {self.site_name}: page {page_num} — {page_url}")

                driver.get(page_url)
                time.sleep(3)

                # Cookies (une seule fois)
                if not cookies_done:
                    for text in ['Allow all', 'Allow All']:
                        try:
                            btn = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, f"//button[contains(text(), '{text}')]")
                                )
                            )
                            btn.click()
                            time.sleep(1)
                            cookies_done = True
                            break
                        except TimeoutException:
                            continue

                # Attendre rendu React
                logger.info(f"   Attente rendu React ({WAIT_REACT}s)...")
                time.sleep(WAIT_REACT)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)

                # Trouver tous les liens d'annonces residentielles
                links = driver.find_elements(
                    By.CSS_SELECTOR,
                    "a[href*='/fr-lu/mandats-de-vente/'][href*='/a-louer/']"
                )

                new_count = 0
                for link in links:
                    href = link.get_attribute('href') or ''
                    if not href or href in all_listings:
                        continue

                    prop_type = self._parse_type_from_url(href)
                    if prop_type not in ALLOWED_TYPES:
                        continue

                    try:
                        # Prix depuis span.card-first-price dans la carte
                        price_el  = link.find_element(By.CSS_SELECTOR, 'span.card-first-price')
                        price_txt = price_el.text
                    except NoSuchElementException:
                        price_txt = link.text

                    price = self._parse_remax_price(price_txt)
                    if price <= 0:
                        continue

                    city             = self._parse_city_from_url(href)
                    listing_id       = self._parse_listing_id(href)
                    rooms, surface   = self._extract_rooms_surface(link)
                    image_url        = self._extract_image_from_ancestors(driver, link)
                    title_type       = prop_type.capitalize()
                    title            = f"{title_type} à louer — {city}"

                    # Date de disponibilite
                    from utils import extract_available_from
                    full_text = link.text[:500]
                    available_from = extract_available_from(full_text)

                    listing = {
                        'listing_id':   listing_id,
                        'site':         'Remax.lu',
                        'title':        title,
                        'city':         city,
                        'price':        price,
                        'rooms':        rooms,
                        'surface':      surface,
                        'url':          href,
                        'image_url':    image_url,
                        'latitude':     None,
                        'longitude':    None,
                        'distance_km':  None,
                        'available_from': available_from,
                        'time_ago':     'Recemment',
                        'full_text':    full_text,
                    }

                    if matches_criteria(listing):
                        all_listings[href] = listing
                        new_count += 1

                logger.info(f"   Page {page_num}: {new_count} nouvelles annonces (total {len(all_listings)})")

                if new_count == 0:
                    logger.info(f"   Fin pagination a la page {page_num}")
                    break

            listings = list(all_listings.values())
            logger.info(f"✅ {self.site_name}: {len(listings)} annonces valides")
            return listings

        except Exception as e:
            logger.error(f"❌ {self.site_name}: {e}")
            return []
        finally:
            if driver:
                driver.quit()

    def find_listings_elements(self, driver):
        return []

    def extract_listing_data(self, element):
        return None


remax_scraper = RemaxScraper()
