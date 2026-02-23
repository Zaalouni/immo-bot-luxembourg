
#!/usr/bin/env python3
# =============================================================================
# scrapers/luxhome_scraper.py — Scraper Luxhome.lu via JSON/Regex embarque
# =============================================================================
# Methode : requete HTTP GET, extraction des annonces par regex sur JSON
#           embarque dans le HTML. Base sur script test valide (61 annonces).
# Types : appartement, maison, duplex, triplex, penthouse
# GPS : calcul distance Haversine depuis point de reference config.py
# Images : extraction thumbnails depuis le HTML
# Filtrage : prix, rooms, surface, mots exclus, distance GPS max
# Fallback : luxhome_scraper_final.py (Selenium) si cet import echoue
# Instance globale : luxhome_scraper
# =============================================================================
import requests
import re
import random
from typing import List, Dict
import logging
from config import USER_AGENTS
from utils import haversine_distance, validate_listing_data

logger = logging.getLogger(__name__)
class LuxhomeScraper:
    def __init__(self):
        self.name = "Luxhome.lu"
        self.base_url = "https://www.luxhome.lu"
        self.search_url = f"{self.base_url}/recherche/?status%5B%5D=location"

    def decode_text(self, text: str) -> str:
        """Décode caractères Unicode + HTML entities"""
        replacements = {
            '\\u00e9': 'é', '\\u00e8': 'è', '\\u00ea': 'ê', '\\u00e0': 'à',
            '\\u00e2': 'â', '\\u00ee': 'î', '\\u00f4': 'ô', '\\u00fb': 'û',
            '\\u00e7': 'ç', '\\u00ef': 'ï', '\\u00eb': 'ë', '\\u00fc': 'ü',
            '\\u00f9': 'ù', '\\u20ac': '€', '\\u00b2': '²', '\\u00b3': '³',
            '&#8217;': "'", '&#8211;': '-', '&#8220;': '"', '&#8221;': '"',
            '&#038;': '&', '\\/': '/'
        }
        for code, char in replacements.items():
            text = text.replace(code, char)
        return text

    def extract_number(self, text: str, pattern: str) -> int:
        """Extrait premier nombre depuis texte via regex"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except:
                pass
        return 0

    def scrape(self) -> List[Dict]:
        """
        Extrait annonces location depuis Luxhome.lu
        Retourne liste objets standardisés : {id, site, title, price, rooms, surface, location, url}
        """
        try:
            # Import config ici (évite erreur circulaire)
            from config import (
                MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE,
                PREFERRED_CITIES, EXCLUDED_WORDS
            )

            logger.info(f"Scraping {self.search_url}")

            response = requests.get(
                self.search_url,
                headers={'User-Agent': random.choice(USER_AGENTS)},
                timeout=15,
                verify=True
            )
            response.raise_for_status()
            html = response.text

            # Security: Limite taille réponse pour éviter ReDoS
            if len(html) > 10_000_000:  # 10MB max
                logger.warning(f"Response trop volumineux ({len(html)/1e6:.1f}MB)")
                return []

            # Pattern regex validé par script test (61 annonces extraites)
            # Bounded: [^"]+ → [^"]{1,500} pour éviter ReDoS
            pattern = r'\{\s*"title":"([^"]{1,500})",\s*"propertyType":"([^"]{1,200})",\s*"price":"([^"]{1,100})",\s*"url":"([^"]{1,500})",\s*"id":(\d+),\s*"lat":"([^"]{1,50})",\s*"lng":"([^"]{1,50})",\s*"thumb":"([^"]{1,500})",'

            matches = re.findall(pattern, html, re.DOTALL)
            logger.info(f"Annonces brutes trouvées: {len(matches)}")

            listings = []

            for match in matches:
                titre_raw, type_raw, prix_raw, url_rel, id_str, lat, lng, thumb_raw = match

                # Décodage Unicode + suppression balises HTML
                titre = re.sub(r'<[^>]+>', '', self.decode_text(titre_raw)).strip()
                type_bien = re.sub(r'<[^>]+>', '', self.decode_text(type_raw)).strip()

                # Construction URL complète (correction /fr/)
                url = self.decode_text(url_rel)
                
                # Ajouter /fr/ si URL commence par /bien/
                if url.startswith('/bien/'):
                    url = f"{self.base_url}/fr{url}"
                elif url.startswith('/'):
                    url = f"{self.base_url}{url}"
                elif not url.startswith('http'):
                    url = f"{self.base_url}/{url}"

                # Extraction prix (format "2 500 €/mois" ou "2500€" ou "1.100€")
                prix = 0
                prix_clean = prix_raw.replace('\\u20ac', '').replace('€', '').replace(' ', '').replace('.', '').replace(',', '')
                prix_match = re.search(r'(\d+)', prix_clean)
                if prix_match:
                    try:
                        prix = int(prix_match.group(1))
                    except:
                        pass

                # Extraction surface (depuis titre)
                surface = self.extract_number(titre, r'(\d+)\s*m\s*[²2b]')

                # Extraction chambres (depuis titre)
                chambres = self.extract_number(titre, r'(\d+)\s*(chambre|chbr|chr|pi[èe]ce|room|ch\b|bedroom)')

                # Extraction localisation (depuis titre)
                localisation = ''
                for city in PREFERRED_CITIES:
                    if city.lower() in titre.lower():
                        localisation = city
                        break

                # === FILTRAGE (applique critères config.py) ===

                # Filtre 1 : Type appartement/maison uniquement (studio exclu via EXCLUDED_WORDS)
                type_lower = type_bien.lower()
                if not ('appartement' in type_lower or 'apartment' in type_lower or 'maison' in type_lower or 'house' in type_lower or 'duplex' in type_lower or 'triplex' in type_lower or 'penthouse' in type_lower):
                    continue

                # Filtre 2 : Prix
                if prix < MIN_PRICE or prix > MAX_PRICE:
                    continue

                # Filtre 3 : Chambres (si détectées)
                # Note : Luxhome a peu d'info chambres dans titre, on accepte si non détecté
                if chambres > 0 and (chambres < MIN_ROOMS or chambres > MAX_ROOMS):
                    continue

                # Filtre 4 : Surface (si détectée)
                if surface > 0 and surface < MIN_SURFACE:
                    continue

                # Filtre 5 : Mots exclus
                titre_lower = titre.lower()
                if any(word.lower() in titre_lower for word in EXCLUDED_WORDS):
                    continue

                # Calcul distance depuis point référence
                distance_km = None
                if lat and lng:
                    try:
                        from config import REFERENCE_LAT, REFERENCE_LNG, MAX_DISTANCE
                        distance_km = haversine_distance(
                            REFERENCE_LAT, REFERENCE_LNG,
                            float(lat), float(lng)
                        )
                        # Filtre 6 : Distance max
                        if distance_km is not None and distance_km > MAX_DISTANCE:
                            continue
                    except Exception:
                        pass

                # Image thumbnail
                image_url = None
                if thumb_raw:
                    thumb = self.decode_text(thumb_raw)
                    if thumb.startswith('//'):
                        thumb = 'https:' + thumb
                    elif thumb.startswith('/'):
                        thumb = self.base_url + thumb
                    image_url = thumb

                # Construction objet standardisé
                listing = {
                    'listing_id': f"luxhome_{id_str}",
                    'site': self.name,
                    'title': titre,
                    'price': prix,
                    'rooms': chambres if chambres > 0 else 0,
                    'surface': surface if surface > 0 else 0,
                    'city': localisation,
                    'url': url,
                    'image_url': image_url,
                    'latitude': lat,
                    'longitude': lng,
                    'distance_km': distance_km
                }

                # Valider avant ajout
                try:
                    validated = validate_listing_data(listing)
                    listings.append(validated)
                except (ValueError, KeyError) as ve:
                    logger.debug(f"Validation échouée: {ve}")

            logger.info(f"✅ {len(listings)} annonces après filtrage")
            return listings

        except requests.RequestException as e:
            logger.error(f"❌ Erreur HTTP Luxhome: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Erreur scraping Luxhome: {e}", exc_info=True)
            return []

# Instance globale (pour import dans main.py)
luxhome_scraper = LuxhomeScraper()
