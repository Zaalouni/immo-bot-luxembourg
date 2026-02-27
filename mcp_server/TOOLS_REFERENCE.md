# Référence API — Tools MCP Immo-Bot Luxembourg

Référence complète de tous les 11 tools MCP avec paramètres, types, valeurs par défaut et exemples.

---

## Tool 1: `search_listings`

Recherche d'annonces avec filtres combinables. Retourne texte formaté + JSON.

### Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `price_min` | `integer` | `0` | Prix minimum €/mois |
| `price_max` | `integer` | `999999` | Prix maximum €/mois |
| `city` | `string` | `""` | Ville (recherche partielle, insensible casse) |
| `rooms_min` | `integer` | `null` | Chambres minimum (si renseigné en DB) |
| `rooms_max` | `integer` | `null` | Chambres maximum |
| `surface_min` | `integer` | `null` | Surface minimum m² |
| `site` | `string` | `""` | Site source (athome, immotop, etc.) |
| `max_distance_km` | `number` | `null` | Distance max depuis référence GPS |
| `only_new` | `boolean` | `false` | Seulement annonces non-notifiées |
| `sort_by` | `enum` | `date_desc` | `price_asc`, `price_desc`, `distance_asc`, `date_desc`, `surface_desc` |
| `limit` | `integer` | `20` | Max résultats (1-100) |

### Réponse (texte)

```
=== RECHERCHE IMMOBILIÈRE — 5 résultat(s) ===
(Triés par: price_asc, Limite: 5)

1. [ATHOME] Appartement 3 chambres Kirchberg
   📍 Kirchberg | 2.1 km
   💰 1650€/mois (17.4€/m²) | 95m² | 3 ch.
   🔗 https://www.athome.lu/fr/...
   🕐 Ajouté le 27/02/2026 09:30
   ID: athome_12345

--- Résumé (5 annonces) ---
Prix moyen: 1820€/mois
Prix min:   1650€/mois
Prix max:   2100€/mois
```

### Réponse (JSON)

```json
{
  "count": 5,
  "listings": [
    {
      "listing_id": "athome_12345",
      "site": "athome",
      "title": "Appartement 3 chambres Kirchberg",
      "city": "Kirchberg",
      "price": 1650,
      "rooms": 3,
      "surface": 95,
      "url": "https://www.athome.lu/fr/...",
      "latitude": 49.63,
      "longitude": 6.15,
      "distance_km": 2.1,
      "price_per_m2": 17.4,
      "distance_formatted": "2.1 km",
      "created_at": "27/02/2026 09:30",
      "notified": 0
    }
  ]
}
```

### Exemples d'appel

```python
# Annonces < 1800€ à Luxembourg
search_listings(price_max=1800, city="luxembourg")

# 3 chambres minimum, surface > 80m²
search_listings(rooms_min=3, surface_min=80, sort_by="price_asc")

# Nouvelles annonces non notifiées, triées par prix
search_listings(only_new=True, sort_by="price_asc", limit=10)

# Depuis Athome uniquement, dans 5 km
search_listings(site="athome", max_distance_km=5)
```

---

## Tool 2: `get_stats`

Statistiques complètes du marché immobilier en temps réel.

### Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `include_by_site` | `boolean` | `true` | Répartition par site source |
| `include_by_city` | `boolean` | `true` | Top 15 villes avec prix moy/min/max |
| `include_price_ranges` | `boolean` | `true` | Distribution par tranches de prix |

### Réponse (texte)

