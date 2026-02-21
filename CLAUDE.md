# Immo-Bot Luxembourg

## Debut de session — lire dans cet ordre
1. MEMORY.md (deja charge) — version, etat, patterns
2. planning.md — taches en cours
3. architecture.md — si besoin schema DB/flux

## Regles
- dashboard_generator.py = SOURCE de map.html et index.html → ne jamais editer ces HTML directement
- Commits : `git add <fichier>` explicite, jamais run.sh ni fichiers non touches
- Langue : francais partout

## Fichiers cles
| Fichier | Role |
|---------|------|
| main.py | Orchestrateur scrape→dedup→filtre→DB→Telegram |
| dashboard_generator.py | Genere dashboards/ (index.html, map.html, PWA) |
| database.py | SQLite listings.db, dedup, cleanup |
| notifier.py | Telegram photo+Maps+prix/m2 |
| utils.py | GPS haversine, geocode_city 130 villes |
| config.py | .env : prix/rooms/surface/distance/tokens |
| scrapers/ | detail → architecture.md |

## Contrat scraper
`.scrape()` → `list[dict]` : listing_id, site, title, city, price, rooms, surface, url, image_url, latitude, longitude, distance_km, time_ago, full_text
