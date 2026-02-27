# =============================================================================
# scrapers/sothebys_scraper.py — Scraper Sotheby's Realty Luxembourg
# =============================================================================
# Methode : requete HTTP GET sur la page de locations, extraction des cartes
#           par regex (h3 type, h2 ville, ul>li details, p prix + ref)
# URL liste : /fra/rentals (pagination ?page=N)
# Images : les images de la liste sont blank.gif (JS-charge), donc fetch
#          de chaque page individuelle pour trouver l'asset URL
#          Pattern: https://sothebysrealty.lu/asset/{ID}/1200/650
# Ville : depuis le champ location (ex: "Luxembourg Gasperich" → "Luxembourg")
# Filtrage : MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS, EXCLUDED_CITIES
# Annonces "Loue" filtrees
# Instance globale : sothebys_scraper
# =============================================================================
import requests
import re
import time
import logging
import random
from requests.exceptions import RequestException, Timeout, ConnectionError
from config import MAX_PRICE, MIN_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS, EXCLUDED_CITIES, SCRAPER_TIMEOUTS, SCRAPER_SLEEP_CONFIG, RETRY_CONFIG
from utils import retry_with_backoff

logger = logging.getLogger(__name__)

TIMEOUT = SCRAPER_TIMEOUTS.get('cloudflare', 30)  # Sotheby's peut être lent, utiliser timeout Cloudflare
SLEEP_BETWEEN_PAGES = SCRAPER_SLEEP_CONFIG.get('between_pages', (1, 2))


