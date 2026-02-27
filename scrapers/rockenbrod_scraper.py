# =============================================================================
# scrapers/rockenbrod_scraper.py — Scraper Rockenbrod.lu via HTML requests
# =============================================================================
# Methode : requete HTTP GET sur la page de location, extraction des URLs
#           d'annonces par regex, puis fetch de chaque page individuelle
#           pour titre, prix, surface, chambres, ville et image (og:image)
# URL liste : /letting/?usage=private
# URL annonce : /proprietes/slug/
# Ville : extraite du prefixe du titre (LUX-QUARTIER ou COMMUNE)
# Images : og:image sur la page individuelle de chaque annonce
# Classe energetique : extraite depuis le HTML complet de la page individuelle
# Pagination : tentative ?usage=private&paged=N (WordPress)
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS
# Instance globale : rockenbrod_scraper
# =============================================================================
import requests
import re
import time
import logging
from config import MAX_PRICE, MIN_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS
from utils import extract_energy_class

logger = logging.getLogger(__name__)


class RockenBrodScraper:
    def __init__(self):
        self.base_url = "https://www.rockenbrod.lu"
        self.list_url = f"{self.base_url}/letting/?usage=private"
        self.site_name = "Rockenbrod.lu"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'fr-LU,fr;q=0.9',
        }

    def scrape(self):
        """Scraper Rockenbrod.lu — locations privees"""
        all_urls = []
        seen_urls = set()
        MAX_PAGES = 5

        try:
            for page_num in range(1, MAX_PAGES + 1):
                if page_num == 1:
                    url = self.list_url
                else:
                    url = f"{self.list_url}&paged={page_num}"

                logger.info(f"[Rockenbrod] Chargement page {page_num}: {url}")
                resp = requests.get(url, headers=self.headers, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"  HTTP {resp.status_code}")
                    break

                html = resp.text

                # Extraire toutes les URLs d'annonces /proprietes/slug/
                urls = re.findall(
                    r'href="(https://www\.rockenbrod\.lu/proprietes/[^"]+)"',
                    html
                )
                new_urls = [u for u in urls if u not in seen_urls]
                for u in new_urls:
                    seen_urls.add(u)
                    all_urls.append(u)

                logger.info(f"  Page {page_num}: {len(new_urls)} nouvelles URLs")

                if not new_urls:
                    break

                if page_num < MAX_PAGES:
                    time.sleep(1)

        except Exception as e:
            logger.error(f"❌ Collecte URLs Rockenbrod: {e}")
            return []

        logger.info(f"  {len(all_urls)} annonces a traiter")

        # Scraper chaque page individuelle
        listings = []
        for listing_url in all_urls:
            try:
                listing = self._scrape_listing_page(listing_url)
                if listing:
                    listings.append(listing)
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"  Erreur {listing_url}: {e}")

        logger.info(f"✅ Rockenbrod.lu: {len(listings)} annonces apres filtrage")
        return listings

    def _scrape_listing_page(self, url):
        """Scraper une page d'annonce individuelle"""
        resp = requests.get(url, headers=self.headers, timeout=15)
        if resp.status_code != 200:
            return None

        html = resp.text

        # Titre depuis og:title ou <title>
        title = ''
        og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if og_title:
            title = og_title.group(1).strip()
        else:
            title_tag = re.search(r'<title>([^<]+)</title>', html)
            if title_tag:
                title = title_tag.group(1).split('|')[0].strip()

        if not title:
            return None

        # Prix : "1 250,00 €" → prendre la partie entiere avant la virgule
        price = 0
        price_match = re.search(r'([\d][\d\s]*[\d])\s*(?:,\d+)?\s*€', html)
        if price_match:
            price_clean = re.sub(r'\s', '', price_match.group(1))
            try:
                price = int(price_clean)
            except ValueError:
                pass

        if price <= 0 or price < MIN_PRICE or price > MAX_PRICE:
            return None

        # Chambres : "2 chambres" ou "1 chambre"
        rooms = 0
        rooms_match = re.search(r'(\d+)\s*chambre', html, re.IGNORECASE)
        if rooms_match:
            rooms = int(rooms_match.group(1))
        elif re.search(r'\bstudio\b', html, re.IGNORECASE):
            rooms = 1

        if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
            return None

        # Surface : "+/- 26,00 m²" ou "76 m²"
        surface = 0
        surface_match = re.search(r'(\d+)(?:[,\.]\d+)?\s*m[²2]', html)
        if surface_match:
            surface = int(surface_match.group(1))

        if surface > 0 and surface < MIN_SURFACE:
            return None

        # Ville extraite depuis le slug URL
        slug = url.rstrip('/').split('/')[-1]
        slug_clean = re.sub(r'^lux-', '', slug)
        city_match = re.match(
            r'^([a-z][a-z-]*?)(?:-(?:rue|avenue|route|monte|allee|bd|chemin|place|impasse|voie|\d))',
            slug_clean
        )
        if city_match:
            city = city_match.group(1).replace('-', ' ').title()
        else:
            city = slug_clean.split('-')[0].title()

        # ID depuis URL (slug)
        listing_id = f'rockenbrod_{slug}'

        # Image : og:image
        image_url = None
        og_image = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if og_image:
            image_url = og_image.group(1)
        else:
            wp_match = re.search(
                r'https://www\.rockenbrod\.lu/wp-content/uploads/[^\s"\']+\.(?:jpg|jpeg|png|webp)',
                html, re.IGNORECASE
            )
            if wp_match:
                image_url = wp_match.group(0)

        # Mots exclus
        full_text = f"{title} {html[:2000]}"
        check = full_text.lower()
        if any(w.strip().lower() in check for w in EXCLUDED_WORDS if w.strip()):
            return None

        # Classe energetique (full page disponible — meilleure source)
        energy_class = extract_energy_class(html)

        return {
            'listing_id': listing_id,
            'site': self.site_name,
            'title': title[:80],
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'image_url': image_url,
            'time_ago': 'Récemment',
            'full_text': title,
            'energy_class': energy_class,
        }


rockenbrod_scraper = RockenBrodScraper()
