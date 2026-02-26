# Dashboard Immo Luxembourg — Analyse complète et corrections

> Ce fichier documente l'analyse complète du système de dashboard du bot immobilier,
> ses composants actuels, les problèmes identifiés et les corrections à apporter.

---

## 📊 Vue d'ensemble du problème

Le projet a **3 scripts de dashboard redondants** qui ne sont **pas intégrés au bot principal** :

| Script | Type | Statut | Problème |
|--------|------|--------|---------|
| `dashboard.py` | Console + HTML statique | ⚠️ Legacy | Généré manuellement, HTML inline 350 lignes |
| `dashboard_generator.py` | PWA statique | ✅ Meilleur | HTML inline 450 lignes, pas de template externe |
| `web_dashboard.py` | Flask web server | ❌ Non utilisé | Dépendance Flask absente, pas intégré, créé à l'init |

**Résultat** : Utilisateur doit choisir quelle version utiliser, aucune n'est automatisée.

---

## 📁 État actuel du dashboard

### Structure des répertoires

```
immo-bot-luxembourg/
├── dashboard.py              ← Console + HTML statique (vieux, 350 loc)
├── dashboard_generator.py    ← PWA statique (meilleur, 676 loc, HTML inline)
├── web_dashboard.py          ← Flask server (non utilisé, 475 loc)
│
├── dashboard.html            ← Généré par dashboard.py (17/01/2026, obsolète)
│
├── templates/
│   └── dashboard.html        ← Créé par web_dashboard.py au démarrage (template Jinja2)
│
└── dashboards/               ← Généré par dashboard_generator.py
    ├── index.html            ← Dashboard PWA principal (42 Ko)
    ├── manifest.json         ← PWA manifest
    ├── icon.svg              ← Logo PWA
    ├── sw.js                 ← Service Worker (PWA offline)
    ├── map.html              ← Page bonus
    ├── photos.html           ← Page bonus
    │
    ├── archives/             ← Snapshots HTML quotidiens (YYYY-MM-DD.html)
    │
    └── data/
        ├── listings.js       ← Données JS (variable LISTINGS)
        ├── stats.js          ← Stats + couleurs sites
        ├── listings.json     ← Données JSON pur
        └── history/
            └── YYYY-MM-DD.json ← Archive JSON quotidienne
```

### État des fichiers

#### ✅ dashboard_generator.py (676 lignes)
**Meilleur script, le plus complet**

**Fonctionnalités** :
- ✅ Lit listings.db → exporte JSON + JS
- ✅ Calcule stats (total, prix moyen, par site, par ville, par tranche prix)
- ✅ Génère PWA standalone (fonctionne offline)
- ✅ Archive quotidienne (JSON + HTML)
- ✅ Bootstrap 5 + Leaflet.js via CDN
- ✅ 5 onglets : Tableau triable, Par ville, Par prix, Carte, Stats
- ✅ Filtres client-side (JavaScript) : ville, prix min/max, surface, site
- ✅ Tri interactif sur colonnes
- ✅ Carte Leaflet avec pins colorés (1 couleur par site)
- ✅ Fonction formatage, responsive mobile

**Structure de données** :
```javascript
// listings.js
const LISTINGS = [
  {
    listing_id, site, title, city, price, rooms, surface,
    url, latitude, longitude, distance_km, created_at,
    price_m2  // Calculé
  },
  ...
]

// stats.js
const STATS = {
  total, avg_price, min_price, max_price, avg_surface, cities,
  sites: { 'Athome.lu': 12, ... },
  by_city: [ { city, count, avg_price }, ... ],
  by_price_range: { '< 1500': 5, ... }
}
const SITE_COLORS = { 'Athome.lu': '#FF6384', ... }
```

**Problème principal** :
- ❌ **Code HTML inline** : 450 lignes dans une f-string (lignes 179-624)
- ❌ Pas de template externe → difficile à maintenir/modifier
- ❌ Pas d'intégration dans main.py → doit être lancé manuellement

#### ⚠️ dashboard.py (350 lignes)
**Legacy, redondant avec dashboard_generator.py**

**Fonctionnalités** :
- Console dashboard (affichage texte coloré)
- Export JSON (dashboard_stats.json)
- Export HTML (dashboard.html) — **C'est une fonction dans le code, pas vraiment utilisée**
- Export CSV (listings_export.csv)

**Problèmes** :
- ❌ HTML généré en ligne (150 lignes)
- ❌ Redondant avec dashboard_generator.py (les mêmes stats)
- ❌ Pas de PWA, pas de filtres interactifs
- ⚠️ dashboard.html généré le 17/01/2026 = très vieux