```
=======================================================
  STATISTIQUES MARCHÉ IMMOBILIER LUXEMBOURG
  27/02/2026 10:00
=======================================================

--- TOTAUX ---
  Total annonces:     122
  Nouvelles:          45  (non notifiées)
  Notifiées:          77
  Ajoutées 24h:       12
  Ajoutées 7 jours:   38
  Villes couvertes:   65

--- PRIX ---
  Moyen:   2185€/mois
  Médian:  2100€/mois
  Min:     1400€/mois
  Max:     2500€/mois
  Prix/m²: 20.3€/m²
  Surface moy.: 108m²

--- TRANCHES DE PRIX ---
  < 1500€       8 annonces (  6.6%) ##
  1500-2000€   42 annonces ( 34.4%) #######
  2000-2500€   65 annonces ( 53.3%) ##########
  > 2500€       7 annonces (  5.7%) #

--- PAR SITE ---
  athome               45 ann. (36.9%) | moy. 2150€
  nextimmo             21 ann. (17.2%) | moy. 2230€
  vivi                 14 ann. (11.5%) | moy. 1980€
  ...
```

### Réponse (JSON)

```json
{
  "timestamp": "2026-02-27T10:00:00",
  "total": 122,
  "new": 45,
  "notified": 77,
  "last_24h": 12,
  "last_7d": 38,
  "city_count": 65,
  "price": {
    "avg": 2185,
    "median": 2100,
    "min": 1400,
    "max": 2500,
    "avg_per_m2": 20.3
  },
  "avg_surface": 108,
  "gps": {
    "avg_distance_km": 8.2,
    "min_distance_km": 0.3,
    "gps_count": 98
  },
  "by_site": {
    "athome": {"count": 45, "percent": 36.9, "avg_price": 2150}
  },
  "by_city": {
    "Luxembourg": {"count": 35, "avg_price": 2280, "min_price": 1600, "max_price": 2500}
  },
  "price_ranges": {
    "< 1500€": {"count": 8, "percent": 6.6}
  }
}
```

---

## Tool 3: `run_scraper`

Lancer un scraper à la demande.

### Paramètres

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `scraper_name` | `string` | **Oui** | Nom du scraper ou `"all"` |
| `dry_run` | `boolean` | Non (défaut: `false`) | Tester sans sauvegarder en DB |

### Scrapers disponibles

| Nom | Site | Technologie |
|-----|------|-------------|
| `athome` | athome.lu | JSON embedded |
| `immotop` | immotop.lu | HTML/regex |
| `luxhome` | luxhome.lu | JSON/regex |
| `vivi` | vivi.lu | Selenium |
| `newimmo` | newimmo.lu | HTTP |
| `nextimmo` | nextimmo.lu | HTTP |
| `unicorn` | unicorn.lu | HTTP |
| `wortimmo` | wortimmo.lu | HTTP |
| `immoweb` | immoweb.be | HTTP |
| `sigelux` | sigelux.lu | HTTP |
| `sothebys` | sothebys.lu | HTTP |
| `remax` | remax.lu | HTTP |
| `floor` | floor.lu | HTTP |
| `apropos` | apropos.lu | HTTP |
| `ldhome` | ldhome.lu | HTTP |
| `immostar` | immostar.lu | HTTP |
| `nexvia` | nexvia.lu | HTTP |
| `propertyinvest` | propertyinvest.lu | HTTP |
| `rockenbrod` | rockenbrod.lu | HTTP |
| `homepass` | homepass.lu | HTTP |
| `actuel` | actuel.lu | Selenium |
| `all` | Tous | — |

### Réponse

```
=== SCRAPER: ATHOME [LIVE] ===
Démarrage: 10:05:32

Annonces trouvées: 47
Temps d'exécution: 8.3s

Nouvelles en DB:  3
Doublons:         44

--- Aperçu (5 premières) ---
1. Appartement lumineux 3 ch. Kirchberg
   Kirchberg | 1850€ | 95m² | 3ch.
```

---

## Tool 4: `list_scrapers`

Lister tous les scrapers avec statut et compteurs.

### Paramètres

Aucun paramètre requis.

### Réponse

