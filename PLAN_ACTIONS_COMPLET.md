# 🎯 PLAN D'ACTIONS COMPLET — Immo-Bot Luxembourg

> **Fichier central de planification**
> Quoi faire, en détail, avec le besoin et les files concernés.

---

## 🎨 Vue globale du projet

### ❓ Vos besoins

1. **Données correctes** : Prix, chambres, surface, URL, photos ✅
2. **Dates de publication** : Savoir si annonce est nouvelle (< 1h), hier, ou ancienne
3. **Dashboard** : Voir annonces triées par DATE, avec filtres (24h, 48h, 7j)
4. **Bot 2x/jour** : Lancer minimum 2 fois par jour, capturer les annonces fraîches

### ✅ Ce qu'on a créé

| Fichier créé | Rôle | Pages |
|--------------|------|-------|
| **TEST_AND_FIX_GUIDE.md** | Corriger bugs prix/chambres | 5 |
| **PUBLICATION_DATE_GUIDE.md** | Ajouter dates + fallback | 10 |
| **test_scrapers_quality.py** | Tests qualité données | 400 lignes |
| **test_price_parsing.py** | Tests parsing prix | 400 lignes |
| **scrapers_analysis.md** | Analyse 7 scrapers | 15 pages |
| **SCRAPERS_BUGS_REPORT.md** | Rapport bugs détaillé | 4 pages |
| **PLAN_ACTIONS_COMPLET.md** | **CE FICHIER** | Roadmap détaillée |

---

## 📊 DASHBOARD ACTUEL — État et corrections

### ⚠️ Problème : 3 scripts redondants

Il existe **3 dashboards** qui ne sont pas intégrés au bot principal :

| Script | Type | État | Problème |
|--------|------|------|---------|
| **dashboard_generator.py** | PWA standalone | ✅ Meilleur | HTML inline 450L, lancement manuel |
| **dashboard.py** | Console + HTML | ⚠️ Legacy | Redondant, HTML vieux |
| **web_dashboard.py** | Flask server | ❌ Non utilisé | Flask absent, jamais appelé |

**Solution** : Utiliser **dashboard_generator.py** + l'améliorer avec **published_at**

### 📋 Améliorations dashboard (Phase 3)

**À ajouter à dashboard_generator.py** :

```python
# 1. Modifier requête SQL pour inclure published_at
SELECT listing_id, site, title, city, price, rooms, surface,
       url, latitude, longitude, distance_km, created_at, published_at
FROM listings
ORDER BY published_at DESC  # ← Tri par date publication

# 2. Ajouter published_at + time_ago aux exports JSON/JS
"published_at": "2026-02-26T09:45:00",
"time_ago": "5 min",

# 3. Modifier template HTML: ajouter colonne "Publié"
<th>📅 Publié</th>
<td>${formatTime(l.time_ago)}</td>

# 4. Trier tableau par défaut par published_at DESC
listings.sort((a,b) => new Date(b.published_at) - new Date(a.published_at))
```

**À ajouter à main.py** :

```python
# Import
from dashboard_generator import generate_dashboard

# Après scraping:
def check_new_listings(self):
    # ... scraping code ...

    # À la fin: rafraîchir dashboard automatiquement
    logger.info("Rafraîchissement du dashboard...")
    generate_dashboard()  # ← Appelé automatiquement 2x/jour
```

**Résultat** :
- ✅ Dashboard rafraîchi automatiquement (2x/jour via main.py)
- ✅ Annonces triées par published_at (nouvelles en haut)
- ✅ Colonne "Publié il y a X min/h/j"
- ✅ Filtres et carte toujours disponibles

---

## 📋 Roadmap : 3 étapes principales

