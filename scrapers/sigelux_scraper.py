# =============================================================================
# scrapers/sigelux_scraper.py — Scraper Sigelux.lu via HTML requests + BeautifulSoup
# =============================================================================
# Methode : requete HTTP GET sur /locations, parsing HTML avec BeautifulSoup
#           Navigation DOM : <h2><a href="/location/TYPE/CITY/ID">
#           Prix direct : "3 800 €" dans le conteneur (pas de label "Prix:")
#           Rooms : "3 chambre(s)" dans le texte
#           Surface : "141 m²" dans le texte
# Pagination : /locations/currentPage/N
# Images : <img src> dans le conteneur de l'annonce (CDN Athome)
# Filtrage type : exclut bureau, local-commercial, terrain, entrepot, commerce
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS
# Ville : slug URL (/location/TYPE/VILLE/ID → VILLE)
# Instance globale : sigelux_scraper
# =============================================================================
import re
import time
import logging
from bs4 import BeautifulSoup
from config import MAX_PRICE, MIN_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS
from scrapers.utils_retry import make_session

logger = logging.getLogger(__name__)

# Types d'annonces a exclure (non residentiels)
EXCLUDED_TYPES = {
    'garage-parking', 'bureau', 'local-commercial', 'terrain',
    'entrepot', 'commerce', 'parking', 'cave', 'atelier'
}


class SigeluxScraper:
    def __init__(self):
        self.base_url = "https://www.sigelux.lu"
        self.site_name = "Sigelux.lu"
        self.session = make_session(headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'fr-LU,fr;q=0.9,en;q=0.8',
        })

    def scrape(self):
        """Scrape toutes les annonces de location Sigelux.lu"""
        MAX_PAGES = 5
        listings = []
        seen_ids = set()

        try:
            for page_num in range(1, MAX_PAGES + 1):
                if page_num == 1:
                    url = f"{self.base_url}/locations"
                else:
                    url = f"{self.base_url}/locations/currentPage/{page_num}"

                logger.info(f"[Sigelux] Page {page_num}: {url}")
                resp = self.session.get(url, timeout=15)

                if resp.status_code != 200:
                    logger.warning(f"  HTTP {resp.status_code}, arret pagination")
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')
                page_listings = self._parse_page(soup, seen_ids)

                if not page_listings:
                    logger.info(f"  Page {page_num}: aucune annonce, arret")
                    break

                listings.extend(page_listings)
                logger.info(f"  Page {page_num}: {len(page_listings)} annonces acceptees")

                if page_num < MAX_PAGES:
                    time.sleep(1)

        except Exception as e:
            logger.error(f"❌ Sigelux scraping: {e}")
            import traceback
            traceback.print_exc()

        logger.info(f"✅ Sigelux.lu: {len(listings)} annonces apres filtrage")
        return listings

    def _parse_page(self, soup, seen_ids):
        """Extraire les annonces d'une page HTML parsee.
        Structure reelle : <h2><a href="/location/TYPE/CITY/ID">
        Prix direct dans le conteneur : "3 800 €" (sans label "Prix:")
        """
        page_listings = []

        # Liens annonces : /location/TYPE/CITY/ID (exactement 4 composantes)
        links = soup.find_all('a', href=re.compile(r'^/location/[^/]+/[^/]+/\d+$'))
        seen_hrefs = set()

        for link in links:
            href = link.get('href', '')
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            url_parts = href.strip('/').split('/')
            if len(url_parts) < 4:
                continue

            listing_type = url_parts[1]
            listing_id   = url_parts[3]

            if listing_type in EXCLUDED_TYPES:
                continue
            if listing_id in seen_ids:
                continue

            title = link.get_text(' ', strip=True)
            if not title:
                continue

            # Ville depuis le slug URL
            city = url_parts[2].replace('-', ' ').title()

            # Remonter pour trouver le conteneur complet (contient le prix)
            container = self._find_container(link)
            if not container:
                continue

            container_text = container.get_text(' ', strip=True)

            # Prix : "3 800 €" ou "1 480 €" (espaces insecables possibles)
            price = self._extract_price(container_text)
            if price is None or price < MIN_PRICE or price > MAX_PRICE:
                continue

            # Surface et chambres
            surface = self._extract_surface(container_text)
            if surface > 0 and surface < MIN_SURFACE:
                continue

            rooms = self._extract_rooms(container_text)
            if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                continue

            # Mots exclus
            if any(w.strip().lower() in title.lower() for w in EXCLUDED_WORDS if w.strip()):
                continue

            image_url = self._extract_image(container)

            # Date de disponibilite
            from utils import extract_available_from
            available_from = extract_available_from(container_text)

            seen_ids.add(listing_id)
            page_listings.append({
                'listing_id':   f'sigelux_{listing_id}',
                'site':         self.site_name,
                'title':        title[:80],
                'city':         city,
                'price':        price,
                'rooms':        rooms,
                'surface':      surface,
                'url':          f"{self.base_url}{href}",
                'image_url':    image_url,
                'available_from': available_from,
                'time_ago':     'Recemment',
                'full_text':    container_text[:500],
            })

        return page_listings

    def _find_container(self, link):
        """Remonter depuis le <a> pour trouver le conteneur complet de l'annonce.
        On cherche le premier ancetre qui contient le symbole € (prix)."""
        from bs4 import Tag
        node = link.parent
        for _ in range(10):
            if not isinstance(node, Tag):
                break
            if '€' in node.get_text():
                return node
            node = node.parent
        return link.parent

    def _extract_price(self, text):
        """Extraire le prix depuis '3 800 €' ou '1 480 €' (espaces variés)"""
        # Normaliser les espaces insecables
        text_n = re.sub(r'[\s\u202f\xa0\u00a0]+', ' ', text)
        m = re.search(r'(\d[\d ]*\d)\s*€', text_n)
        if not m:
            m = re.search(r'(\d+)\s*€', text_n)
        if not m:
            return None
        price_str = m.group(1).replace(' ', '')
        try:
            val = int(price_str)
            return val if 100 <= val <= 50000 else None
        except ValueError:
            return None

    def _extract_surface(self, text):
        """Extraire la surface : '141 m²' ou '75 m2'"""
        m = re.search(r'(\d+)\s*m[²2]', text)
        return int(m.group(1)) if m else 0

    def _extract_rooms(self, text):
        """Extraire les chambres : '3 chambre(s)' ou '3 ch'"""
        m = re.search(r'(\d+)\s*chambre', text, re.IGNORECASE)
        return int(m.group(1)) if m else 0

    def _extract_image(self, container):
        """Extraire l'URL de l'image depuis le conteneur"""
        img = container.find('img')
        if img:
            src = img.get('src') or img.get('data-src') or ''
            if src.startswith('http'):
                return src
        return None


sigelux_scraper = SigeluxScraper()
