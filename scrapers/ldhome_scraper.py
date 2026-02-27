#!/usr/bin/env python3
# =============================================================================
# scrapers/ldhome_scraper.py — Scraper LDHome.lu via HTTP + BeautifulSoup
# =============================================================================
# Methode : requete HTTP GET, parsing HTML avec BeautifulSoup
#           Structure Bootstrap standard, tout en HTML statique (pas de JS requis)
#           Cards : <div class="property-result" data-price="1750" data-area="55">
#           Prix : data-price attribut + <span class="proerty-price pull-right">
#           Surface : data-area attribut (m²)
#           Chambres : icones <img alt="Bedroom icon"> + texte adjacent
#           Image : <img data-src="..."> (lazy-load, utiliser data-src)
#           Ville : <h5><a>Luxembourg - Bonnevoie</a> → partie avant " - "
# Pagination : ?page=N (14 pages de ~10 annonces)
# Total : ~140 annonces de location appartements
# GPS : geocode_city depuis nom de ville
# Filtrage : prix, rooms, surface, mots exclus, distance GPS max
# Instance globale : ldhome_scraper
# =============================================================================
import re
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from scrapers.utils_retry import make_session
from utils import haversine_distance, geocode_city

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ldhome.lu"
LISTING_URL = f"{BASE_URL}/en/property/rental/apartment"


class LDHomeScraper:
    def __init__(self):
        self.name = "LDHome.lu"
        self.base_url = BASE_URL
        self.max_pages = 14
        self.session = make_session(headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

    def parse_price(self, card) -> int:
        """Extrait le prix depuis data-price ou le span texte '1.750 €'"""
        # Priorite : attribut data-price (plus fiable)
        val = card.get('data-price')
        if val:
            try:
                return int(val)
            except ValueError:
                pass
        # Fallback : texte du span proerty-price
        span = card.find('span', class_=lambda c: c and 'proerty-price' in c)
        if span:
            clean = re.sub(r'[^\d]', '', span.get_text())
            try:
                return int(clean)
            except ValueError:
                pass
        return 0

    def parse_surface(self, card) -> int:
        """Extrait la surface depuis data-area"""
        val = card.get('data-area')
        if val:
            try:
                return int(val)
            except ValueError:
                pass
        return 0

    def parse_rooms(self, card) -> int:
        """Extrait les chambres depuis icone 'Bedroom icon' + texte adjacent"""
        for img in card.find_all('img'):
            alt = img.get('alt', '').lower()
            if 'bedroom' in alt:
                # Le nombre est dans le nœud texte suivant (ex: &nbsp;1)
                nxt = img.next_sibling
                if nxt:
                    text = str(nxt).replace('\xa0', ' ').strip()
                    m = re.search(r'(\d+)', text)
                    if m:
                        try:
                            return int(m.group(1))
                        except ValueError:
                            pass
        return 0

    def parse_city(self, card) -> str:
        """Extrait la ville depuis '<h5><a>Luxembourg - Bonnevoie</a>'"""
        h5 = card.find('h5')
        if h5:
            text = h5.get_text(strip=True)
            # Format "Luxembourg - Bonnevoie" → "Luxembourg"
            parts = text.split(' - ')
            return parts[0].strip()
        return ''

    def parse_image(self, card) -> Optional[str]:
        """Extrait l'image depuis data-src (lazy-load)"""
        img = card.find('img', attrs={'data-src': True})
        if img:
            src = img['data-src']
            return src if src.startswith('http') else self.base_url + src
        return None

    def scrape_page(self, page: int) -> List[Dict]:
        """Scrape une page et retourne les annonces filtrees"""
        from config import (
            MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE,
            EXCLUDED_WORDS, REFERENCE_LAT, REFERENCE_LNG, MAX_DISTANCE
        )
        from utils import extract_available_from

        url = f"{LISTING_URL}?page={page}" if page > 1 else LISTING_URL
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"LDHome page {page}: erreur HTTP {e}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        # Cards : div avec classe "property-result"
        cards = soup.find_all('div', class_=lambda c: c and 'property-result' in c)

        if not cards:
            logger.info(f"LDHome page {page}: aucune card trouvee")
            return []

        listings = []
        for card in cards:
            try:
                # Type de bien : filtrer les non-residentiels
                type_span = card.find('span', class_='pull-left')
                type_text = ''
                if type_span:
                    b = type_span.find('b')
                    type_text = b.get_text(strip=True).lower() if b else ''
                if not any(t in type_text for t in ['apartment', 'house', 'penthouse', 'duplex', 'villa']):
                    continue

                # URL de l'annonce
                link = card.find('a', href=True)
                if not link:
                    continue
                href = link['href']
                url_annonce = href if href.startswith('http') else self.base_url + href

                # ID unique : dernier segment de l'URL (ex: lbonn25)
                listing_ref = href.rstrip('/').split('/')[-1].upper()
                listing_id = f"ldhome_{listing_ref.lower()}"

                # Prix
                prix = self.parse_price(card)
                if prix == 0 or prix < MIN_PRICE or prix > MAX_PRICE:
                    continue

                # Surface
                surface = self.parse_surface(card)
                if surface > 0 and surface < MIN_SURFACE:
                    continue

                # Chambres
                rooms = self.parse_rooms(card)
                if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                    continue

                # Ville
                city = self.parse_city(card)

                # Titre
                h5 = card.find('h5')
                title = h5.get_text(strip=True) if h5 else f"Appartement {city}"

                # Mots exclus
                if any(w.lower() in title.lower() for w in EXCLUDED_WORDS):
                    continue

                # Image
                image_url = self.parse_image(card)

                # Description complete
                desc = card.find('p', class_='line-clamp')
                full_text = desc.get_text(strip=True) if desc else title

                # Date de disponibilite
                available_from = extract_available_from(full_text)

                # GPS depuis nom de ville
                lat, lng = geocode_city(city)
                distance_km = None
                if lat and lng:
                    distance_km = haversine_distance(REFERENCE_LAT, REFERENCE_LNG, lat, lng)
                    if distance_km > MAX_DISTANCE:
                        continue

                listing = {
                    'listing_id':     listing_id,
                    'site':           self.name,
                    'title':          title,
                    'price':          prix,
                    'rooms':          rooms,
                    'surface':        surface,
                    'city':           city,
                    'url':            url_annonce,
                    'image_url':      image_url,
                    'latitude':       lat,
                    'longitude':      lng,
                    'distance_km':    distance_km,
                    'available_from': available_from,
                    'time_ago':       'Recemment',
                    'full_text':      full_text,
                }
                listings.append(listing)

            except Exception as e:
                logger.warning(f"LDHome: erreur extraction card: {e}")
                continue

        logger.debug(f"LDHome page {page}: {len(listings)} apres filtrage")
        return listings

    def scrape(self) -> List[Dict]:
        """Scrape toutes les pages de LDHome.lu"""
        all_listings = []
        seen_ids = set()

        for page in range(1, self.max_pages + 1):
            logger.info(f"LDHome.lu — page {page}/{self.max_pages}")
            page_listings = self.scrape_page(page)

            if not page_listings and page > 1:
                logger.info(f"LDHome: page {page} vide — arret")
                break

            # Deduplication locale
            for lst in page_listings:
                if lst['listing_id'] not in seen_ids:
                    seen_ids.add(lst['listing_id'])
                    all_listings.append(lst)

        logger.info(f"✅ LDHome.lu — {len(all_listings)} annonces apres filtrage")
        return all_listings


# Instance globale (pour import dans main.py)
ldhome_scraper = LDHomeScraper()