#### ❌ web_dashboard.py (475 lignes)
**Non utilisé, Flask dépendance absente**

**Problèmes** :
- ❌ Flask n'est pas dans requirements.txt
- ❌ Crée templates/dashboard.html au démarrage (jamais utilisé)
- ❌ Nécessite serveur web (contraire à la philosophie PWA)
- ❌ Routes API jamais appelées
- ❌ Vue Jinja2 malformée (utilise syntaxe Jinja dans f-string)
- ❌ Pas d'intégration dans main.py

---

## 🔍 Analyse détaillée des composants

### 1. Données et source

#### Entrée : listings.db (SQLite)

```sql
SELECT listing_id, site, title, city, price, rooms, surface,
       url, latitude, longitude, distance_km, created_at
FROM listings
ORDER BY id DESC
```

**Champs utilisés** :
- `listing_id`, `site`, `title`, `city` : texte
- `price`, `rooms` : entiers
- `surface` : entier (peut être 0 si inconnu)
- `url`, `latitude`, `longitude`, `distance_km` : localisation
- `created_at` : timestamp

#### Sortie : JSON/JS/HTML

**dashboard_generator.py exporte** :

1. **listings.js** (LISTINGS variable) : Toutes les annonces
2. **stats.js** (STATS + SITE_COLORS) : Statistiques agrégées
3. **listings.json** : Pur JSON (reutilisable)
4. **data/history/YYYY-MM-DD.json** : Archive quotidienne

### 2. Filtres (côté JavaScript)

**Onglet "Tableau"** :
```javascript
applyFilters() {
  const city = document.getElementById('f-city').value;
  const pmin = parseInt(document.getElementById('f-pmin').value) || 0;
  const pmax = parseInt(document.getElementById('f-pmax').value) || 999999;
  const site = document.getElementById('f-site').value;
  const smin = parseInt(document.getElementById('f-smin').value) || 0;

  filtered = LISTINGS.filter(l => {
    if (city && l.city !== city) return false;
    if (l.price < pmin || l.price > pmax) return false;
    if (site && l.site !== site) return false;
    if (smin && (!l.surface || l.surface < smin)) return false;
    return true;
  });
  sortAndRender();
}
```

**Tri** :
```javascript
sortCol = 'price';  // Colonne à trier
sortAsc = true;     // Croissant
// Clic sur colonne header → toggle sort direction
```

### 3. Interface utilisateur

**Onglets** (Bootstrap tabs) :
1. **Tableau** : Filtres + tableau triable interactif
2. **Par ville** : Groupes par ville avec stats
3. **Par prix** : Groupes par tranche prix
4. **Carte** : Leaflet.js avec pins

**Responsive** :
- Desktop : Grid 12 colonnes, fonts normales
- Mobile : Ajust fonts, layout adapté

### 4. PWA (Progressive Web App)

**manifest.json** :
```json
{
  "name": "Immo Luxembourg Dashboard",
  "short_name": "ImmoLux",
  "start_url": "./index.html",
  "display": "standalone",
  "icons": [{ "src": "data:image/svg+xml...", "sizes": "any" }]
}
```

**sw.js** (Service Worker) : Permet offline, cache

**Avantage** : Instable sur téléphone comme app native

---

## ❌ Problèmes identifiés

### Problème 1 : Code HTML inline (CRITIQUE)

**Localisation** : dashboard_generator.py, lignes 179-624

```python
def generate_html(stats, site_colors):
    html = f'''<!DOCTYPE html>
<html lang="fr">
...
'''  # 450 lignes de HTML/CSS/JS inline
```

**Conséquences** :
- ❌ Difficile à lire/modifier
- ❌ Pas de syntax highlighting dans l'IDE
- ❌ Impossible de tester le HTML seul
- ❌ Maintenance compliquée
- ❌ Pas de séparation concerns

### Problème 2 : Redondance des 3 scripts

**dashboard.py** + **web_dashboard.py** = Redondant avec dashboard_generator.py

**Conséquences** :
- ❌ Code dupliqué (calc_stats dans les 3)
- ❌ Utilisateur confus : lequel utiliser ?
- ❌ Maintenance : 3 endroits à mettre à jour

### Problème 3 : Pas d'intégration dans le bot

**main.py** n'appelle jamais :
- dashboard.py
- dashboard_generator.py
- web_dashboard.py

**Conséquence** :
- ❌ Utilisateur doit lancer manuellement `python dashboard_generator.py`
- ❌ Dashboard pas à jour automatiquement
- ❌ Pas de sync avec le cycle du bot