```
ÉTAPE 1: Corriger bugs prix/chambres (PRIORITÉ HAUTE) — 20 min
┣━ 2 bugs confirmés : VIVI + Immotop
┣━ Fichier: TEST_AND_FIX_GUIDE.md
┗━ Résultat: Données correctes

ÉTAPE 2: Ajouter dates publication (PRIORITÉ MOYENNE) — 10h
┣━ published_at pour 7 scrapers + BD + fallback
┣━ Fichier: PUBLICATION_DATE_GUIDE.md
┗━ Résultat: Chaque annonce a published_at

ÉTAPE 3: Intégrer dashboard (PRIORITÉ HAUTE) — 2h
┣━ Améliorer dashboard_generator.py
┣━ Appel automatique depuis main.py
┗━ Résultat: Dashboard rafraîchi 2x/jour, trié par date
```

**TOTAL: 12.5 heures (~1.5 jours)**

---

## 🚀 ÉTAPE 1 : Corriger bugs prix/chambres

### ❓ Pourquoi c'est critique

- Vous avez des **fausses annonces** avec prix/chambres incorrects
- 2 bugs confirmés par tests : VIVI (loyer vs charges), Immotop (€ non nettoyé)
- 4 bugs théoriques identifiés : Luxhome, Newimmo, Unicorn, Athome
- **Conséquence** : Annonces filtrées ou acceptées avec mauvaises données

### 📁 Fichiers concernés

```
scrapers/vivi_scraper_selenium.py      ← Bug #1 (VIVI): loyer vs charges
scrapers/immotop_scraper_real.py       ← Bug #2 (Immotop): € non nettoyé
scrapers/luxhome_scraper.py            ← Bug #3 (théorique): format mixte
scrapers/newimmo_scraper_real.py       ← Bug #4: décimal mixte
scrapers/unicorn_scraper_real.py       ← Bug #4: décimal mixte
scrapers/athome_scraper_json.py        ← Bug #1: prix dict imbriqué
utils.py                               ← À ajouter: parse_price_robust()

Tests:
test_price_parsing.py                  ← Valider après corrections
test_scrapers_quality.py               ← Valider avec données réelles
```

### 📋 À faire : Plan détaillé (Phase 1-3 de TEST_AND_FIX_GUIDE.md)

#### **Phase 1.1 : Corriger VIVI (Bug #1) — 5 min**

**Le bug** :
```
Texte: "Charges: 150€\nLoyer: 1250€"
Résultat: Capture 150€ au lieu de 1250€ ❌
```

**Fichier** : `scrapers/vivi_scraper_selenium.py` ligne 123-133

**Action** :
```bash
# 1. Ouvrir fichier
nano scrapers/vivi_scraper_selenium.py

# 2. Trouver section _extract_listing() ligne 123
#    Chercher boucle: for line in text.split('\n'):

# 3. Remplacer par (chercher "loyer" spécifiquement):
price = 0

# Étape 1: Chercher ligne avec "loyer"
for line in text.split('\n'):
    if '€' in line and 'loyer' in line.lower():
        price_digits = re.sub(r'[^\d]', '', line)
        if price_digits:
            try:
                price = int(price_digits)
                break
            except ValueError:
                continue

# Étape 2: Fallback si pas trouvé
if price == 0:
    for line in text.split('\n'):
        if '€' in line and not any(kw in line.lower() for kw in ['charge', 'dépôt', 'frais']):
            price_digits = re.sub(r'[^\d]', '', line)
            if price_digits:
                try:
                    price = int(price_digits)
                    if price > 100:
                        break
                except ValueError:
                    continue

# 4. Valider
python test_price_parsing.py TestPriceParsing.test_vivi_charges_before_loyer
# ✅ Attendre: PASSED

# 5. Committer
git add scrapers/vivi_scraper_selenium.py
git commit -m "Fix VIVI bug #1: chercher 'loyer' spécifiquement"
```

---

#### **Phase 1.2 : Corriger Immotop (Bug #2) — 5 min**

**Le bug** :
```
Input: "1 250€"
Traitement: int("1250€") → ValueError ❌
Résultat: Prix = 0, annonce rejetée
```

**Fichier** : `scrapers/immotop_scraper_real.py` ligne 85

