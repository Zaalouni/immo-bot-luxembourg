# Cas d'Usage & Exemples — MCP Server Immo-Bot Luxembourg

Manuel d'expert avec tous les cas d'utilisation détaillés, scénarios avancés et workflows.

---

## Cas d'Usage 1 — Recherche quotidienne du matin

**Objectif:** Vérifier les nouvelles annonces de la nuit, identifier les opportunités.

### Workflow

```
1. get_stats()                          → Vue d'ensemble du marché
2. search_listings(only_new=True,
     sort_by="price_asc", limit=20)    → Nouvelles annonces non notifiées
3. detect_anomalies(threshold_percent=25) → Y a-t-il des prix anormaux ?
4. send_alert(listing_ids=[...])        → Notifier les meilleures
```

### Questions à Claude

```
"Bonjour! Montre-moi les nouvelles annonces de cette nuit, triées par prix"

"Y a-t-il des opportunités sous 1700€ parmi les nouvelles ?"

"Envoie une alerte Telegram pour les annonces athome_12345 et vivi_67890"
```

### Résultat attendu

Claude cherche automatiquement avec `only_new=True`, filtre les prix bas,
identifie les opportunités, et envoie les alertes Telegram sélectionnées.

---

## Cas d'Usage 2 — Analyse de marché hebdomadaire

**Objectif:** Rapport de marché complet pour la semaine écoulée.

### Workflow

```
1. analyze_market(period_days=7)        → Tendances 7 jours
2. get_stats(include_by_city=True)      → Répartition géographique
3. analyze_market(period_days=7,
     focus_city="Kirchberg")            → Focus sur Kirchberg
4. analyze_market(period_days=7,
     focus_city="Esch-sur-Alzette")     → Focus sur Esch
5. generate_dashboard()                  → Mettre à jour les dashboards
```

### Questions à Claude

```
"Fais-moi un rapport complet du marché immobilier cette semaine au Luxembourg"

"Quelle ville a eu le plus d'activité les 7 derniers jours ?"

"Le prix moyen a-t-il évolué par rapport à la semaine dernière ?"

"Génère les dashboards avec les données à jour"
```

---

## Cas d'Usage 3 — Recherche par proximité

**Objectif:** Trouver un appartement proche d'un lieu de travail spécifique.

### Workflow

```
1. geocode_city("Kirchberg")            → Obtenir GPS Kirchberg
2. find_nearby(city_name="Kirchberg",
     radius_km=3, limit=20)             → Annonces dans 3 km
3. search_listings(city="kirchberg",
     price_max=2000, rooms_min=2)       → Affiner par critères
4. find_nearby(latitude=49.6116,
     longitude=6.1319, radius_km=2)    → Rayon autour Centre-Ville
```

### Questions à Claude

```
"Je travaille à Kirchberg. Trouve-moi des appartements à moins de 3 km"

"Quelles sont les annonces les plus proches du Centre-Ville de Luxembourg ?"

"Compare les prix entre Kirchberg et Strassen pour un 3 pièces"
```

---

## Cas d'Usage 4 — Veille multi-sites

**Objectif:** Vérifier si les scrapers fonctionnent et récupérer les nouvelles annonces.

### Workflow

```
1. list_scrapers()                      → État de tous les scrapers
2. run_scraper("athome")                → Lancer Athome (rapide)
3. run_scraper("nextimmo")              → Lancer Nextimmo
4. run_scraper("vivi")                  → Lancer Vivi
5. get_stats(include_by_site=True)      → Vérifier les compteurs par site
```

### Questions à Claude

```
"Quels scrapers ont le moins d'annonces en base ? Il faut les relancer ?"

"Lance les scrapers athome, nextimmo et vivi et dis-moi combien d'annonces nouvelles"

"Fais un dry_run de tous les scrapers pour voir combien ils trouvent"
```

### Mode dry_run (test sans écriture DB)

```
run_scraper("athome", dry_run=True)     → Voir ce qu'athome trouve SANS sauvegarder
run_scraper("all", dry_run=True)        → Test global de tous les scrapers
```

---

## Cas d'Usage 5 — Audit qualité de la base de données

**Objectif:** Nettoyer et auditer les données en DB.

### Workflow