### Problème 4 : Dependencies

**web_dashboard.py** :
- ❌ Import Flask (pas dans requirements.txt)
- ❌ Jamais testé

### Problème 5 : Files obsolètes

**dashboard.html** (racine) :
- ⚠️ Généré le 17/01/2026 (très vieux)
- ⚠️ Duplique ce que dashboard_generator fait
- ❌ Pas dans .gitignore (devrait être généré, pas commité)

**templates/dashboard.html** :
- ⚠️ Créé par web_dashboard.py (non utilisé)
- ❌ Syntaxe Jinja2 incorrecte (utilisée dans f-string)

### Problème 6 : Fonctionnalités manquantes/bugguées

#### 6a. Comparateur (annoncé mais pas implémenté)
- Onglet annonce "Comparateur" mais pas de code JavaScript

#### 6b. Archive HTML
- Archive quotidienne créée mais pas d'index pour les consulter
- Pas de page "historique" pour voir les anciennes versions

#### 6c. Pas de tests
- Aucun test pour dashboard_generator.py
- Aucun test pour les filtres/tri

#### 6d. Performance
- Si listings.db a 10 000+ annonces, LISTINGS JS peut être gros (1+ MB)
- Filtres en mémoire sont lents sur mobile

---

## ✅ Corrections à apporter (Étape 1 : Analyse)

### Priorité CRITIQUE

#### 1. Extraire HTML dans template externe

**Fichier** : `templates/dashboard.html` (créer/remplacer)

**Approche** : Template Jinja2 ou string template simple (pas de Flask)

```html
<!DOCTYPE html>
<html lang="fr">
<head>...</head>
<body>
  <!-- Header avec {{ stats.total }}, {{ stats.cities }}, etc -->
  <script src="data/listings.js"></script>
  <script src="data/stats.js"></script>
  <!-- Rest of HTML/JS -->
</body>
</html>
```

**Avantage** :
- ✅ Séparation concerns
- ✅ Editeur Python peut lire HTML normalement
- ✅ Facile à maintenir
- ✅ Pas de dépendance externe (simple string replace)

#### 2. Consolider en 1 seul script

**Décision** : Conserver seulement `dashboard_generator.py`

**Actions** :
- Supprimer `dashboard.py`
- Supprimer `web_dashboard.py` (ou le mettre en legacy/)
- Garder `dashboard_generator.py` comme seul source of truth

#### 3. Intégrer dans main.py

**Approche** : Appeler dashboard_generator après chaque cycle complet

```python
# main.py - fin de check_new_listings()
if len(new_listings) > 0:
    # ... notifications ...
    # Regénérer dashboard
    from dashboard_generator import generate_dashboard
    generate_dashboard()
```

**Avantage** :
- ✅ Dashboard auto-updated après chaque scraping
- ✅ Pas d'action manuelle
- ✅ Données toujours fraîches

### Priorité HAUTE

#### 4. Implémenter le comparateur

**Fonctionnalité** : Cocher 2-3 annonces → modal tableau côte-à-côte

```javascript
// HTML
<input type="checkbox" class="listing-checkbox" data-id="athome_123">

// JS
function compareSelected() {
  const selected = [...document.querySelectorAll('.listing-checkbox:checked')]
    .map(c => LISTINGS.find(l => l.listing_id === c.dataset.id));
  if (selected.length < 2) return alert('Sélectionner 2-3 annonces');
  showComparisonModal(selected);
}
```

#### 5. Ajouter index des archives

**Fichier** : `dashboards/archives/index.html`

```html
<h1>Historique des dashboards</h1>
<ul>
  <li><a href="2026-02-26.html">26 fév 2026 (42 annonces)</a></li>
  <li><a href="2026-02-25.html">25 fév 2026 (40 annonces)</a></li>
  ...
</ul>
```

#### 6. Ajouter tests

**Fichier** : `test_dashboard.py`

```python
import unittest
from dashboard_generator import calc_stats, read_listings

class TestDashboard(unittest.TestCase):
    def test_read_listings(self):
        listings = read_listings()
        self.assertIsInstance(listings, list)

    def test_calc_stats(self):
        listings = [
            {'price': 1000, 'surface': 50, 'site': 'A', 'city': 'X'},
            {'price': 2000, 'surface': 100, 'site': 'B', 'city': 'Y'},
        ]
        stats = calc_stats(listings)
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['avg_price'], 1500)
```

### Priorité MOYENNE

#### 7. Optimiser perf pour gros volumes

