#!/usr/bin/env python3
# =============================================================================
# scrapers/propertyinvest_scraper.py — Scraper PropertyInvest.lu via HTTP + BS4
# =============================================================================
# Methode : requete HTTP GET, parsing HTML avec BeautifulSoup
#           Site Drupal avec Alpine.js pour le carousel images UNIQUEMENT.
#           Les donnees listing (prix, surface, chambres) sont SERVER-RENDERED.
#
# Structure listing card :
#   <li class="views-row">
#     <div x-data="propertyCard({totalSlides:4})">
#       <!-- Image : <img src> dans le premier slide Alpine.js -->
#       <a href="/en/rent/apartment-junglinster-0">
#         <ul>
#           <li><span class="sr-only">Surface</span><span class="text-xs">155Sqm</span></li>
#           <li><span class="sr-only">Rooms</span><span class="text-xs">3</span></li>
#         </ul>
#         <h3>Apartment in Junglinster</h3>
#         <p>3 300 €</p>
#       </a>
#
# Titre format : "Apartment in CITY" → ville extraite apres " in "
# Prix format  : "3 300 €" (espace comme separateur milliers)
# Surface      : "155Sqm" → 155 m²
# Image        : <img src> dans le premier div Alpine.js (x-show="currentSlide == 1")
# Pagination   : page unique (petite agence, ~5-10 annonces)
# GPS          : geocode_city depuis nom de ville
# Filtrage     : prix, rooms, surface, mots exclus, distance GPS max
# Instance globale : propertyinvest_scraper
# =============================================================================
import re
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from scrapers.utils_retry import make_session
from utils import haversine_distance, geocode_city

logger = logging.getLogger(__name__)

BASE_URL    = "https://www.propertyinvest.lu"
LISTING_URL = f"{BASE_URL}/en/rent"


class PropertyInvestScraper:
    def __init__(self):
        self.name = "PropertyInvest.lu"
        self.base_url = BASE_URL
        self.session = make_session(headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

    def parse_price(self, text: str) -> int:
        """Extrait prix depuis '3 300 €' ou '1 400 €'"""
        clean = re.sub(r'[^\d]', '', text)
        try:
            return int(clean)
        except ValueError:
            return 0

    def parse_surface(self, text: str) -> int:
        """Extrait surface depuis '155Sqm' ou '82 Sqm'"""
        m = re.search(r'(\d+)\s*[Ss]qm', text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        return 0

    def parse_city(self, title: str) -> str:
        """Extrait ville depuis 'Apartment in Junglinster' → 'Junglinster'"""
        # Format anglais : "TYPE in CITY"
        m = re.search(r'\bin\s+(.+)$', title, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return ''

    def parse_image(self, card) -> Optional[str]:
        """Extrait l'image depuis le premier slide Alpine.js"""
        # Les images sont dans des div avec x-show="currentSlide == 1"
        # On cherche le premier <img> dans la zone de l'image du carousel
        for div in card.find_all('div'):
            x_show = div.get('x-show', '') or div.get(':x-show', '')
            if 'currentSlide == 1' in x_show or 'currentSlide==1' in x_show:
                img = div.find('img', src=True)
                if img:
                    src = img['src']
                    return src if src.startswith('http') else self.base_url + src
        # Fallback : premier img du card
        img = card.find('img', src=True)
        if img:
            src = img['src']
            # Ignorer les icones SVG et placeholders
            if src.endswith(('.jpg', '.jpeg', '.png', '.webp')) or '/files/' in src:
                return src if src.startswith('http') else self.base_url + src
        return None

    def extract_property_fields(self, card) -> dict:
        """Extrait surface et chambres depuis la liste <ul> des icones"""
        result = {'surface': 0, 'rooms': 0}
        # Les champs sont dans des <li> avec <span class="sr-only">Label</span>
        # suivi d'un <span class="text-xs">Valeur</span>
        items = card.find_all('li', class_=lambda c: c and 'items-center' in c)
        for item in items:
            label_span = item.find('span', class_='sr-only')
            value_span = item.find('span', class_='text-xs')
            if not label_span or not value_span:
                continue
            label = label_span.get_text(strip=True).lower()
            value = value_span.get_text(strip=True)
            if 'surface' in label or 'area' in label:
                result['surface'] = self.parse_surface(value)
            elif 'room' in label or 'bed' in label or 'chambre' in label:
                try:
                    result['rooms'] = int(value)
                except ValueError:
                    pass
        return result

    def scrape(self) -> List[Dict]:
        """Scrape toutes les annonces PropertyInvest.lu"""
        from config import (
            MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE,
            EXCLUDED_WORDS, REFERENCE_LAT, REFERENCE_LNG, MAX_DISTANCE
        )
        from utils import extract_available_from

        try:
            resp = self.session.get(LISTING_URL, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"PropertyInvest.lu: erreur HTTP: {e}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        # Cards : <li class="views-row">
        cards = soup.find_all('li', class_=lambda c: c and 'views-row' in c)
        logger.info(f"PropertyInvest.lu: {len(cards)} cards trouvees")

        listings = []
        seen_ids = set()

        for card in cards:
            try:
                # Trouver le lien principal de l'annonce
                link = card.find('a', href=lambda h: h and '/rent/' in h)
                if not link:
                    link = card.find('a', href=True)
                if not link:
                    continue

                href = link['href']
                url_annonce = href if href.startswith('http') else self.base_url + href

                # ID unique depuis le slug (ex: apartment-junglinster-0)
                slug = href.rstrip('/').split('/')[-1]
                listing_id = f"propertyinvest_{slug}"
                if listing_id in seen_ids:
                    continue
                seen_ids.add(listing_id)

                # Titre et ville
                h3 = card.find('h3')
                if not h3:
                    continue
                title = h3.get_text(strip=True)
                city = self.parse_city(title)

                # Prix : <p> contenant "€"
                prix = 0
                for p in card.find_all('p'):
                    txt = p.get_text(strip=True)
                    if '€' in txt:
                        prix = self.parse_price(txt)
                        if prix > 0:
                            break

                if prix == 0 or prix < MIN_PRICE or prix > MAX_PRICE:
                    continue

                # Surface et chambres
                fields = self.extract_property_fields(card)
                surface = fields['surface']
                rooms   = fields['rooms']

                if surface > 0 and surface < MIN_SURFACE:
                    continue
                if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                    continue

                # Mots exclus
                if any(w.lower() in title.lower() for w in EXCLUDED_WORDS):
                    continue

                # Image
                image_url = self.parse_image(card)

                # Date de disponibilite
                available_from = extract_available_from(title)

                # GPS
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
                    'full_text':      title,
                }
                listings.append(listing)

            except Exception as e:
                logger.warning(f"PropertyInvest: erreur card: {e}")
                continue

        logger.info(f"✅ PropertyInvest.lu — {len(listings)} annonces apres filtrage")
        return listings


# Instance globale (pour import dans main.py)
propertyinvest_scraper = PropertyInvestScraper()