**Action** :
```bash
# 1. Ouvrir fichier
nano scrapers/immotop_scraper_real.py

# 2. Trouver ligne 85 dans _scrape()
#    Chercher: price_clean = price_text.replace(' ', '')

# 3. Remplacer:
# Avant:
price_clean = price_text.replace(' ', '').replace('\u202f', '').replace(',', '')

# Après (ajouter .replace('€', '')):
price_clean = price_text.replace(' ', '').replace('\u202f', '').replace(',', '').replace('€', '')

# 4. Valider
python test_price_parsing.py TestPriceParsing.test_immotop_euro_symbol
# ✅ Attendre: PASSED

# 5. Committer
git add scrapers/immotop_scraper_real.py
git commit -m "Fix Immotop bug #2: ajouter .replace('€', '')"
```

---

#### **Phase 1.3 : Validation complète — 10 min**

**Action** :
```bash
# 1. Lancer tous les tests parsing
python test_price_parsing.py
# ✅ Attendre: 23/23 PASSED (ou au minimum 21/23)

# 2. Optionnel: Tester sur données réelles
timeout 600 python test_scrapers_quality.py --all
# ✅ Attendre: Moins d'erreurs prix

# 3. Vérifier logs
python3 << 'EOF'
from scrapers.vivi_scraper_selenium import vivi_scraper_selenium
listings = vivi_scraper_selenium.scrape()
if listings:
    print(f"✅ VIVI: {len(listings)} annonces")
    print(f"Prix range: {min(l['price'] for l in listings)} - {max(l['price'] for l in listings)}")
    print(f"Prix = 0: {len([l for l in listings if l['price'] == 0])}")
EOF

# 4. Committer validation
git add test_price_parsing.py
git commit -m "Phase 1 validated: 2 critical bugs fixed, 23/23 tests passing"

# 5. OPTIONNEL Phase 2 (robustesse): Créer parse_price_robust()
# → Voir TEST_AND_FIX_GUIDE.md Phase 2
```

---

### ✅ **Résultat Phase 1**

- ✅ Bug #1 (VIVI) corrigé
- ✅ Bug #2 (Immotop) corrigé
- ✅ Tests parsing 23/23 passants
- ✅ Annonces VIVI + Immotop : données correctes

### ⏱️ Temps total Phase 1 : **20 min**

---

## 🗓️ ÉTAPE 2 : Ajouter dates de publication

### ❓ Pourquoi c'est important

- Vous lancez bot **2x/jour minimum**
- Besoin de savoir : **"C'est une annonce nouvelle ?"**
- Sans date : impossible de filtrer les annonces fraîches
- Avec date : dashboard peut trier par date, notifier si < 1h, etc.

### 📁 Fichiers concernés

```
utils.py                              ← À ajouter: ensure_published_at()
database.py                           ← À modifier: add column published_at
scrapers/athome_scraper_json.py       ← À modifier: ajouter published_at
scrapers/immotop_scraper_real.py      ← À modifier: ajouter published_at
scrapers/luxhome_scraper.py           ← À modifier: ajouter published_at
scrapers/vivi_scraper_selenium.py     ← À modifier: ajouter published_at
scrapers/nextimmo_scraper.py          ← À modifier: ajouter published_at
scrapers/newimmo_scraper_real.py      ← À modifier: ajouter published_at
scrapers/unicorn_scraper_real.py      ← À modifier: ajouter published_at

Tests:
test_date_parsing.py                  ← À créer (valider parsing date)
test_date_quality.py                  ← À créer (valider qualité date)
```

### 📋 À faire : Plan détaillé (Phase 1-7 de PUBLICATION_DATE_GUIDE.md)

#### **Phase 2.1 : Analyser sources date — 2h**

**Objectif** : Savoir où est la date dans chaque scraper