**Si > 5000 annonces** :
- Paginer le tableau JS (500 annonces/page)
- Pré-calculer indices de recherche
- Compresser listings.js (minify)

#### 8. Ajouter filtres avancés

- Filtres multiples simultanés (ET logique, pas OU)
- Sauvegarde des filtres dans localStorage
- Export filtré en CSV

#### 9. Ajouter graphiques

- Utiliser Chart.js (léger, CDN)
- Graphiques par site (doughnut)
- Graphiques par prix (bar)
- Timeline des annonces

#### 10. Améliorer PWA

- Icônes PNG 192x512
- Splash screens
- Offline tout contenu local

---

## 📋 Plan de corrections (Étape 2 : Implémentation)

### Phase 1 : Refactoring HTML (Jour 1-2)

**Tâche 1.1** : Créer `templates/dashboard.html` (template externe)
- Copier HTML depuis dashboard_generator.py:generate_html()
- Remplacer valeurs par placeholders : {stats.total}, {now}, etc.
- Garder tout JS inline (pas de framework)

**Tâche 1.2** : Modifier `dashboard_generator.py`
- Lire template depuis fichier
- Remplacer placeholders avec dict Python
- Tester que output = ancien output

**Tâche 1.3** : Supprimer code redondant
- Supprimer `dashboard.py`
- Supprimer `web_dashboard.py`
- Supprimer `dashboard.html` (vieux, à la racine)

### Phase 2 : Intégration dans bot (Jour 2-3)

**Tâche 2.1** : Intégrer `dashboard_generator()` dans `main.py`
- Importer generate_dashboard()
- Appeler après check_new_listings() si nouveautés
- Gérer erreurs (catch exceptions, log, continuer)

**Tâche 2.2** : Tester intégration
- Lancer bot en mode --once
- Vérifier dashboards/index.html généré
- Vérifier filtres/tri fonctionnent

### Phase 3 : Nouvelles fonctionnalités (Jour 3-4)

**Tâche 3.1** : Implémenter comparateur

**Tâche 3.2** : Ajouter index archives

**Tâche 3.3** : Ajouter tests (test_dashboard.py)

**Tâche 3.4** : Ajouter graphiques (Chart.js)

---

## 🧪 Checklist de test

### Test 1 : Génération

- [ ] `python dashboard_generator.py` génère tous fichiers
- [ ] dashboards/index.html s'ouvre sans erreurs
- [ ] dashboards/data/listings.js contient valeurs correctes
- [ ] dashboards/data/stats.js a STATS + SITE_COLORS

### Test 2 : Filtres

- [ ] Filtre ville marche (affiche seulement cette ville)
- [ ] Filtre prix min/max marche (exclut hors range)
- [ ] Filtre surface min marche
- [ ] Filtre site marche
- [ ] Reset bouton réinitialise tous filtres
- [ ] Compteur affiche correct "N / TOTAL"

### Test 3 : Tri

- [ ] Tri site (A-Z, Z-A)
- [ ] Tri prix (croissant, décroissant)
- [ ] Tri distance (km min → max)
- [ ] Flèche ↑↓ s'affiche correctement

### Test 4 : Onglets

- [ ] Tab "Tableau" : tableau + filtres visibles
- [ ] Tab "Par ville" : groupes ville s'affichent
- [ ] Tab "Par prix" : tranches prix s'affichent
- [ ] Tab "Carte" : map Leaflet se charge, pins visibles

### Test 5 : Mobile

- [ ] Sur mobile 375px : layout responsive
- [ ] Filtres visibles et cliquables
- [ ] Tableau scrollable horizontalement
- [ ] Pas de scrollbar indésirable

### Test 6 : PWA/Offline

- [ ] manifest.json correct
- [ ] App installable sur Chrome/Firefox
- [ ] App icone visible
- [ ] Service Worker fonctionne (debug DevTools)

---

## 📚 Ressources utilisées dans code actuel

### CDN externes

```html
<!-- Bootstrap 5 CSS -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">

<!-- Bootstrap 5 JS -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<!-- Leaflet.js (Maps) -->
<link href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<!-- Chart.js (Graphiques) - PAS UTILISÉ ACTUELLEMENT -->
<!-- À ajouter : <script src="https://cdn.jsdelivr.net/npm/chart.js"></script> -->
```

### Dépendances Python

**dashboard_generator.py** :
- ✅ sqlite3 (stdlib)
- ✅ json (stdlib)
- ✅ os (stdlib)
- ✅ shutil (stdlib)
- ✅ datetime (stdlib)

**Zéro dépendance externe = parfait ! Pas besoin d'ajouter packages.**

