# Immo-Bot Luxembourg — Contexte rapide pour IA

## Quoi
Bot Python qui scrape 9 sites immobiliers luxembourgeois, filtre les annonces de location, deduplique cross-sites, stocke en SQLite et notifie via Telegram (photos + Google Maps).

## Fichiers cles
| Fichier | Role |
|---------|------|
| main.py | Orchestrateur : ImmoBot.check_new_listings() → scrape → dedup → filtre → DB → Telegram |
| config.py | Charge .env : prix, rooms, surface, distance GPS, mots exclus, tokens Telegram |
| database.py | SQLite listings.db : insert, dedup (listing_exists + similar_listing_exists), cleanup >30j |
| notifier.py | Telegram HTML : send_listing (photo+Maps+prix/m2+hashtags), send_photo, retry+rate limit |
| utils.py | GPS : haversine_distance, format_distance, get_distance_emoji |
| scrapers/ | 9 scrapers actifs (voir ci-dessous) |

## Scrapers actifs
| Scraper | Site | Methode |
|---------|------|---------|
| athome_scraper_json.py | Athome.lu | JSON __INITIAL_STATE__, multi-URL appart+maison |
| immotop_scraper_real.py | Immotop.lu | HTML regex |
| luxhome_scraper.py | Luxhome.lu | JSON/Regex + GPS |
| vivi_scraper_selenium.py | VIVI.lu | Selenium |
| newimmo_scraper_real.py | Newimmo.lu | Selenium (herite selenium_template) |
| unicorn_scraper_real.py | Unicorn.lu | Selenium + regex page_source (override scrape) |
| wortimmo_scraper.py | Wortimmo.lu | Selenium, 3 methodes cascade (JSON→liens→prix) |
| immoweb_scraper.py | Immoweb.be | Selenium |
| nextimmo_scraper.py | Nextimmo.lu | API JSON + fallback HTML |

## Contrat scraper
Chaque scraper expose `.scrape()` → `list[dict]` avec cles : listing_id, site, title, city, price, rooms, surface, url, image_url, latitude, longitude, distance_km, time_ago, full_text

## Etat actuel
- **Version** : v2.1 (2025-02-15)
- **Statut** : fonctionnel, en production
- **Derniere action** : documentation (README, architecture, analyse, planning) + commentaires sources

## Prochaines actions (voir planning.md)
- v2.2 : nettoyage fichiers legacy (backups, scrapers inutilises, scrapers.sauv/)
- v3.0 : async scrapers HTTP, retry auto, tests pytest, centraliser filtrage

## Problemes connus
- Scrapers Selenium fragiles (sites changent leur HTML regulierement)
- Filtrage duplique (chaque scraper + main.py) → a centraliser
- ~10 fichiers scrapers legacy inutilises dans scrapers/
- Pas de tests automatises

## Docs detaillees
- architecture.md : flux complet, schema DB, roles fichiers
- analyse.md : historique corrections, problemes, metriques
- planning.md : toutes les actions avec statut/date/version