**Action** :
```bash
# Pour chaque scraper, tester manuellement

# 1. ATHOME
python3 << 'EOF'
from scrapers.athome_scraper_json import athome_scraper_json
import json
listings = athome_scraper_json.scrape()
if listings:
    print("=== ATHOME ===")
    item = listings[0]
    print(f"Clés disponibles: {list(item.keys())}")
    # Chercher clé date: publishDate, createdAt, timestamp, time_ago
    for key in ['publishDate', 'createdAt', 'timestamp', 'time_ago', 'date', 'created']:
        if key in item:
            print(f"✅ TROUVÉ: {key} = {item[key]}")
EOF

# 2. NEXTIMMO
python3 << 'EOF'
from scrapers.nextimmo_scraper import nextimmo_scraper
import json
listings = nextimmo_scraper.scrape()
if listings:
    print("=== NEXTIMMO ===")
    item = listings[0]
    print(f"Clés disponibles: {list(item.keys())}")
    for key in ['createdAt', 'publishedAt', 'timestamp', 'date', 'published', 'created']:
        if key in item:
            print(f"✅ TROUVÉ: {key} = {item[key]}")
EOF

# 3-7. Même chose pour IMMOTOP, LUXHOME, VIVI, NEWIMMO, UNICORN

# Résultat attendu: Document "DATE_SOURCES.txt" listant clé + format
# Ex:
# Athome: publishDate (ISO 8601)
# Nextimmo: createdAt (ISO 8601)
# Immotop: time_ago (texte "il y a 2h")
# VIVI: datetime attribute dans HTML
# etc.
```

**Résultat** : Créer `DATE_SOURCES.txt` avec tableau récapitulatif

---

#### **Phase 2.2 : Créer fonctions utilitaires — 1h**

**Fichier** : `utils.py`

**Action** :
```bash
# 1. Ajouter à la fin de utils.py :

cat >> utils.py << 'EOF'

# ===== DATE PARSING =====
from datetime import datetime, timedelta

def ensure_published_at(published_at=None):
    """
    ⭐ FONCTION CRITIQUE
    Garantir que published_at JAMAIS None.
    Fallback central pour tous les scrapers.
    """
    if published_at is None:
        return datetime.now()
    if not isinstance(published_at, datetime):
        return datetime.now()
    now = datetime.now()
    if published_at > now:
        return now  # Correction futur
    return published_at

def parse_relative_date(text):
    """Parser "il y a X jours" → datetime"""
    if not text:
        return None
    text_lower = text.lower()

    if 'récemment' in text_lower or 'aujourd' in text_lower:
        return datetime.now()

    match = re.search(r'(\d+)\s*(?:heure|jour|semaine|mois)s?', text_lower)
    if match:
        number = int(match.group(1))
        if 'heure' in match.group(0):
            return datetime.now() - timedelta(hours=number)
        elif 'jour' in match.group(0):
            return datetime.now() - timedelta(days=number)
        elif 'semaine' in match.group(0):
            return datetime.now() - timedelta(weeks=number)
        elif 'mois' in match.group(0):
            return datetime.now() - timedelta(days=number*30)
    return None

def parse_iso_date(date_str):
    """Parser ISO 8601 (ex: "2026-02-26T09:45:00Z")"""
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        return None

def parse_absolute_date(date_str, format_str="%d/%m/%Y"):
    """Parser date absolue (ex: "26/02/2026")"""
    try:
        return datetime.strptime(date_str, format_str)
    except:
        return None
EOF

# 2. Tester
python3 << 'EOF'
from utils import ensure_published_at, parse_relative_date, parse_iso_date
from datetime import datetime

tests = [
    (ensure_published_at(None), datetime.now(), "Fallback None"),
    (parse_relative_date("il y a 2 heures"), lambda: datetime.now() - timedelta(hours=2), "Relative 2h"),
    (parse_iso_date("2026-02-26T09:45:00Z"), datetime(2026, 2, 26, 9, 45), "ISO date"),
]

print("✅ Fonctions date créées dans utils.py")
EOF

# 3. Committer
git add utils.py
git commit -m "Phase 2.2: Add date parsing functions (ensure_published_at, parse_*)"
```

