
# =============================================================================
# scrapers/athome_scraper_json.py — Scraper Athome.lu via JSON embarque
# =============================================================================
# Methode : extrait window.__INITIAL_STATE__ du HTML, parse le JSON, extrait
#           les annonces depuis data['search']['list']
# Multi-URL : scrape /location/appartement/ ET /location/maison/
# Pagination : URLs filtrees (prix, chambres) + pages 1..MAX_PAGES
# Robustesse : _safe_str() gere les champs dict/list/None dans le JSON Athome
#              (immotype, price, city, description peuvent etre des dicts)
# Fallbacks JSON : si parse echoue → extraction directe du tableau "list"
#                  → troncature + completion des brackets
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE,
#            EXCLUDED_WORDS, MAX_DISTANCE (GPS Haversine)
# Instance globale : athome_scraper_json
# =============================================================================
import requests
import re
import json
import time
import logging
import random
from config import MAX_PRICE, MIN_PRICE, MIN_ROOMS, MAX_ROOMS, USER_AGENTS
from utils import haversine_distance, validate_listing_data

logger = logging.getLogger(__name__)

MAX_PAGES = 12

class AthomeScraperJSON:
    def __init__(self):
        self.base_url = "https://www.athome.lu"
        # URLs filtrees par prix et chambres pour reduire les resultats
        filter_params = f"?price_min={MIN_PRICE}&price_max={MAX_PRICE}&bedrooms_min={MIN_ROOMS}&bedrooms_max={MAX_ROOMS}"
        self.search_urls = [
            f"{self.base_url}/location/appartement/{filter_params}",
            f"{self.base_url}/location/maison/{filter_params}",
        ]
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

    def _parse_page(self, url):
        """Parser une page Athome et retourner la liste d'items JSON"""
        try:
            # Rotation User-Agent pour éviter détection bot
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} pour {url}")
                return []

            html = response.text
            json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+\});', html, re.DOTALL)
            if not json_match:
                return []

            json_str = json_match.group(1).strip()
            json_clean = json_str
            json_clean = re.sub(r':\s*undefined\b', ':null', json_clean)
            json_clean = re.sub(r',\s*undefined\b', ',null', json_clean)
            json_clean = re.sub(r'\bundefined\s*[,}]', 'null,', json_clean)
            json_clean = re.sub(r':\s*NaN\b', ':null', json_clean)
            json_clean = re.sub(r':\s*-?Infinity\b', ':null', json_clean)
            json_clean = re.sub(r',\s*([}\]])', r'\1', json_clean)
            json_clean = re.sub(r'new\s+Date\([^)]*\)', 'null', json_clean)

            try:
                data = json.loads(json_clean)
            except json.JSONDecodeError as e:
                # Fallback: extraction directe du tableau "list"
                try:
                    list_match = re.search(r'"list"\s*:\s*(\[.*?\])\s*,\s*"(?:total|count|pagination)', json_clean, re.DOTALL)
                    if list_match:
                        return json.loads(list_match.group(1))
                except (json.JSONDecodeError, ValueError) as parse_err:
                    logger.debug(f"Fallback list extraction échouée: {parse_err}")
                # Dernier recours: tronquer et compléter
                try:
                    json_truncated = json_clean[:e.pos]
                    open_braces = json_truncated.count('{') - json_truncated.count('}')
                    open_brackets = json_truncated.count('[') - json_truncated.count(']')
                    json_fixed = json_truncated + (']' * max(0, open_brackets)) + ('}' * max(0, open_braces))
                    data = json.loads(json_fixed)
                except (json.JSONDecodeError, ValueError) as trunc_err:
                    logger.debug(f"Truncate JSON échoué: {trunc_err}")
                    return []

            if 'search' in data and 'list' in data['search']:
                return data['search']['list']
            return []

        except Exception as e:
            logger.debug(f"Erreur parse {url}: {e}")
            return []

    def scrape(self):
        """Scraper Athome.lu — appartements + maisons, avec pagination"""
        try:
            logger.info("Scraping Athome.lu via JSON (appartements + maisons, pagination)")
            all_items = []
            seen_ids = set()

            for search_url in self.search_urls:
                type_label = search_url.split('?')[0].rstrip('/').split('/')[-1]
                for page_num in range(1, MAX_PAGES + 1):
                    page_url = f"{search_url}&page={page_num}"
                    items = self._parse_page(page_url)
                    logger.info(f"  {type_label} page {page_num}: {len(items)} annonces")

                    if not items:
                        break

                    new_count = 0
                    for item in items:
                        item_id = item.get('id')
                        if item_id and item_id not in seen_ids:
                            seen_ids.add(item_id)
                            all_items.append(item)
                            new_count += 1

                    if new_count == 0:
                        break

                    time.sleep(1)

            logger.info(f"Total brut (dedupliqué): {len(all_items)}")

            listings = []
            for item in all_items:
                try:
                    listing = self._extract_listing(item)
                    if listing and self._matches_criteria(listing):
                        # Valider les données avant insertion
                        try:
                            validated = validate_listing_data(listing)
                            listings.append(validated)
                        except (ValueError, KeyError) as ve:
                            logger.debug(f"Validation échouée pour {listing.get('listing_id')}: {ve}")
                except Exception as e:
                    logger.debug(f"Erreur extraction: {e}")
                    continue

            logger.info(f"✅ {len(listings)} annonces après filtrage")
            return listings

        except Exception as e:
            logger.error(f"❌ Scraping Athome: {e}")
            return []

    def _safe_str(self, val, default=''):
        """Convertir en string de façon sûre (dict, list, None → string)"""
        if val is None:
            return default
        if isinstance(val, dict):
            return str(val.get('value', '') or val.get('label', '') or val.get('name', '') or default)
        if isinstance(val, list):
            return str(val[0]) if val else default
        return str(val)

    def _extract_listing(self, item):
        """Extraire données d'une annonce JSON Athome.lu"""
        # ID
        id_val = item.get('id')
        if not id_val:
            return None

        # Prix (int direct)
        price = 0
        price_raw = item.get('price', 0)
        if isinstance(price_raw, dict):
            price_raw = price_raw.get('value', 0) or price_raw.get('amount', 0) or 0
        try:
            price = int(float(price_raw or 0))
        except (ValueError, TypeError):
            price = 0

        # Type immeuble — immotype peut être dict, string, ou autre
        immotype_raw = item.get('immotype', {})
        if isinstance(immotype_raw, dict):
            label = immotype_raw.get('label', '') or ''
            if isinstance(label, dict):
                label = label.get('value', '') or label.get('name', '') or ''
            portal = immotype_raw.get('portal_group', 'apartment') or 'apartment'
            if isinstance(portal, dict):
                portal = portal.get('value', '') or portal.get('name', '') or 'apartment'
            immotype = str(label or portal).lower()
        elif isinstance(immotype_raw, str):
            immotype = immotype_raw.lower()
        else:
            immotype = str(item.get('propertyType', 'apartment') or 'apartment').lower()
        type_fr = self.type_map.get(immotype, immotype)

        # Ville + GPS — geo a cityName, lat, lon
        geo = item.get('geo', {}) or {}
        if isinstance(geo, str):
            city = geo
            lat = None
            lng = None
        else:
            city_raw = geo.get('cityName', '') or geo.get('city', '') or 'Luxembourg'
            city = self._safe_str(city_raw, 'Luxembourg')
            lat = geo.get('lat') or geo.get('latitude')
            lng = geo.get('lon') or geo.get('lng') or geo.get('longitude')

        city_slug = city.lower().replace(' ', '-').replace("'", '')

        # Construction URL
        url = f"{self.base_url}/location/{type_fr}/{city_slug}/id-{id_val}.html"

        # Chambres — top-level roomsCount/bedroomsCount ou characteristic.bedrooms_count
        rooms = 0
        rooms_count = item.get('roomsCount') or item.get('bedroomsCount') or 0
        if isinstance(rooms_count, dict):
            rooms_count = rooms_count.get('value', 0) or 0
        try:
            rooms = int(rooms_count)
        except (ValueError, TypeError):
            pass
        # Fallback dans characteristic
        if rooms == 0:
            char = item.get('characteristic', {}) or {}
            if isinstance(char, dict):
                bc = char.get('bedrooms_count', 0) or char.get('rooms_count', 0) or 0
                if isinstance(bc, dict):
                    bc = bc.get('value', 0) or 0
                try:
                    rooms = int(bc)
                except (ValueError, TypeError):
                    pass

        # Surface — top-level propertySurface ou characteristic
        surface = 0
        surface_raw = item.get('propertySurface') or item.get('minPropertySurface') or 0
        if isinstance(surface_raw, dict):
            surface_raw = surface_raw.get('value', 0) or 0
        try:
            surface = int(float(surface_raw or 0))
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

        # Description/Titre — peut être dict, list, ou string
        description = item.get('description', '') or ''
        if isinstance(description, dict):
            description = str(description.get('value', '') or description.get('text', '') or '')
        elif isinstance(description, list):
            description = str(description[0]) if description else ''
        title = str(description)[:70] if description else f"{type_fr.title()} {city}"

        # Image — chercher dans photos/images/pictures
        image_url = None
        photos = item.get('photos') or item.get('images') or item.get('pictures') or []
        if isinstance(photos, list) and photos:
            first = photos[0]
            if isinstance(first, dict):
                image_url = first.get('url') or first.get('src') or first.get('thumb')
            elif isinstance(first, str):
                image_url = first
        elif isinstance(photos, dict):
            image_url = photos.get('url') or photos.get('src') or photos.get('thumb')
        # Fallback: mainPhoto
        if not image_url:
            main_photo = item.get('mainPhoto') or item.get('photo') or item.get('thumbnail')
            if isinstance(main_photo, dict):
                image_url = main_photo.get('url') or main_photo.get('src')
            elif isinstance(main_photo, str):
                image_url = main_photo

        return {
            'listing_id': f'athome_{id_val}',
            'site': 'Athome.lu',
            'title': title,
            'city': city,
            'price': price,
            'rooms': rooms,
            'surface': surface,
            'url': url,
            'image_url': image_url,
            'latitude': lat,
            'longitude': lng,
            'distance_km': distance_km,
            'time_ago': 'Récemment'
        }

    def _matches_criteria(self, listing):
        """Vérifier critères filtrage complets"""
        try:
            from config import MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS, MAX_DISTANCE

            price = listing.get('price', 0)
            if price <= 0 or price < MIN_PRICE or price > MAX_PRICE:
                return False

            rooms = listing.get('rooms', 0) or 0
            if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                return False

            surface = listing.get('surface', 0) or 0
            if surface > 0 and surface < MIN_SURFACE:
                return False

            title = str(listing.get('title', '')).lower()
            if any(w.strip().lower() in title for w in EXCLUDED_WORDS if w.strip()):
                return False

            distance_km = listing.get('distance_km')
            if distance_km is not None:
                try:
                    if float(distance_km) > MAX_DISTANCE:
                        return False
                except (ValueError, TypeError):
                    pass

            return True
        except Exception:
            return False

athome_scraper_json = AthomeScraperJSON()
