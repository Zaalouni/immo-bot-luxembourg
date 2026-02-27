# Architecture — Immo-Bot Luxembourg

> Ce fichier decrit l'architecture complete du projet, le role de chaque fichier,
> le flux de donnees et les interactions entre modules. Il est concu pour etre
> lisible par tout outil IA (Claude, GPT, Copilot) afin de comprendre rapidement
> le projet sans lire tout le code source.

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                              │
│                   Classe ImmoBot                            │
│                                                             │
│  run_continuous() / run_once()                              │
│       │                                                     │
│       ▼                                                     │
│  check_new_listings()                                       │
│       │                                                     │
│       ├── Pour chaque scraper (9 sites) :                   │
│       │       scraper.scrape() → liste de dicts             │
│       │       (delai 5s entre chaque)                       │
│       │                                                     │
│       ├── _deduplicate() → supprime doublons cross-sites    │
│       │                                                     │
│       ├── _matches_criteria() → filtre prix/rooms/surface/  │
│       │                         distance/mots exclus        │
│       │                                                     │
│       ├── db.listing_exists() → verifie si deja en base     │
│       ├── db.similar_listing_exists() → dedup DB            │
│       ├── db.add_listing() → insere en base                 │
│       │                                                     │
│       └── notifier.send_listing() → Telegram avec photo     │
│               notifier.send_photo() (si image dispo)        │
│               notifier.send_message() (fallback texte)      │
└─────────────────────────────────────────────────────────────┘
```

## Fichiers principaux — Roles detailles

### main.py — Orchestrateur principal

- **Classe** : `ImmoBot`
- **Role** : Point d'entree, orchestre le cycle scraping → filtrage → dedup → notification
- **Methodes cles** :
  - `check_new_listings()` : execute un cycle complet sur tous les scrapers
  - `_matches_criteria(listing)` : filtre central (prix, rooms, surface, distance, mots exclus)
  - `_deduplicate(listings)` : dedup cross-sites en memoire (prix + ville normalisee + surface ±15m2)
  - `_normalize_city(city)` : normalise noms de villes (accents, suffixes -gare/-centre)
  - `_listing_quality_score(listing)` : score pour choisir le meilleur doublon (GPS=3, surface=2, rooms=2, city=1, image=1)
  - `run_once()` : mode test (1 cycle)
  - `run_continuous()` : mode production (boucle infinie avec CHECK_INTERVAL)
- **Imports dynamiques** : chaque scraper est importe dans un try/except pour tolerence aux pannes
- **Compteur echecs** : `scraper_failures{}` — alerte Telegram apres 3 echecs consecutifs

### config.py — Configuration centralisee

- **Role** : charge toutes les variables depuis `.env` via python-dotenv
- **Variables exposees** :
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_CHAT_IDS` (liste)
  - `MIN_PRICE`, `MAX_PRICE`, `MIN_ROOMS`, `MAX_ROOMS`, `MIN_SURFACE`
  - `EXCLUDED_WORDS` (liste nettoyee), `CITIES`, `PREFERRED_CITIES`
  - `REFERENCE_LAT`, `REFERENCE_LNG`, `REFERENCE_NAME`, `MAX_DISTANCE`
  - `CHECK_INTERVAL`, `DEBUG`, `USER_AGENT`
- **Validation** : exit(1) si token/chat_id manquants ou erreur conversion

### database.py — Persistence SQLite

- **Classe** : `Database` (instance globale `db`)
- **Base** : `listings.db` (SQLite3)
- **Table** : `listings` avec colonnes : id, listing_id (UNIQUE), site, title, city, price, rooms, surface, url (UNIQUE), latitude, longitude, distance_km, created_at, notified
- **Index** : listing_id, created_at, distance_km
- **Methodes cles** :
  - `listing_exists(listing_id)` : verifie doublon par ID unique
  - `similar_listing_exists(price, city, surface)` : dedup cross-site en DB (meme prix + ville LIKE + surface ±15m2)
  - `add_listing(listing_data)` : insere, retourne False si IntegrityError
  - `mark_as_notified(listing_id)` : flag notified=1
  - `get_stats()` : total, new, notified, by_site, avg_distance
  - `get_closest_listings(limit)` : top N par distance ASC
  - `cleanup_old_listings(days)` : DELETE + VACUUM des annonces > N jours

