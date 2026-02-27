#!/usr/bin/env python3
# =============================================================================
# utils.py — Utilitaires GPS + geocodage villes pour le bot immobilier
# =============================================================================
# Fonctions :
#   - haversine_distance(lat1, lng1, lat2, lng2) : distance en km entre 2 points
#   - geocode_city(city_name) : retourne (lat, lng) depuis dictionnaire local
#   - enrich_listing_gps(listing) : ajoute GPS + distance si manquants
#   - format_distance(km) : formatage lisible ("moins de 1 km", "3.5 km")
#   - get_distance_emoji(km) : emoji couleur selon distance
#
# Dictionnaire LUXEMBOURG_CITIES : ~120 villes/localites avec coordonnees GPS
# Utilise par : main.py (enrichissement + filtrage) et notifier.py (affichage)
# =============================================================================
import math
import logging
import unicodedata

logger = logging.getLogger(__name__)

# =============================================================================
# Dictionnaire GPS des villes/localites du Luxembourg
# Source : coordonnees approximatives centre-ville
# Couvre les communes, quartiers de Luxembourg-Ville et localites courantes
# =============================================================================
LUXEMBOURG_CITIES = {
    # --- Luxembourg-Ville et quartiers ---
    'luxembourg': (49.6116, 6.1319),
    'luxembourg-ville': (49.6116, 6.1319),
    'luxembourg ville': (49.6116, 6.1319),
    'luxemburg': (49.6116, 6.1319),
    'limpertsberg': (49.6200, 6.1250),
    'belair': (49.6100, 6.1150),
    'bel-air': (49.6100, 6.1150),
    'gare': (49.6000, 6.1342),
    'luxembourg-gare': (49.6000, 6.1342),
    'bonnevoie': (49.5950, 6.1400),
    'gasperich': (49.5850, 6.1300),
    'cloche d\'or': (49.5800, 6.1200),
    'cloche dor': (49.5800, 6.1200),
    'kirchberg': (49.6300, 6.1500),
    'kirchberg plateau': (49.6300, 6.1500),
    'beggen': (49.6350, 6.1200),
    'eich': (49.6280, 6.1180),
    'cents': (49.6150, 6.1550),
    'hamm': (49.6050, 6.1500),
    'hollerich': (49.6000, 6.1200),
    'merl': (49.6050, 6.1050),
    'rollingergrund': (49.6200, 6.1100),
    'grund': (49.6100, 6.1350),
    'pfaffenthal': (49.6180, 6.1350),
    'clausen': (49.6130, 6.1420),
    'neudorf': (49.6200, 6.1500),
    'weimerskirch': (49.6350, 6.1400),
    'muhlenbach': (49.6280, 6.1280),
    'dommeldange': (49.6400, 6.1300),
    'cessange': (49.5900, 6.1100),
    'bouneweg': (49.5950, 6.1350),
    'pulvermuhl': (49.6100, 6.1450),

    # --- Communes proches (< 15 km) ---
    'strassen': (49.6200, 6.0700),
    'bertrange': (49.6100, 6.0500),
    'mamer': (49.6270, 6.0230),
    'leudelange': (49.5750, 6.0650),
    'hesperange': (49.5700, 6.1500),
    'sandweiler': (49.5850, 6.2200),
    'niederanven': (49.6500, 6.2500),
    'walferdange': (49.6600, 6.1300),
    'steinsel': (49.6750, 6.1250),
    'kopstal': (49.6600, 6.0700),
    'kehlen': (49.6700, 6.0350),
    'capellen': (49.6450, 6.0000),
    'garnich': (49.6100, 5.9600),
    'bridel': (49.6550, 6.0800),
    'senningerberg': (49.6400, 6.2200),
    'findel': (49.6350, 6.2050),
    'howald': (49.5850, 6.1500),
    'itzig': (49.5700, 6.1700),
    'alzingen': (49.5600, 6.1600),
    'roeser': (49.5450, 6.1500),
    'bettembourg': (49.5200, 6.1050),
    'dudelange': (49.4800, 6.0900),
    'kayl': (49.4850, 6.0350),
    'rumelange': (49.4600, 6.0300),
    'schifflange': (49.5050, 6.0150),
    'mondercange': (49.5350, 6.0200),
    'sanem': (49.5500, 5.9800),
    'differdange': (49.5250, 5.8900),
    'petange': (49.5600, 5.8700),
    'rodange': (49.5500, 5.8400),
    'bascharage': (49.5650, 5.9200),

    # --- Communes moyennes (15-30 km) ---
    'mersch': (49.7500, 6.1050),
    'steinfort': (49.6600, 5.9200),
    'junglinster': (49.7100, 6.2500),
    'grevenmacher': (49.6800, 6.4400),
    'remich': (49.5450, 6.3650),
    'mondorf-les-bains': (49.5050, 6.2800),
    'mondorf': (49.5050, 6.2800),
    'frisange': (49.5100, 6.1900),
    'contern': (49.5750, 6.2300),
    'schuttrange': (49.6200, 6.2650),
    'betzdorf': (49.6800, 6.3500),
    'flaxweiler': (49.6550, 6.3400),
    'wormeldange': (49.6100, 6.4100),
    'stadtbredimus': (49.5650, 6.3650),
    'dalheim': (49.5500, 6.2600),
    'waldbredimus': (49.5550, 6.2850),
    'bous': (49.5600, 6.3200),
    'lenningen': (49.5700, 6.3600),
    'manternach': (49.7100, 6.4200),
    'mertert': (49.7050, 6.4800),
    'wasserbillig': (49.7100, 6.5000),
    'echternach': (49.8100, 6.4200),
    'beaufort': (49.8350, 6.2900),
    'larochette': (49.7850, 6.2200),
    'nommern': (49.7850, 6.1700),
    'lorentzweiler': (49.6950, 6.1400),
    'lintgen': (49.7200, 6.1200),
    'colmar-berg': (49.8100, 6.0950),
    'ettelbruck': (49.8450, 6.1000),
    'diekirch': (49.8700, 6.1600),
    'vianden': (49.9350, 6.2050),
    'clervaux': (50.0550, 6.0300),
    'wiltz': (49.9650, 5.9300),
    'esch-sur-alzette': (49.4950, 5.9800),
    'esch sur alzette': (49.4950, 5.9800),
    'esch/alzette': (49.4950, 5.9800),

    # --- Localites supplementaires courantes ---
    'bertrange (mamer)': (49.6100, 6.0500),
    'bereldange': (49.6650, 6.1250),
    'heisdorf': (49.6700, 6.1350),
    'munsbach': (49.6300, 6.2600),
    'syren': (49.5900, 6.2500),
    'oetrange': (49.5950, 6.2700),
    'roodt-sur-syre': (49.6600, 6.3000),
    'mensdorf': (49.6750, 6.2800),
    'tuntange': (49.7100, 6.0100),
    'olm': (49.6400, 6.0100),
    'windhof': (49.6350, 5.9600),
    'belvaux': (49.5100, 5.9300),
    'soleuvre': (49.5200, 5.9400),
    'oberkorn': (49.5300, 5.8900),
    'niederkorn': (49.5350, 5.8700),
    'lamadelaine': (49.5550, 5.8500),
    'tetange': (49.4750, 6.0350),
    'tетange': (49.4750, 6.0350),
    'foetz': (49.5250, 6.0100),
    'wickrange': (49.5550, 6.0500),
    'berchem': (49.5450, 6.0750),
    'bivange': (49.5500, 6.1100),
    'crauthem': (49.5600, 6.1400),
    'fentange': (49.5700, 6.1550),
    'kockelscheuer': (49.5750, 6.1350),
    'reckange-sur-mess': (49.5650, 6.0350),
    'pontpierre': (49.5550, 6.0550),
    'limpach': (49.5400, 6.0500),
    'noertzange': (49.5100, 6.0700),
    'peppange': (49.5250, 6.1300),
    'aspelt': (49.5200, 6.2100),
    'hellange': (49.5300, 6.2000),
    'weiler-la-tour': (49.5400, 6.1900),
    'hassel': (49.5650, 6.2100),
    'rippig': (49.7000, 6.3100),
    'bech': (49.7500, 6.3600),
    'born': (49.7200, 6.4200),
    'rosport': (49.8050, 6.5050),
    'hinkel': (49.6950, 6.2700),
    'schengen': (49.4700, 6.3700),
    'remerschen': (49.4900, 6.3550),
    'burmerange': (49.4750, 6.3200),
    'wellenstein': (49.5150, 6.3500),
    'bettendorf': (49.8756, 6.2062),
    'reisdorf': (49.8700, 6.2600),
    'oberanven': (49.6577, 6.2406),
    'hostert': (49.6650, 6.2500),
    'gonderange': (49.6900, 6.2500),
    'bourglinster': (49.7050, 6.2200),
    'canach': (49.6100, 6.2900),
    'ahn': (49.6250, 6.4100),
    'ehnen': (49.6100, 6.4000),
    'machtum': (49.6700, 6.4700),
    'greiveldange': (49.5700, 6.3300),
}


