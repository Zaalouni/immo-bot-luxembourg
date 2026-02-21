# =============================================================================
# scrapers/immostar_scraper.py — Scraper ImmoStar.lu via HTML + BeautifulSoup
# =============================================================================
# Methode : requete HTTP GET sur /en/rent/N, parsing BeautifulSoup
# Structure : <div class="list" data-ref="ID" data-url="/rent/TYPE/CITY/ID">
# Prix     : <div class="price">1,650€</div> (virgule = separateur milliers)
# Surface  : extraction depuis <div class="desc"> (regex "75 m²")
# Chambres : extraction depuis description (regex "X chambre/bedroom")
# Image    : <source type="image/jpeg" srcset="..."> ou <img src="...">
# Ville    : slug URL (data-url[2] → "perl" → "Perl")
# Pagination : /en/rent/N jusqu'a MAX_PAGES
# Filtrage type : exclut commercial-room, parking, land, garage, office, etc.
# Instance globale : immostar_scraper
# =============================================================================
import re
import time
import logging
from bs4 import BeautifulSoup
from filters import matches_criteria
from scrapers.utils_retry import make_session

logger = logging.getLogger(__name__)

EXCLUDED_TYPES = {
    'commercial-room', 'commercial', 'parking', 'land', 'garage',
    'office', 'warehouse', 'storage', 'shop', 'cave'
}
MAX_PAGES = 5


class ImmostarScraper:
    def __init__(self):
        self.base_url  = 'https://www.immostar.lu'
        self.site_name = 'ImmoStar.lu'
        self.session   = make_session(headers={
            'User-Agent':      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                               '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'fr-LU,fr;q=0.9,en;q=0.8',
        })

    def scrape(self):
        """Scrape toutes les annonces de location ImmoStar.lu"""
        listings = []
        seen_ids = set()

        try:
            for page_num in range(1, MAX_PAGES + 1):
                url = f"{self.base_url}/en/rent/{page_num}"
                logger.info(f"[ImmoStar] Page {page_num}: {url}")
                resp = self.session.get(url, timeout=15)

                if resp.status_code != 200:
                    logger.warning(f"  HTTP {resp.status_code}, arret")
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')
                # Compter les cartes brutes (avant filtrage) pour la pagination
                raw_cards = len(soup.find_all('div', class_='list'))
                if raw_cards == 0:
                    logger.info(f"  Page {page_num}: page vide, arret")
                    break

                page_listings = self._parse_page(soup, seen_ids)
                listings.extend(page_listings)
                logger.info(f"  Page {page_num}: {raw_cards} brutes, {len(page_listings)} acceptees")

                if page_num < MAX_PAGES:
                    time.sleep(1)

        except Exception as e:
            logger.error(f"❌ ImmoStar scraping: {e}")
            import traceback
            traceback.print_exc()

        logger.info(f"✅ ImmoStar.lu: {len(listings)} annonces apres filtrage")
        return listings

    def _parse_page(self, soup, seen_ids):
        """Extraire les annonces depuis <div class="list" data-ref="ID" data-url="/rent/TYPE/CITY/ID">"""
        page_listings = []
        cards = soup.find_all('div', class_='list')

        for card in cards:
            data_url = card.get('data-url', '')
            data_ref = card.get('data-ref', '')

            if not data_url or not data_ref:
                continue

            # data-url format : /rent/apartment/perl/212448
            parts = data_url.strip('/').split('/')
            if len(parts) < 4:
                continue

            listing_type = parts[1]   # 'apartment'
            city_slug    = parts[2]   # 'perl'
            listing_id   = data_ref   # '212448'

            if listing_type in EXCLUDED_TYPES:
                continue
            if listing_id in seen_ids:
                continue

            # Titre : "APARTMENT FOR RENT IN PERL"
            title_el = card.find('div', class_='title')
            title = title_el.get_text(strip=True) if title_el else f"{listing_type.title()} {city_slug.title()}"
            if not title:
                continue

            # Prix : "1,650€" → 1650
            price_el   = card.find('div', class_='price')
            price_text = price_el.get_text(strip=True) if price_el else ''
            price      = self._parse_price(price_text)
            if price <= 0:
                continue

            # Description (surface + chambres)
            desc_el   = card.find('div', class_='desc')
            desc_text = desc_el.get_text(' ', strip=True) if desc_el else ''

            surface = self._extract_surface(desc_text)
            rooms   = self._extract_rooms(desc_text)
            city = city_slug.replace('-', ' ').title()

            # GPS depuis nom de ville — si ville inconnue (hors Luxembourg) → rejeter
            from utils import geocode_city, haversine_distance
            from config import REFERENCE_LAT, REFERENCE_LNG
            lat, lng = geocode_city(city)
            if lat is None:
                logger.debug(f"  Ville '{city}' inconnue (hors Luxembourg) → ignorée")
                continue
            distance_km = haversine_distance(REFERENCE_LAT, REFERENCE_LNG, lat, lng)

            # Image : <source type="image/jpeg" srcset="url"> prioritaire
            image_url = None
            source = card.find('source', attrs={'type': 'image/jpeg'})
            if source:
                image_url = source.get('srcset')
            if not image_url:
                img = card.find('img', class_='imagecover')
                if img:
                    image_url = img.get('src') or img.get('data-src')
            if image_url and not image_url.startswith('http'):
                image_url = None

            # Date de disponibilite
            from utils import extract_available_from
            available_from = extract_available_from(desc_text)

            listing = {
                'listing_id':   f'immostar_{listing_id}',
                'site':         self.site_name,
                'title':        title[:80],
                'city':         city,
                'price':        price,
                'rooms':        rooms,
                'surface':      surface,
                'url':          f"{self.base_url}{data_url}",
                'image_url':    image_url,
                'latitude':     lat,
                'longitude':    lng,
                'distance_km':  distance_km,
                'available_from': available_from,
                'time_ago':     'Recemment',
                'full_text':    desc_text[:500],
            }

            if matches_criteria(listing):
                seen_ids.add(listing_id)
                page_listings.append(listing)

        return page_listings

    def _parse_price(self, text):
        """Extraire le prix depuis '1,650€' ou '2 400€'"""
        cleaned = re.sub(r'[,\s€]', '', text)
        m = re.search(r'(\d+)', cleaned)
        if m:
            try:
                val = int(m.group(1))
                return val if 100 <= val <= 50000 else 0
            except ValueError:
                pass
        return 0

    def _extract_surface(self, text):
        """Extraire la surface : '75 m²' ou '120 m2'"""
        m = re.search(r'(\d+)\s*m[²2]', text)
        return int(m.group(1)) if m else 0

    def _extract_rooms(self, text):
        """Extraire le nombre de chambres"""
        m = re.search(r'(\d+)\s*(?:chambre|bedroom|room|pièce)', text, re.IGNORECASE)
        return int(m.group(1)) if m else 0


immostar_scraper = ImmostarScraper()
