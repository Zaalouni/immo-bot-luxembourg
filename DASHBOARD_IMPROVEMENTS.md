# 🎨 Dashboard Improvements — Corrections détaillées

> **Fichier technique** : Comment améliorer et intégrer le dashboard existant
> avec support des dates de publication

---

## 📊 État actuel du dashboard

### 3 scripts redondants

```
✅ dashboard_generator.py (676 loc) — MEILLEUR, à utiliser
   ├─ Reads listings.db
   ├─ Exports JSON + JS + HTML
   ├─ Génère PWA standalone (offline)
   ├─ 5 onglets: Tableau, Villes, Prix, Carte, Stats
   └─ Problème: HTML inline 450L, lancement manuel

⚠️ dashboard.py (350 loc) — LEGACY
   ├─ Console dashboard
   ├─ Export JSON/CSV
   └─ Redondant avec dashboard_generator

❌ web_dashboard.py (475 loc) — NON UTILISÉ
   ├─ Flask server (Flask absent)
   ├─ Templates/dashboard.html (jamais utilisé)
   └─ Pas intégré au bot
```

---

## 🔧 Phase 3 : Corrections détaillées

### Modification 1 : dashboard_generator.py (requête SQL)

**Fichier** : `dashboard_generator.py`

**Avant** (sans published_at) :
```python
cursor.execute('''
    SELECT id, listing_id, site, title, city, price, rooms, surface,
           url, image_url, latitude, longitude, distance_km, created_at
    FROM listings
    ORDER BY id DESC
''')
listings = cursor.fetchall()
```

**Après** (avec published_at) :
```python
cursor.execute('''
    SELECT id, listing_id, site, title, city, price, rooms, surface,
           url, image_url, latitude, longitude, distance_km, created_at,
           published_at
    FROM listings
    ORDER BY published_at DESC
''')
listings = cursor.fetchall()
```

**Changements** :
- ✅ Ajouter `published_at` à la requête SELECT
- ✅ Trier par `published_at DESC` (nouvelles en haut)
- ✅ Si `published_at` est NULL → trier par `created_at`

---

### Modification 2 : Fonction time_ago (nouveau)

**À ajouter à dashboard_generator.py** :

```python
from datetime import datetime, timedelta

def calculate_time_ago(published_at):
    """
    Convertir timestamp en "il y a X..."

    Args:
        published_at: datetime ou None

    Returns:
        str: "À l'instant", "5 min", "2h", "1 j", etc.
    """
    if not published_at:
        return "N/A"

    # Gérer type (string ISO ou datetime)
    if isinstance(published_at, str):
        try:
            published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        except:
            return "N/A"

    delta = datetime.now() - published_at
    seconds = delta.total_seconds()

    if seconds < 60:
        return "À l'instant"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} min"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h"
    elif seconds < 604800:  # 7 jours
        days = int(seconds / 86400)
        return f"{days}j"
    else:
        # Afficher date complète si > 7j
        date_str = published_at.strftime("%d/%m/%Y")
        return f"{date_str}"
```

---

### Modification 3 : Export JSON avec published_at

**Avant** :
```python
def export_to_json(listings, filename='dashboards/data/listings.json'):
    data = []
    for listing in listings:
        item = {
            'listing_id': listing[1],
            'site': listing[2],
            'title': listing[3],
            # ... autres champs ...
            'created_at': listing[-1],  # dernière colonne
        }
        data.append(item)

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
```

**Après** :
```python
def export_to_json(listings, filename='dashboards/data/listings.json'):
    data = []
    for listing in listings:
        published_at = listing[-1]  # Dernière colonne (nouvellement ajoutée)

        item = {
            'listing_id': listing[1],
            'site': listing[2],
            'title': listing[3],
            # ... autres champs ...
            'created_at': listing[-2],  # Avant-dernière colonne
            'published_at': published_at.isoformat() if published_at else None,
            'time_ago': calculate_time_ago(published_at),
        }
        data.append(item)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
```

---

### Modification 4 : Export JS avec published_at

**Avant** :
```python
def export_to_js(listings):
    # Construire tableau JavaScript
    js_content = "const LISTINGS = [\n"
    for listing in listings:
        js_content += f"""
  {{
    listing_id: '{listing[1]}',
    site: '{listing[2]}',
    title: '{escape_js(listing[3])}',
    ...
    created_at: '{listing[-1]}',
  }},
"""
    js_content += "]\n"
    # Écrire dashboards/data/listings.js
```