---

#### **Phase 2.3 : Modifier base de données — 30 min**

**Fichier** : `database.py`

**Action** :
```bash
# 1. Ajouter colonne published_at dans init_db()
nano database.py

# Chercher: CREATE TABLE IF NOT EXISTS listings (
# Ajouter après notified:
    published_at TIMESTAMP,  # ← NOUVELLE

# Ajouter index:
self.cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_published_at
    ON listings(published_at)
''')

# 2. Modifier add_listing() pour accepter published_at
# Chercher: def add_listing(self, listing_data):
# Modifier INSERT pour inclure published_at

# Avant:
INSERT INTO listings
(listing_id, site, title, city, price, rooms, surface, url, latitude, longitude, distance_km)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

# Après:
INSERT INTO listings
(listing_id, site, title, city, price, rooms, surface, url, latitude, longitude, distance_km, published_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

# Ajouter dans VALUES tuple:
listing_data.get('published_at')  # ← À la fin

# 3. Ajouter méthode get_listings_by_date()
# Voir code dans PUBLICATION_DATE_GUIDE.md section "Nouvelle méthode pour query par date"

# 4. Tester
python3 << 'EOF'
from database import Database
db = Database()
print("✅ Database schéma mis à jour")
EOF

# 5. Migrate DB existante (optionnel)
sqlite3 listings.db << 'EOF'
ALTER TABLE listings ADD COLUMN published_at TIMESTAMP;
CREATE INDEX idx_published_at ON listings(published_at);
EOF

# 6. Committer
git add database.py
git commit -m "Phase 2.3: Add published_at column + index to DB"
```

---

#### **Phase 2.4 : Modifier 7 scrapers — 3h (30 min chacun)**

**Pattern pour tous les scrapers** :

```python
# Au début du fichier scraper, ajouter import:
from utils import ensure_published_at, parse_relative_date, parse_iso_date
from datetime import datetime

# Dans _extract_listing() ou équivalent, À LA FIN avant return:

# Étape 1: Chercher date de publication
published_at = None
# [Code spécifique au scraper pour extraire date]

# Étape 2: FALLBACK GARANTI
published_at = ensure_published_at(published_at)

# Dans return dict:
'published_at': published_at  # ← JAMAIS None
```

**Action par scraper** :

```bash
# 1. NEXTIMMO (API propre, easy) — 20 min
nano scrapers/nextimmo_scraper.py
# Dans _extract_from_json(), avant return:
# Chercher: createdAt ou publishedAt dans item
# Code exemple:
date_str = item.get('createdAt') or item.get('publishedAt')
published_at = None
if date_str:
    published_at = parse_iso_date(date_str)
published_at = ensure_published_at(published_at)
# Ajouter au return: 'published_at': published_at

# 2. IMMOTOP (texte visible) — 20 min
nano scrapers/immotop_scraper_real.py
# Dans scrape(), chercher texte "il y a X jours"
# Utiliser parse_relative_date()

# 3. VIVI (Selenium + HTML) — 20 min
nano scrapers/vivi_scraper_selenium.py
# Dans _extract_listing(), chercher <time> ou attribut data-date

# 4. ATHOME (JSON) — 20 min
nano scrapers/athome_scraper_json.py
# Chercher publishDate, createdAt, timestamp dans item

# 5. LUXHOME (JSON/regex) — 15 min
nano scrapers/luxhome_scraper.py
# Chercher clé date dans regex match

# 6. NEWIMMO (regex HTML) — 15 min
nano scrapers/newimmo_scraper_real.py
# Chercher "Publié le DD/MM/YYYY" dans contexte

# 7. UNICORN (regex HTML) — 15 min
nano scrapers/unicorn_scraper_real.py
# Chercher <time> ou "depuis X jours"

# Après chaque modification:
python test_price_parsing.py  # Vérifier parsing OK
python3 << 'EOF'
from scrapers.xxx_scraper import xxx_scraper
listings = xxx_scraper.scrape()
if listings:
    print(f"✅ {len(listings)} listings avec published_at")
    print(f"Sample: {listings[0].get('published_at')}")
EOF

# Committer par scraper
git add scrapers/xxx_scraper.py
git commit -m "Phase 2.4: Add published_at extraction to xxx_scraper"
```

