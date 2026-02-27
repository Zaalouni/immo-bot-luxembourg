# Manuel Complet — MCP Server Immo-Bot Luxembourg

**Version:** 1.0.0 | **Date:** 2026-02-27 | **Auteur:** Immo-Bot Luxembourg

---

## Table des matières

1. [Introduction](#1-introduction)
2. [Qu'est-ce que le MCP ?](#2-quest-ce-que-le-mcp-)
3. [Architecture du système](#3-architecture-du-système)
4. [Installation complète](#4-installation-complète)
5. [Configuration Claude Desktop](#5-configuration-claude-desktop)
6. [Les 11 Tools — Guide détaillé](#6-les-11-tools--guide-détaillé)
7. [Les 6 Resources — Guide détaillé](#7-les-6-resources--guide-détaillé)
8. [Workflows recommandés](#8-workflows-recommandés)
9. [Tests et validation](#9-tests-et-validation)
10. [Dépannage expert](#10-dépannage-expert)
11. [Extension et personnalisation](#11-extension-et-personnalisation)
12. [Référence technique](#12-référence-technique)

---

## 1. Introduction

Le **MCP Server Immo-Bot Luxembourg** transforme votre bot de veille immobilière
en un assistant IA interactif. Vous pouvez désormais dialoguer avec Claude en
langage naturel pour :

- Interroger vos 122+ annonces immobilières
- Analyser les tendances du marché luxembourgeois
- Lancer des scrapers à la demande
- Recevoir des notifications Telegram ciblées
- Générer des rapports de marché

**Avant MCP:**
```
Vous → ouvrez listings.db manuellement → tapez des requêtes SQL → interprétez
```

**Après MCP:**
```
Vous → "Montre-moi les 3ch < 1900€ à moins de 5km de Kirchberg"
Claude → search + geo → Résultat formaté instantanément
```

---

## 2. Qu'est-ce que le MCP ?

Le **Model Context Protocol** (MCP) est un standard ouvert développé par Anthropic
permettant à des LLMs comme Claude de se connecter à des sources de données externes
et d'exécuter des actions via des "tools" standardisés.

### Principes fondamentaux

```
┌─────────────────────────────────────────────┐
│  MCP = Interface standardisée entre LLM     │
│        et systèmes externes                 │
│                                             │
│  LLM ←──── MCP Protocol ────→ Votre système│
│                                             │
│  • Tools    : Actions que Claude peut faire │
│  • Resources: Données que Claude peut lire  │
│  • Transport: stdio (stdin/stdout)          │
└─────────────────────────────────────────────┘
```

### Flux d'une requête

```
1. Vous écrivez à Claude: "Prix moyen à Kirchberg ?"
2. Claude identifie: → appeler get_stats() ou search_listings(city="kirchberg")
3. Claude envoie: {"method": "tools/call", "name": "get_stats", "arguments": {...}}
4. MCP Server reçoit sur stdin, exécute la requête SQLite
5. MCP Server répond sur stdout avec les statistiques
6. Claude reçoit les données et formule une réponse naturelle
7. Vous recevez: "Le prix moyen à Kirchberg est de 2280€/mois, avec..."
```

---

## 3. Architecture du système

### Vue composants

```
immo-bot-luxembourg/
│
├── main.py              ← Bot principal (scraping continu, 10min)
├── database.py          ← Couche SQLite (listings.db)
├── notifier.py          ← Notifications Telegram
├── config.py            ← Configuration depuis .env
├── utils.py             ← GPS, Haversine, 120+ villes
├── filters.py           ← Filtrage centralisé
├── scrapers/            ← 21+ scrapers sites luxembourgeois
├── dashboard_generator.py ← Export DB → fichiers statiques
│
└── mcp_server/          ← ← ← CE PROJET
    ├── mcp_server.py    ← Serveur MCP principal (point d'entrée)
    ├── tools/           ← 11 handlers de tools
    ├── resources/       ← 6 handlers de resources
    ├── config_mcp.py    ← Configuration MCP
    └── test_mcp_server.py ← 40+ tests unitaires
```

### Interactions entre composants

```
mcp_server.py
   ├── tools/search_tool.py      ←── sqlite3 → listings.db
   ├── tools/stats_tool.py       ←── sqlite3 → listings.db
   ├── tools/scraper_tool.py     ←── importlib → scrapers/*.py
   ├── tools/market_tool.py      ←── sqlite3 + filesystem → history/*.json
   ├── tools/geo_tool.py         ←── utils.py (geocode_city, haversine)
   ├── tools/dashboard_tool.py   ←── subprocess → dashboard_generator.py
   ├── tools/notify_tool.py      ←── notifier.py → Telegram API
   ├── resources/listings_resource.py ←── sqlite3 → listings.db
   ├── resources/stats_resource.py    ←── sqlite3 → listings.db
   └── resources/history_resource.py  ←── filesystem → history/*.json
```

---

## 4. Installation complète

### 4.1 Vérification des prérequis

```bash
# Python 3.10+ requis
python --version

# Venv existant
source /home/user/immo-bot-luxembourg/venv/bin/activate

# DB existante
ls -la /home/user/immo-bot-luxembourg/listings.db

# Config existante
python /home/user/immo-bot-luxembourg/config.py
```

### 4.2 Installation du SDK MCP

```bash
cd /home/user/immo-bot-luxembourg
source venv/bin/activate

# Installation minimale
pip install mcp>=1.0.0

# Installation complète avec dépendances de dev
pip install -r mcp_server/requirements_mcp.txt

# Vérification
python -c "import mcp; print('OK:', mcp.__version__)"
```

### 4.3 Test de démarrage

```bash
python mcp_server/mcp_server.py
# Affiche les logs de démarrage puis attend (Ctrl+C pour arrêter)
```

### 4.4 Tests unitaires

```bash
python mcp_server/test_mcp_server.py -v
# → 40+ tests, doit afficher 0 échecs
```

---

## 5. Configuration Claude Desktop

### 5.1 Localiser le fichier de config

```bash
# Chemin standard Linux
~/.config/claude/claude_desktop_config.json

# Créer si absent
mkdir -p ~/.config/claude
echo '{"mcpServers":{}}' > ~/.config/claude/claude_desktop_config.json
```

### 5.2 Ajouter le serveur MCP

```json
{
  "mcpServers": {
    "immo-bot-luxembourg": {
      "command": "python",
      "args": [
        "/home/user/immo-bot-luxembourg/mcp_server/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/home/user/immo-bot-luxembourg",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 5.3 Redémarrer Claude

Après modification du fichier de config, redémarrer Claude Desktop ou
relancer Claude Code pour que les changements soient pris en compte.

### 5.4 Vérification

Dans Claude, taper:
```
Teste la connexion Telegram et montre-moi les statistiques du marché
```

Claude doit appeler `test_connection()` et `get_stats()` et afficher les résultats.

---

## 6. Les 11 Tools — Guide détaillé

### 6.1 `search_listings` — Recherche d'annonces

**Usage type:** Recherche quotidienne avec critères spécifiques.

```
Paramètres clés:
  price_min / price_max  → Fourchette de prix (€/mois)
  city                   → Ville (partiel, insensible casse)
  rooms_min / rooms_max  → Nombre de chambres
  surface_min            → Surface minimum (m²)
  site                   → Site source (athome, vivi, etc.)
  max_distance_km        → Distance depuis référence GPS
  only_new               → Seulement non-notifiées
  sort_by                → price_asc / price_desc / distance_asc / date_desc / surface_desc
  limit                  → 1 à 100 (défaut: 20)
```

**Exemple concret:**
```
Claude: "Trouve-moi des apparts 3 chambres entre 1600€ et 2000€ à Luxembourg,
         triés du moins cher au plus cher"

→ search_listings(price_min=1600, price_max=2000, rooms_min=3,
                  city="luxembourg", sort_by="price_asc")
```

### 6.2 `get_stats` — Statistiques marché

**Usage type:** Vue d'ensemble quotidienne ou rapport de réunion.

```
Paramètres:
  include_by_site      → Répartition par site (défaut: true)
  include_by_city      → Top 15 villes (défaut: true)
  include_price_ranges → Tranches < 1500€, 1500-2000€, etc. (défaut: true)
```

**Métriques retournées:**
- Total / nouveaux / notifiés / ajoutés 24h / 7j
- Prix moyen / médian / min / max
- Prix moyen au m²
- Surface moyenne
- Distance GPS moyenne
- Répartition visuelle par tranches (graphe ASCII)

### 6.3 `run_scraper` — Lancer un scraper

**Usage type:** Récupération manuelle d'annonces sur un site spécifique.

```
Modes:
  run_scraper("athome")          → Scraper simple, ~10s, ~50 annonces
  run_scraper("vivi")            → Selenium, ~30s, ~15 annonces
  run_scraper("all")             → Tous (21 scrapers), 5-15 minutes
  run_scraper("athome", dry_run=True)  → Test sans écriture DB
```

**Attention:**
- `vivi` et `actuel` utilisent Selenium (Firefox headless) → plus lent
- `wortimmo` et `immoweb` peuvent être bloqués par Cloudflare
- `run_scraper("all")` peut prendre 10-15 minutes

### 6.4 `list_scrapers` — Liste des scrapers

**Usage type:** Audit de l'état de tous les scrapers.

Retourne pour chaque scraper:
- Nom et module Python correspondant
- Statut (fichier existe ou non)
- Nombre d'annonces en DB pour ce site

### 6.5 `analyze_market` — Tendances marché

**Usage type:** Rapport de marché périodique, comparaison temporelle.

```
Paramètres:
  period_days          → 1 à 90 jours (défaut: 7)
  focus_city           → Analyser une ville spécifique
  include_opportunities→ Annonces < 80% de la moyenne (défaut: true)
```

**Données comparées:**
- État actuel vs archives historiques (history/YYYY-MM-DD.json)
- Activité par jour (graphe ASCII)
- Villes les plus actives
- Sites les plus actifs
- Évolution du prix moyen

### 6.6 `detect_anomalies` — Audit qualité données

**Usage type:** Maintenance de la qualité des données en DB.

```
Paramètre:
  threshold_percent → Seuil ±X% pour considérer comme anomalie (défaut: 30)
```

**Anomalies détectées:**
- Prix > moyenne + X% (trop chers)
- Prix < moyenne - X% (trop bas, potentiellement erronés)
- Surface = 0 ou NULL (données incomplètes)
- GPS manquant (distance non calculable)
- URLs invalides (annonces inaccessibles)
- Doublons potentiels (même prix + ville)

### 6.7 `find_nearby` — Recherche géographique

**Usage type:** Trouver un logement proche d'un lieu de travail ou d'un POI.

```
Options de centre:
  Par nom de ville: find_nearby(city_name="Kirchberg", radius_km=3)
  Par coordonnées: find_nearby(latitude=49.63, longitude=6.15, radius_km=3)
```

**Algorithme:**
1. Résolution GPS du centre (via `geocode_city()` ou coordonnées directes)
2. Récupération de toutes les annonces avec GPS depuis la DB
3. Calcul distance Haversine pour chaque annonce
4. Filtrage par `radius_km`
5. Tri par distance croissante

### 6.8 `geocode_city` — GPS d'une ville

**Usage type:** Obtenir les coordonnées d'une ville avant une recherche géographique.

```
Dictionnaire intégré: 120+ villes et localités luxembourgeoises
Pas d'API externe: 100% local, aucun coût, instantané

Exemples:
  Luxembourg → (49.6116, 6.1319)
  Kirchberg  → (49.6300, 6.1500)
  Esch/Alzette → (49.4950, 5.9800)
  Cloche d'Or → (49.5800, 6.1200)
```

### 6.9 `generate_dashboard` — Régénérer le dashboard

**Usage type:** Mettre à jour les fichiers du dashboard web après scraping.

**Fichiers générés dans `dashboards/data/`:**
- `listings.js` — Variable JS avec toutes les annonces
- `listings.json` — JSON pur (réutilisable)
- `stats.js` — Statistiques pour les graphiques
- `market-stats.js` — Analyse de marché
- `anomalies.js` — Anomalies détectées
- `history/YYYY-MM-DD.json` — Archive du jour

### 6.10 `send_alert` — Alerte Telegram

**Usage type:** Notifier manuellement sur des annonces spécifiques identifiées.

```
Utilisation:
  send_alert(listing_ids=["athome_12345"])
  send_alert(listing_ids=["athome_12345", "vivi_67890"],
             message="Opportunité identifiée par Claude!")
```

**Format de la notification:**
- Photo de l'annonce (si URL photo disponible)
- Titre, ville, prix, surface, chambres
- Lien direct vers l'annonce
- Distance GPS si disponible
- Message personnalisé si fourni

### 6.11 `test_connection` — Test Telegram

**Usage type:** Diagnostic de la connexion Telegram avant d'envoyer des alertes.

**Vérifications:**
- Bot actif (getMe API)
- Chaque chat ID accessible (getChat API)
- Retourne statut opérationnel / nombre de chats OK

---

## 7. Les 6 Resources — Guide détaillé

Les resources sont des **données en lecture seule** exposées comme des URLs.
Contrairement aux tools, elles ne prennent pas de paramètres.

### 7.1 `listings://all`

Toutes les annonces actives en JSON.

```json
{
  "resource": "listings://all",
  "count": 122,
  "generated": "2026-02-27T10:00:00",
  "listings": [/* tous les objets listing */]
}
```

**Quand l'utiliser:**
- Export complet pour traitement externe
- Chargement initial dans une autre application
- Analyse exhaustive (sans filtres)

### 7.2 `listings://new`

Annonces des dernières 24 heures uniquement.

```json
{
  "resource": "listings://new",
  "period": "dernières 24h",
  "count": 12,
  "listings": [/* annonces récentes */]
}
```

### 7.3 `listings://by-site`

Annonces regroupées par site source, avec statistiques par site.

```json
{
  "resource": "listings://by-site",
  "total": 122,
  "sites": 9,
  "by_site": {
    "athome": {
      "count": 45,
      "avg_price": 2150,
      "min_price": 1400,
      "max_price": 2500,
      "listings": [/* ... */]
    }
  }
}
```

### 7.4 `stats://current`

Snapshot complet des statistiques de marché.

```json
{
  "resource": "stats://current",
  "total": 122,
  "new": 45,
  "price": {"avg": 2185, "median": 2100, "min": 1400, "max": 2500},
  "by_site": {"athome": 45, "nextimmo": 21},
  "last_24h": 12,
  "last_7d": 38
}
```

### 7.5 `stats://by-city`

Statistiques de prix par ville.

```json
{
  "cities": [
    {
      "city": "Luxembourg",
      "count": 35,
      "avg_price": 2280,
      "min_price": 1600,
      "max_price": 2500,
      "avg_surface": 105,
      "avg_distance": 1.8
    }
  ]
}
```

### 7.6 `history://YYYY-MM-DD`

Archive journalière depuis `dashboards/data/history/`.

```
history://today           → Archive du jour
history://2026-02-20      → Archive d'une date précise
history://list            → Liste toutes les dates disponibles
```

---

## 8. Workflows recommandés

### Workflow matinal (5 minutes)

```
1. test_connection()                     → Vérifier que Telegram fonctionne
2. get_stats()                           → Vue d'ensemble du marché
3. search_listings(only_new=True,
     sort_by="price_asc", limit=10)     → Nouvelles opportunités
4. detect_anomalies()                    → Qualité des données
5. send_alert(listing_ids=[/* top 3 */]) → Alerter les meilleures
```

### Workflow hebdomadaire (15 minutes)

```
1. run_scraper("all")                    → Mise à jour complète
2. analyze_market(period_days=7)         → Rapport de la semaine
3. get_stats(include_by_city=True)       → Répartition géographique
4. detect_anomalies(threshold_percent=20) → Audit qualité
5. generate_dashboard()                   → Mise à jour dashboard web
```

### Workflow de recherche active

```
1. geocode_city("MonLieuDeTravail")     → Obtenir GPS
2. find_nearby(city_name="...",
     radius_km=5)                        → Annonces proches
3. search_listings(price_max=2000,
     rooms_min=3, max_distance_km=5)    → Filtrer selon critères
4. analyze_market(period_days=30,
     focus_city="MaVille")              → Tendances locales
```

---

## 9. Tests et validation

### Lancer les tests

```bash
# Tous les tests (recommandé)
python mcp_server/test_mcp_server.py -v

# Via pytest (si installé)
pytest mcp_server/test_mcp_server.py -v --tb=short

# Classe spécifique
python mcp_server/test_mcp_server.py TestSearchTool
python mcp_server/test_mcp_server.py TestGeoTool
python mcp_server/test_mcp_server.py TestResources
```

### Classes de tests

| Classe | Tests | Couvre |
|--------|-------|--------|
| `TestConfig` | 4 | Configuration et imports |
| `TestSearchTool` | 7 | search_listings (filtres, tri, JSON) |
| `TestStatsTool` | 4 | get_stats (totaux, prix, JSON) |
| `TestScraperTool` | 5 | run_scraper, list_scrapers |
| `TestMarketTool` | 5 | analyze_market, detect_anomalies |
| `TestGeoTool` | 8 | find_nearby, geocode_city, haversine |
| `TestResources` | 7 | Toutes les resources MCP |
| `TestIntegration` | 4 | Flux complets bout-en-bout |
| `TestEdgeCases` | 5 | DB vide, coordonnées extrêmes, etc. |

**Total: 49+ tests unitaires**

### Résultat attendu

```
============================================================
  MCP SERVER — SUITE DE TESTS COMPLÈTE
  27/02/2026 10:00:00
============================================================
TestConfig::test_import_config_mcp ... ok
TestConfig::test_config_summary ... ok
...
TestEdgeCases::test_market_analysis_long_period ... ok

Tests: 49 | OK: 49 | Échecs: 0 | Erreurs: 0
============================================================
```

---

## 10. Dépannage expert

### Diagnostic complet

```bash
# Étape 1: Vérifier Python et SDK
python --version && python -c "import mcp; print(mcp.__version__)"

# Étape 2: Vérifier les imports
python -c "
import sys
sys.path.insert(0, '/home/user/immo-bot-luxembourg')
from mcp_server.config_mcp import get_config_summary
import json
print(json.dumps(get_config_summary(), indent=2))
"

# Étape 3: Tester le démarrage
MCP_LOG_LEVEL=DEBUG python mcp_server/mcp_server.py 2>&1 | head -30

# Étape 4: Lancer les tests
python mcp_server/test_mcp_server.py -v
```

### Problèmes courants

**`SyntaxError: invalid syntax` sur `X | Y`**
```
Cause: Python < 3.10
Solution: Utiliser python3.10 ou modifier les type hints
```

**`ModuleNotFoundError: mcp`**
```
Solution: pip install mcp>=1.0.0
Si venv: /home/user/immo-bot-luxembourg/venv/bin/pip install mcp
```

**`OperationalError: database is locked`**
```
Cause: main.py tourne en arrière-plan et a un verrou DB
Solution: Le MCP server ouvre/ferme la connexion à chaque requête
→ Normalement résolu automatiquement (timeout=10s dans sqlite3.connect)
```

**`ImportError: No module named 'config'`**
```
Solution: PYTHONPATH=/home/user/immo-bot-luxembourg python mcp_server/mcp_server.py
```

**Scraper retourne erreur de permission Cloudflare**
```
Cause: wortimmo, immoweb bloqués par Cloudflare
Solution: Utiliser les scrapers alternatifs (athome, nextimmo, vivi)
```

---

## 11. Extension et personnalisation

### Ajouter un nouveau tool (étapes complètes)

**Fichier: `mcp_server/tools/mon_nouveau_tool.py`**
```python
import mcp.types as types

async def handle_mon_nouveau_tool(args: dict) -> list[types.TextContent]:
    param = args.get("mon_param", "valeur_defaut")
    # ... logique ...
    return [types.TextContent(type="text", text=f"Résultat: {param}")]
```

**Dans `mcp_server/mcp_server.py`:**
```python
# Imports
from mcp_server.tools.mon_nouveau_tool import handle_mon_nouveau_tool

# Dans list_tools()
types.Tool(
    name="mon_nouveau_tool",
    description="Description claire pour Claude",
    inputSchema={
        "type": "object",
        "properties": {
            "mon_param": {"type": "string", "description": "..."}
        }
    }
)

# Dans call_tool()
elif name == "mon_nouveau_tool":
    return await handle_mon_nouveau_tool(arguments)
```

### Ajouter un scraper

**Fichier: `scrapers/mon_site_scraper.py`**
```python
def scrape() -> list[dict]:
    """Scraper pour mon-site.lu"""
    listings = []
    # ... logique de scraping ...
    return listings
```

**Dans `mcp_server/tools/scraper_tool.py`:**
```python
SCRAPER_REGISTRY = {
    # ... existants ...
    "monsite": ("scrapers.mon_site_scraper", "scrape"),
}
```

### Modifier la configuration

**`mcp_server/config_mcp.py`:**
```python
MAX_SEARCH_RESULTS = 200    # Augmenter la limite
MAX_SCRAPER_TIMEOUT = 180   # Timeout plus long pour scrapers lents
```

---

## 12. Référence technique

### Schéma de données — Annonce

```python
listing = {
    "listing_id":   str,      # ID unique (ex: "athome_12345")
    "site":         str,      # Source (ex: "athome")
    "title":        str,      # Titre (max 200 chars)
    "city":         str,      # Ville/commune
    "price":        int,      # Loyer mensuel en €
    "rooms":        int,      # Nombre de chambres (0 = inconnu)
    "surface":      int,      # Surface en m² (0 = inconnu)
    "url":          str,      # URL directe de l'annonce
    "latitude":     float,    # GPS latitude (None si inconnu)
    "longitude":    float,    # GPS longitude (None si inconnu)
    "distance_km":  float,    # Distance depuis référence GPS (None si inconnu)
    "price_per_m2": float,    # Calculé: price/surface (None si surface = 0)
    "created_at":   str,      # Date ajout en DB
    "notified":     int,      # 0 = pas notifié, 1 = notifié
}
```

### Formule Haversine

```python
R = 6371.0  # km
a = sin((lat2-lat1)/2)² + cos(lat1) * cos(lat2) * sin((lng2-lng1)/2)²
c = 2 * atan2(√a, √(1-a))
distance = R * c
```

### Villes du dictionnaire GPS (extrait)

```
Luxembourg-Ville:  49.6116, 6.1319
Kirchberg:         49.6300, 6.1500
Belair:            49.6100, 6.1150
Gare:              49.6000, 6.1342
Limpertsberg:      49.6200, 6.1250
Bonnevoie:         49.5950, 6.1400
Gasperich:         49.5850, 6.1300
Strassen:          49.6200, 6.0700
Bertrange:         49.6100, 6.0500
Mamer:             49.6270, 6.0230
Hesperange:        49.5700, 6.1500
Esch-sur-Alzette:  49.4950, 5.9800
Bettembourg:       49.5200, 6.1050
Dudelange:         49.4800, 6.0900
Ettelbruck:        49.8450, 6.1000
... (120+ villes)
```

### Point de référence GPS par défaut

```python
REFERENCE_LAT  = 49.6000   # Luxembourg-Gare
REFERENCE_LNG  = 6.1342
REFERENCE_NAME = "Luxembourg Gare"
MAX_DISTANCE   = 15.0      # km (configurable dans .env)
```

---

*Manuel généré le 2026-02-27 | Version 1.0.0 | Immo-Bot Luxembourg MCP Server*