def _normalize_for_lookup(city_name):
    """Normaliser un nom de ville pour recherche dans le dictionnaire"""
    if not city_name:
        return ''
    name = str(city_name).lower().strip()
    # Supprimer accents
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    # Nettoyer
    name = name.replace('-', ' ').replace("'", '').replace('/', ' ')
    # Supprimer "commune de", "quartier de", etc.
    for prefix in ['commune de ', 'quartier de ', 'ville de ']:
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.strip()


def geocode_city(city_name):
    """
    Retourne (lat, lng) pour une ville luxembourgeoise depuis le dictionnaire local.
    Cherche d'abord le nom exact, puis un match partiel.

    Returns:
        tuple (lat, lng) ou None si ville inconnue
    """
    if not city_name:
        return None

    normalized = _normalize_for_lookup(city_name)
    if not normalized:
        return None

    # 1. Match exact
    if normalized in LUXEMBOURG_CITIES:
        return LUXEMBOURG_CITIES[normalized]

    # 2. Match exact avec tirets (pour les noms composes)
    dashed = normalized.replace(' ', '-')
    if dashed in LUXEMBOURG_CITIES:
        return LUXEMBOURG_CITIES[dashed]

    # 3. Match partiel : la ville du dico est contenue dans le nom ou inversement
    for key, coords in LUXEMBOURG_CITIES.items():
        if key in normalized or normalized in key:
            return coords

    logger.debug(f"Ville non trouvee dans le dico: '{city_name}' (normalise: '{normalized}')")
    return None