**Après** :
```python
def export_to_js(listings):
    # Construire tableau JavaScript avec published_at
    js_content = "const LISTINGS = [\n"
    for listing in listings:
        published_at = listing[-1]
        time_ago = calculate_time_ago(published_at)

        js_content += f"""
  {{
    listing_id: '{listing[1]}',
    site: '{listing[2]}',
    title: '{escape_js(listing[3])}',
    ...
    created_at: '{listing[-2]}',
    published_at: '{published_at.isoformat() if published_at else ""}',
    time_ago: '{time_ago}',
  }},
"""
    js_content += "]\n"
```

---

### Modification 5 : Template HTML — Ajouter colonne

**Où trouver le template HTML** :

Dans `dashboard_generator.py`, il y a une longue f-string (ligne ~180-620) contenant le HTML inline.

**Avant** (exemple de structure table) :
```html
<table class="table table-striped table-sm">
  <thead>
    <tr>
      <th>ID</th>
      <th>Site</th>
      <th>Titre</th>
      <th>Ville</th>
      <th>Prix</th>
      <th>Chambres</th>
      <th>Surface</th>
      ...
    </tr>
  </thead>
  <tbody id="listings-table">
  </tbody>
</table>
```

**Après** (ajouter colonne "Publié") :
```html
<table class="table table-striped table-sm">
  <thead>
    <tr>
      <th onclick="sortTable(0)">📅 Publié</th>  ← NOUVELLE COLONNE
      <th>ID</th>
      <th>Site</th>
      <th>Titre</th>
      <th>Ville</th>
      <th>Prix</th>
      <th>Chambres</th>
      <th>Surface</th>
      ...
    </tr>
  </thead>
  <tbody id="listings-table">
  </tbody>
</table>
```

---

### Modification 6 : JavaScript — Remplir colonne

**Avant** (template ligne de tableau) :
```javascript
function renderListings(listings) {
    const tbody = document.getElementById('listings-table');
    tbody.innerHTML = '';

    listings.forEach((l, index) => {
        const row = tbody.insertRow();
        row.insertCell().textContent = l.listing_id;
        row.insertCell().textContent = l.site;
        row.insertCell().textContent = l.title;
        row.insertCell().textContent = l.city;
        row.insertCell().textContent = `${l.price}€`;
        // ...
    });
}
```

**Après** (ajouter colonne published_at en première position) :
```javascript
function renderListings(listings) {
    const tbody = document.getElementById('listings-table');
    tbody.innerHTML = '';

    listings.forEach((l, index) => {
        const row = tbody.insertRow();

        // Nouvelle colonne: Publié (TIME AGO)
        const timeCell = row.insertCell();
        timeCell.textContent = l.time_ago || 'N/A';
        // Highlight si < 1h
        if (l.time_ago && (l.time_ago.includes('min') || l.time_ago === 'À l\'instant')) {
            timeCell.classList.add('badge', 'bg-warning', 'text-dark');
        }

        // Autres colonnes (comme avant)
        row.insertCell().textContent = l.listing_id;
        row.insertCell().textContent = l.site;
        row.insertCell().textContent = l.title;
        row.insertCell().textContent = l.city;
        row.insertCell().textContent = `${l.price}€`;
        // ...
    });
}
```

---

### Modification 7 : Tri par published_at

**Avant** (tri par défaut) :
```javascript
// Au chargement du dashboard
const listings = LISTINGS.sort((a, b) => b.id - a.id);  // Tri par ID DESC
renderListings(listings);
```

**Après** (tri par published_at DESC) :
```javascript
// Au chargement du dashboard
const listings = LISTINGS.sort((a, b) => {
    if (!a.published_at || !b.published_at) {
        // Si pas de published_at, fallback à created_at
        return new Date(b.created_at) - new Date(a.created_at);
    }
    return new Date(b.published_at) - new Date(a.published_at);  // DESC
});
renderListings(listings);
```

---

### Modification 8 : Intégration dans main.py

**Fichier** : `main.py`

**Ajouter import** :
```python
import logging
from database import db
import dashboard_generator  # ← AJOUTER

logger = logging.getLogger(__name__)
```

**Modifier ImmoBot.check_new_listings()** :

**Avant** :
```python
def check_new_listings(self):
    """Lancer les scrapers et notifier"""
    logger.info("🔍 Lancement des scrapers...")

    all_listings = []
    for scraper in self.scrapers:
        listings = scraper.scrape()
        all_listings.extend(listings)

    # ... dedup, filtrage, notif ...

    logger.info(f"✅ Total: {len(new_listings)} annonces trouvées")
```

