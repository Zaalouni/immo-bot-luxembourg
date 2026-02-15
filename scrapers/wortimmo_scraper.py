
# =============================================================================
# scrapers/wortimmo_scraper.py — Scraper Wortimmo.lu (Luxemburger Wort)
# =============================================================================
# Methode : Selenium Firefox headless avec 3 strategies d'extraction en cascade :
#   1. _extract_from_json()  : cherche JSON embarque (Nuxt, Next, INITIAL_STATE)
#      avec recherche recursive dans les dicts imbriques (_find_listings_in_dict)
#   2. _extract_from_links() : regex sur tous les liens /en/rent/ dans le HTML,
#      extraction du contexte HTML (±1500 chars) autour de chaque lien
#   3. _extract_from_price_elements() : fallback Selenium, cherche les <a>
#      dont le texte contient "€"
#
# GPS : extraction lat/lng depuis JSON + calcul distance Haversine
# Ville : extraite depuis l'URL (/en/rent/TYPE/VILLE/...)
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE,
#            EXCLUDED_WORDS, MAX_DISTANCE
# Instance globale : wortimmo_scraper
# =============================================================================
import logging
import re
import json
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


class WortimmoScraper:
    """Scraper pour Wortimmo.lu via Selenium"""

    def __init__(self):
        self.base_url = 'https://www.wortimmo.lu'
        self.search_url = 'https://www.wortimmo.lu/en/rent'
        self.site_name = 'Wortimmo.lu'

    def scrape(self):
        """Scraper les annonces de location"""
        driver = None

        try:
            logger.info(f"🔍 Scraping {self.site_name} (Selenium)...")

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            driver = webdriver.Firefox(options=options)
            driver.set_page_load_timeout(30)

            logger.info(f"   Chargement {self.search_url}")
            driver.get(self.search_url)

            import time
            time.sleep(10)

            # Accepter cookies
            try:
                cookie_btns = driver.find_elements(By.CSS_SELECTOR,
                    '[id*="accept"], [class*="accept"], button[data-action="accept"], '
                    '.didomi-continue-without-agreeing, #didomi-notice-agree-button')
                if cookie_btns:
                    cookie_btns[0].click()
                    time.sleep(2)
            except Exception:
                pass

            # Scroll complet
            for pct in [0.25, 0.5, 0.75, 1.0]:
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{pct});")
                time.sleep(2)

            page_source = driver.page_source
            logger.info(f"   Page source: {len(page_source)} chars")

            # Méthode 1: Chercher JSON embarqué (Nuxt, Next, initial state)
            listings = self._extract_from_json(page_source)
            if listings:
                logger.info(f"✅ {len(listings)} annonces (JSON)")
                return listings

            # Méthode 2: Chercher TOUS les liens /en/rent/ (relatifs ou absolus)
            listings = self._extract_from_links(driver, page_source)
            if listings:
                logger.info(f"✅ {len(listings)} annonces (liens)")
                return listings

            # Méthode 3: Chercher les <a> contenant un prix
            listings = self._extract_from_price_elements(driver)
            if listings:
                logger.info(f"✅ {len(listings)} annonces (prix elements)")
                return listings

            logger.warning(f"   ⚠️ Aucune annonce trouvée")
            return []

        except Exception as e:
            logger.error(f"❌ Scraping {self.site_name}: {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _extract_from_json(self, page_source):
        """Extraire depuis JSON embarqué dans la page"""
        listings = []

        # Patterns JSON courants
        json_patterns = [
            r'window\.__NUXT__\s*=\s*(\{.+?\});\s*</script>',
            r'window\.__NEXT_DATA__\s*=\s*(\{.+?\});\s*</script>',
            r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});\s*</script>',
            r'window\.__data\s*=\s*(\{.+?\});\s*</script>',
            r'"listings"\s*:\s*(\[.+?\])\s*[,}]',
            r'"properties"\s*:\s*(\[.+?\])\s*[,}]',
            r'"results"\s*:\s*(\[.+?\])\s*[,}]',
        ]

        for pattern in json_patterns:
            match = re.search(pattern, page_source, re.DOTALL)
            if match:
                try:
                    raw = match.group(1)
                    # Nettoyer JS → JSON
                    raw = re.sub(r':\s*undefined\b', ':null', raw)
                    raw = re.sub(r':\s*NaN\b', ':null', raw)
                    raw = re.sub(r',\s*([}\]])', r'\1', raw)

                    data = json.loads(raw)
                    items = []

                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict):
                        # Chercher récursivement un tableau d'annonces
                        items = self._find_listings_in_dict(data)

                    if items:
                        logger.info(f"   📊 JSON trouvé: {len(items)} items")
                        for item in items[:20]:
                            listing = self._parse_json_item(item)
                            if listing and self._matches_criteria(listing):
                                listings.append(listing)
                        if listings:
                            return listings

                except (json.JSONDecodeError, Exception) as e:
                    logger.debug(f"   JSON parse: {e}")
                    continue

        return listings if listings else None

    def _find_listings_in_dict(self, data, depth=0):
        """Chercher récursivement une liste d'annonces dans un dict"""
        if depth > 5:
            return []

        if isinstance(data, list) and len(data) > 2:
            # Vérifier si c'est une liste d'annonces (dicts avec price/url)
            if all(isinstance(i, dict) for i in data[:3]):
                sample = data[0]
                if any(k in sample for k in ['price', 'rent', 'url', 'href', 'id']):
                    return data
            return []

        if isinstance(data, dict):
            for key in ['listings', 'properties', 'results', 'items', 'data', 'list', 'ads', 'records']:
                if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                    return data[key]
            # Recursion
            for val in data.values():
                if isinstance(val, (dict, list)):
                    result = self._find_listings_in_dict(val, depth + 1)
                    if result:
                        return result

        return []

    def _parse_json_item(self, item):
        """Parser un item JSON Wortimmo"""
        if not isinstance(item, dict):
            return None

        # ID
        prop_id = item.get('id') or item.get('property_id') or item.get('adId')
        if not prop_id:
            return None

        # Prix
        price = 0
        for key in ['price', 'rent', 'monthly_rent', 'rentPrice']:
            val = item.get(key)
            if val:
                if isinstance(val, dict):
                    val = val.get('value') or val.get('amount') or 0
                try:
                    price = int(float(val))
                    if price > 0:
                        break
                except (ValueError, TypeError):
                    continue
        if price <= 0:
            return None

        # Titre
        title = str(item.get('title', '') or item.get('name', '') or item.get('headline', '') or 'Annonce Wortimmo')

        # Ville
        city = 'Luxembourg'
        for key in ['city', 'locality', 'location', 'address']:
            val = item.get(key)
            if val:
                if isinstance(val, dict):
                    val = val.get('name') or val.get('city') or val.get('locality') or ''
                if isinstance(val, str) and val.strip():
                    city = val.strip()
                    break

        # Chambres
        rooms = 0
        for key in ['bedrooms', 'rooms', 'bedroomCount', 'nbBedrooms']:
            val = item.get(key)
            if val:
                try:
                    rooms = int(val)
                    if rooms > 0:
                        break
                except (ValueError, TypeError):
                    continue

        # Surface
        surface = 0
        for key in ['surface', 'area', 'livingArea', 'size']:
            val = item.get(key)
            if val:
                if isinstance(val, dict):
                    val = val.get('value') or 0
                try:
                    surface = int(float(val))
                    if surface > 0:
                        break
                except (ValueError, TypeError):
                    continue

        # URL
        url_path = item.get('url') or item.get('href') or item.get('link') or ''
        if url_path and not url_path.startswith('http'):
            url = f"{self.base_url}{url_path}"
        elif url_path:
            url = url_path
        else:
            url = f"{self.base_url}/en/rent/property/{prop_id}"

        # GPS
        lat = item.get('latitude') or item.get('lat')
        lng = item.get('longitude') or item.get('lng') or item.get('lon')
        distance_km = None
        if lat and lng:
            try:
                from utils import haversine_distance
                from config import REFERENCE_LAT, REFERENCE_LNG
                distance_km = haversine_distance(REFERENCE_LAT, REFERENCE_LNG, float(lat), float(lng))
            except Exception:
                pass

        return {
            'listing_id': f'wortimmo_{prop_id}',
            'site': self.site_name,
            'title': str(title)[:200],
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

    def _extract_from_links(self, driver, page_source):
        """Extraire depuis les liens dans le HTML rendu"""
        listings = []

        # Patterns URL larges (relatifs et absolus) — inclure TOUT lien wortimmo detail
        url_patterns = [
            r'href="(/en/rent/[^"]{10,})"',
            r'href="(/fr/location/[^"]{10,})"',
            r'href="(/de/mieten/[^"]{10,})"',
            r'href="(https?://(?:www\.)?wortimmo\.lu/(?:en/rent|fr/location|de/mieten)/[^"]+)"',
            r'href="(/[a-z]{2}/[^"]*(?:apartment|house|flat|studio|appartement|maison)[^"]*)"',
        ]

        all_links = set()
        for pattern in url_patterns:
            matches = re.findall(pattern, page_source)
            all_links.update(matches)

        # Filtrer les liens de navigation (trop courts, pas de détail)
        detail_links = []
        for link in all_links:
            parts = link.rstrip('/').split('/')
            # Un lien de détail a 5+ segments ou contient un ID numérique
            if len(parts) >= 5 or re.search(r'/\d{3,}', link):
                detail_links.append(link)

        logger.info(f"   Liens détail trouvés: {len(detail_links)}")

        if not detail_links:
            return None

        seen_ids = set()
        for link_url in detail_links[:20]:
            full_url = link_url if link_url.startswith('http') else self.base_url + link_url

            # ID depuis URL
            id_match = re.search(r'/(\d{4,})', link_url)
            if not id_match:
                id_match = re.search(r'property[/-](\d+)', link_url)
            if not id_match:
                listing_id = link_url.rstrip('/').split('/')[-1][:30]
            else:
                listing_id = id_match.group(1)

            if listing_id in seen_ids:
                continue
            seen_ids.add(listing_id)

            # Contexte HTML
            escaped = re.escape(link_url)
            ctx_match = re.search(rf'(.{{0,1500}}){escaped}(.{{0,800}})', page_source, re.DOTALL)
            if not ctx_match:
                continue

            context = ctx_match.group(1) + ctx_match.group(2)
            text = re.sub(r'<[^>]+>', ' ', context)
            text = re.sub(r'\s+', ' ', text)

            # Prix
            price = 0
            price_match = re.search(r'([\d\s.,]+)\s*€', text)
            if price_match:
                price_str = price_match.group(1).replace(' ', '').replace('.', '').replace(',', '')
                try:
                    price = int(price_str)
                except ValueError:
                    pass
            if price <= 0 or price > 100000:
                continue

            # Ville depuis URL
            city = self._extract_city(link_url)

            # Chambres
            rooms = 0
            rooms_match = re.search(r'(\d+)\s*(?:chambre|bedroom|room|pièce|ch\.)', text, re.I)
            if rooms_match:
                rooms = int(rooms_match.group(1))

            # Surface
            surface = 0
            surface_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', text)
            if surface_match:
                surface = int(float(surface_match.group(1).replace(',', '.')))

            # Titre
            title_parts = link_url.rstrip('/').split('/')
            title = ' '.join(title_parts[-2:]).replace('-', ' ').title() if len(title_parts) >= 2 else f'Annonce {city}'

            listing = {
                'listing_id': f'wortimmo_{listing_id}',
                'site': self.site_name,
                'title': str(title)[:200],
                'city': city,
                'price': price,
                'rooms': rooms,
                'surface': surface,
                'url': full_url,
                'time_ago': 'Récemment'
            }

            if self._matches_criteria(listing):
                listings.append(listing)

        return listings if listings else None

    def _extract_from_price_elements(self, driver):
        """Dernier fallback: chercher éléments contenant un prix"""
        listings = []

        # Chercher tous les <a> dont le texte contient €
        price_links = driver.find_elements(By.XPATH, "//a[contains(., '€')]")
        logger.info(f"   <a> avec €: {len(price_links)}")

        seen_urls = set()
        for elem in price_links[:50]:
            try:
                href = elem.get_attribute('href') or ''
                text = elem.text or ''

                if not href or not text or href in seen_urls:
                    continue
                # Accepter tout lien wortimmo (les detail links n'ont pas forcement /rent/)
                if 'wortimmo.lu' not in href:
                    continue
                # Ignorer navigation et pagination
                clean_href = href.rstrip('/')
                if clean_href == self.search_url.rstrip('/'):
                    continue
                if '?page=' in href and '/' not in href.split('?page=')[1]:
                    continue
                # Ignorer liens trop courts (navigation)
                path = href.replace('https://www.wortimmo.lu', '').rstrip('/')
                if len(path) < 10:
                    continue
                seen_urls.add(href)

                # Prix
                price = 0
                for line in text.split('\n'):
                    if '€' in line:
                        digits = re.sub(r'[^\d]', '', line.split('€')[0])
                        if digits:
                            try:
                                p = int(digits)
                                if 100 < p < 100000:
                                    price = p
                                    break
                            except ValueError:
                                continue
                if price <= 0:
                    continue

                # ID
                id_match = re.search(r'/(\d{4,})', href)
                listing_id = id_match.group(1) if id_match else str(abs(hash(href)))[:8]

                # Titre
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                title = lines[0] if lines else 'Annonce Wortimmo'

                # Chambres / Surface
                rooms = 0
                rooms_match = re.search(r'(\d+)\s*(?:chambre|room|bedroom)', text, re.I)
                if rooms_match:
                    rooms = int(rooms_match.group(1))

                surface = 0
                surface_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', text)
                if surface_match:
                    surface = int(float(surface_match.group(1).replace(',', '.')))

                city = self._extract_city(href)

                listing = {
                    'listing_id': f'wortimmo_{listing_id}',
                    'site': self.site_name,
                    'title': str(title)[:200],
                    'city': city,
                    'price': price,
                    'rooms': rooms,
                    'surface': surface,
                    'url': href,
                    'time_ago': 'Récemment'
                }

                if self._matches_criteria(listing):
                    listings.append(listing)

            except Exception as e:
                logger.debug(f"   Erreur extraction prix elem: {e}")
                continue

        return listings if listings else None

    def _extract_city(self, url):
        """Extraire ville depuis URL Wortimmo"""
        parts = url.split('/')
        for i, part in enumerate(parts):
            if part in ('rent', 'louer', 'mieten') and i + 2 < len(parts):
                city_slug = parts[i + 2]
                # Ignorer les segments numériques et les types
                if not city_slug.isdigit() and city_slug not in ('apartment', 'house', 'property', 'flat', 'studio'):
                    return city_slug.replace('-', ' ').title()
        return 'Luxembourg'

    def _matches_criteria(self, listing):
        """Vérifier critères complets"""
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


wortimmo_scraper = WortimmoScraper()
