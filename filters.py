# =============================================================================
# filters.py — Filtrage centralise des annonces immobilieres
# =============================================================================
# Remplace les _matches_criteria() dupliques dans chaque scraper.
# Importe les criteres depuis config.py (MIN_PRICE, MAX_PRICE, etc.)
# Utilise par : tous les scrapers + main.py
#
# matches_criteria(listing) -> bool
#   Verifie prix, chambres, surface, mots exclus, distance GPS
# =============================================================================
import logging

logger = logging.getLogger(__name__)


def matches_criteria(listing):
    """
    Filtre une annonce selon les criteres definis dans config.py.

    Args:
        listing (dict): annonce avec cles price, rooms, surface, title,
                        full_text, distance_km

    Returns:
        bool: True si l'annonce passe tous les criteres
    """
    try:
        from config import MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS, MAX_DISTANCE

        price = listing.get('price', 0)
        if not isinstance(price, (int, float)) or price <= 0:
            return False
        if price < MIN_PRICE or price > MAX_PRICE:
            return False

        rooms = listing.get('rooms', 0) or 0
        if isinstance(rooms, (int, float)) and rooms > 0:
            if rooms < MIN_ROOMS or rooms > MAX_ROOMS:
                return False

        surface = listing.get('surface', 0) or 0
        if isinstance(surface, (int, float)) and surface > 0:
            if surface < MIN_SURFACE:
                return False

        check_text = (str(listing.get('title', '')) + ' ' + str(listing.get('full_text', ''))).lower()
        if any(w.strip().lower() in check_text for w in EXCLUDED_WORDS if w.strip()):
            return False

        distance_km = listing.get('distance_km')
        if distance_km is not None:
            try:
                if float(distance_km) > MAX_DISTANCE:
                    return False
            except (ValueError, TypeError):
                pass

        return True

    except Exception as e:
        logger.debug(f"Erreur filtre: {e}")
        return False