```
1. get_stats()                          → Chiffres de base
2. detect_anomalies(threshold_percent=20) → Anomalies strictes
3. search_listings(sort_by="price_asc",
     limit=10)                          → Les 10 moins chères (doublons ?)
4. search_listings(sort_by="price_desc",
     limit=10)                          → Les 10 plus chères
5. analyze_market(period_days=1)        → Activité de la journée
```

### Questions à Claude

```
"Y a-t-il des anomalies ou doublons dans la base de données ?"

"Montre-moi les 10 annonces les plus chères — sont-elles légitimes ?"

"Combien d'annonces n'ont pas de surface renseignée ?"

"Quels sites ont des données de mauvaise qualité ?"
```

---

## Cas d'Usage 6 — Comparaison de villes

**Objectif:** Comparer le marché entre plusieurs villes.

### Workflow

```
1. get_stats(include_by_city=True)      → Stats par ville (top 15)
2. search_listings(city="luxembourg",
     sort_by="price_asc")               → Annonces Luxembourg
3. search_listings(city="strassen",
     sort_by="price_asc")               → Annonces Strassen
4. find_nearby(city_name="Luxembourg",
     radius_km=5)                       → Luxembourg + proches
5. find_nearby(city_name="Strassen",
     radius_km=3)                       → Strassen + proches
```

### Questions à Claude

```
"Compare les prix entre Luxembourg-Centre et Strassen"

"Quelle est la ville la moins chère parmi les communes proches de Luxembourg ?"

"Pour le même budget de 1800€, où peut-on trouver le plus d'espace ?"

"Classe les villes par rapport prix/surface"
```

---

## Cas d'Usage 7 — Pipeline automatisé complet

**Objectif:** Scraping → Analyse → Dashboard → Notification en une séquence.

### Workflow séquentiel

```
1. run_scraper("all")                   → Récupérer toutes les nouvelles annonces
2. detect_anomalies()                   → Vérifier la qualité des données
3. search_listings(only_new=True,
     sort_by="price_asc", limit=5)      → Top 5 nouvelles opportunités
4. generate_dashboard()                  → Mettre à jour les dashboards web
5. send_alert(listing_ids=[top5_ids])   → Notifier sur Telegram
```

### Question unique à Claude

```
"Lance un cycle complet: scrape tous les sites, trouve les 5 meilleures
nouvelles annonces (prix < 1800€, 3+ chambres), génère les dashboards,
et envoie une alerte Telegram"
```

---

## Cas d'Usage 8 — Analyse historique

**Objectif:** Comprendre l'évolution du marché dans le temps.

### Workflow

```
1. analyze_market(period_days=30)       → Tendance mensuelle
2. analyze_market(period_days=90)       → Tendance trimestrielle
3. history://list                       → Voir les archives disponibles
4. history://2026-01-01                 → Archive d'une date précise
5. analyze_market(period_days=7,
     include_opportunities=True)        → Opportunités récentes
```

### Questions à Claude

```
"Le marché a-t-il évolué ces 30 derniers jours ?"

"Quelle est la tendance des prix sur les 3 derniers mois ?"

"Compare l'état du marché aujourd'hui avec il y a 2 semaines"
```

---

## Requêtes SQL avancées (via search_listings)

### Combinaisons de filtres complexes

```python
# Appartement idéal: 3 chambres, > 90m², < 2000€, < 5km
search_listings(
    rooms_min=3,
    surface_min=90,
    price_max=2000,
    max_distance_km=5,
    sort_by="price_asc"
)

# Nouvelles annonces Athome seulement, triées par distance
search_listings(
    site="athome",
    only_new=True,
    sort_by="distance_asc",
    limit=20
)

# Annonces avec beaucoup d'espace pour le prix (tri surface desc)
search_listings(
    price_max=1800,
    sort_by="surface_desc",
    limit=10
)

# Chercher sur plusieurs sites: lancer séquentiellement
search_listings(site="athome", limit=10)
search_listings(site="vivi", limit=10)
search_listings(site="nextimmo", limit=10)
```

---

## Interprétation des résultats

### Prix/m² — Benchmarks Luxembourg 2026

| Segment | Prix/m² | Qualité |
|---------|---------|---------|
| Très bon marché | < 15€/m² | Vérifier état logement |
| Bon marché | 15-18€/m² | Opportunité |
| Marché normal | 18-22€/m² | Standard |
| Élevé | 22-27€/m² | Quartier premium |
| Très élevé | > 27€/m² | Kirchberg/Centre-Ville |

