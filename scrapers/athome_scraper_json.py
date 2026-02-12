
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

            # Parser JSON (corriger valeurs JavaScript → JSON valide)
            json_str = json_match.group(1).strip()

            # Corrections JS → JSON
            json_clean = json_str
            # undefined, NaN, Infinity → null
            json_clean = re.sub(r':\s*undefined\b', ':null', json_clean)
            json_clean = re.sub(r',\s*undefined\b', ',null', json_clean)
            json_clean = re.sub(r'\bundefined\s*[,}]', 'null,', json_clean)
            json_clean = re.sub(r':\s*NaN\b', ':null', json_clean)
            json_clean = re.sub(r':\s*-?Infinity\b', ':null', json_clean)
            # Trailing commas: ,] ou ,}
            json_clean = re.sub(r',\s*([}\]])', r'\1', json_clean)
            # new Date(...) → null
            json_clean = re.sub(r'new\s+Date\([^)]*\)', 'null', json_clean)

            try:
                data = json.loads(json_clean)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error pos {e.pos}, tentative extraction list...")
                # Extraire directement le tableau "list" depuis le JSON brut
                try:
                    list_match = re.search(r'"list"\s*:\s*(\[.*?\])\s*,\s*"(?:total|count|pagination)', json_clean, re.DOTALL)
                    if list_match:
                        items = json.loads(list_match.group(1))
                        logger.info(f"Extraction directe list: {len(items)} annonces")
                        listings = []
                        for item in items[:15]:
                            try:
                                listing = self._extract_listing(item)
                                if listing and self._matches_criteria(listing):
                                    listings.append(listing)
                            except Exception:
                                continue
                        logger.info(f"✅ {len(listings)} annonces après filtrage")
                        return listings
                except Exception as e2:
                    logger.debug(f"Extraction directe échouée: {e2}")

                # Dernière tentative : tronquer et compléter
                try:
                    json_truncated = json_clean[:e.pos]
                    open_braces = json_truncated.count('{') - json_truncated.count('}')
                    open_brackets = json_truncated.count('[') - json_truncated.count(']')
                    json_fixed = json_truncated + (']' * max(0, open_brackets)) + ('}' * max(0, open_braces))
                    data = json.loads(json_fixed)
                    logger.warning("JSON parsé partiellement après troncature")
                except Exception:
                    logger.error("Impossible de parser JSON")
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
        """Extraire données d'une annonce JSON Athome.lu"""
        # ID
        id_val = item.get('id')
        if not id_val:
            return None

        # Prix (int direct)
        price = 0
        try:
            price = int(float(item.get('price', 0) or 0))
        except (ValueError, TypeError):
            price = 0

        # Type immeuble — immotype est un dict {label, portal_group, ...}
        immotype_raw = item.get('immotype', {})
        if isinstance(immotype_raw, dict):
            immotype = str(immotype_raw.get('label', '') or immotype_raw.get('portal_group', 'apartment')).lower()
        elif isinstance(immotype_raw, str):
            immotype = immotype_raw.lower()
        else:
            immotype = str(item.get('propertyType', 'apartment')).lower()
        type_fr = self.type_map.get(immotype, immotype)

        # Ville + GPS — geo a cityName, lat, lon
        geo = item.get('geo', {}) or {}
        city = str(geo.get('cityName', '') or geo.get('city', '') or 'Luxembourg')
        lat = geo.get('lat') or geo.get('latitude')
        lng = geo.get('lon') or geo.get('lng') or geo.get('longitude')

        city_slug = city.lower().replace(' ', '-').replace("'", '')

        # Construction URL
        url = f"{self.base_url}/location/{type_fr}/{city_slug}/id-{id_val}.html"

        # Chambres — top-level roomsCount/bedroomsCount ou characteristic.bedrooms_count
        rooms = 0
        rooms_count = item.get('roomsCount') or item.get('bedroomsCount') or 0
        try:
            rooms = int(rooms_count)
        except (ValueError, TypeError):
            pass
        # Fallback dans characteristic
        if rooms == 0:
            char = item.get('characteristic', {}) or {}
            if isinstance(char, dict):
                bc = char.get('bedrooms_count', 0) or char.get('rooms_count', 0) or 0
                try:
                    rooms = int(bc)
                except (ValueError, TypeError):
                    pass

        # Surface — top-level propertySurface ou characteristic
        surface = 0
        surface_raw = item.get('propertySurface') or item.get('minPropertySurface') or 0
        try:
            surface = int(float(surface_raw))
        except (ValueError, TypeError):
            pass

        # Calcul distance GPS
        distance_km = None
        if lat and lng:
            try:
                from config import REFERENCE_LAT, REFERENCE_LNG
                distance_km = haversine_distance(
                    REFERENCE_LAT, REFERENCE_LNG,
                    float(lat), float(lng)
                )
            except Exception:
                pass

        # Description/Titre
        description = item.get('description', '') or ''
        if isinstance(description, dict):
            description = str(description.get('value', '') or '')
        title = str(description)[:70] if description else f"{type_fr.title()} {city}"

        return {
            'listing_id': f'athome_{id_val}',
            'site': 'Athome.lu',
            'title': title,
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'latitude': lat,
            'longitude': lng,
            'distance_km': distance_km,
            'time_ago': 'Récemment'
        }

    def _matches_criteria(self, listing):
        """Vérifier critères filtrage"""
        try:
            price = listing.get('price', 0)
            rooms = listing.get('rooms', 0)

            if price <= 0:
                logger.debug(f"Athome rejeté (prix=0): {listing.get('listing_id')}")
                return False
            if price > MAX_PRICE:
                logger.debug(f"Athome rejeté (prix={price} > {MAX_PRICE}): {listing.get('listing_id')}")
                return False
            if rooms > 0 and rooms < MIN_ROOMS:
                logger.debug(f"Athome rejeté (rooms={rooms} < {MIN_ROOMS}): {listing.get('listing_id')}")
                return False

            return True
        except Exception:
            return False

athome_scraper_json = AthomeScraperJSON()