```
=== SCRAPERS DISPONIBLES ===
Total: 21 scrapers

  athome               ✓ actif              DB:  45 annonces
  immotop              ✓ actif              DB:   2 annonces
  luxhome              ✓ actif              DB:   8 annonces
  vivi                 ✓ actif              DB:  14 annonces
  nextimmo             ✓ actif              DB:  21 annonces
  ...

Usage: run_scraper avec scraper_name='<nom>' ou 'all'
```

---

## Tool 5: `analyze_market`

Analyse des tendances du marché sur une période.

### Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `period_days` | `integer` | `7` | Période d'analyse en jours (1-90) |
| `focus_city` | `string` | `""` | Analyser une ville spécifique |
| `include_opportunities` | `boolean` | `true` | Annonces sous 80% de la moyenne |

### Réponse (texte)

```
============================================================
  ANALYSE MARCHÉ — Luxembourg complet
  Période: 7 jour(s) | 27/02/2026
============================================================

--- SITUATION ACTUELLE ---
  Total annonces:  122
  Prix moyen:      2185€/mois
  Prix min:        1400€/mois
  Prix max:        2500€/mois

--- ACTIVITÉ (derniers 7 jours) ---
  Nouvelles annonces: 38
  Prix moyen (période): 2210€/mois
  Rythme: 5.4 annonces/jour

--- ANNONCES PAR JOUR ---
  2026-02-27  12  ████████████
  2026-02-26   8  ████████
  2026-02-25   5  █████
  ...

--- ÉVOLUTION HISTORIQUE ---
  vs 1j: annonces +12, prix moy. +45€
  vs 7j: annonces +38, prix moy. +120€
  vs 14j: annonces +55, prix moy. +80€

--- OPPORTUNITÉS (< 1748€, soit < 80% de la moyenne) ---
  1400€ | 85m² | 2ch. — Strassen
    Appartement calme proche tram
    https://...
```

---

## Tool 6: `detect_anomalies`

Détecter les anomalies de prix et données dans la DB.

### Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `threshold_percent` | `number` | `30` | Seuil déviation % pour anomalie |

### Réponse

```
=======================================================
  DÉTECTION D'ANOMALIES — Immo-Bot Luxembourg
  Seuil: ±30% (moyenne: 2185€)
=======================================================

--- PRIX TRÈS ÉLEVÉS (> 2840€) ---
  2500€ (+14.4%) — Kirchberg [athome] | athome_99999

--- PRIX TRÈS BAS (< 1529€) ---
  1400€ (-35.9%) — Strassen [vivi] | vivi_00001

--- DONNÉES MANQUANTES ---
  Surface inconnue:   24 annonces
  GPS manquant:       24 annonces
  URLs invalides:      0 annonces

--- DOUBLONS POTENTIELS (même prix + ville) ---
  1800€ à Luxembourg: 3 annonces similaires

=======================================================
TOTAL ANOMALIES: 4 détectées
  Prix aberrants: 1 hauts, 1 bas
  Doublons: 1 groupes
```

---

## Tool 7: `find_nearby`

Recherche géographique par rayon autour d'un point GPS ou d'une ville.

### Paramètres

| Paramètre | Type | Description |
|-----------|------|-------------|
| `latitude` | `number` | Latitude du point central (ex: 49.6116) |
| `longitude` | `number` | Longitude du point central (ex: 6.1319) |
| `city_name` | `string` | Ville comme centre (alternative à lat/lng) |
| `radius_km` | `number` | Rayon en km (défaut: 5.0) |
| `limit` | `integer` | Max résultats (défaut: 15) |

**Note:** Fournir soit `city_name`, soit `latitude + longitude`.

### Réponse

```
=== ANNONCES À 3.0 km DE Kirchberg (49.6300, 6.1500) ===
Trouvées: 8 annonces

1. [ATHOME] Appartement moderne 3 ch.
   📍 Kirchberg — 0.3 km du point central
   💰 1950€/mois (20.5€/m²) | 95m² | 3ch.
   🔗 https://...

2. [VIVI] Grand appartement Kirchberg
   📍 Kirchberg — 0.8 km du point central
   💰 2100€/mois | 110m²
   ...

--- Résumé ---
Prix moyen dans le rayon: 2050€/mois
Prix min: 1800€ | max: 2400€
```