### notifier.py — Notifications Telegram

- **Classe** : `TelegramNotifier` (instance globale `notifier`)
- **Role** : envoie messages HTML formates a 1+ chats Telegram
- **Methodes cles** :
  - `send_message(text, parse_mode, silent, retry_count)` : envoi texte avec retry + gestion rate limit
  - `send_photo(photo_url, caption)` : envoi image avec legende (max 1024 chars)
  - `send_listing(listing)` : formate une annonce complete :
    - Photo si disponible (fallback texte)
    - Lien Google Maps cliquable si GPS
    - Prix/m2 calcule
    - Hashtags dynamiques (#PrixBas, #Proche, #GrandeSurface, #Ville, #TypeBien)
  - `send_startup_message()`, `send_shutdown_message()`, `send_error_message()`
  - `test_connection()` : verifie bot + chaque chat au demarrage
- **Securite HTML** : `_escape_html()` sur tous les champs utilisateur

### utils.py — Utilitaires GPS

- **Fonctions** :
  - `haversine_distance(lat1, lng1, lat2, lng2)` : distance en km entre 2 points GPS
  - `format_distance(distance_km)` : formatage lisible ("moins de 1 km", "3.5 km", "12 km")
  - `get_distance_emoji(distance_km)` : emoji couleur selon distance (vert < 2km, jaune < 5km, orange < 10km, rouge > 10km)

### test_scrapers.py — Tests manuels

- **Role** : lance chaque scraper individuellement, affiche resultats et filtres actifs
- **Usage** : `python test_scrapers.py`

## Scrapers — Repertoire scrapers/

Tous les scrapers suivent le meme contrat :
- **Methode publique** : `scrape()` → retourne `list[dict]` ou `[]`
- **Dict standard** (listing) :

```python
{
    'listing_id': str,    # ID unique prefixe par site (ex: 'athome_12345')
    'site': str,          # Nom du site source
    'title': str,         # Titre de l'annonce (max 200 chars)
    'city': str,          # Ville
    'price': int,         # Prix mensuel en euros
    'rooms': int,         # Nombre de chambres (0 = inconnu)
    'surface': int,       # Surface en m2 (0 = inconnu)
    'url': str,           # URL complete vers l'annonce
    'image_url': str,     # URL de la photo principale (ou None)
    'latitude': float,    # GPS latitude (ou None)
    'longitude': float,   # GPS longitude (ou None)
    'distance_km': float, # Distance au point de reference (ou None)
    'time_ago': str,      # Anciennete ('Recemment' par defaut)
    'full_text': str,     # Texte complet pour filtrage mots exclus
}
```

### Scrapers actifs

| Fichier | Site | Methode scraping | Particularites |
|---------|------|------------------|----------------|
| `athome_scraper_json.py` | Athome.lu | JSON `__INITIAL_STATE__` | Multi-URL (appart+maison), _safe_str() pour dicts imbriques, fallback regex si JSON casse |
| `immotop_scraper_real.py` | Immotop.lu | HTML regex | Extraction images par data-src, regex prix/chambres/surface |
| `luxhome_scraper.py` | Luxhome.lu | JSON + regex | Calcul distance GPS, extraction thumbnails, types etendus |
| `vivi_scraper_selenium.py` | VIVI.lu | Selenium (Firefox) | Scroll + extraction cartes, images, full_text |
| `newimmo_scraper_real.py` | Newimmo.lu | Selenium (herite SeleniumScraperBase) | Surface decimale (52.00 m2), filtrage titre+texte |
| `unicorn_scraper_real.py` | Unicorn.lu | Selenium + regex page_source | Override scrape(), multi-URL, extraction contexte HTML autour des liens |
| `wortimmo_scraper.py` | Wortimmo.lu | Selenium + 3 methodes cascade | 1) JSON embarque 2) Liens HTML 3) Elements avec prix. Recherche recursive dans JSON |
| `immoweb_scraper.py` | Immoweb.be | Selenium | Luxembourg section du site belge |
| `nextimmo_scraper.py` | Nextimmo.lu | API JSON + fallback HTML | Multi-type (appart+maison), dedup interne seen_ids |