---

#### **Phase 2.5-2.7 : Tests + Validation**

```bash
# Phase 2.5: Tests qualité (1h)
python test_date_quality.py  # À créer
# Vérifier: tous les listings ont published_at
# Vérifier: published_at <= now()
# Vérifier: pas de dates trop anciennes (> 30j)

# Phase 2.6: Dashboard (2h)
# Créer dashboard.py avec:
# - get_listings_by_date(hours=24)
# - HTML table triée par date décroissante
# - Filter buttons: 24h, 48h, 7j

# Phase 2.7: Validation finale (30 min)
git status
sqlite3 listings.db "SELECT COUNT(*), COUNT(published_at) FROM listings;"
# ✅ Tous les listings ont published_at
```

---

### ✅ **Résultat Phase 2**

- ✅ Fonction `ensure_published_at()` en utils.py
- ✅ BD + colonne `published_at` + index
- ✅ 7 scrapers modi avec extraction date + fallback
- ✅ Dashboard affichant annonces triées par date
- ✅ Filtres : 24h, 48h, 7 jours

### ⏱️ Temps total Phase 2 : **10 heures**

---

## 📊 ÉTAPE 3 : Intégrer et améliorer dashboard

### ❓ Pourquoi c'est utile

- Dashboard **existant** (dashboard_generator.py) — le meilleur des 3
- Améliorer avec **published_at** (dates de publication)
- Appel **automatique** depuis main.py (2x/jour)
- Vue centralisée, triée par date, avec filtres

### 📁 Fichiers concernés

```
dashboard_generator.py     ← À modifier (ajouter published_at)
main.py                    ← À modifier (appel automatique)
dashboards/index.html      ← Sera régénéré
dashboards/data/
├── listings.js            ← Inclura published_at
└── listings.json
```

### 📋 À faire : Plan détaillé

#### **Phase 3.1 : Améliorer dashboard_generator.py**

```python
# Créer fichier: dashboard.py

from database import db
from datetime import datetime, timedelta

def get_dashboard_listings(filter_hours=24):
    """Récupérer annonces pour dashboard"""
    listings = db.get_listings_by_date(hours=filter_hours, limit=100)

    result = []
    for listing in listings:
        listing_id, site, title, city, price, published_at = listing

        # Calculer temps écoulé
        if published_at:
            delta = datetime.now() - published_at
            if delta.total_seconds() < 60:
                time_str = "À l'instant"
            elif delta.total_seconds() < 3600:
                time_str = f"{int(delta.total_seconds() / 60)} min"
            elif delta.total_seconds() < 86400:
                time_str = f"{int(delta.total_seconds() / 3600)}h"
            else:
                time_str = f"{int(delta.total_seconds() / 86400)} j"
        else:
            time_str = "N/A"

        result.append({
            'listing_id': listing_id,
            'site': site,
            'title': title,
            'city': city,
            'price': price,
            'published_at': published_at,
            'time_str': time_str,
        })

    return result

def render_html(filter_hours=24):
    """Générer HTML du dashboard"""
    listings = get_dashboard_listings(filter_hours)

    html = f"""
    <html>
    <head>
        <title>Immo-Bot Dashboard</title>
        <link rel="stylesheet" href="dashboard_style.css">
    </head>
    <body>
        <h1>📊 Dashboard Annonces Immobilières</h1>

        <div class="filters">
            <a href="?filter=24" class="{'active' if filter_hours == 24 else ''}">24h</a>
            <a href="?filter=48" class="{'active' if filter_hours == 48 else ''}">48h</a>
            <a href="?filter=168" class="{'active' if filter_hours == 168 else ''}">7 jours</a>
        </div>

        <table class="listings">
            <thead>
                <tr>
                    <th>📅 Publié</th>
                    <th>Site</th>
                    <th>Titre</th>
                    <th>Ville</th>
                    <th>💰 Prix</th>
                </tr>
            </thead>
            <tbody>
    """

    for listing in listings:
        html += f"""
                <tr class="site-{listing['site'].lower().replace('.', '')}">
                    <td><span title="{listing['published_at']}">{listing['time_str']}</span></td>
                    <td>{listing['site']}</td>
                    <td>{listing['title']}</td>
                    <td>{listing['city']}</td>
                    <td>{listing['price']}€</td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return html
```

