# =============================================================================
# scrapers/apropos_scraper.py — Scraper Apropos.lu (powered by Immotop) via HTML
# =============================================================================
# Methode : requete HTTP GET sur /en/annonces/location/?category=rent&page=N
# Structure : <article class="property-row">
#               <a class="property-row-picture-target" href="/en/ID_type-for-rent-city/">
#               <h3 class="property-row-title">City</h3>
#               <div class="property-row-subtitle">Type X Bedrooms</div>
#               <div class="property-row-price digits">€ 4 400</div>
#               <p>description avec "240 m²"...</p>
# ID       : extrait depuis href regex (\d+)_
# Filtrage : uniquement href contenant "for-rent" (exclut "for-sale")
# Filtrage type : exclut parking, garage, land, commercial, office, warehouse
# Surface  : regex dans description <p>
# Chambres : regex dans <div class="property-row-subtitle">
# Pagination : ?category=rent&page=N jusqu'a MAX_PAGES
# Instance globale : apropos_scraper
# =============================================================================
import re
import time
import logging
from bs4 import BeautifulSoup
from filters import matches_criteria
from scrapers.utils_retry import make_session

logger = logging.getLogger(__name__)

SEARCH_URL = 'https://www.apropos.lu/en/annonces/location/'
MAX_PAGES  = 5

EXCLUDED_TYPES = {
    'parking', 'garage', 'land', 'commercial', 'office',
    'warehouse', 'storage', 'shop'
}


class AproposScraper:
    def __init__(self):
        self.base_url  = 'https://www.apropos.lu'
        self.site_name = 'Apropos.lu'
        self.session   = make_session(headers={
            'User-Agent':      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                               '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'fr-LU,fr;q=0.9,en;q=0.8',
        })

    def scrape(self):
        """Scrape toutes les annonces de location Apropos.lu"""
        listings = []
        seen_ids = set()

        try:
            for page_num in range(1, MAX_PAGES + 1):
                url = f"{SEARCH_URL}?category=rent&page={page_num}"
                logger.info(f"[Apropos] Page {page_num}: {url}")
                resp = self.session.get(url, timeout=15)

                if resp.status_code != 200:
                    logger.warning(f"  HTTP {resp.status_code}, arret")
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')
                # Compter les articles bruts (avant filtrage) pour la pagination
                raw_articles = len(soup.find_all('article', class_='property-row'))
                if raw_articles == 0:
                    logger.info(f"  Page {page_num}: page vide, arret")
                    break

                page_listings = self._parse_page(soup, seen_ids)
                listings.extend(page_listings)
                logger.info(f"  Page {page_num}: {raw_articles} brutes, {len(page_listings)} acceptees")

                if page_num < MAX_PAGES:
                    time.sleep(1)

        except Exception as e:
            logger.error(f"❌ Apropos scraping: {e}")
            import traceback
            traceback.print_exc()

        logger.info(f"✅ Apropos.lu: {len(listings)} annonces apres filtrage")
        return listings

    def _parse_page(self, soup, seen_ids):
        """Extraire les annonces depuis <article class="property-row">"""
        page_listings = []
        articles = soup.find_all('article', class_='property-row')

        for article in articles:
            # URL depuis le lien image
            pic_link = article.find('a', class_='property-row-picture-target')
            if not pic_link:
                continue
            href = pic_link.get('href', '')
            if not href:
                continue

            # Uniquement les locations
            if 'for-rent' not in href:
                continue

            # ID depuis href : /en/28216418_house-for-rent-in-luxembourg/
            m = re.search(r'/(\d+)_', href)
            if not m:
                continue
            listing_id = m.group(1)

            if listing_id in seen_ids:
                continue

            # Type depuis href : /ID_TYPE-for-rent-in-CITY/
            type_match = re.search(r'/\d+_([^-]+)-for-rent', href)
            listing_type = type_match.group(1).lower() if type_match else ''
            if listing_type in EXCLUDED_TYPES:
                continue

            # Ville : h3.property-row-title
            city_el = article.find('h3', class_='property-row-title')
            city = city_el.get_text(strip=True) if city_el else 'Luxembourg'

            # Chambres depuis subtitle : "House 4 Bedrooms"
            rooms = 0
            subtitle = article.find('div', class_='property-row-subtitle')
            if subtitle:
                sub_text = subtitle.get_text(' ', strip=True)
                r_match = re.search(r'(\d+)\s*(?:Bedroom|bedroom|chambre|pièce)', sub_text, re.IGNORECASE)
                if r_match:
                    rooms = int(r_match.group(1))

            # Prix : "€ 4 400" → 4400
            price_el   = article.find('div', class_='property-row-price')
            price_text = price_el.get_text(strip=True) if price_el else ''
            price      = self._parse_price(price_text)
            if price <= 0:
                continue

            # Description pour surface (regex "240 m²")
            desc_el   = article.find('p')
            desc_text = desc_el.get_text(' ', strip=True) if desc_el else ''
            surface   = self._extract_surface(desc_text)

            # Image
            img = article.find('img', class_='wp-post-image')
            image_url = img.get('src') if img else None
            if image_url and not image_url.startswith('http'):
                image_url = None

            type_label = listing_type.title() if listing_type else 'Bien'
            title = f"{type_label} a louer — {city}"
            full_url = href if href.startswith('http') else f"{self.base_url}{href}"

            listing = {
                'listing_id': f'apropos_{listing_id}',
                'site':       self.site_name,
                'title':      title[:80],
                'city':       city,
                'price':      price,
                'rooms':      rooms,
                'surface':    surface,
                'url':        full_url,
                'image_url':  image_url,
                'time_ago':   'Recemment',
                'full_text':  desc_text[:500],
            }

            if matches_criteria(listing):
                seen_ids.add(listing_id)
                page_listings.append(listing)

        return page_listings

    def _parse_price(self, text):
        """Extraire le prix depuis '€ 4 400' ou '€ 1 200'"""
        cleaned = re.sub(r'[€,\s]', '', text)
        m = re.search(r'(\d+)', cleaned)
        if m:
            try:
                val = int(m.group(1))
                return val if 100 <= val <= 50000 else 0
            except ValueError:
                pass
        return 0

    def _extract_surface(self, text):
        """Extraire la surface : '240 m²' ou '75 m2'"""
        m = re.search(r'(\d+)\s*m[²2]', text)
        return int(m.group(1)) if m else 0


apropos_scraper = AproposScraper()
