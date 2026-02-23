# Immo-Bot Luxembourg — Contexte rapide pour IA

## Quoi
Bot Python qui scrape 7 sites immobiliers luxembourgeois, filtre les annonces de location, deduplique cross-sites, stocke en SQLite et notifie via Telegram (photos + Google Maps).

## Fichiers cles
| Fichier | Role |
|---------|------|
| main.py | Orchestrateur : ImmoBot.check_new_listings() → scrape → dedup → filtre → DB → Telegram |
| config.py | Charge .env : prix, rooms, surface, distance GPS, mots exclus, tokens Telegram |
| database.py | SQLite listings.db : insert, dedup (listing_exists + similar_listing_exists), cleanup >30j |
| notifier.py | Telegram HTML : send_listing (photo+Maps+prix/m2+hashtags), send_photo, retry+rate limit |
| utils.py | GPS : haversine_distance, geocode_city (~130 villes), enrich_listing_gps |
| scrapers/ | 7 scrapers actifs + 2 desactives + 1 template Selenium |

## Scrapers actifs (7/9)
| Scraper | Pages | Statut |
|---------|-------|--------|
| scraper_1.py | 12 pages | Pagination v2.6 |
| scraper_2.py | 5 pages | Pagination v2.6 |
| scraper_3.py | 1 page (tout) | Stable |
| scraper_4.py | 3 pages | Pagination v2.6 |
| scraper_5.py | 10 pages | Pagination v2.6 |
| scraper_6.py | 3 pages | Pagination v2.6 |
| scraper_7.py | 2 pages | Pagination v2.6 |

## Scrapers desactives (2/9) — Maintenance
| Scraper | Raison |
|---------|--------|
| scraper_8.py | Architecture legacy, complexite d'integration |
| scraper_9.py | Architecture legacy, complexite d'integration |

## Contrat scraper
Chaque scraper expose `.scrape()` → `list[dict]` avec cles : listing_id, site, title, city, price, rooms, surface, url, image_url, latitude, longitude, distance_km, time_ago, full_text

## Etat actuel
- **Version** : v2.6 (2026-02-17)
- **Statut** : fonctionnel, en production, 7/9 scrapers actifs
- **Derniere action** : pagination tous scrapers (v2.6), URLs filtrees Athome, +309 annonces captees

## Localisation (v2.3+)
- utils.py contient LUXEMBOURG_CITIES (~130 villes → lat/lng)
- main.py appelle enrich_listing_gps() avant dedup/filtrage
- Si geocodage echoue → filtre par ACCEPTED_CITIES (.env, fallback)

## Prochaines actions (voir planning.md)
- v3.0 : async scrapers HTTP, retry auto, centraliser filtrage, tests pytest
- v3.1 : nouveaux scrapers pour remplacer Wortimmo/Immoweb

## Problemes connus
- Wortimmo + Immoweb bloques par Cloudflare/CAPTCHA → remplacer par nouveaux sites
- Unicorn : CAPTCHA intermittent, peu d'annonces, filtrage surface strict
- Filtrage duplique (chaque scraper + main.py) → a centraliser v3.0
- Pas de tests automatises (uniquement test_scrapers.py manuel)

## Docs detaillees
- architecture.md : flux complet, schema DB, roles fichiers
- analyse.md : historique corrections, problemes, metriques
- planning.md : toutes les actions avec statut/date/version