---

#### **Phase 3.2 : Créer dashboard_style.css**

```css
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
    background-color: #f5f5f5;
}

h1 {
    color: #333;
    text-align: center;
    border-bottom: 3px solid #007bff;
    padding-bottom: 10px;
}

.filters {
    margin: 20px 0;
    text-align: center;
}

.filters a {
    padding: 10px 20px;
    margin: 0 5px;
    background: #f0f0f0;
    text-decoration: none;
    border-radius: 4px;
    color: #333;
    transition: all 0.3s;
}

.filters a.active {
    background: #007bff;
    color: white;
    font-weight: bold;
}

table.listings {
    width: 100%;
    border-collapse: collapse;
    background: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-radius: 4px;
    overflow: hidden;
}

table.listings th {
    background: #007bff;
    color: white;
    padding: 15px;
    text-align: left;
    font-weight: bold;
}

table.listings td {
    padding: 12px 15px;
    border-bottom: 1px solid #eee;
}

table.listings tr:hover {
    background: #f9f9f9;
}

/* Highlight nouvelles annonces (< 1h) */
table.listings tr:has(td:first-child span[title*="202"]) {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
}

/* Colorer par site */
tr.site-athomelulocalStorage { border-left: 4px solid #004E89; }
tr.site-immotoplulocalStorage { border-left: 4px solid #FF6B35; }
tr.site-luxhomelulocalStorage { border-left: 4px solid #118AB2; }
tr.site-vivilulocalStorage { border-left: 4px solid #A23B72; }
tr.site-nextimmolulocalStorage { border-left: 4px solid #073B4C; }
tr.site-newimlolulocalStorage { border-left: 4px solid #006E90; }
tr.site-unicornlulocalStorage { border-left: 4px solid #F77F00; }
```

---

#### **Phase 3.3 : Intégrer dans main.py**

```bash
# Modifier main.py pour ajouter route dashboard

# À ajouter:
from dashboard import render_html
from flask import Flask, request

app = Flask(__name__)

@app.route('/dashboard')
def dashboard():
    filter_hours = int(request.args.get('filter', 24))
    return render_html(filter_hours)

# Optionnel: afficher aussi dans logs
def check_new_listings():
    listings = dashbaord.get_dashboard_listings(hours=1)  # < 1h
    logger.info(f"🆕 {len(listings)} annonces dans dernière heure")
```

---

### ✅ **Résultat Phase 3**

- ✅ Dashboard HTML affichant annonces triées par date
- ✅ Filtres : 24h, 48h, 7 jours
- ✅ Highlighting annonces récentes (< 1h)
- ✅ Styling professionnel

### ⏱️ Temps total Phase 3 : **3 heures**

---

## 📅 Timeline complète

```
LUNDI:
  ├─ Matin (1h) : Corriger bugs VIVI + Immotop
  ├─ Après-midi (1.5h) : Lancer tests qualité
  └─ Total : 2.5h → Phase 1 COMPLÈTE ✅

MARDI + MERCREDI:
  ├─ 2h : Analyser sources date (Phase 2.1)
  ├─ 1h : Créer fonctions date (Phase 2.2)
  ├─ 30min : Modifier BD (Phase 2.3)
  ├─ 3h : Modifier 7 scrapers (Phase 2.4)
  ├─ 2.5h : Tests + Validation (2.5-2.7)
  └─ Total : 10h → Phase 2 COMPLÈTE ✅

JEUDI:
  ├─ 1h : Créer dashboard.py
  ├─ 30min : CSS styling
  ├─ 30min : Intégrer main.py
  ├─ 1h : Tests finaux
  └─ Total : 3h → Phase 3 COMPLÈTE ✅

TOTAL: 15.5 heures (~2 jours complets)
```

