# Planning — Immo-Bot Luxembourg

> Ce fichier suit les actions planifiees, en cours et terminees.
> Chaque action a un identifiant, une version cible, une date et un statut.
> Ce fichier est mis a jour a chaque session de travail.

## Legende statuts

- `DONE` — Termine et commite
- `IN_PROGRESS` — En cours de developpement
- `TODO` — Planifie, pas encore commence
- `BLOCKED` — Bloque par une dependance ou un probleme
- `CANCELLED` — Annule

## Versions livrees

### v1.0 — Initial (2025-01-17)

| ID | Action | Statut | Date |
|----|--------|--------|------|
| 1.0.1 | Creer structure projet (main, config, db, notifier) | DONE | 2025-01-17 |
| 1.0.2 | Scraper Athome.lu (JSON __INITIAL_STATE__) | DONE | 2025-01-17 |
| 1.0.3 | Scraper Immotop.lu (HTML regex) | DONE | 2025-01-17 |
| 1.0.4 | Scraper Luxhome.lu (JSON/Regex) | DONE | 2025-01-17 |
| 1.0.5 | Scraper VIVI.lu (Selenium) | DONE | 2025-01-17 |
| 1.0.6 | Scraper Unicorn.lu (Selenium) | DONE | 2025-01-17 |
| 1.0.7 | Notifications Telegram texte HTML | DONE | 2025-01-17 |
| 1.0.8 | Base SQLite + dedup par listing_id | DONE | 2025-01-17 |
| 1.0.9 | Configuration .env (prix, rooms) | DONE | 2025-01-17 |

### v1.1-v1.5 — Corrections et nouveaux sites (2025-01-17 → 2025-01-18)

| ID | Action | Statut | Date |
|----|--------|--------|------|
| 1.1.1 | Ajouter scrapers Newimmo, Wortimmo, Immoweb, Nextimmo | DONE | 2025-01-17 |
| 1.2.1 | Fix filtrage trop strict (rooms=0 rejetait tout) | DONE | 2025-01-17 |
| 1.3.1 | Fix 3 bugs identifies dans les logs | DONE | 2025-01-17 |
| 1.4.1 | Fix Athome JSON parsing (champs dict au lieu de str) | DONE | 2025-01-18 |
| 1.4.2 | Fix Wortimmo Selenium + Immotop filtrage | DONE | 2025-01-18 |
| 1.5.1 | Fix Unicorn URL changee | DONE | 2025-02-12 |
| 1.5.2 | Fix Immoweb timeout Selenium | DONE | 2025-02-12 |
| 1.5.3 | Fix Athome dict crash (immotype, price, city, description) | DONE | 2025-02-12 |

### v2.0 — Refonte majeure (2025-02-12)