def enrich_listing_gps(listing):
    """
    Enrichir une annonce avec GPS + distance si manquants.
    Utilise le geocodage par ville si pas de coordonnees GPS.
    Modifie le listing in-place.

    Returns:
        listing modifie (meme objet)
    """
    from config import REFERENCE_LAT, REFERENCE_LNG

    lat = listing.get('latitude')
    lng = listing.get('longitude')

    # Si pas de GPS, essayer le geocodage par ville
    if not lat or not lng:
        city = listing.get('city', '')
        coords = geocode_city(city)
        if coords:
            lat, lng = coords
            listing['latitude'] = lat
            listing['longitude'] = lng
            listing['gps_source'] = 'geocode'  # marquer la source
            logger.debug(f"Geocode: '{city}' → ({lat}, {lng})")

    # Calculer la distance si GPS disponible et pas deja calculee
    if lat and lng and listing.get('distance_km') is None:
        try:
            dist = haversine_distance(REFERENCE_LAT, REFERENCE_LNG, float(lat), float(lng))
            if dist is not None:
                listing['distance_km'] = dist
        except (ValueError, TypeError):
            pass

    return listing


def haversine_distance(lat1, lng1, lat2, lng2):
    """
    Calcule distance entre 2 points GPS (formule Haversine)
    
    Returns:
        Distance en kilomètres (float) ou None si erreur
    """
    try:
        R = 6371.0  # Rayon Terre en km
        
        # Convertir degrés en radians
        lat1_rad = math.radians(float(lat1))
        lng1_rad = math.radians(float(lng1))
        lat2_rad = math.radians(float(lat2))
        lng2_rad = math.radians(float(lng2))
        
        # Différences
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        # Formule Haversine
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return round(distance, 1)
    
    except (ValueError, TypeError) as e:
        logger.debug(f"Erreur calcul distance: {e}")
        return None

def format_distance(distance_km):
    """Formate distance pour affichage"""
    if distance_km is None:
        return "N/A"
    elif distance_km < 1:
        return "moins de 1 km"
    elif distance_km < 10:
        return f"{distance_km:.1f} km"
    else:
        return f"{int(distance_km)} km"