---

## 🔑 Décisions architecturales

### 1. Pourquoi pas Flask ?

**Raison** : Philosophie PWA standalone
- ✅ Fichier HTML ouvert direct dans navigateur (file://)
- ✅ Fonctionne offline
- ✅ Zéro serveur web requis
- ✅ Déploiement ultra-simple (copy HTML)

**Flask serait pour** :
- ❌ API temps-réel (actualisations live)
- ❌ Utilisateurs multiples (auth)
- ❌ Données dynamiques (pas possible ici, on re-génère)

### 2. Pourquoi Leaflet.js et pas Google Maps ?

**Raison** :
- ✅ Open source, CDN gratuit
- ✅ Pas de clé API
- ✅ Léger (~40 Ko)
- ✅ Suffisant pour 50-100 annonces

### 3. Pourquoi pas framework JS (Vue/React) ?

**Raison** :
- ✅ Zéro build step, zéro bundler
- ✅ HTML standalone = distribution simple
- ✅ Vanilla JS + Bootstrap = assez
- ❌ Ajouter framework = 300+ Ko minifiés, trop lourd

---

## 📌 Résumé des corrections à faire

| # | Description | Priorité | Effort | Jour |
|----|------------|----------|--------|------|
| 1 | Extraire HTML dans `templates/dashboard.html` | 🔴 CRITIQUE | 1-2h | 1 |
| 2 | Modifier dashboard_generator.py pour utiliser template | 🔴 CRITIQUE | 30min | 1 |
| 3 | Supprimer dashboard.py + web_dashboard.py | 🔴 CRITIQUE | 5min | 1 |
| 4 | Intégrer dashboard_generator() dans main.py | 🔴 CRITIQUE | 30min | 2 |
| 5 | Tester génération + filtres + tri | 🔴 CRITIQUE | 1-2h | 2 |
| 6 | Implémenter comparateur | 🟠 HAUTE | 1-2h | 3 |
| 7 | Ajouter index archives | 🟠 HAUTE | 1h | 3 |
| 8 | Ajouter test_dashboard.py | 🟠 HAUTE | 1-2h | 3 |
| 9 | Ajouter graphiques (Chart.js) | 🟡 MOYENNE | 2-3h | 4 |
| 10 | Optimiser perf (pagination si > 5k) | 🟡 MOYENNE | 2h | 4 |

---

## 📞 Questions avant implémentation

1. **Fréquence génération** : Après chaque scraping ? Chaque X cycles ? Manuel ?
   → Proposé : Après chaque `check_new_listings()` si nouveautés

2. **Rétention archives** : Garder archives infinies ou nettoyer > 90 jours ?
   → Proposé : Garder 90 derniers jours

3. **Taille data** : Quand listings.db > 10 000 annonces, paginer le tableau ?
   → Proposé : Oui, 500/page avec pagination JS

4. **Comparateur** : Nécessaire pour MVP ou peut attendre ?
   → Proposé : Peut attendre Phase 3

---

## 📝 Notes de développeur

### Code actuel (dashboard_generator.py)

**Force** :
- ✅ Structure de données claire (LISTINGS, STATS)
- ✅ Onglets séparés (logique claire)
- ✅ Filtres/tri performants (côté client)
- ✅ Responsive mobile
- ✅ PWA ready (manifest + sw.js)

**Faiblesse** :
- ❌ HTML inline 450 lignes (main issue)
- ❌ Pas de tests
- ❌ Pas intégré dans bot
- ❌ Comparateur annoncé mais pas implémenté

### À ne pas changer

- ✅ Format LISTINGS/STATS (bon design)
- ✅ Structure répertoires dashboards/
- ✅ Onglets (bonne UX)
- ✅ Leaflet.js (léger, bon)

### À refactor

- ❌ Fonction generate_html() → utiliser template
- ❌ Code redondant dans 3 scripts → consolider
- ❌ Pas d'intégration main.py → ajouter

---

## 🎯 Conclusion

**État** : Dashboard fonctionnel mais non intégré et mal structuré

**Solution** :
1. ✅ Refactor HTML dans template (1-2 jours)
2. ✅ Intégrer dans main.py (1 jour)
3. ✅ Ajouter tests + nouvelles features (2-3 jours)

**Résultat final** : Dashboard auto-généré, maintainable, avec tests, toutes features.

**Timeline estimée** : 5-7 jours pour tout (Phase 1-3)

---

**Dernière mise à jour** : 2026-02-26
**Auteur** : Claude Code
**Statut** : Analyse complète, prêt pour Étape 2 (Implémentation)
