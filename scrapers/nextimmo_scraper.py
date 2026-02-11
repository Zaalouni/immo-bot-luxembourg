
# scrapers/nextimmo_scraper.py
# Scraper pour Nextimmo.lu — portail immobilier Luxembourg
import requests
import logging
import re
from bs4 import BeautifulSoup
from config import USER_AGENT, MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class NextimmoScraper:
    """Scraper pour Nextimmo.lu — annonces location Luxembourg"""

    def __init__(self):
        self.base_url = 'https://nextimmo.lu'
        self.search_url = 'https://nextimmo.lu/en/rent/apartment/luxembourg-country'
        self.site_name = 'Nextimmo.lu'
        self.headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
        }

    def scrape(self):
        """Scraper les annonces de location"""
        listings = []

        try:
            logger.info(f"🔍 Scraping {self.site_name}...")

            response = requests.get(self.search_url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} pour {self.search_url}")
                return []

            soup = BeautifulSoup(response.text, 'lxml')

            # Chercher les cartes d'annonces
            cards = (
                soup.select('.property-card') or
                soup.select('.listing-item') or
                soup.select('[class*="property"]') or
                soup.select('[class*="listing"]') or
                soup.select('article') or
                soup.select('.card')
            )

            if not cards:
                # Essayer de parser les liens d'annonces en mode regex
                return self._parse_links(response.text)

            logger.info(f"   🔍 {len(cards)} éléments trouvés")

            for card in cards[:20]:
                try:
                    listing = self._extract_listing(card)
                    if listing and self._matches_criteria(listing):
                        listings.append(listing)
                except Exception as e:
                    logger.debug(f"Erreur extraction: {e}")
                    continue

            logger.info(f"✅ {len(listings)} annonces après filtrage")
            return listings

        except requests.RequestException as e:
            logger.error(f"❌ Erreur réseau {self.site_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Erreur scraping {self.site_name}: {e}")
            return []

    def _extract_listing(self, card):
        """Extraire les données d'une carte annonce"""
        # URL
        link = card.find('a', href=True)
        if not link:
            return None

        url = link['href']
        if not url.startswith('http'):
            url = self.base_url + url

        if 'nextimmo.lu' not in url and not url.startswith(self.base_url):
            return None

        # ID depuis URL
        listing_id = url.rstrip('/').split('/')[-1].split('?')[0]
        if not listing_id or len(listing_id) < 2:
            # Essayer un hash de l'URL
            listing_id = str(abs(hash(url)))[:10]

        # Titre
        title_elem = card.find(['h2', 'h3', 'h4']) or card.find(class_=re.compile(r'title', re.I))
        title = title_elem.get_text(strip=True) if title_elem else ''
        if not title:
            title = link.get_text(strip=True)[:100]

        # Prix
        text = card.get_text()
        price = 0
        price_match = re.search(r'([\d\s\.,]+)\s*€', text)
        if price_match:
            price = self._parse_price(price_match.group(1))

        if price <= 0:
            return None

        # Chambres
        rooms = 0
        rooms_match = re.search(r'(\d+)\s*(?:chambre|bedroom|pièce|room|ch\.)', text, re.IGNORECASE)
        if rooms_match:
            rooms = int(rooms_match.group(1))

        # Surface
        surface = 0
        surface_match = re.search(r'(\d+)\s*m[²2]', text)
        if surface_match:
            surface = int(surface_match.group(1))

        # Ville
        city = "Luxembourg"
        city_match = re.search(
            r'\b(Luxembourg|Esch|Differdange|Dudelange|Mersch|Walferdange|Bertrange|Strassen|Howald|Hesperange|Mamer|Kirchberg|Belair|Bonnevoie|Limpertsberg|Merl|Ettelbruck|Diekirch)\b',
            text, re.IGNORECASE
        )
        if city_match:
            city = city_match.group(1).title()

        return {
            'listing_id': f'nextimmo_{listing_id}',
            'site': self.site_name,
            'title': title[:200],
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'time_ago': 'Récemment'
        }

    def _parse_links(self, html):
        """Parser les liens d'annonces en mode regex (fallback)"""
        listings = []

        # Chercher les URLs d'annonces avec prix
        pattern = re.compile(
            r'href="([^"]*(?:property|listing|annonce|rent)[^"]*)"[^>]*>.*?'
            r'([\d\s\.]+)\s*€',
            re.DOTALL | re.IGNORECASE
        )

        matches = pattern.findall(html)

        for url_path, price_str in matches[:15]:
            url = url_path if url_path.startswith('http') else self.base_url + url_path
            price = self._parse_price(price_str)

            if price <= 0 or price > MAX_PRICE:
                continue

            listing_id = url.rstrip('/').split('/')[-1].split('?')[0]

            listings.append({
                'listing_id': f'nextimmo_{listing_id}',
                'site': self.site_name,
                'title': 'Appartement Luxembourg',
                'city': 'Luxembourg',
                'price': price,
                'rooms': 0,
                'surface': 0,
                'url': url,
                'time_ago': 'Récemment'
            })

        logger.info(f"✅ {len(listings)} annonces trouvées (regex fallback)")
        return listings

    def _parse_price(self, price_str):
        """Parser un prix"""
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

nextimmo_scraper = NextimmoScraper()
