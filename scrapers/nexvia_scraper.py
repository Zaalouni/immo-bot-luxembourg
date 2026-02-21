#!/usr/bin/env python3
# =============================================================================
# scrapers/nexvia_scraper.py — Scraper Nexvia.lu via Selenium + BeautifulSoup
# =============================================================================
# Methode : Selenium Firefox headless, scroll infini pour declencher lazy-load
#           La page /fr/rent utilise un lazy-loading-container JS (pas de ?page=N)
#           Apres scroll complet, parsing HTML avec BeautifulSoup
#
# Structure listing card :
#   <a class="listings-item-wrapper" href="/rent/detail/ID/slug">
#     <div class="listings-item-header" data-lazyLoadedStyle="background-image: url(...)">
#     <div class="listings-item-city-neighborhood">Luxembourg - Belair</div>
#     <span class="listings-item-right-label">€ 2 200 / month</span>
#     <span class="listing-icons-icon-area-surface">81 sqm</span>
#     <span class="listing-icons-icon-bed">2</span>
#
# Images : background-image CSS dans data-lazyLoadedStyle de .listings-item-header
# Prix : €/month dans listings-item-right-label (extrait depuis la page listing)
# Pagination : infinite scroll (JS lazy-loading), Selenium scrolle jusqu'en bas
# GPS : geocode_city depuis nom de ville
# Filtrage : prix, rooms, surface, mots exclus, distance GPS max
# Instance globale : nexvia_scraper
# =============================================================================
import re
import time
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from scrapers.selenium_template import SeleniumScraperBase
from utils import haversine_distance, geocode_city

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.nexvia.lu/fr/rent"
BASE_URL   = "https://www.nexvia.lu"


