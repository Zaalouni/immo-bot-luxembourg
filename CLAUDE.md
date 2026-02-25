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
| Scraper | Site | Methode | Pages | Statut |
|---------|------|---------|-------|--------|
| athome_scraper_json.py | Athome.lu | JSON __INITIAL_STATE__, URLs filtrees | 12 pages | Pagination v2.6 |
| immotop_scraper_real.py | Immotop.lu | HTML regex | 5 pages | Pagination v2.6 |
| luxhome_scraper.py | Luxhome.lu | JSON/Regex + GPS | 1 page (tout) | Stable |
| vivi_scraper_selenium.py | VIVI.lu | Selenium | 3 pages | Pagination v2.6 |
| nextimmo_scraper.py | Nextimmo.lu | API JSON + fallback HTML | 10 pages | Pagination v2.6 |
| newimmo_scraper_real.py | Newimmo.lu | Selenium + page_source regex /fr/louer/ | 3 pages | Pagination v2.6 |
| unicorn_scraper_real.py | Unicorn.lu | Selenium + data-id card extraction | 2 pages | Pagination v2.6 |

## Scrapers desactives (2/9) — Cloudflare/CAPTCHA
| Scraper | Site | Raison |
|---------|------|--------|
| wortimmo_scraper.py | Wortimmo.lu | Cloudflare bloque les donnees listing (prix = dropdown filtres) |
| immoweb_scraper.py | Immoweb.be | CAPTCHA bloque tout (page 1592 chars) |

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

---

## Scripts autorisés — Diagnostic & Execution

Tu peux me demander d'exécuter ces types de scripts pour:
- **Scripts diagnostic** — Valider état du bot (scrapers, DB, Telegram)
- **Scripts analyse logs** — Examiner performances, erreurs, patterns
- **Commandes git/npm/pip** — Dépendances, versioning, commits

## Workflow Immo-Bot Avec Claude Code

### 1️⃣ Session Start (A FAIRE À CHAQUE FOIS)
**Lis automatiquement tout contexte disponible:**
- Ce fichier (CLAUDE.md)
- analyse.md, architecture.md, planning.md
- Utilise ces infos pour comprendre état + historique

### 2️⃣ Proposer → Exécuter → Analyser
1. **Propose** un script diagnostic (lisible, expliqué)
2. **Toi**: Tu l'exécutes, colle l'output
3. **Moi**: J'analyse output → propse corrections/actions

### 3️⃣ Règles Exécution
✅ **AUTO-APPROVE**: git status, git log, tests scrapers, diagnostics
❌ **DEMANDE CONFIRMATION**: git push, modifications code, DB cleanup
❌ **JAMAIS SANS DEMANDER**: rm -rf, git reset --hard, destructive ops

### 4️⃣ Fichiers Contexte Auto
Au démarrage, j'interroge automatiquement:
```
/home/user/immo-bot-luxembourg/
├── CLAUDE.md              ← Ce fichier
├── README.md              ← État générale
├── analyse.md             ← Historique + problèmes
├── architecture.md        ← Flux technique complet
├── planning.md            ← Toutes actions (statut/date/version)
└── docs/*.md              ← Si existe
```

**Impact:** Je propose actions mieux ciblées, exploite historique de corrections, évite regressions

### 5️⃣ Communication Recommandée
- **Vous démarrez session**: "Bonjour, lis contexte et résume état"
- **Vous demandez action**: "Corrige le scraper Athome" (je lis analyse.md + architecture.md en background)
- **Vous partagez logs**: "Voici output du diagnostic" (je relis CLAUDE.md + analyse.md pour interpréter)

---

## Scripts Diagnostic Recommandés

### Dashboard Health Check
```bash
# Valider fichiers + structure
ls -lah dashboards/index.html dashboards/data/
file dashboards/index.html | head -20
wc -l dashboards/data/listings.js

# Tester génération
python dashboard_generator.py

# Vérifier erreurs HTML
grep -i "error\|undefined\|null" dashboards/index.html | head -5
```

### Bot Status
```bash
# Scrapers
python test_scrapers.py 2>&1 | tail -30

# Database
sqlite3 listings.db "SELECT COUNT(*) as total, COUNT(DISTINCT site) as sites FROM listings;"

# Logs (si existe)
tail -50 *.log
```

### Git Status
```bash
git status
git log --oneline -10
git diff HEAD~1
```

### Performance Baseline (Async ready)
```bash
# Timing scraping actuel
time python -c "from main import ImmoBot; bot = ImmoBot(); bot.check_new_listings()"
```

---

## Processus Correction & Optimisation

### Avant chaque correction majeure:
1. Lancer diagnostic (voir scripts ci-dessus)
2. Noter baseline (temps, erreurs, counts)
3. Appliquer correction
4. Re-lancer diagnostic
5. Comparer avant/après
6. Documenter dans analyse.md

### Après correction/optimisation:
Toujours actualiser:
- **analyse.md** — Ajouter entrée v[X.Y] avec ce qui a changé
- **CLAUDE.md** — Si change état/version/architecture
- **Commit message** — Inclure metrics (ex: "+309 listings", "2-3min → 30sec async")

### Exemple commit après correction dashboard:
```
dashboard: fix html syntax + add chart.js

- Remove legacy dashboard.py + templates/
- Fix template accolades/Jinja2 formatting
- Add Chart.js initialization (doughnut + bar)
- Add Timeline interactive slider
- All 132 listings now render without errors

Before: 8/8 tabs, 5/8 incomplete
After:  8/8 tabs, 3/8 incomplete (Heatmap, Anomalies)

Metrics:
- Generation time: <5 sec
- HTML size: 2.3 MB
- GPS coverage: 94.7%

Tested: python dashboard_generator.py → no errors
```
