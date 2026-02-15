
# scrapers/unicorn_scraper_real.py
# Scraper Unicorn.lu — URL corrigée /recherche/location/appartement
import logging
import re
from scrapers.selenium_template import SeleniumScraperBase
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

class UnicornScraperReal(SeleniumScraperBase):
    def __init__(self):
        super().__init__(
            site_name="Unicorn.lu",
            base_url="https://www.unicorn.lu",
            search_url="https://www.unicorn.lu/recherche/location/appartement"
        )
        # Chercher appartements ET maisons
        self.search_urls = [
            "https://www.unicorn.lu/recherche/location/appartement",
            "https://www.unicorn.lu/recherche/location/maison",
        ]

    def find_listings_elements(self, driver):
        """Trouver les éléments d'annonces — retourne des URLs uniques"""
        # Les <a> de Unicorn ont un texte vide (wrappers image)
        # On extrait depuis le page_source à la place
        return []  # Force le fallback vers scrape() override

    def extract_listing_data(self, element):
        """Non utilisé — extraction via page_source"""
        return None

    def scrape(self):
        """Override: extraire depuis page_source — appartements + maisons"""
        import time
        driver = None
        try:
            driver = self.setup_driver()
            all_links = set()
            all_sources = []

            for search_url in self.search_urls:
                try:
                    logger.info(f"🟡 {self.site_name}: Chargement {search_url}")
                    driver.get(search_url)
                    time.sleep(8)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)

                    page_source = driver.page_source
                    all_sources.append(page_source)

                    links = set(re.findall(r'href="(/detail-\d+-location-[^"]+)"', page_source))
                    new_links = links - all_links
                    all_links.update(links)
                    logger.info(f"  {search_url.split('/')[-1]}: {len(new_links)} nouvelles annonces")
                except Exception as e:
                    logger.debug(f"Erreur {search_url}: {e}")
                    continue

            logger.info(f"🔍 {self.site_name}: {len(all_links)} annonces uniques total")

            if not all_links:
                return []

            # Fusionner tous les sources pour l'extraction
            combined_source = '\n'.join(all_sources)

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
        """Extraire données d'une annonce depuis le HTML source"""
        full_url = f"https://www.unicorn.lu{link_path}"

        # ID: /detail-9278-location-...
        id_match = re.search(r'/detail-(\d+)', link_path)
        listing_id = id_match.group(1) if id_match else None
        if not listing_id:
            return None

        # Chercher le bloc HTML autour de ce lien (methode rapide sans regex lourd)
        pos = page_source.find(link_path)
        if pos == -1:
            return None

        start = max(0, pos - 2000)
        end = min(len(page_source), pos + 1000)
        context = page_source[start:end]
        text = re.sub(r'<[^>]+>', ' ', context)  # Strip HTML
        text = re.sub(r'\s+', ' ', text)  # Normalize spaces

        # Prix — "1 250€" ou "1250 €"
        price = 0
        price_match = re.search(r'([\d\s\.]+)\s*€', text)
        if price_match:
            price_str = price_match.group(1).replace(' ', '').replace('.', '')
            try:
                price = int(price_str)
            except ValueError:
                pass

        # Ignorer les charges
        if price <= 0 or price > 100000:
            return None

        # Chambres
        rooms = 0
        rooms_match = re.search(r'(\d+)\s*[Cc]hambre', text)
        if rooms_match:
            rooms = int(rooms_match.group(1))

        # Surface
        surface = 0
        surface_match = re.search(r'(\d+)\s*m[²2]', text)
        if surface_match:
            surface = int(surface_match.group(1))

        # Titre depuis URL: detail-9278-location-studio-esch-sur-alzette
        parts = link_path.split('-location-')
        if len(parts) > 1:
            title_slug = parts[1]
            title = title_slug.replace('-', ' ').title()
        else:
            title = 'Annonce Unicorn.lu'

        # Ville depuis URL — supprimer tous les mots-clés type de bien
        city = 'Luxembourg'
        type_words = r'(?:appartement|studio|maison|penthouse|duplex|loft|bureau|meuble|chambre|colocation|terrain|commerce|parking|garage)'
        location_match = re.search(rf'location-{type_words}(?:-{type_words})*-(.+)$', link_path)
        if not location_match:
            location_match = re.search(r'location-[^-]+-(.+)$', link_path)
        if location_match:
            city = location_match.group(1).replace('-', ' ').title()

        # Image — chercher img dans le contexte local
        image_url = None
        img_match = re.search(r'<img[^>]+(?:src|data-src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', context)
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
        title_lower = title.lower()
        if any(w.strip().lower() in title_lower for w in EXCLUDED_WORDS if w.strip()):
            return None

        return {
            'listing_id': f'unicorn_{listing_id}',
            'site': 'Unicorn.lu',
            'title': str(title)[:200],
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': full_url,
            'image_url': image_url,
            'time_ago': 'Récemment'
        }

unicorn_scraper_real = UnicornScraperReal()
