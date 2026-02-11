
# scrapers/athome_scraper_json.py
# Scraper Athome.lu basé sur parsing JSON (CORRIGÉ)
import requests
import re
import json
import logging
from config import MAX_PRICE, MIN_ROOMS
from utils import haversine_distance

logger = logging.getLogger(__name__)

class AthomeScraperJSON:
    def __init__(self):
        self.base_url = "https://www.athome.lu"
        self.search_url = f"{self.base_url}/location"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # Mapping types immobiliers
        self.type_map = {
            'apartment': 'appartement',
            'house': 'maison',
            'office': 'bureau',
            'parking': 'parking',
            'land': 'terrain',
            'commercial': 'commerce'
        }

    def scrape(self):
        try:
            logger.info("Scraping Athome.lu via JSON")
            response = requests.get(self.search_url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code}")
                return []

            html = response.text

            # Extraire JSON depuis window.__INITIAL_STATE__
            # Chercher pattern jusqu'au }; final
            json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+\});', html, re.DOTALL)
            if not json_match:
                logger.error("JSON __INITIAL_STATE__ non trouvé")
                return []

            # Parser JSON (corriger undefined → null)
            json_str = json_match.group(1).strip()

            # Corrections multiples
            json_clean = (json_str
                .replace(':undefined', ':null')
                .replace(',undefined', ',null')
                .replace('undefined,', 'null,')
                .replace('undefined}', 'null}'))

            try:
                data = json.loads(json_clean)
            except json.JSONDecodeError as e:
                logger.error(f"Parsing JSON échoué position {e.pos}: {e.msg}")
                # Tentative avec extraction jusqu'à position erreur
                try:
                    # Chercher dernier objet valide avant erreur
                    json_truncated = json_clean[:e.pos]
                    # Compléter si nécessaire
                    open_braces = json_truncated.count('{') - json_truncated.count('}')
                    json_fixed = json_truncated + ('}' * open_braces)
                    data = json.loads(json_fixed)
                    logger.warning("JSON parsé partiellement après correction")
                except:
                    logger.error("Impossible de parser JSON même partiellement")
                    return []

            # Extraire annonces
            if 'search' not in data or 'list' not in data['search']:
                logger.error("Structure JSON inattendue")
                return []

            items = data['search']['list']
            logger.info(f"Annonces trouvées: {len(items)}")

            listings = []
            for item in items[:15]:  # Limiter à 15
                try:
                    listing = self._extract_listing(item)
                    if listing and self._matches_criteria(listing):
                        listings.append(listing)
                except Exception as e:
                    logger.debug(f"Erreur extraction: {e}")
                    continue

            logger.info(f"✅ {len(listings)} annonces après filtrage")
            return listings

        except Exception as e:
            logger.error(f"❌ Scraping Athome: {e}")
            return []

    def _extract_listing(self, item):
        """Extraire données d'une annonce JSON"""
        # ID
        id_val = item.get('id')
        if not id_val:
            return None

        # Prix
        price = item.get('price', 0)
        if not isinstance(price, int):
            price = 0

        # Type immeuble
        immotype = item.get('immotype', 'apartment').lower()
        type_fr = self.type_map.get(immotype, immotype)

        # Ville + GPS
        geo = item.get('geo', {})
        lat = None
        lng = None
        
        if isinstance(geo, dict):
            city_raw = geo.get('city')
            city = city_raw if isinstance(city_raw, str) else 'Luxembourg'
            
            # Extraire coordonnées GPS
            lat = geo.get('lat') or geo.get('latitude')
            lng = geo.get('lng') or geo.get('longitude')
        else:
            city = 'Luxembourg'

        city_slug = city.lower().replace(' ', '-').replace("'", '')

        # Construction URL
        url = f"{self.base_url}/location/{type_fr}/{city_slug}/id-{id_val}.html"

        # Chambres depuis characteristic
        rooms = 1
        char = item.get('characteristic', {})
        if isinstance(char, dict):
            rooms_count = char.get('rooms_count')
            if isinstance(rooms_count, int) and rooms_count > 0:
                rooms = rooms_count
            elif isinstance(rooms_count, dict):
                rooms = rooms_count.get('value', 1)

        # Surface - utiliser property_surface
        surface = 0
        if isinstance(char, dict):
            # Priorité: property_surface > property_max_surface
            surface_val = char.get('property_surface') or char.get('property_max_surface')
            if isinstance(surface_val, (int, float)) and surface_val > 0:
                surface = int(surface_val)

        # Calcul distance GPS
        distance_km = None
        if lat is not None and lng is not None:
            try:
                from config import REFERENCE_LAT, REFERENCE_LNG
                distance_km = haversine_distance(
                    REFERENCE_LAT, REFERENCE_LNG,
                    float(lat), float(lng)
                )
            except Exception as e:
                logger.debug(f"Erreur calcul distance: {e}")


        # Description/Titre
        description = item.get('description', '')
        title = description[:70] if description else f"{type_fr.title()} {city}"

        return {
            'listing_id': f'athome_{id_val}',
            'site': 'Athome.lu',
            'title': title,
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'time_ago': 'Récemment'
        }

    def _matches_criteria(self, listing):
        """Vérifier critères filtrage"""
        try:
            if listing['price'] > MAX_PRICE or listing['price'] <= 0:
                return False

            if listing['rooms'] < MIN_ROOMS:
                return False

            return True
        except:
            return False

athome_scraper_json = AthomeScraperJSON()