---

## 🎁 Résultat final

### Dashboard avec annonces triées par date

```
📊 Immo-Bot Dashboard

[Filtres: 24h | 48h | 7j]

| 📅 Publié | Site     | Titre                      | Ville       | Prix  |
|-----------|----------|--------------------------|-------------|-------|
| 5 min    | Athome   | 2ch, 75m², lumineux       | Luxembourg  | 1250€ |
| 45 min   | Nextimmo | 3ch, 90m², proche train   | Esch        | 1800€ |
| 2h       | VIVI     | 2ch, 80m², balcon         | Differdange | 1500€ |
| 8h       | Luxhome  | 1ch, 45m², calme          | Dudelange   | 900€  |
| 1j       | Immotop  | 2ch, 65m², parking incl   | Luxembourg  | 1400€ |
```

### Notification Telegram enrichie

```
🏠 Nouvelle annonce!
   Publiée il y a 5 minutes ⏰

📌 2 chambres, 1250€/mois
   75 m², Luxembourg

🔗 Athome.lu
```

---

## 💾 Commandes récapitulatif

```bash
# Phase 1: Bugs prix (20 min)
nano scrapers/vivi_scraper_selenium.py      # Fix loyer vs charges
nano scrapers/immotop_scraper_real.py       # Fix € symbol
python test_price_parsing.py                # Valider
git commit -m "Phase 1: Fix price bugs"

# Phase 2: Dates (10h)
nano utils.py                               # Add date functions
nano database.py                            # Add published_at column
# For each of 7 scrapers:
nano scrapers/xxx_scraper.py                # Add published_at
python test_date_quality.py                 # Valider
git commit -m "Phase 2: Add publication dates"

# Phase 3: Dashboard (3h)
cat > dashboard.py << 'EOF'...             # Create dashboard
cat > dashboard_style.css << 'EOF'...      # Create CSS
nano main.py                               # Add /dashboard route
git commit -m "Phase 3: Create dashboard"

# Final
git log --oneline -10                      # Vérifier commits
git push origin claude/dashboard-analysis-docs-FLiRU
```

---

## 🚀 Commencer maintenant

### Option A : Faire tout (15.5h)
```
Jour 1: Phase 1 (bugs prix) + Phase 2 (dates)
Jour 2: Phase 3 (dashboard)
Résultat: Système complet
```

### Option B : Faire progressivement
```
Semaine 1: Phase 1 (corriger bugs)
Semaine 2: Phase 2 (ajouter dates)
Semaine 3: Phase 3 (créer dashboard)
```

### Option C : Prioriser urgent
```
Urgent: Phase 1 (20 min) — Corriger fausses données
Ensuite: Phase 2 (10h) — Ajouter dates
Optionnel: Phase 3 (3h) — Dashboard (peut rester simple)
```

---

## 📞 Questions fréquentes

**Q: Par où commencer ?**
A: Phase 1 (20 min) pour corriger bugs, puis Phase 2 (10h) pour dates.

**Q: Et si je n'ai pas 15h ?**
A: Phase 1 seul (20 min) donne déjà des données correctes.

**Q: Comment valider chaque phase ?**
A: Tests fournis : test_price_parsing.py, test_date_quality.py, etc.

**Q: Puis-je faire phases 1+2 en parallèle ?**
A: Oui, mais Phase 1 d'abord (plus rapide et urgent).

---

**Créé** : 2026-02-26
**Dernière mise à jour** : 2026-02-26
**Statut** : Prêt pour exécution

