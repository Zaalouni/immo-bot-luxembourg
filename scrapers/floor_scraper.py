# =============================================================================
# scrapers/floor_scraper.py — Scraper Floor.lu via HTML statique
# =============================================================================
# Méthode : requête HTTP GET, extraction des articles HTML regex
# URL : https://floor.lu/type/location/ avec pagination /page/N/
# Annonces : <article class="cards-bien__el"> contient tous les infos
#           - URL: href du lien <a>
#           - Type: <p class="name">
#           - Prix: <p class="price"> (format: "1.250 €/mois")
#           - Localisation: <p class="localisation">
#           - Chambres: <p class="infos__el--bedroom">
#           - Surface: <p class="infos__el--surface"> (format: "22.00 m²")
#           - Image: <img data-lazy-src="...">
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE,
#            EXCLUDED_WORDS, EXCLUDED_CITIES
# Instance globale : floor_scraper
# =============================================================================
import requests
import re
import time
import logging
import random
from config import MAX_PRICE, MIN_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS, EXCLUDED_CITIES, USER_AGENTS, SCRAPER_TIMEOUTS, SCRAPER_SLEEP_CONFIG, RETRY_CONFIG
from utils import validate_listing_data, retry_with_backoff
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)

# Utiliser config centralisée (fallback si config missing)
MAX_PAGES = 5
TIMEOUT = SCRAPER_TIMEOUTS.get('default', 30)  # Fallback 30s si config manque
SLEEP_BETWEEN_PAGES = SCRAPER_SLEEP_CONFIG.get('between_pages', (1, 2))


class FloorScraper:
    """Scraper Floor.lu via HTML statique"""

    def __init__(self):
        self.base_url = "https://floor.lu"
        self.list_url = f"{self.base_url}/type/location/"
        self.site_name = "Floor.lu"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

    def scrape(self):
        """Scraper Floor.lu — locations"""
        all_cards = []
        seen_refs = set()

        try:
            for page_num in range(1, MAX_PAGES + 1):
                # Page 1: URL base, pages suivantes: /page/N/
                if page_num == 1:
                    url = self.list_url
                else:
                    url = f"{self.list_url}page/{page_num}/"

                logger.info(f"[Floor.lu] Chargement page {page_num}: {url}")

                try:
                    # Utiliser retry automatique avec backoff
                    resp = retry_with_backoff(
                        lambda: requests.get(url, headers=self.headers, timeout=TIMEOUT),
                        max_attempts=RETRY_CONFIG.get('max_attempts', 3),
                        base_delay=RETRY_CONFIG.get('base_delay', 1),
                        backoff_multiplier=RETRY_CONFIG.get('backoff_multiplier', 2),
                        logger_obj=logger
                    )
                    if resp.status_code != 200:
                        logger.warning(f"  HTTP {resp.status_code}")
                        break
                except (Timeout, ConnectionError, RequestException) as e:
                    logger.warning(f"  Erreur réseau page {page_num}: {type(e).__name__}")
                    break

                html = resp.text

                # Extraire les articles
                # Pattern: <article class="cards-bien__el">...</article>
                article_pattern = re.compile(
                    r'<article[^>]*class="cards-bien__el"[^>]*>(.*?)</article>',
                    re.DOTALL
                )

                new_count = 0
                for m in article_pattern.finditer(html):
                    article_html = m.group(1)

                    card_data = self._parse_article(article_html)
                    if card_data:
                        ref = card_data['listing_id']
                        if ref not in seen_refs:
                            seen_refs.add(ref)
                            all_cards.append(card_data)
                            new_count += 1

                logger.info(f"  Page {page_num}: {new_count} nouvelles annonces")

                if new_count == 0:
                    break

                if page_num < MAX_PAGES:
                    # Sleep aléatoire entre pages (config centralisée)
                    sleep_min, sleep_max = SLEEP_BETWEEN_PAGES
                    sleep_delay = random.uniform(sleep_min, sleep_max)
                    time.sleep(sleep_delay)

        except Exception as e:
            logger.error(f"❌ Scraping Floor.lu: {e}")
            return []

        logger.info(f"✅ Floor.lu: {len(all_cards)} annonces apres filtrage")
        return all_cards

    def _parse_article(self, article_html):
        """Parser le HTML d'une article"""
        try:
            # Lien
            url_match = re.search(r'<a\s+href="([^"]+)"', article_html)
            if not url_match:
                return None
            full_url = url_match.group(1)

            # Extraire ref depuis l'URL
            ref_match = re.search(r'/bien/([^/]+)/?$', full_url)
            if not ref_match:
                return None
            ref = ref_match.group(1)

            # Type de bien
            type_match = re.search(r'<p\s+class="name">([^<]+)</p>', article_html)
            prop_type = type_match.group(1).strip() if type_match else 'Appartement'

            # Prix: "1.250 €/mois" → extraire 1250
            price = 0
            price_match = re.search(r'<p\s+class="price">\s*([\d\.]+)\s*€', article_html)
            if price_match:
                price_str = price_match.group(1).replace('.', '').replace(',', '')
                try:
                    price = int(price_str)
                except ValueError:
                    return None

            # Filtrer prix
            if price <= 0 or price < MIN_PRICE or price > MAX_PRICE:
                return None

            # Localisation (ville)
            loc_match = re.search(r'<p\s+class="localisation">([^<]+)</p>', article_html)
            location = loc_match.group(1).strip() if loc_match else 'Luxembourg'

            # Ville = premier mot
            city = location.split()[0] if location else 'Luxembourg'

            # Filtrer villes exclues
            if EXCLUDED_CITIES:
                city_check = city.lower().strip()
                if city_check and any(excl in city_check or city_check in excl for excl in EXCLUDED_CITIES):
                    return None

            # Titre
            title = f"{prop_type} — {location}"

            # Chambres
            rooms = 0
            bedroom_match = re.search(r'<p\s+class="infos__el\s+infos__el--bedroom">([^<]+)</p>', article_html)
            if bedroom_match:
                try:
                    rooms = int(bedroom_match.group(1).strip())
                except ValueError:
                    rooms = 0

            # Filtrer chambres
            if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                return None

            # Surface
            surface = 0
            surface_match = re.search(r'<p\s+class="infos__el\s+infos__el--surface">([^<]+)', article_html)
            if surface_match:
                surface_str = surface_match.group(1)
                m_surf = re.search(r'([\d\.]+)\s*m', surface_str)
                if m_surf:
                    try:
                        surface = int(float(m_surf.group(1).replace(',', '.')))
                    except ValueError:
                        surface = 0

            # Filtrer surface
            if surface > 0 and surface < MIN_SURFACE:
                return None

            # Image: data-lazy-src ou src
            image_url = None
            img_match = re.search(r'<img[^>]*data-lazy-src="([^"]+)"', article_html)
            if not img_match:
                img_match = re.search(r'<img[^>]*src="([^"]+)"', article_html)
            if img_match:
                image_url = img_match.group(1)

            # Full text pour filtrage mots exclus
            text = re.sub(r'<[^>]+>', ' ', article_html).lower()

            # Filtrer mots exclus
            if any(w.strip().lower() in text for w in EXCLUDED_WORDS if w.strip()):
                return None

            return {
                'listing_id': f'floor_{ref}',
                'site': self.site_name,
                'title': title[:80],
                'city': city,
                'price': price,
                'rooms': rooms,
                'surface': surface,
                'url': full_url,
                'image_url': image_url,
                'time_ago': 'Récemment',
                'full_text': text[:300],
            }

        except Exception as e:
            logger.debug(f"  Erreur parse article: {e}")
            return None


floor_scraper = FloorScraper()
