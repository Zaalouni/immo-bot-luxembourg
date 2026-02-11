
# scrapers/immoweb_scraper.py
# Scraper pour Immoweb.be — section Luxembourg
import requests
import logging
import re
import json
from config import USER_AGENT, MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class ImmowebScraper:
    """Scraper pour Immoweb.be — annonces Luxembourg"""

    def __init__(self):
        self.base_url = 'https://www.immoweb.be'
        # API JSON d'Immoweb (retourne du JSON directement)
        self.search_url = 'https://www.immoweb.be/en/search/apartment/for-rent/luxembourg/province'
        self.site_name = 'Immoweb.be'
        self.headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
        }

    def scrape(self):
        """Scraper les annonces de location au Luxembourg"""
        listings = []

        try:
            logger.info(f"🔍 Scraping {self.site_name}...")

            response = requests.get(self.search_url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} pour {self.search_url}")
                return []

            html = response.text

            # Immoweb stocke les données dans un JSON embarqué
            # Chercher window.__CLASSIFIED_LIST__ ou iw-search
            json_match = re.search(r'window\.classified\s*=\s*(\{.+?\});', html, re.DOTALL)

            if json_match:
                return self._parse_json(json_match.group(1))

            # Sinon, parser le HTML avec regex
            return self._parse_html(html)

        except requests.RequestException as e:
            logger.error(f"❌ Erreur réseau {self.site_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Erreur scraping {self.site_name}: {e}")
            return []

    def _parse_html(self, html):
        """Parser le HTML pour extraire les annonces"""
        listings = []

        # Pattern pour les cartes d'annonces Immoweb
        # Format: <article> avec data-url, prix, titre, etc.
        card_pattern = re.compile(
            r'<article[^>]*class="[^"]*card--result[^"]*"[^>]*>.*?</article>',
            re.DOTALL | re.IGNORECASE
        )

        cards = card_pattern.findall(html)

        if not cards:
            # Alternative : chercher les liens d'annonces
            link_pattern = re.compile(
                r'href="(/en/classified/[^"]+/(\d+))"[^>]*>.*?'
                r'([\d\s\.]+)\s*€',
                re.DOTALL | re.IGNORECASE
            )
            matches = link_pattern.findall(html)

            for match in matches[:15]:
                url_path, listing_id, price_str = match
                price = self._parse_price(price_str)

                if price <= 0 or price > MAX_PRICE:
                    continue

                listings.append({
                    'listing_id': f'immoweb_{listing_id}',
                    'site': self.site_name,
                    'title': f'Appartement Luxembourg',
                    'city': 'Luxembourg',
                    'price': price,
                    'rooms': 0,
                    'surface': 0,
                    'url': f'{self.base_url}{url_path}',
                    'time_ago': 'Récemment'
                })

            logger.info(f"✅ {len(listings)} annonces trouvées (HTML)")
            return listings

        for card_html in cards[:15]:
            try:
                listing = self._extract_from_card(card_html)
                if listing and self._matches_criteria(listing):
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Erreur extraction: {e}")
                continue

        logger.info(f"✅ {len(listings)} annonces après filtrage")
        return listings

    def _extract_from_card(self, card_html):
        """Extraire données d'une carte HTML"""
        # URL
        url_match = re.search(r'href="(/en/classified/[^"]+/(\d+))"', card_html)
        if not url_match:
            return None

        url = f'{self.base_url}{url_match.group(1)}'
        listing_id = url_match.group(2)

        # Titre
        title_match = re.search(r'<h2[^>]*>(.*?)</h2>', card_html, re.DOTALL)
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else 'Appartement'

        # Prix
        price_match = re.search(r'([\d\s\.]+)\s*€', card_html)
        price = self._parse_price(price_match.group(1)) if price_match else 0

        if price <= 0:
            return None

        # Chambres
        rooms = 0
        rooms_match = re.search(r'(\d+)\s*(?:ch\.|bedroom|chambre|room)', card_html, re.IGNORECASE)
        if rooms_match:
            rooms = int(rooms_match.group(1))

        # Surface
        surface = 0
        surface_match = re.search(r'(\d+)\s*m[²2]', card_html)
        if surface_match:
            surface = int(surface_match.group(1))

        # Ville
        city = 'Luxembourg'
        city_match = re.search(
            r'\b(Luxembourg|Esch|Differdange|Dudelange|Mersch|Ettelbruck|Diekirch|Wiltz|Clervaux|Remich|Grevenmacher)\b',
            card_html, re.IGNORECASE
        )
        if city_match:
            city = city_match.group(1).title()

        return {
            'listing_id': f'immoweb_{listing_id}',
            'site': self.site_name,
            'title': title[:200],
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'time_ago': 'Récemment'
        }

    def _parse_json(self, json_str):
        """Parser les données JSON embarquées"""
        listings = []
        try:
            data = json.loads(json_str)
            items = data if isinstance(data, list) else data.get('results', [])

            for item in items[:15]:
                try:
                    listing_id = item.get('id', '')
                    price = item.get('price', {}).get('mainValue', 0) if isinstance(item.get('price'), dict) else 0
                    title = item.get('property', {}).get('title', 'Appartement')
                    city = item.get('property', {}).get('location', {}).get('locality', 'Luxembourg')
                    rooms = item.get('property', {}).get('bedroomCount', 0)
                    surface = item.get('property', {}).get('netHabitableSurface', 0)
                    url = f'{self.base_url}/en/classified/{listing_id}'

                    if price > 0 and self._matches_criteria({'price': price, 'rooms': rooms}):
                        listings.append({
                            'listing_id': f'immoweb_{listing_id}',
                            'site': self.site_name,
                            'title': str(title)[:200],
                            'city': str(city),
                            'price': int(price),
                            'rooms': int(rooms) if rooms else 0,
                            'surface': int(surface) if surface else 0,
                            'url': url,
                            'time_ago': 'Récemment'
                        })
                except Exception as e:
                    logger.debug(f"Erreur extraction JSON: {e}")
                    continue

            logger.info(f"✅ {len(listings)} annonces trouvées (JSON)")
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")

        return listings

    def _parse_price(self, price_str):
        """Parser un prix depuis une chaîne"""
        if not price_str:
            return 0
        cleaned = price_str.replace(' ', '').replace('.', '').replace('\u202f', '').replace(',', '')
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def _matches_criteria(self, listing):
        """Vérifier critères"""
        try:
            if listing['price'] > MAX_PRICE or listing['price'] <= 0:
                return False
            if listing.get('rooms', 0) < MIN_ROOMS:
                return False
            return True
        except Exception:
            return False

immoweb_scraper = ImmowebScraper()