---

## Tool 8: `geocode_city`

Convertir un nom de ville luxembourgeoise en coordonnées GPS.

### Paramètres

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `city_name` | `string` | **Oui** | Nom de la ville |

### Villes supportées (120+)

Luxembourg-Ville et quartiers, communes proches, communes moyennes :
`Luxembourg`, `Kirchberg`, `Belair`, `Gare`, `Limpertsberg`, `Bonnevoie`,
`Gasperich`, `Strassen`, `Bertrange`, `Mamer`, `Hesperange`, `Howald`,
`Esch-sur-Alzette`, `Bettembourg`, `Dudelange`, `Ettelbruck`, `Diekirch`, ...

### Réponse

```
=== GEOCODAGE: Kirchberg ===

  Latitude:  49.63
  Longitude: 6.15

  Google Maps: https://maps.google.com/?q=49.63,6.15
  OpenStreetMap: https://www.openstreetmap.org/?mlat=49.63&mlon=6.15
```

---

## Tool 9: `generate_dashboard`

Régénérer les fichiers statiques du dashboard (listings.js, stats.js, etc.).

### Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `include_archive` | `boolean` | `true` | Créer archive dans `history/` |

### Réponse

```
=== GÉNÉRATION DASHBOARD ===
Démarrage: 10:10:00
Générateur: /home/user/immo-bot-luxembourg/dashboard_generator.py

Statut: SUCCÈS (12.3s)

--- Fichiers générés (6 fichiers, 248.5 KB total) ---
  listings.js                       185.2 KB
  listings.json                      62.1 KB
  stats.js                            0.8 KB
  market-stats.js                     0.4 KB
  anomalies.js                        0.1 KB
  history/2026-02-27.json            62.1 KB
```

---

## Tool 10: `send_alert`

Envoyer une notification Telegram pour des annonces spécifiques.

### Paramètres

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `listing_ids` | `array[string]` | **Oui** | Liste de `listing_id` |
| `message` | `string` | Non | Message personnalisé additionnel |

### Réponse

```
=== ENVOI ALERTES TELEGRAM ===
Annonces à notifier: 2

✓ athome_12345 — Envoyé: Kirchberg | 1850€ | Appartement 3 ch...
✓ vivi_67890   — Envoyé: Luxembourg | 1650€ | Studio renové...

========================================
RÉSUMÉ: 2 envoyées, 0 échecs, 0 introuvables
```

---

## Tool 11: `test_connection`

Vérifier la connexion Telegram.

### Paramètres

Aucun paramètre requis.

### Réponse

```
=== TEST CONNEXION TELEGRAM ===
Heure: 10:15:00

✓ Bot actif: @ImmoLuxBot (Immo Luxembourg)
  Bot ID: 123456789

Chats configurés: 2
  ✓ Chat -1001234567890: Immo Luxembourg (supergroup)
  ✓ Chat 987654321: Jean Dupont (private)

Résultat: 2/2 chats accessibles
✓ Connexion Telegram opérationnelle
```

---

## Codes d'erreur communs

| Erreur | Cause | Solution |
|--------|-------|----------|
| `DB introuvable` | `listings.db` absent | Lancer `python main.py --once` |
| `scraper_name requis` | Paramètre manquant | Ajouter `scraper_name="athome"` |
| `Scraper inconnu` | Nom incorrect | Vérifier avec `list_scrapers()` |
| `Ville non trouvée` | Orthographe | Voir liste des 120+ villes dans `utils.py` |
| `TELEGRAM_BOT_TOKEN manquant` | `.env` mal configuré | Vérifier `.env` |
| `Import error` | Scraper défaillant | Vérifier fichier dans `scrapers/` |