### Fichiers support scrapers

| Fichier | Role |
|---------|------|
| `selenium_template.py` | Classe de base `SeleniumScraperBase` : setup_driver (Firefox+Chrome fallback), parse_price, parse_rooms, parse_surface |
| `selenium_template_fixed.py` | Version alternative (non utilisee) |
| `__init__.py` | Vide — imports directs dans main.py |

### Scrapers non utilises (legacy)

Ces fichiers sont presents dans `scrapers/` mais ne sont pas importes par `main.py` :
- `athome_scraper_simple.py`, `athome_scraper_real.py` — anciennes versions Athome
- `luxhome_scraper_simple.py`, `luxhome_scraper_stealth.py`, `luxhome_scraper_real.py`, `luxhome_scraper_final.py` — anciennes versions Luxhome
- `vivi_scraper_real.py` — ancienne version VIVI

## Flux de donnees detaille

```
1. CONFIGURATION
   .env → config.py → variables globales importees partout

2. SCRAPING (pour chaque site, sequentiel avec 5s de delai)
   scraper.scrape()
   → requete HTTP ou Selenium
   → parsing JSON/HTML/regex
   → _matches_criteria() local (filtrage par scraper)
   → retourne list[dict]

3. DEDUPLICATION MEMOIRE (main.py)
   _deduplicate(all_listings)
   → cle = prix + ville normalisee
   → si meme cle + surface ±15m2 → garde le meilleur (score qualite)

4. FILTRAGE CENTRAL (main.py)
   _matches_criteria(listing)
   → prix dans [MIN_PRICE, MAX_PRICE]
   → rooms dans [MIN_ROOMS, MAX_ROOMS] (si connu)
   → surface >= MIN_SURFACE (si connu)
   → aucun mot exclu dans titre+full_text
   → distance <= MAX_DISTANCE (si GPS dispo)

5. DEDUPLICATION DB
   db.listing_exists(listing_id) → par ID unique
   db.similar_listing_exists(prix, ville, surface) → cross-site

6. PERSISTENCE
   db.add_listing(listing) → INSERT SQLite
   db.mark_as_notified(listing_id) → apres envoi Telegram

7. NOTIFICATION
   notifier.send_listing(listing)
   → si image_url : send_photo() avec caption HTML
   → sinon : send_message() texte HTML
   → inclut : photo, titre, ville, distance+Maps, prix+prix/m2,
     chambres, surface, lien, hashtags
```

## Dependances externes

```
requests        — HTTP pour scrapers + Telegram API
beautifulsoup4  — parsing HTML (utilise dans certains scrapers)
selenium        — scraping sites JS (Firefox/Chrome headless)
python-dotenv   — chargement .env
lxml            — parser HTML rapide
feedparser      — (installe mais non utilise actuellement)
schedule        — (installe mais non utilise actuellement)
webdriver-manager — gestion automatique des drivers Selenium
```

## Base de donnees — Schema

```sql
CREATE TABLE listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id TEXT UNIQUE NOT NULL,   -- ex: 'athome_12345'
    site TEXT NOT NULL,                -- ex: 'Athome.lu'
    title TEXT,
    city TEXT,
    price INTEGER,
    rooms INTEGER,
    surface INTEGER,
    url TEXT UNIQUE NOT NULL,
    latitude REAL,
    longitude REAL,
    distance_km REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notified BOOLEAN DEFAULT 0
);

-- Index
CREATE INDEX idx_listing_id ON listings(listing_id);
CREATE INDEX idx_created_at ON listings(created_at);
CREATE INDEX idx_distance ON listings(distance_km);
```