def get_distance_emoji(distance_km):
    """Retourne emoji selon distance"""
    if distance_km is None:
        return "📍"
    elif distance_km < 2:
        return "🟢"  # Très proche
    elif distance_km < 5:
        return "🟡"  # Proche
    elif distance_km < 10:
        return "🟠"  # Moyen
    else:
        return "🔴"  # Loin


# =============================================================================
# DATE PARSING — Parsing dates de publication pour tous scrapers
# =============================================================================
from datetime import datetime, timedelta
import re

def ensure_published_at(published_at=None):
    """
    Garantir que published_at JAMAIS None.
    Fallback central pour tous les scrapers.
    """
    if published_at is None:
        return datetime.now()
    if not isinstance(published_at, datetime):
        return datetime.now()
    now = datetime.now()
    if published_at > now:
        return now  # Correction futur
    return published_at


def parse_relative_date(text):
    """Parser texte relatif 'il y a X jours' → datetime"""
    if not text:
        return None
    text_lower = text.lower()

    if 'récemment' in text_lower or 'aujourd' in text_lower or 'now' in text_lower:
        return datetime.now()

    match = re.search(r'(\d+)\s*(?:heure|jour|semaine|mois|h|d|w|m)s?', text_lower)
    if match:
        number = int(match.group(1))
        unit = match.group(0).split()[-1].lower()

        if any(x in unit for x in ['heure', 'h']):
            return datetime.now() - timedelta(hours=number)
        elif any(x in unit for x in ['jour', 'd']):
            return datetime.now() - timedelta(days=number)
        elif any(x in unit for x in ['semaine', 'w']):
            return datetime.now() - timedelta(weeks=number)
        elif any(x in unit for x in ['mois', 'm']):
            return datetime.now() - timedelta(days=number*30)
    return None


def parse_iso_date(date_str):
    """Parser ISO 8601 (ex: '2026-02-26T09:45:00Z')"""
    if not date_str:
        return None
    try:
        clean = date_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean)
    except (ValueError, TypeError, AttributeError):
        return None


def parse_absolute_date(date_str, format_str="%d/%m/%Y"):
    """Parser date absolue (ex: '26/02/2026')"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), format_str)
    except (ValueError, TypeError):
        return None


# =============================================================================
# RETRY MECHANISM — Retry with exponential backoff for HTTP requests
# =============================================================================
import time

def retry_with_backoff(func, max_attempts=3, base_delay=1, backoff_multiplier=2, logger_obj=None):
    """
    Retry a function with exponential backoff on failure.
    """
    delay = base_delay

    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            error_type = type(e).__name__

            if logger_obj:
                logger_obj.debug(f"Attempt {attempt}/{max_attempts} failed ({error_type})")

            if attempt < max_attempts:
                if logger_obj:
                    logger_obj.debug(f"Retrying in {delay}s...")
                time.sleep(delay)
                delay *= backoff_multiplier
            else:
                if logger_obj:
                    logger_obj.error(f"All {max_attempts} attempts failed ({error_type})")
                raise


def validate_listing_data(listing):
    """
    Validate that a listing dict has required fields.
    """
    if not isinstance(listing, dict):
        return False

    required_fields = ['listing_id', 'site', 'title', 'price', 'url']
    return all(field in listing and listing[field] for field in required_fields)


def extract_energy_class(text):
    """
    Extract energy class from text (A, B, C, D, E, F, G).
    """
    if not text:
        return None
    import re
    match = re.search(r'\b([A-G])\b', str(text).upper())
    if match:
        return match.group(1)
    return None


def extract_available_from(text):
    """
    Extract available from date from text.
    Examples: "Disponible immédiatement", "Disponible à partir du 01/03/2026"

    Returns:
        str: Date string or "Immédiatement" or None
    """
    if not text:
        return None
    text_lower = text.lower()

    # Immediately available
    if 'immédiat' in text_lower or 'immediate' in text_lower or 'now' in text_lower:
        return "Immédiatement"

    # Date pattern: "01/03/2026" or "1 mars 2026"
    import re
    date_match = re.search(r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})', text)
    if date_match:
        return date_match.group(1)

    # Month pattern: "mars 2026"
    month_match = re.search(r'(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*\d{4}', text_lower)
    if month_match:
        return month_match.group(0).title()

    return None