class SothebysRealtyScaper:
    def __init__(self):
        self.base_url = "https://sothebysrealty.lu"
        self.list_url = f"{self.base_url}/fra/rentals"
        self.site_name = "SothebysRealty.lu"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://sothebysrealty.lu/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def scrape(self):
        """Scraper Sotheby's Realty Luxembourg — locations"""
        all_cards = []
        seen_refs = set()
        MAX_PAGES = 5

        try:
            for page_num in range(1, MAX_PAGES + 1):
                url = self.list_url if page_num == 1 else f"{self.list_url}?page={page_num}"
                logger.info(f"[Sotheby's] Chargement page {page_num}: {url}")

                if page_num > 1:
                    sleep_min, sleep_max = SLEEP_BETWEEN_PAGES
                    time.sleep(random.uniform(sleep_min, sleep_max))

                try:
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
                logger.debug(f"  HTML reçu: {len(html)} chars")

                # Extraire les liens /fra/rentals/REF_... plus rapidement
                # Chercher tous les hrefs d'abord
                href_pattern = re.compile(r'href="(/fra/rentals/(\d+)_[^"]+)"', re.IGNORECASE)
                hrefs = list(href_pattern.finditer(html))
                logger.debug(f"  {len(hrefs)} liens trouvés")

                new_count = 0
                for href_match in hrefs:
                    rel_url = href_match.group(1)
                    ref = href_match.group(2)

                    # Extraire contexte HTML autour du lien (±800 chars)
                    start_pos = max(0, href_match.start() - 800)
                    end_pos = min(len(html), href_match.end() + 800)
                    card_html = html[start_pos:end_pos]

                    if ref in seen_refs:
                        continue
                    seen_refs.add(ref)

                    card_data = self._parse_card(rel_url, ref, card_html)
                    if card_data:
                        all_cards.append(card_data)
                        new_count += 1

                logger.info(f"  Page {page_num}: {new_count} nouvelles annonces")

                if new_count == 0:
                    break

                if page_num < MAX_PAGES:
                    sleep_min, sleep_max = SLEEP_BETWEEN_PAGES
                    time.sleep(random.uniform(sleep_min, sleep_max))

        except (Timeout, ConnectionError, RequestException) as e:
            logger.error(f"❌ Scraping Sotheby's - Erreur réseau: {type(e).__name__}")
            return []
        except Exception as e:
            logger.error(f"❌ Scraping Sotheby's - Erreur: {type(e).__name__}: {str(e)[:100]}")
            return []

        # Récupérer les images depuis les pages individuelles
        logger.info(f"Fetching images for {len(all_cards)} listings...")
        for card in all_cards:
            detail_url = card.pop('_detail_url', None)
            if detail_url:
                try:
                    image_url = self._get_image(detail_url)
                    if image_url:
                        card['image_url'] = image_url
                        logger.debug(f"  Image trouvée: {detail_url}")
                    time.sleep(0.5)  # Rate limit
                except Exception as e:
                    logger.debug(f"  Erreur fetch image: {e}")

        logger.info(f"✅ Sotheby's Realty: {len(all_cards)} annonces apres filtrage")
        return all_cards

    def _parse_card(self, rel_url, ref, card_html):
        """Parser le HTML d'une carte d'annonce depuis la page liste"""
        try:
            # Ignorer les annonces louees
            if re.search(r'lou[eé]', card_html, re.IGNORECASE):
                return None

            # Type de bien (h3)
            type_match = re.search(r'<h3[^>]*>([^<]+)</h3>', card_html, re.IGNORECASE)
            prop_type = type_match.group(1).strip() if type_match else 'Appartement'

            # Localisation (h2)
            loc_match = re.search(r'<h2[^>]*>([^<]+)</h2>', card_html, re.IGNORECASE)
            location = loc_match.group(1).strip() if loc_match else 'Luxembourg'

            # Ville = premier mot de la localisation
            city = location.split()[0] if location else 'Luxembourg'

            # Titre = type + location
            title = f"{prop_type} — {location}"

            # Details depuis les <li> : surface, chambres, sdb
            li_items = re.findall(r'<li[^>]*>([^<]+)</li>', card_html)
            rooms = 0
            surface = 0
            for item in li_items:
                item = item.strip()
                m_surf = re.search(r'(\d+)\s*m[²2]', item)
                if m_surf:
                    surface = int(m_surf.group(1))
                m_ch = re.search(r'(\d+)\s*chambre', item, re.IGNORECASE)
                if m_ch:
                    rooms = int(m_ch.group(1))

            # Prix depuis <p> : "2 350 € — Charges : 300 €" ou "1 800 €"
            # FIX v3.8: Utiliser findall() + MAX au lieu de search() (premier match)
            # Raison: search() capture le PREMIER prix (ex: "2" de "2600"), findall() prend le PLUS GRAND
            price = 0
            # Chercher dans tout le texte brut
            text = re.sub(r'<[^>]+>', ' ', card_html)
            price_matches = re.findall(r'([\d\s]+)\s*€', text)
            if price_matches:
                # Convertir tous les prix trouvés et prendre le MAXIMUM
                # (le loyer principal est toujours > charges/frais)
                try:
                    price_values = []
                    for match in price_matches:
                        clean = re.sub(r'[^\d]', '', match)
                        if clean:
                            price_values.append(int(clean))
                    if price_values:
                        price = max(price_values)
                except Exception:
                    pass

            # Filtres prix
            if price <= 0 or price < MIN_PRICE or price > MAX_PRICE:
                return None

            # Filtres chambres
            if rooms > 0 and (rooms < MIN_ROOMS or rooms > MAX_ROOMS):
                return None

            # Filtres surface
            if surface > 0 and surface < MIN_SURFACE:
                return None

            # Mots exclus
            check = text.lower()
            if any(w.strip().lower() in check for w in EXCLUDED_WORDS if w.strip()):
                return None

            # Filtrer les villes exclues (ex: Arlon en Belgique)
            if EXCLUDED_CITIES:
                city_check = city.lower().strip()
                if city_check and any(excl in city_check or city_check in excl for excl in EXCLUDED_CITIES):
                    return None

            full_url = f"{self.base_url}{rel_url}"

            return {
                'listing_id': f'sothebys_{ref}',
                'site': self.site_name,
                'title': title[:80],
                'city': city,
                'price': price,
                'rooms': rooms,
                'surface': surface,
                'url': full_url,
                'image_url': None,
                '_detail_url': full_url,  # temporaire, supprime apres enrichissement
                'time_ago': 'Récemment',
                'full_text': text[:300],
            }

        except Exception as e:
            logger.debug(f"  Erreur parse card ref={ref}: {e}")
            return None

    def _get_image(self, listing_url):
        """Recuperer l'image principale depuis la page individuelle de l'annonce"""
        try:
            resp = requests.get(listing_url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                return None
            html = resp.text

            # Photo principale = asset avec dimensions 1200/650 (pas la photo agent)
            match = re.search(r'https://sothebysrealty\.lu/asset/(\d+)/1200/650', html)
            if match:
                return f"https://sothebysrealty.lu/asset/{match.group(1)}/1200/650"

            # Fallback: og:image
            og = re.search(r'<meta property="og:image" content="([^"]+)"', html)
            if og:
                return og.group(1)

        except Exception:
            pass
        return None


sothebys_scraper = SothebysRealtyScaper()
