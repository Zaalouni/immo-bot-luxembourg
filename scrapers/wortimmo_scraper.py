
# scrapers/wortimmo_scraper.py
# Scraper pour Wortimmo.lu (Luxemburger Wort immobilier)
import requests
import logging
import re
from bs4 import BeautifulSoup
from config import USER_AGENT, MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class WortimmoScraper:
    """Scraper pour Wortimmo.lu — petites annonces du Luxemburger Wort"""

    def __init__(self):
        self.base_url = 'https://www.wortimmo.lu'
        self.search_url = 'https://www.wortimmo.lu/en/rent'
        self.site_name = 'Wortimmo.lu'
        self.headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
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

            # Chercher les cartes d'annonces avec différents sélecteurs
            cards = (
                soup.select('article.property-card') or
                soup.select('.listing-card') or
                soup.select('[class*="property"]') or
                soup.select('[class*="listing"]') or
                soup.select('article')
            )

            if not cards:
                logger.info(f"   📭 Aucune carte trouvée sur {self.site_name}")
                return []

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

        # ID depuis URL
        listing_id = url.rstrip('/').split('/')[-1].split('?')[0]
        if not listing_id or len(listing_id) < 2:
            return None

        # Titre
        title_elem = card.find(['h2', 'h3', 'h4']) or card.find(class_=re.compile(r'title', re.I))
        title = title_elem.get_text(strip=True) if title_elem else ''
        if not title:
            title = link.get_text(strip=True)[:100]

        # Prix
        price = 0
        text = card.get_text()
        price_match = re.search(r'([\d\s\.]+)\s*€', text)
        if price_match:
            price_str = price_match.group(1).replace(' ', '').replace('.', '').replace('\u202f', '')
            try:
                price = int(price_str)
            except ValueError:
                pass

        if price <= 0:
            return None

        # Chambres
        rooms = 0
        rooms_match = re.search(r'(\d+)\s*(?:chambre|pièce|room|ch\.)', text, re.IGNORECASE)
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
            r'\b(Luxembourg|Esch|Differdange|Dudelange|Mersch|Walferdange|Bertrange|Strassen|Howald|Hesperange|Mamer|Kirchberg|Belair|Bonnevoie|Limpertsberg|Merl|Gasperich|Hollerich|Cessange)\b',
            text, re.IGNORECASE
        )
        if city_match:
            city = city_match.group(1).title()

        return {
            'listing_id': f'wortimmo_{listing_id}',
            'site': self.site_name,
            'title': title[:200],
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'time_ago': 'Récemment'
        }

    def _matches_criteria(self, listing):
        """Vérifier critères"""
        try:
            if listing['price'] > MAX_PRICE or listing['price'] <= 0:
                return False
            rooms = listing.get('rooms', 0)
            if rooms > 0 and rooms < MIN_ROOMS:
                return False
            return True
        except Exception:
            return False

wortimmo_scraper = WortimmoScraper()