| ID | Action | Statut | Date |
|----|--------|--------|------|
| 2.0.1 | Filtrage complet : MIN_PRICE, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS, MAX_DISTANCE | DONE | 2025-02-12 |
| 2.0.2 | Dedup cross-sites en memoire (prix+ville+surface) | DONE | 2025-02-12 |
| 2.0.3 | Dedup cross-sites en DB (similar_listing_exists) | DONE | 2025-02-12 |
| 2.0.4 | Nettoyage auto DB (annonces > 30 jours) | DONE | 2025-02-12 |
| 2.0.5 | Compteur echecs + alerte Telegram apres 3 fails | DONE | 2025-02-12 |
| 2.0.6 | Photos dans notifications Telegram (send_photo) | DONE | 2025-02-12 |
| 2.0.7 | Lien Google Maps si GPS disponible | DONE | 2025-02-12 |
| 2.0.8 | Prix/m2 dans notifications | DONE | 2025-02-12 |
| 2.0.9 | Hashtags dynamiques (#PrixBas, #Proche, #GrandeSurface) | DONE | 2025-02-12 |
| 2.0.10 | Multi-type tous scrapers (appartements + maisons) | DONE | 2025-02-12 |
| 2.0.11 | Extraction images tous scrapers | DONE | 2025-02-12 |
| 2.0.12 | Reecriture Unicorn (page_source regex) | DONE | 2025-02-12 |
| 2.0.13 | Reecriture Wortimmo (3 methodes cascade) | DONE | 2025-02-12 |
| 2.0.14 | Selenium fallback Chrome si Firefox absent | DONE | 2025-02-12 |
| 2.0.15 | Test scrapers affiche filtres actifs | DONE | 2025-02-12 |

### v2.1 — Documentation (2025-02-15)

| ID | Action | Statut | Date |
|----|--------|--------|------|
| 2.1.1 | Creer README.md | DONE | 2025-02-15 |
| 2.1.2 | Creer architecture.md | DONE | 2025-02-15 |
| 2.1.3 | Creer analyse.md | DONE | 2025-02-15 |
| 2.1.4 | Creer planning.md | DONE | 2025-02-15 |
| 2.1.5 | Ajouter commentaires detailles dans tous les fichiers sources | DONE | 2025-02-15 |

## Actions planifiees (futures)

### v2.2 — Nettoyage et robustesse (TODO)

| ID | Action | Statut | Priorite | Notes |
|----|--------|--------|----------|-------|
| 2.2.1 | Supprimer fichiers backup racine (*.backup, *.123, *.1801, etc.) | TODO | Haute | Encombrent le repo |
| 2.2.2 | Supprimer scrapers legacy non utilises dans scrapers/ | TODO | Haute | ~8 fichiers inutiles |
| 2.2.3 | Supprimer scrapers.sauv/ (dossier backup complet) | TODO | Haute | Doublon de backup/ |
| 2.2.4 | Verifier historique git pour .env commite accidentellement | TODO | Critique | Tokens Telegram exposes |
| 2.2.5 | Ajouter rotation des logs (RotatingFileHandler) | TODO | Moyenne | immo_bot.log grossit indefiniment |
| 2.2.6 | Supprimer feedparser et schedule de requirements.txt | TODO | Basse | Non utilises |

### v3.0 — Performance et fiabilite (TODO)

| ID | Action | Statut | Priorite | Notes |
|----|--------|--------|----------|-------|
| 3.0.1 | Passer les scrapers HTTP en async (aiohttp) | TODO | Haute | Reduire temps cycle de ~3min a ~30s |
| 3.0.2 | Ajouter retry automatique pour scrapers en echec | TODO | Moyenne | 1 retry apres 30s si echec |
| 3.0.3 | Creer une classe de base commune pour tous les scrapers | TODO | Moyenne | Interface uniforme scrape() + matches_criteria() |
| 3.0.4 | Deplacer _matches_criteria() hors des scrapers (centraliser dans main.py uniquement) | TODO | Moyenne | Le filtrage est duplique dans chaque scraper + main.py |
| 3.0.5 | Ajouter tests unitaires (pytest) | TODO | Haute | Aucun test automatise actuellement |
| 3.0.6 | Ajouter healthcheck endpoint ou commande /status Telegram | TODO | Basse | Pour monitoring distant |
| 3.0.7 | Dashboard web (reactiver dashboard.py ou web_dashboard.py) | TODO | Basse | Fichiers presents mais non integres |

### v3.1 — Nouveaux scrapers (TODO)

| ID | Action | Statut | Priorite | Notes |
|----|--------|--------|----------|-------|
| 3.1.1 | Evaluer ajout Century21.lu | TODO | Basse | Scraper legacy dans backup/ |
| 3.1.2 | Evaluer ajout ImmoScout24.lu | TODO | Basse | Site present au Luxembourg |
| 3.1.3 | Evaluer ajout Engelvoelkers.com/lu | TODO | Basse | Segment premium |

## Journal des sessions

| Date | Session | Actions realisees |
|------|---------|-------------------|
| 2025-01-17 | Session 1 | Creation projet, 6 scrapers, bot fonctionnel (v1.0) |
| 2025-01-17-18 | Session 2 | +3 scrapers, corrections bugs, filtrage (v1.1-v1.5) |
| 2025-02-12 | Session 3 | Refonte v2.0 : dedup, photos, GPS, filtrage complet |
| 2025-02-15 | Session 4 | Analyse structure, push GitHub, documentation |