class NexviaScraper(SeleniumScraperBase):
    def __init__(self):
        super().__init__(
            site_name="Nexvia.lu",
            base_url=BASE_URL,
            search_url=SEARCH_URL,
        )

    def find_listings_elements(self, driver):
        """Non utilise — parsing via page_source"""
        return []

    def extract_listing_data(self, element):
        """Non utilise — parsing via page_source"""
        return None

    def parse_nexvia_price(self, text: str) -> int:
        """Extrait prix depuis '€ 2 200 / month' ou '€ 1 800 / month'"""
        clean = re.sub(r'[^\d]', '', text)
        try:
            return int(clean)
        except ValueError:
            return 0

    def parse_nexvia_surface(self, text: str) -> int:
        """Extrait surface depuis '81 sqm' ou '95 sqm'"""
        m = re.search(r'(\d+)\s*sqm', text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        return 0

    def parse_nexvia_rooms(self, text: str) -> int:
        """Extrait nombre de chambres depuis texte brut"""
        m = re.search(r'^(\d+)', text.strip())
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        return 0

    def parse_nexvia_image(self, card) -> Optional[str]:
        """Extrait image depuis data-lazyLoadedStyle (background-image CSS)"""
        header = card.find('div', class_=lambda c: c and 'listings-item-header' in c)
        if not header:
            return None
        # Priorite : data-lazyLoadedStyle (URL complete)
        style = header.get('data-lazyLoadedStyle') or header.get('style') or ''
        m = re.search(r"url\(['\"]?([^'\")\s]+)['\"]?\)", style)
        if m:
            url = m.group(1)
            return url if url.startswith('http') else BASE_URL + url
        return None

    def parse_nexvia_city(self, card) -> str:
        """Extrait ville depuis 'Luxembourg - Belair' → 'Luxembourg'"""
        div = card.find('div', class_=lambda c: c and 'listings-item-city-neighborhood' in c)
        if div:
            text = div.get_text(strip=True)
            parts = text.split(' - ')
            return parts[0].strip()
        return ''

    def scroll_to_load_all(self, driver) -> str:
        """Scrolle jusqu'en bas de page pour charger tous les listings lazy-load"""
        SCROLL_PAUSE = 2.5
        MAX_SCROLLS = 20  # limite securite (~200 annonces max)

        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(MAX_SCROLLS):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break  # Plus de contenu a charger
            last_height = new_height

        return driver.page_source

    def scrape(self) -> List[Dict]:
        """Scrape toutes les annonces Nexvia.lu via Selenium scroll infini"""
        from config import (
            MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE,
            EXCLUDED_WORDS, REFERENCE_LAT, REFERENCE_LNG, MAX_DISTANCE
        )
        from utils import extract_available_from

        driver = None
        try:
            driver = self.setup_driver()
            logger.info(f"Nexvia.lu: chargement {SEARCH_URL}")
            driver.get(SEARCH_URL)
            time.sleep(5)  # Attendre chargement initial

            # Scroll infini pour tout charger
            logger.info("Nexvia.lu: scroll infini pour lazy-load...")
            html = self.scroll_to_load_all(driver)

        except Exception as e:
            logger.error(f"Nexvia.lu: erreur Selenium: {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        soup = BeautifulSoup(html, 'html.parser')
        # Cards : <a class="listings-item-wrapper">
        cards = soup.find_all('a', class_=lambda c: c and 'listings-item-wrapper' in c)
        logger.info(f"Nexvia.lu: {len(cards)} cards trouvees apres scroll")

        listings = []
        seen_ids = set()

        for card in cards:
            try:
                # URL de l'annonce
                href = card.get('href', '')
                if not href:
                    continue
                url_annonce = href if href.startswith('http') else BASE_URL + href

                # ID unique depuis URL : /rent/detail/{ID}/{slug}
                m_id = re.search(r'/detail/(\d+)/', href)
                if not m_id:
                    continue
                listing_id = f"nexvia_{m_id.group(1)}"
                if listing_id in seen_ids:
                    continue
                seen_ids.add(listing_id)

                # Prix
                price_span = card.find('span', class_=lambda c: c and 'listings-item-right-label' in c)
                if not price_span:
                    continue
                prix = self.parse_nexvia_price(price_span.get_text())
                if prix == 0 or prix < MIN_PRICE or prix > MAX_PRICE:
                    continue

                # Surface
                surf_span = card.find('span', class_=lambda c: c and 'listing-icons-icon-area-surface' in c)
                surface = self.parse_nexvia_surface(surf_span.get_text()) if surf_span else 0
                if surface > 0 and surface < MIN_SURFACE:
                    continue

                # Chambres
                rooms_span = card.find('span', class_=lambda c: c and 'listing-icons-icon-bed' in c)
                rooms = self.parse_nexvia_rooms(rooms_span.get_text()) if rooms_span else 0
                if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                    continue

                # Ville
                city = self.parse_nexvia_city(card)

                # Titre : ville + rue si disponible
                street_div = card.find('div', class_=lambda c: c and 'listings-item-street' in c)
                street = street_div.get_text(strip=True) if street_div else ''
                city_div = card.find('div', class_=lambda c: c and 'listings-item-city-neighborhood' in c)
                city_full = city_div.get_text(strip=True) if city_div else city
                title = f"{city_full}" + (f" — {street}" if street else '')

                # Mots exclus
                if any(w.lower() in title.lower() for w in EXCLUDED_WORDS):
                    continue

                # Image
                image_url = self.parse_nexvia_image(card)

                # Date de disponibilite
                available_from = extract_available_from(title)

                # GPS depuis nom de ville
                lat, lng = geocode_city(city)
                distance_km = None
                if lat and lng:
                    distance_km = haversine_distance(REFERENCE_LAT, REFERENCE_LNG, lat, lng)
                    if distance_km > MAX_DISTANCE:
                        continue

                listing = {
                    'listing_id':     listing_id,
                    'site':           self.site_name,
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
                logger.warning(f"Nexvia: erreur card: {e}")
                continue

        logger.info(f"✅ Nexvia.lu — {len(listings)} annonces apres filtrage")
        return listings


# Instance globale (pour import dans main.py)
nexvia_scraper = NexviaScraper()
