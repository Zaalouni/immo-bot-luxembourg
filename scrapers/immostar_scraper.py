# =============================================================================
# scrapers/immostar_scraper.py — Scraper ImmoStar.lu via HTML + BeautifulSoup
# =============================================================================
# URL     : https://immostar.lu/search/1?t=1&loc=lu|Luxembourg (pays)
# Methode : requete HTTP GET, parsing BeautifulSoup
# Structure : <div class="list"> contient image, titre, prix, description
# Image   : <img src="https://img.immostar.lu/id/XXXXX/...">
# Prix    : extrait du texte (ex: "1 200€")
# Surface : extrait du texte (ex: "70 m²")
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

# Types à exclure
EXCLUDED_TYPES = {'commercial', 'parking', 'garage', 'bureau', 'office', 'entrepôt', 'cave', 'terrain'}


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

        try:
            for page_num in range(1, MAX_PAGES + 1):
                # URL avec paramètres de recherche
                url = f"{self.base_url}/search/{page_num}?t=1&loc=lu|Luxembourg%C2%A0(pays)"
                logger.info(f"[ImmoStar] Page {page_num}: {url}")

                resp = self.session.get(url, timeout=20)

                if resp.status_code != 200:
                    logger.warning(f"  HTTP {resp.status_code}, arrêt")
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')

                # Trouver les cartes d'annonces
                cards = soup.find_all('div', class_='list')
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
        # Extraire le texte complet de la carte
        text = ' '.join(card.get_text().split())

        # Extraire ID et prix avec le pattern: ID (6 chiffres) + prix
        # Format: "2124721 200€" = ID 212472, prix 1200€
        id_price_match = re.search(r'(\d{6})(\d[\d\s]*)\s*€', text)
        if not id_price_match:
            return None

        listing_id = id_price_match.group(1)
        price_raw = id_price_match.group(2).replace(' ', '')

        if listing_id in seen_ids:
            return None

        # Extraire le prix
        try:
            price = int(price_raw)
        except:
            return None

        # Prix raisonnable pour une location résidentielle
        if price < 500 or price > 10000:
            return None

        # Extraire le titre (avant l'ID/prix)
        title_match = re.search(r'([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][^€]+?)(?=\d{6})', text)
        title = title_match.group(1).strip() if title_match else text[:80]

        # Vérifier si c'est un type exclu
        title_lower = title.lower()
        if any(excl in title_lower for excl in EXCLUDED_TYPES):
            return None

        # Extraire la ville depuis le titre (ex: "À LOUER À REMICH")
        city_match = re.search(r'(?:À|A|IN|ZU)\s+([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][A-Za-zÀÂÄÉÈÊËÏÎÔÙÛÜÇàâäéèêëïîôùûüç\-]+)\s*$', title.strip())
        if city_match:
            city = city_match.group(1).strip().title()
        else:
            city = ''

        # Extraire la surface
        surface_match = re.search(r'(\d+)\s*m[²2]', text)
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

        # URL de l'annonce (construire depuis l'ID)
        # On n'a pas l'URL exacte, utiliser l'URL de recherche comme fallback
        url = f"{self.base_url}/fr/{listing_id}"

        # Image
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
