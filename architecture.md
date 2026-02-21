# Architecture — Immo-Bot Luxembourg (v3.2)

## Flux principal

```
main.py:ImmoBot.check_new_listings()
  → ThreadPoolExecutor(4 workers) : 9 scrapers en parallele
  → enrich_listing_gps() : GPS depuis LUXEMBOURG_CITIES si absent
  → _deduplicate() : dedup cross-sites (prix+ville+surface ±15m2)
  → _matches_criteria() : filtre prix/rooms/surface/distance/mots exclus
  → db.listing_exists() + similar_listing_exists() : dedup DB
  → db.add_listing() → notifier.send_listing() [si --no-notify : skip]
```

## Fichiers principaux

| Fichier | Role | Notes cles |
|---------|------|------------|
| main.py | Orchestrateur ImmoBot | --no-notify, --once, scraper_failures{} alerte 3 echecs |
| config.py | .env → variables globales | MIN/MAX_PRICE/ROOMS/SURFACE, EXCLUDED_WORDS, GPS ref, TELEGRAM |
| database.py | SQLite listings.db | migration auto image_url + available_from, cleanup >30j |
| notifier.py | Telegram HTML | send_listing : photo+Maps+prix/m2+hashtags+📅 Disponible |
| utils.py | GPS + utilitaires | geocode_city (toujours tuple), haversine, extract_available_from |
| filters.py | Filtrage centralise | matches_criteria() importe par scrapers |
| dashboard_generator.py | HTML statique | genere dashboards/index.html + map.html |

## utils.py — Fonctions cles

| Fonction | Retour | Notes |
|----------|--------|-------|
| `geocode_city(name)` | `(lat, lng)` ou `(None, None)` | Jamais None seul — ~130 villes LU |
| `haversine_distance(lat1,lng1,lat2,lng2)` | float km | — |
| `enrich_listing_gps(listing)` | modifie dict | check `if lat is not None` |
| `extract_available_from(text)` | str ou None | detecte DD/MM/YYYY, noms mois, "immediatement" |
| `format_distance(km)` | str | "moins de 1 km", "3.5 km" |
| `get_distance_emoji(km)` | str | vert<2km, jaune<5km, orange<10km, rouge>10km |

## Contrat scraper

```python
{
    'listing_id': str,       # prefixe site ex: 'athome_12345'
    'site': str,             # 'Athome.lu'
    'title': str,            # max 80-200 chars
    'city': str,
    'price': int,            # euros/mois
    'rooms': int,            # 0 = inconnu
    'surface': int,          # m2, 0 = inconnu
    'url': str,
    'image_url': str|None,
    'latitude': float|None,
    'longitude': float|None,
    'distance_km': float|None,
    'available_from': str|None,  # ex: '01/03/2026', 'immediatement'
    'time_ago': str,         # 'Recemment' par defaut
    'full_text': str,        # texte complet pour filtrage mots exclus
}
```

## Scrapers actifs (9/11)

| Fichier | Site | Methode | Particularites |
|---------|------|---------|----------------|
| athome_scraper_json.py | Athome.lu | JSON __INITIAL_STATE__ | 12 pages, URLs filtrees, _safe_str() |
| immotop_scraper_real.py | Immotop.lu | HTML regex | 5 pages, data-src images |
| luxhome_scraper.py | Luxhome.lu | JSON/Regex | 1 page tout |
| vivi_scraper_selenium.py | VIVI.lu | Selenium Firefox | 3 pages, images background-image CSS |
| nextimmo_scraper.py | Nextimmo.lu | API JSON | 10 pages, seen_ids dedup |
| newimmo_scraper_real.py | Newimmo.lu | Selenium | 3 pages, regex prix specifique |
| unicorn_scraper_real.py | Unicorn.lu | Selenium + page_source | 2 pages, regex prix specifique |
| remax_scraper.py | Remax.lu | Selenium React | 5 pages, images ancetres DOM |
| sigelux_scraper.py | Sigelux.lu | HTTP + BS4 | 5 pages |

## Scrapers desactives (2/11)

| Fichier | Site | Raison |
|---------|------|--------|
| wortimmo_scraper.py | Wortimmo.lu | Cloudflare |
| immoweb_scraper.py | Immoweb.be | CAPTCHA |

## Base de donnees — Schema

```sql
CREATE TABLE listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id TEXT UNIQUE NOT NULL,   -- ex: 'athome_12345'
    site TEXT NOT NULL,
    title TEXT, city TEXT, price INTEGER, rooms INTEGER, surface INTEGER,
    url TEXT UNIQUE NOT NULL,
    latitude REAL, longitude REAL, distance_km REAL,
    image_url TEXT,                    -- migration auto v2.8
    available_from TEXT,               -- migration auto v3.2
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notified BOOLEAN DEFAULT 0
);
CREATE INDEX idx_listing_id ON listings(listing_id);
CREATE INDEX idx_created_at ON listings(created_at);
CREATE INDEX idx_distance ON listings(distance_km);
```

## Dependances

```
requests, beautifulsoup4, selenium, python-dotenv, lxml, webdriver-manager
```

## Regles importantes

- `geocode_city()` retourne TOUJOURS un tuple `(lat, lng)` ou `(None, None)`, jamais `None` seul
- Prix regex scrapers Selenium : `(?<!\d)(\d{1,2}[\s\u202f\xa0]\d{3}|\d{3,5})(?!\d)\s*€` (evite greedy ID capture)
- Migration DB auto dans `init_db()` : ALTER TABLE si colonne absente
- `--no-notify` dans main.py : skip tous les appels notifier (send_listing, startup, shutdown, error)
- Git remote : origin → https://github.com/Zaalouni/immo-bot-luxembourg.git (branche main)
