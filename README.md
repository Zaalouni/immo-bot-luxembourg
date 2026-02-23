# Immo-Bot Luxembourg

## Description

Bot de surveillance immobiliere automatise pour le marche locatif au Luxembourg.
Il scrape 9 sites immobiliers, filtre les annonces selon des criteres configurables,
deduplique les resultats cross-sites, stocke en base SQLite et envoie des notifications
Telegram en temps reel avec photos, liens Google Maps et hashtags.

## Fonctionnalites principales

- **9 scrapers actifs** : Multiples sources de données immobilières (plateformes de location luxembourgeoises et régionales)
- **Filtrage complet** : prix min/max, chambres min/max, surface min, distance GPS max, mots exclus
- **Deduplication** : cross-sites en memoire (meme cycle) + en base (cycles precedents)
- **Notifications Telegram** : photos, lien Google Maps, prix/m2, hashtags dynamiques
- **Multi-destinataires** : supporte plusieurs Chat IDs Telegram
- **Nettoyage automatique** : suppression des annonces > 30 jours
- **Alerte pannes** : notification apres 3 echecs consecutifs d'un scraper
- **2 modes** : continu (production) ou test unique (`--once`)

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.x |
| Base de donnees | SQLite3 (listings.db) |
| Notifications | Telegram Bot API (HTML) |
| Scraping HTTP | requests + BeautifulSoup + regex |
| Scraping JS | Selenium (Firefox headless, fallback Chrome) |
| Configuration | python-dotenv (.env) |
| GPS | Formule Haversine (utils.py) |

## Installation

```bash
# Cloner le repo
git clone https://github.com/Zaalouni/immo-bot-luxembourg.git
cd immo-bot-luxembourg

# Environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Dependances
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Editer .env avec vos tokens Telegram et criteres
```

## Configuration (.env)

```env
# Telegram
TELEGRAM_BOT_TOKEN=votre_token
TELEGRAM_CHAT_ID=votre_chat_id  # ou plusieurs: id1,id2

# Criteres de recherche
MIN_PRICE=1000
MAX_PRICE=2800
MIN_ROOMS=2
MAX_ROOMS=3
MIN_SURFACE=70
EXCLUDED_WORDS=parking,garage,cave

# GPS - Point de reference
REFERENCE_LAT=49.6000
REFERENCE_LNG=6.1342
REFERENCE_NAME=Luxembourg Gare
MAX_DISTANCE=15

# Technique
CHECK_INTERVAL=600  # secondes (10 min)
```

## Utilisation

```bash
# Mode production (boucle continue toutes les 10 min)
python main.py

# Test unique (1 seul cycle)
python main.py --once

# Tester les scrapers individuellement
python test_scrapers.py
```

## Structure du projet

Voir [architecture.md](architecture.md) pour le detail complet.

```
immo-bot-luxembourg/
  main.py              # Point d'entree, classe ImmoBot
  config.py            # Configuration depuis .env
  database.py          # SQLite wrapper
  notifier.py          # Notifications Telegram
  utils.py             # Utilitaires GPS
  test_scrapers.py     # Tests des scrapers
  scrapers/            # 9 scrapers + template Selenium
  .env                 # Secrets (non commite)
  listings.db          # Base SQLite (non commitee)
```

## Versioning

| Version | Date | Description |
|---------|------|-------------|
| v1.0 | 2025-01-17 | Initial : bot basique, scrapers simples |
| v1.1-v1.5 | 2025-01-17/18 | Corrections JSON Athome, filtrage, nouveaux scrapers |
| v2.0 | 2025-02-12 | Filtrage complet, dedup cross-sites, photos, GPS Maps |

## Voir aussi

- [architecture.md](architecture.md) — Architecture detaillee et roles des fichiers
- [analyse.md](analyse.md) — Analyse technique, corrections effectuees, problemes connus
- [planning.md](planning.md) — Planning des actions, versioning, suivi