**Après** (ajouter dashboard refresh) :
```python
def check_new_listings(self):
    """Lancer les scrapers, notifier, et rafraîchir dashboard"""
    logger.info("🔍 Lancement des scrapers...")

    all_listings = []
    for scraper in self.scrapers:
        listings = scraper.scrape()
        all_listings.extend(listings)

    # ... dedup, filtrage, notif ...

    logger.info(f"✅ Total: {len(new_listings)} annonces trouvées")

    # ✅ NOUVEAU: Rafraîchir le dashboard
    logger.info("🎨 Génération du dashboard...")
    try:
        dashboard_generator.generate_dashboard()
        logger.info("✅ Dashboard rafraîchi (/dashboards/index.html)")
    except Exception as e:
        logger.warning(f"⚠️ Erreur génération dashboard: {e}")
        # Continue même si dashboard échoue
```

---

## 🚀 Résumé des modifications

| # | Fichier | Modification | Impact |
|----|---------|--------------|--------|
| 1 | dashboard_generator.py | Ajouter published_at à la requête SQL | Tri par date publication |
| 2 | dashboard_generator.py | Créer fonction calculate_time_ago() | Conversion timestamp en "5 min", "2h" |
| 3 | dashboard_generator.py | Ajouter published_at à export JSON | Données JSON complètes |
| 4 | dashboard_generator.py | Ajouter published_at à export JS | Variable LISTINGS inclut published_at |
| 5 | dashboard_generator.py | Template HTML: ajouter colonne "Publié" | Colonne visible dans tableau |
| 6 | dashboard_generator.py | JavaScript: remplir colonne time_ago | Afficher "5 min", "2h", etc. |
| 7 | dashboard_generator.py | Modifier tri (published_at DESC) | Nouvelles annonces en haut |
| 8 | main.py | Ajouter appel dashboard_generator.generate_dashboard() | Rafraîchir 2x/jour automatiquement |

---

## ✅ Checklist de validation

### Avant modifications
- [ ] Lire ce fichier complètement
- [ ] Lire PUBLICATION_DATE_GUIDE.md (Phase 2 : ajouter published_at à BD + scrapers)
- [ ] Vérifier que published_at existe en BD
- [ ] Vérifier que tous les scrapers retournent published_at

### Pendant modifications
- [ ] Modifier dashboard_generator.py (SQL + functions + exports + template)
- [ ] Modifier main.py (ajouter import + appel automatique)
- [ ] Tester: `python dashboard_generator.py`
- [ ] Vérifier: `ls -lh dashboards/index.html` (fichier généré avec published_at)

### Après modifications
- [ ] Ouvrir `dashboards/index.html` dans navigateur
- [ ] Vérifier colonne "Publié" affiche "5 min", "2h", etc.
- [ ] Vérifier tri par défaut: nouvelles annonces en haut
- [ ] Vérifier filtres fonctionnent (tableau, villes, prix, carte, stats)
- [ ] Lancer main.py et vérifier logs: "✅ Dashboard rafraîchi"
- [ ] Vérifier `dashboards/data/listings.json` contient published_at

### Production (2x/jour)
- [ ] Bot lancé 2x/jour
- [ ] Dashboard ré-généré automatiquement
- [ ] Archive quotidienne créée (`dashboards/archives/2026-02-26.html`)
- [ ] Historique JSON gardé (`dashboards/data/history/`)

---

## 📂 Résultat final

**Structure répertoires** :
```
dashboards/
├── index.html                    ← Dashboard rafraîchi 2x/jour ✅
├── data/
│   ├── listings.js               ← Inclut published_at, time_ago
│   ├── listings.json             ← Inclut published_at, time_ago
│   └── history/
│       └── 2026-02-26.json       ← Archive quotidienne
├── archives/
│   ├── 2026-02-26.html           ← Snapshot du jour
│   ├── 2026-02-25.html           ← Snapshot hier
│   └── ...
├── manifest.json                 ← PWA
└── sw.js                         ← Service Worker (offline)
```

**Dashboard visuel** :
```
📊 Immo-Bot Dashboard — Annonces Immobilières

[Filtres: Ville | Prix | Surface | Site]

| 📅 PUBLIÉ  | SITE     | TITRE                 | VILLE        | 💰 PRIX |
|------------|----------|----------------------|--------------|---------|
| À l'instant| Athome   | 2ch, 75m², lumineux  | Luxembourg   | 1250€   |
| 5 min     | Nextimmo | 3ch, 90m², balcon    | Esch         | 1800€   |
| 2h        | VIVI     | 2ch, 80m², balcon    | Differdange  | 1500€   |
| 1j        | Luxhome  | 1ch, 45m², calme     | Dudelange    | 900€    |

[Tableau | Villes | Prix | Carte | Stats]
```

---

**Créé** : 2026-02-26
**Fichier technique** : Corrections dashboard détaillées
**Statut** : Prêt pour intégration Phase 3

