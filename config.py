# =============================================================================
# config.py — Configuration centralisee du bot immobilier
# =============================================================================
# Charge toutes les variables depuis le fichier .env via python-dotenv.
# Variables exposees :
#   - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_CHAT_IDS (liste)
#   - MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE
#   - EXCLUDED_WORDS (liste), CITIES, PREFERRED_CITIES
#   - REFERENCE_LAT, REFERENCE_LNG, REFERENCE_NAME, MAX_DISTANCE (GPS)
#   - CHECK_INTERVAL, DEBUG, USER_AGENT
#
# Validation : le script quitte (exit 1) si les tokens Telegram sont absents
# ou si les valeurs numeriques sont invalides.
#
# Usage : importe par tous les autres modules (main, scrapers, notifier, etc.)
# =============================================================================
import os
import sys
from dotenv import load_dotenv

# Charger .env
load_dotenv()

# ===== TÉLÉGRAM =====
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '').strip()

# Validation
if not TELEGRAM_BOT_TOKEN:
    print("❌ ERREUR: TELEGRAM_BOT_TOKEN manquant dans .env")
    sys.exit(1)

if not TELEGRAM_CHAT_ID:
    print("❌ ERREUR: TELEGRAM_CHAT_ID manquant dans .env")
    sys.exit(1)

# Gérer plusieurs Chat IDs (séparés par virgule)
if ',' in TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_IDS = [cid.strip() for cid in TELEGRAM_CHAT_ID.split(',')]
else:
    TELEGRAM_CHAT_IDS = [TELEGRAM_CHAT_ID.strip()]

# ===== CRITÈRES RECHERCHE =====
try:
    MIN_PRICE = int(os.getenv('MIN_PRICE', '1000'))
    MAX_PRICE = int(os.getenv('MAX_PRICE', '2800'))
    MIN_ROOMS = int(os.getenv('MIN_ROOMS', '2'))
    MAX_ROOMS = int(os.getenv('MAX_ROOMS', '3'))
    MIN_SURFACE = int(os.getenv('MIN_SURFACE', '70'))
    _excluded_raw = os.getenv('EXCLUDED_WORDS', 'parking,garage,cave')
    EXCLUDED_WORDS = [w.strip() for w in _excluded_raw.split(',') if w.strip()]
    CITIES = [city.strip() for city in os.getenv('CITIES', 'Luxembourg').split(',') if city.strip()]
    PREFERRED_CITIES = CITIES  # Alias pour compatibilité
except ValueError as e:
    print(f"❌ ERREUR configuration: {e}")
    sys.exit(1)

# ===== CONFIGURATION DISTANCE GPS =====
try:
    REFERENCE_LAT = float(os.getenv('REFERENCE_LAT', '49.6000'))
    REFERENCE_LNG = float(os.getenv('REFERENCE_LNG', '6.1342'))
    REFERENCE_NAME = os.getenv('REFERENCE_NAME', 'Luxembourg Gare')
    MAX_DISTANCE = float(os.getenv('MAX_DISTANCE', '15'))
    # Filtre villes acceptees (fallback si geocodage echoue)
    # Si vide → pas de filtre par ville (seulement distance GPS)
    _accepted_raw = os.getenv('ACCEPTED_CITIES', '')
    ACCEPTED_CITIES = [c.strip().lower() for c in _accepted_raw.split(',') if c.strip()]
except ValueError:
    print("⚠️ Erreur GPS, valeurs par défaut utilisées")
    REFERENCE_LAT = 49.6000
    REFERENCE_LNG = 6.1342
    REFERENCE_NAME = "Luxembourg Gare"
    MAX_DISTANCE = 15.0
    ACCEPTED_CITIES = []

# ===== CONFIG TECHNIQUE =====
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '600'))  # 10 minutes
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# ===== USER AGENT =====
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

# User agents list for random rotation (used by some scrapers)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# ===== VILLES EXCLUES =====
# Villes hors Luxembourg a exclure (Belgique, Allemagne, France)
_excluded_cities_raw = os.getenv('EXCLUDED_CITIES', 'Arlon,Aubange,Perl,Trier,Konz,Saarbrücken,Cattenom,Longwy,Verdun')
EXCLUDED_CITIES = [c.strip().lower() for c in _excluded_cities_raw.split(',') if c.strip()]

# ===== SCRAPER TIMEOUTS (centralisés) =====
SCRAPER_TIMEOUTS = {
    'default': int(os.getenv('SCRAPER_TIMEOUT_DEFAULT', '15')),      # HTTP standard
    'selenium': int(os.getenv('SCRAPER_TIMEOUT_SELENIUM', '30')),    # Selenium load
    'cloudflare': int(os.getenv('SCRAPER_TIMEOUT_CLOUDFLARE', '60')), # Cloudflare wait
}

# ===== SCRAPER SLEEP CONFIG =====
SCRAPER_SLEEP_CONFIG = {
    'between_pages': (1, 2),              # Random entre pages
    'cloudflare_wait': 8,                 # Wait fixe Cloudflare
    'rate_limit': (0.5, 1.5),             # Random rate limiting
}

# ===== RETRY CONFIG =====
RETRY_CONFIG = {
    'max_attempts': int(os.getenv('RETRY_MAX_ATTEMPTS', '3')),
    'base_delay': int(os.getenv('RETRY_BASE_DELAY', '1')),
    'backoff_multiplier': int(os.getenv('RETRY_BACKOFF_MULTIPLIER', '2')),
}

# ===== VÉRIFICATION =====
if __name__ == "__main__":
    print("✅ Configuration chargée")
    print(f"🤖 Bot token: {TELEGRAM_BOT_TOKEN[:15]}...")
    print(f"👥 Chat ID(s): {TELEGRAM_CHAT_ID}")
    print(f"💰 Prix: {MIN_PRICE}-{MAX_PRICE}€")
    print(f"🛏️ Chambres: {MIN_ROOMS}-{MAX_ROOMS}")
    print(f"📐 Surface: ≥{MIN_SURFACE}m²")
    print(f"📍 Villes: {', '.join(CITIES)}")
    print(f"📍 Référence: {REFERENCE_NAME} ({REFERENCE_LAT}, {REFERENCE_LNG})")
    print(f"📏 Distance max: {MAX_DISTANCE} km")
    print(f"⏰ Intervalle: {CHECK_INTERVAL}s")