### Distance — Référence: Luxembourg Gare

| Distance | Zone | Caractéristiques |
|----------|------|-----------------|
| < 2 km | Centre | Luxembourg-Ville, Kirchberg, Gare |
| 2-5 km | Proche | Strassen, Howald, Hesperange |
| 5-10 km | Moyen | Bertrange, Mamer, Bettembourg |
| > 10 km | Éloigné | Dudelange, Ettelbruck, etc. |

### Sites — Fiabilité des données

| Site | Données GPS | Surface | Chambres | Fiabilité |
|------|------------|---------|----------|-----------|
| athome | Bonne | Bonne | Bonne | ★★★★★ |
| nextimmo | Moyenne | Bonne | Bonne | ★★★★ |
| vivi | Bonne | Bonne | Bonne | ★★★★ |
| immotop | Faible | Moyenne | Moyenne | ★★★ |
| sothebys | Faible | Bonne | Bonne | ★★★ |

---

## Erreurs fréquentes et solutions

### "Aucune annonce trouvée" pour une ville connue

```
Problème: city="luxembourg" ne trouve rien
Causes possibles:
  1. Ville stockée avec orthographe différente en DB
  2. Aucune annonce dans cette ville

Solution:
  - Essayer: city="Luxemb" (partiel)
  - Vérifier: get_stats(include_by_city=True) → voir les noms exacts
  - Essayer: find_nearby(city_name="Luxembourg", radius_km=10)
```

### Scraper retourne 0 annonces

```
Problème: run_scraper("athome") → 0 annonces trouvées
Causes possibles:
  1. Site bloqué (Cloudflare, CAPTCHA)
  2. Changement de structure HTML
  3. Timeout réseau

Solution:
  - Essayer dry_run=True pour voir si le problème est persistant
  - Vérifier dans list_scrapers() le dernier compte en DB
  - Lancer d'autres scrapers en parallèle
```

### Anomalies de doublons

```
Problème: detect_anomalies() montre beaucoup de doublons potentiels
Cause: Même appartement listé sur plusieurs sites au même prix

Solution:
  - C'est normal: la déduplication est dans main.py (cross-site)
  - Les "doublons" en DB sont des sites différents pour le même bien
  - Utiliser search_listings(site="athome") pour isoler un site
```

---

## Tips Expert

### Optimiser les recherches

```python
# Au lieu de: search_listings() puis filtrer manuellement
# Faire: utiliser tous les filtres disponibles
search_listings(
    price_min=1500, price_max=2000,
    rooms_min=2, surface_min=70,
    max_distance_km=8,
    sort_by="price_asc",
    only_new=True
)
```

### Identifier les meilleures opportunités

```python
# Stratégie: prix bas + surface élevée + distance faible
# 1. Récupérer avec prix max
r1 = search_listings(price_max=1700, sort_by="surface_desc", limit=20)

# 2. Vérifier les anomalies de prix bas
detect_anomalies(threshold_percent=25)

# 3. Trouver les proches
find_nearby(city_name="Luxembourg", radius_km=5)
```

### Workflow de monitoring automatique

```python
# Session de travail type:
test_connection()                                 # 1. Vérifier Telegram
run_scraper("athome")                             # 2. Scraper principal
run_scraper("vivi")                               # 3. Scraper secondaire
search_listings(only_new=True, sort_by="price_asc")  # 4. Voir les nouvelles
send_alert(listing_ids=["athome_xxx"])            # 5. Alerter sur les meilleures
generate_dashboard()                              # 6. Mettre à jour le dashboard
```

### Comprendre les resources vs tools

```
Resources (lecture passive):
  listings://all    → Toute la DB d'un coup (lourd, ~185 KB)
  stats://current   → Stats snapshot (léger, ~2 KB)
  history://today   → Archive du jour

Tools (actions, filtres, analyses):
  search_listings   → Requête filtrée (recommandé pour recherches)
  get_stats         → Stats avec options
  analyze_market    → Analyse avec comparaison historique
```

Préférer les **tools** pour les recherches quotidiennes.
Utiliser les **resources** pour importer des données complètes dans d'autres systèmes.
