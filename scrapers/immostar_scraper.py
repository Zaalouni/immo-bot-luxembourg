# =============================================================================
# scrapers/immostar_scraper.py — Scraper ImmoStar.lu via HTML + BeautifulSoup
# =============================================================================
# URL     : https://immostar.lu/search/1?t=1&pmin=1000&pmax=4000&smin=70&rmin=2
# Methode : requete HTTP GET, parsing BeautifulSoup
# Structure : <div class="list" data-ref="ID" data-url="/location/type/city/ID">
# Image   : <img src="https://img.immostar.lu/id/XXXXX/...">
# Prix    : extrait du texte (ex: "1 200€" ou "3 500€")
# Pagination : /search/N pour N = 1, 2, 3...
# Instance globale : immostar_scraper
# =============================================================================
import re
import time
import logging
from bs4 import BeautifulSoup
from filters import matches_criteria
from scrapers.utils_retry import make_session

logger = logging.getLogger(__name__)

MAX_PAGES = 5

# Types à exclure (basé sur l'URL data-url)
EXCLUDED_URL_TYPES = {
    'local-commercial', 'commercial', 'bureau', 'office',
    'fond-de-commerce', 'entrepot', 'parking', 'garage',
    'cave', 'terrain', 'immeuble-de-rapport'
}


class ImmostarScraper:
    def __init__(self):
        self.base_url = 'https://immostar.lu'
        self.site_name = 'ImmoStar.lu'
        self.session = make_session(headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'fr-LU,fr;q=0.9,en;q=0.8',
        })

    def scrape(self):
        """Scrape toutes les annonces de location ImmoStar.lu"""
        listings = []
        seen_ids = set()

        # Importer les critères de config pour construire l'URL
        try:
            from config import MIN_PRICE, MAX_PRICE, MIN_SURFACE, MIN_ROOMS
        except ImportError:
            MIN_PRICE, MAX_PRICE, MIN_SURFACE, MIN_ROOMS = 500, 5000, 50, 1

        try:
            for page_num in range(1, MAX_PAGES + 1):
                # URL avec paramètres de recherche basés sur config.py
                # t=1: location, pmin/pmax: prix, smin: surface min, rmin: pièces min
                url = (f"{self.base_url}/search/{page_num}"
                       f"?t=1&pmin={MIN_PRICE}&pmax={MAX_PRICE}"
                       f"&smin={MIN_SURFACE}&rmin={MIN_ROOMS}"
                       f"&loc=lu|Luxembourg%C2%A0(pays)")
                logger.info(f"[ImmoStar] Page {page_num}: {url}")

                resp = self.session.get(url, timeout=20)

                if resp.status_code != 200:
                    logger.warning(f"  HTTP {resp.status_code}, arrêt")
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')

                # Trouver les cartes d'annonces (ont data-ref et data-url)
                cards = soup.find_all('div', class_='list', attrs={'data-ref': True})
                if not cards:
                    logger.info(f"  Page {page_num}: aucune annonce, arrêt")
                    break

                page_listings = self._parse_page(cards, seen_ids)
                listings.extend(page_listings)
                logger.info(f"  Page {page_num}: {len(cards)} brutes, {len(page_listings)} acceptées")

                # Si moins d'annonces que prévu, c'est probablement la dernière page
                if len(cards) < 10:
                    break

                if page_num < MAX_PAGES:
                    time.sleep(1.5)

        except Exception as e:
            logger.error(f"❌ ImmoStar scraping: {e}")
            import traceback
            traceback.print_exc()

        logger.info(f"✅ ImmoStar.lu: {len(listings)} annonces après filtrage")
        return listings

    def _parse_page(self, cards, seen_ids):
        """Extraire les annonces depuis les divs class='list'"""
        page_listings = []

        for card in cards:
            try:
                listing = self._parse_card(card, seen_ids)
                if listing:
                    page_listings.append(listing)
            except Exception as e:
                logger.debug(f"  Erreur parsing card: {e}")
                continue

        return page_listings

    def _parse_card(self, card, seen_ids):
        """Parser une carte d'annonce"""
        # Extraire l'ID depuis data-ref
        listing_id = card.get('data-ref', '')
        if not listing_id or listing_id in seen_ids:
            return None

        # Extraire l'URL depuis data-url
        data_url = card.get('data-url', '')
        if not data_url:
            return None

        # Vérifier si c'est un type exclu (basé sur l'URL)
        url_lower = data_url.lower()
        for excl_type in EXCLUDED_URL_TYPES:
            if excl_type in url_lower:
                logger.debug(f"  Exclus (type commercial): {data_url}")
                return None

        # Construire l'URL complète
        url = f"{self.base_url}{data_url}"

        # Extraire le texte complet de la carte
        text = ' '.join(card.get_text().split())

        # Extraire le prix (format: ID(6 chiffres) + prix avant €)
        # Le texte contient "2124193 500€" = ID 212419 + prix 3 500€
        price_match = re.search(r'\d{6}(\d[\d\s]{0,6})€', text)
        if not price_match:
            return None

        try:
            price_str = price_match.group(1).replace(' ', '').replace('\xa0', '')
            price = int(price_str)
        except (ValueError, AttributeError):
            return None

        # Prix raisonnable pour une location résidentielle
        if price < 500 or price > 10000:
            return None

        # Extraire le titre (texte majuscule avant le prix)
        # Ex: "MAISON MITOYENNE À LOUER À BERELDANGE"
        title_match = re.search(r'([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ\s]+(?:À LOUER|A LOUER)[^€]*?)(?=\d)', text)
        if title_match:
            title = title_match.group(1).strip()
        else:
            # Fallback: premiers 80 caractères
            title = text[:80]

        # Extraire la ville depuis l'URL (format: /location/type/CITY/id)
        city_match = re.search(r'/location/[^/]+/([^/]+)/\d+', data_url)
        if city_match:
            city = city_match.group(1).replace('-', ' ').title()
        else:
            # Fallback: chercher dans le titre
            city_title_match = re.search(r'(?:À|A)\s+([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][A-Za-zÀÂÄÉÈÊËÏÎÔÙÛÜÇàâäéèêëïîôùûüç\-]+)\s*$', title.strip())
            city = city_title_match.group(1).title() if city_title_match else ''

        # Extraire la surface
        surface_match = re.search(r'(\d+)\s*m[²2]', text, re.I)
        surface = int(surface_match.group(1)) if surface_match else 0

        # Extraire les chambres
        rooms_match = re.search(r'(\d+)\s*(?:chambre|ch\b|bedroom|pièce)', text, re.I)
        rooms = int(rooms_match.group(1)) if rooms_match else 0

        # GPS depuis nom de ville
        lat, lng, distance_km = None, None, None
        if city:
            from utils import geocode_city, haversine_distance
            from config import REFERENCE_LAT, REFERENCE_LNG

            coords = geocode_city(city)
            if coords:
                lat, lng = coords
                distance_km = haversine_distance(REFERENCE_LAT, REFERENCE_LNG, lat, lng)

        # Image - extraire depuis la carte HTML
        img_tag = card.find('img')
        img_src = img_tag.get('src', '') if img_tag else ''
        image_url = img_src if img_src.startswith('http') else None

        listing = {
            'listing_id': f'immostar_{listing_id}',
            'site': self.site_name,
            'title': title[:100],
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'image_url': image_url,
            'latitude': lat,
            'longitude': lng,
            'distance_km': distance_km,
            'time_ago': 'Récemment',
            'full_text': text[:500],
        }

        if matches_criteria(listing):
            seen_ids.add(listing_id)
            return listing

        return None


immostar_scraper = ImmostarScraper()
