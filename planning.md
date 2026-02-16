# 📊 DASHBOARD IMMO LUXEMBOURG - BRIEF CLAUDE CODE

## 🎯 MISSION SIMPLE
Créer **1 script** `dashboard_generator.py` qui génère un **Dashboard HTML interactif** en <5 secondes à partir de `listings.db` SQLite.

**Bot scraping reste intact** (main.py, scrapers inchangés).

---

## 📋 CONTEXTE
- **Données existantes**: listings.db (Athome, Immotop, Century21)
- **Colonnes**: listing_id, title, price, rooms, surface, city, url, score
- **Objectif**: Utilisateur exécute `python dashboard_generator.py` → fichier HTML créé

---

## 🚀 FLUX UTILISATEUR (3 étapes)
```
$ python dashboard_generator.py
✅ Dashboard généré! 42 annonces
$ open dashboards/index.html  (ou double-click)
→ Voir tableau interactif, filtres, carte, comparateur
```

---

## 📁 STRUCTURE
```
immo-bot-luxembourg/
├── main.py, database.py, config.py (INCHANGÉS)
├── listings.db (INCHANGÉ)
│
├── [NOUVEAU] dashboard_generator.py ← À créer
├── [NOUVEAU] templates/dashboard.html ← Template Jinja2
│
└── [NOUVEAU] dashboards/ (créé auto)
    ├── index.html ← Dashboard live
    ├── archives/2025-02-16.html ← Snapshot
    └── data/listings.json ← Données
```

---

## 🔧 4 ÉTAPES DU SCRIPT

| Étape | Quoi | Détails |
|-------|------|---------|
| 1 | **Lire** | Ouvrir listings.db → exporter en JSON (42 annonces) |
| 2 | **Calculer** | Stats: total, prix moyen/ville, annonces/site |
| 3 | **Générer** | Load template Jinja2 + insérer données JSON + stats |
| 4 | **Écrire** | Créer: index.html + archive jour + data/listings.json |

---

## 🎨 DASHBOARD: 5 COMPOSANTS

### 1️⃣ **Tableau** (CRITIQUE)
```
Ville | Prix | m² | €/m² | Score | Site | Action
Belair | 1950€ | 82 | 23.78 | 8.5 | Immotop | [Voir]
...
→ Interactif: tri click, checkboxes, lien URLs
```

### 2️⃣ **Filtres** (CRITIQUE)
```
Ville [multiselect]
Prix [range €1000-3000]
Surface [range m²]
[Appliquer] → Tableau update JavaScript
```

### 3️⃣ **Stats Header**
```
42 annonces | Moy 1938€ | Athome 12 | Immotop 18 | ...
```

### 4️⃣ **Carte** (BONUS)
```
Leaflet.js pins clusters
Click pin → popup (prix, surface)
```

### 5️⃣ **Comparateur** (BONUS)
```
Cocher 2-3 annonces → [Comparer]
Modal tableau côte-à-côte
```

---

## ⚙️ TECHNOS

**Python**: sqlite3, json, jinja2, datetime  
**HTML**: Bootstrap 5 (CDN), Leaflet.js (CDN), JavaScript vanilla  
**Avantage**: Fichier standalone, fonctionne offline, pas serveur web

---

## 💡 CLÉS ARCHITECTURE

✅ HTML standalone (ouvre file:// navigateur)  
✅ Données JSON embedées dans `<script>`  
✅ Filtres/tri côté JavaScript (pas API)  
✅ Archive auto YYYY-MM-DD  
✅ Zéro modification au bot

---

## 📊 PRIORITÉS

| Priorité | Composant | Effort |
|----------|-----------|--------|
| 1 | Tableau + Tri | 🟢 Bas |
| 2 | Filtres | 🟢 Bas |
| 3 | Stats | 🟢 Bas |
| 4 | Carte | 🟡 Moyen |
| 5 | Comparateur | 🟡 Moyen |

**MVP = 1-3** (30min, 95% valeur)

---

## ✅ CRITÈRES SUCCÈS

- ✅ Script <5sec exécution
- ✅ HTML sans erreurs (fichier standalone)
- ✅ Tableau affiche toutes annonces
- ✅ Filtres fonctionnent (JavaScript)
- ✅ Archive créée YYYY-MM-DD
- ✅ Bot inchangé

---

## 🚨 CONTRAINTES

❌ **Pas de**: Flask, FastAPI, serveur web, BD additionnelle, React/Vue  
✅ **Oui**: HTML simple, JavaScript vanilla, CDN externes, offline

---

## 📱 EXEMPLE USAGE

**Jour 1**:
```bash
python dashboard_generator.py
✅ dashboards/index.html créé
open dashboards/index.html → voir 42 annonces
```

**Jour 2** (5 nouvelles annonces scrapées):
```bash
python main.py  # scraping normal
python dashboard_generator.py  # regénère
open dashboards/index.html → 47 annonces à jour
```

---

## 🎯 INSTRUCTIONS CLAUDE CODE
```
Crée: dashboard_generator.py

INPUT:  listings.db (SQLite), templates/dashboard.html (Jinja2)
OUTPUT: dashboards/index.html, dashboards/archives/YYYY-MM-DD.html

LOGIC:
  [1] Read listings.db → JSON
  [2] Calc stats (total, avg price, by site/city)
  [3] Render Jinja2 template (remplace {{listings_json}}, {{stats}})
  [4] Write files + print success

PRIORITÉ: Tableau + Filtres + Stats
BONUS: Carte Leaflet + Comparateur

Pas de modification à main.py/database.py/config.py
HTML standalone, fonctionne offline
```

---

**Envoyez ce fichier à Claude Code avec instruction simple ci-dessus** ✅