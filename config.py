# config.py - Version améliorée
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
    EXCLUDED_WORDS = os.getenv('EXCLUDED_WORDS', 'parking,garage,cave').split(',')
    CITIES = [city.strip() for city in os.getenv('CITIES', 'Luxembourg').split(',')]
    PREFERRED_CITIES = CITIES
except ValueError as e:
    print(f"❌ ERREUR configuration: {e}")
    sys.exit(1)

# ===== CONFIGURATION DISTANCE GPS =====
try:
    REFERENCE_LAT = float(os.getenv('REFERENCE_LAT', '49.6000'))
    REFERENCE_LNG = float(os.getenv('REFERENCE_LNG', '6.1342'))
    REFERENCE_NAME = os.getenv('REFERENCE_NAME', 'Luxembourg Gare')
    MAX_DISTANCE = float(os.getenv('MAX_DISTANCE', '15'))
except ValueError:
    print("⚠️ Erreur GPS, valeurs par défaut utilisées")
    REFERENCE_LAT = 49.6000
    REFERENCE_LNG = 6.1342
    REFERENCE_NAME = "Luxembourg Gare"
    MAX_DISTANCE = 15.0

# ===== CONFIG TECHNIQUE =====
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '600'))  # 10 minutes
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# ===== USER AGENT =====
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

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
