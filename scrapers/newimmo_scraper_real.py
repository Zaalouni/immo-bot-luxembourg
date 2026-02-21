
# =============================================================================
# scrapers/newimmo_scraper_real.py — Scraper Newimmo.lu via Selenium + regex
# =============================================================================
# Methode : herite de SeleniumScraperBase MAIS override scrape() completement.
#           Les selecteurs CSS du site changent souvent, donc on extrait
#           depuis page_source avec regex sur les liens d'annonces.
# Multi-URL : /fr/louer/appartement/ + /fr/louer/maison/
# Extraction : regex sur le HTML autour de chaque lien /fr/louer/TYPE/VILLE/ID-...
# Lien pattern : /fr/louer/appartement/beaufort/127259-appartement-beaufort/
# Ville : extraite depuis l'URL (4eme segment)
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS
# Instance globale : newimmo_scraper_real
# =============================================================================
import logging
import re
from scrapers.selenium_template import SeleniumScraperBase

logger = logging.getLogger(__name__)

class NewimmoScraperReal(SeleniumScraperBase):
    def __init__(self):
        super().__init__(
            site_name="Newimmo.lu",
            base_url="https://www.newimmo.lu",
            search_url="https://www.newimmo.lu/fr/louer/appartement/"
        )
        self.search_urls = [
            "https://www.newimmo.lu/fr/louer/appartement/",
            "https://www.newimmo.lu/fr/louer/maison/",
        ]

    def find_listings_elements(self, driver):
        """Non utilise — extraction via page_source"""
        return []

    def extract_listing_data(self, element):
        """Non utilise — extraction via page_source"""
        return None

    def scrape(self):
        """Override: extraire depuis page_source — appartements + maisons"""
        import time
        driver = None
        try:
            driver = self.setup_driver()
            all_links = set()
            combined_source = ''

            MAX_PAGES = 3
            for search_url in self.search_urls:
                type_label = search_url.rstrip('/').split('/')[-1]
                for page_num in range(1, MAX_PAGES + 1):
                    try:
                        page_url = f"{search_url}?page={page_num}" if page_num > 1 else search_url
                        logger.info(f"🟡 {self.site_name}: Chargement {page_url}")
                        driver.get(page_url)
                        time.sleep(8)
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)

                        page_source = driver.page_source
                        combined_source += '\n' + page_source

                        # Pattern: /fr/louer/TYPE/VILLE/ID-TYPE-VILLE/
                        links = re.findall(
                            r'href="(/fr/louer/(?:appartement|maison|studio|appartement-meuble|duplex|penthouse)/[^/]+/\d+-[^"]+)"',
                            page_source
                        )
                        new_links = set(links) - all_links
                        all_links.update(links)
                        logger.info(f"  {type_label} page {page_num}: {len(new_links)} nouvelles annonces")

                        if len(new_links) == 0:
                            break
                    except Exception as e:
                        logger.debug(f"Erreur {search_url} page {page_num}: {e}")
                        break

            logger.info(f"🔍 {self.site_name}: {len(all_links)} annonces uniques total")

            if not all_links:
                return []

            listings = []
            for link_path in all_links:
                try:
                    listing = self._extract_from_source(combined_source, link_path)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    logger.debug(f"Erreur extraction: {e}")
                    continue

            logger.info(f"✅ {self.site_name}: {len(listings)} annonces valides")
            return listings

        except Exception as e:
            logger.error(f"❌ {self.site_name}: {e}")
            return []
        finally:
            if driver:
                driver.quit()

    def _extract_from_source(self, page_source, link_path):
        """Extraire donnees d'une annonce depuis le HTML source"""
        full_url = f"https://www.newimmo.lu{link_path}"

        # ID depuis URL: /fr/louer/appartement/beaufort/127259-appartement-beaufort/
        id_match = re.search(r'/(\d+)-', link_path)
        listing_id = id_match.group(1) if id_match else str(abs(hash(link_path)))[:10]

        # Contexte HTML autour du lien
        pos = page_source.find(link_path)
        if pos == -1:
            return None

        start = max(0, pos - 1500)
        end = min(len(page_source), pos + 800)
        context = page_source[start:end]
        text = re.sub(r'<[^>]+>', ' ', context)
        text = re.sub(r'\s+', ' ', text)

        # Prix — "5 350€" ou "1 250 €" ou "1250 €"
        # Regex specifique pour eviter de capturer des IDs/references (ex: 127171)
        price = 0
        for m in re.finditer(r'(?<!\d)(\d{1,2}[\s\u202f\xa0]\d{3}|\d{3,5})(?!\d)\s*€', text):
            val_str = re.sub(r'[\s\u202f\xa0]', '', m.group(1))
            try:
                val = int(val_str)
                if 300 <= val <= 20000:
                    price = val
                    break
            except ValueError:
                continue
        if price <= 0:
            return None

        # Ville depuis URL — 5eme segment: /fr/louer/type/VILLE/id
        parts = link_path.strip('/').split('/')
        city = 'Luxembourg'
        if len(parts) >= 4:
            city = parts[3].replace('-', ' ').title()

        # Type de bien depuis URL — 3eme segment
        bien_type = 'Annonce'
        if len(parts) >= 3:
            bien_type = parts[2].replace('-', ' ').title()

        title = f"{bien_type} - {city}"

        # Chambres
        rooms = 0
        rooms_match = re.search(r'(\d+)\s*(?:chambre|pièce|room|ch\.)', text, re.I)
        if rooms_match:
            rooms = int(rooms_match.group(1))

        # Surface
        surface = 0
        surface_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', text)
        if surface_match:
            surface = int(float(surface_match.group(1).replace(',', '.')))

        # Image
        image_url = None
        img_match = re.search(
            r'<img[^>]+(?:src|data-src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
            context
        )
        if img_match:
            image_url = img_match.group(1)

        # Filtrer
        from config import MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS
        if price < MIN_PRICE or price > MAX_PRICE:
            return None
        if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
            return None
        if surface > 0 and surface < MIN_SURFACE:
            return None
        check_text = title.lower()
        if any(w.strip().lower() in check_text for w in EXCLUDED_WORDS if w.strip()):
            return None

        # Date de disponibilite
        from utils import extract_available_from
        available_from = extract_available_from(text)

        return {
            'listing_id': f'newimmo_{listing_id}',
            'site': 'Newimmo.lu',
            'title': str(title)[:200],
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': full_url,
            'image_url': image_url,
            'available_from': available_from,
            'time_ago': 'Récemment'
        }

# Instance à importer
newimmo_scraper_real = NewimmoScraperReal()
