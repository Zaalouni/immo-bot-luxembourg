# Immo-Bot Luxembourg

## Debut session — lire dans cet ordre
1. MEMORY.md (deja charge) — etat, patterns, conventions
2. planning.md — taches + scrapers actifs
3. architecture.md — schema DB/flux si besoin

## Objectif
Trouver de bonnes annonces avec donnees correctes.
PAS de nouveaux scrapers. Priorite : stabilite + qualite + dashboard.

## Regles
- `dashboard_generator.py` = SOURCE de `map.html`/`index.html` → jamais editer le HTML directement
- `git add <fichier>` explicite — jamais run.sh ni fichiers non touches
- Langue : francais partout (logs, commentaires, notifications)
- Bot tourne sur serveur Linux — ne jamais lancer localement
- Test sans Telegram : `python main.py --once --no-notify`

## Fichiers cles
| Fichier | Role |
|---------|------|
| main.py | Orchestrateur scrape→dedup→filtre→DB→Telegram. Args: --once, --no-notify |
| dashboard_generator.py | Genere dashboards/ (index.html, map.html, data/, PWA) |
| database.py | SQLite listings.db — migration auto colonnes, dedup, cleanup |
| notifier.py | Telegram HTML : photo+Maps+prix/m2+available_from |
| utils.py | geocode_city(city)→(lat,lng)|(None,None), haversine, extract_available_from |
| config.py | .env : prix/rooms/surface/distance/tokens Telegram |
| filters.py | matches_criteria() centralise |
| scrapers/ | 9 actifs — voir planning.md |

## Contrat scraper
`.scrape()` → `list[dict]` avec cles :
`listing_id, site, title, city, price, rooms, surface, url, image_url, latitude, longitude, distance_km, available_from, time_ago, full_text`
