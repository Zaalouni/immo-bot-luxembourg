# 📅 Guide : Récupérer la date de publication des annonces

> **Analyse complète** : Comment récupérer la date de publication pour chaque scraper
> et l'intégrer dans le dashboard pour filtrer les annonces par date.

---

## 📋 Table des matières

1. [Contexte et importance](#contexte-et-importance)
2. [État actuel : analyse des 7 scrapers](#état-actuel--analyse-des-7-scrapers)
3. [Stratégies de récupération par scraper](#stratégies-de-récupération-par-scraper)
4. [Modifications à la base de données](#modifications-à-la-base-de-données)
5. [Modifications aux scrapers](#modifications-aux-scrapers)
6. [Intégration dans le dashboard](#intégration-dans-le-dashboard)
7. [Plan d'exécution (étapes)](#plan-dexécution-étapes)

---

## Contexte et importance

### Pourquoi la date est CRITIQUE

Vous lancez le bot **2 fois par jour minimum** → besoin de savoir :
- ✅ **Annonce publiée ce matin ?** (nouvelle, intéressante)
- ✅ **Annonce publiée hier ?** (légèrement moins fraîche)
- ❌ **Annonce publiée il y a 2 semaines ?** (probablement pourvue ou obsolète)

### Cas d'usage dans le dashboard

```
Tableau annonces triées par DATE DÉCROISSANTE:

📅 2026-02-26 09:45 | Athome | 2ch, 1250€ | Luxembourg | ✨ NOUVELLE
📅 2026-02-26 08:15 | Nextimmo | 3ch, 1800€ | Esch | ✨ NOUVELLE
📅 2026-02-25 19:30 | VIVI | 2ch, 1500€ | Differdange | Hier
📅 2026-02-25 14:20 | Luxhome | 1ch, 900€ | Dudelange | Hier
📅 2026-02-24 10:00 | Immotop | 2ch, 1400€ | Luxembourg | 2 jours
```

### Stratégie robuste avec fallback

**Approche à 2 niveaux** (très fiable) :

```
Niveau 1: Chercher date de publication du site
├─ Si trouvée et valide → utiliser
├─ Si format incohérent ou future → rejeter
└─ Si non trouvée → Niveau 2

Niveau 2: Fallback à date d'extraction
├─ published_at = extraction_at (heure du scraping)
└─ C'est la date MINIMALE sûre
```

### Données disponibles

- **Option 1** (Préféré) : Date de publication récupérée du site
- **Option 2** (Fallback fiable) : Date d'extraction de l'annonce = `datetime.now()` au moment du scraping

### Problème et solution

**Problème** :
- Parfois la date est visible dans le texte ("Il y a 2h")
- Parfois elle est dans un attribut JSON
- Parfois elle est complètement absente ❌

**Solution** :
- ✅ Toujours avoir un fallback à la date du scraping
- ✅ Chaque annonce aura UNE date (même si approximée)
- ✅ Pour le dashboard : published_at <= now() toujours

---

## État actuel : analyse des 7 scrapers

### Résumé rapide

| Scraper | Date publi | Format | Récupération | Sévérité | Effort |
|---------|-----------|--------|---------------|----------|--------|
| **Athome.lu** | ❓ Inconnue | ? | À analyser | 🔴 CRITIQUE | Moyen |
| **Immotop.lu** | ✅ Disponible | Text (ex: "il y a 2j") | Parsing texte | 🟠 MOYENNE | Petit |
| **Luxhome.lu** | ❓ Inconnue | ? | À analyser | 🔴 CRITIQUE | Moyen |
| **VIVI.lu** | ✅ Probable | Selenium | Trouver en HTML | 🟠 MOYENNE | Moyen |
| **Nextimmo.lu** | ✅ API | JSON (timestamp?) | À analyser | 🟢 BON | Petit |
| **Newimmo.lu** | ❓ Inconnue | ? | À analyser | 🔴 CRITIQUE | Moyen |
| **Unicorn.lu** | ❓ Inconnue | ? | À analyser | 🔴 CRITIQUE | Moyen |

---

## Stratégies de récupération par scraper

### 1️⃣ Athome.lu

**Scraper** : `scrapers/athome_scraper_json.py`

**Analyse** :
```python
# JSON __INITIAL_STATE__ peut contenir:
item = {
    'id': 123,
    'price': 1250,
    'publishDate': '2026-02-26T09:45:00Z',  # ← À chercher?
    'createdAt': '2026-02-26T09:45:00Z',   # ← À chercher?
    'timestamp': 1708934700,                # ← À chercher?
    'time_ago': 'Il y a 2 heures',         # ← Parsing texte?
}
```

**Actions nécessaires** :
1. ✅ Vérifier JSON pour clé `publishDate`, `createdAt`, `timestamp`, ou `time_ago`
2. ✅ Si trouvé : extraire et parser en `datetime`
3. ✅ Si non trouvé : fallback à date d'extraction

**Exemple attendu** :
```python
# Dans _extract_listing():
published_at = None
for key in ['publishDate', 'createdAt', 'timestamp', 'time_ago']:
    if key in item:
        published_at = parse_date_athome(item[key])
        break

# Ajouter au retour:
'published_at': published_at  # datetime ou None
```

**Probabilité de succès** : 60% (sites web français souvent expose cette info)

---

### 2️⃣ Immotop.lu

**Scraper** : `scrapers/immotop_scraper_real.py`

**Analyse** :
```python
# Immotop affiche généralement:
# "Il y a 2 heures", "Il y a 1 jour", "Récemment", etc.
# Format regex à chercher dans contexte HTML
pattern = r"[Ii]l y a (\d+)\s*(?:heures|jours|semaines)"
```

**Données disponibles** :
```
Texte visible : "Il y a 2 heures"
→ Convertir en datetime : datetime.now() - timedelta(hours=2)

Texte visible : "Il y a 1 jour"
→ Convertir en datetime : datetime.now() - timedelta(days=1)
```

**Actions nécessaires** :
1. ✅ Extraire texte "il y a X..." depuis contexte HTML
2. ✅ Parser nombre + unité (heures/jours/semaines)
3. ✅ Calculer datetime = now() - timedelta

**Exemple** :
```python
import re
from datetime import datetime, timedelta

def parse_immotop_date(text):
    """Extraire "il y a X jours" et convertir en datetime"""
    match = re.search(r"[Ii]l y a (\d+)\s*(?:heure|jour|semaine)s?", text)
    if match:
        number = int(match.group(1))
        if 'heure' in match.group(0):
            return datetime.now() - timedelta(hours=number)
        elif 'jour' in match.group(0):
            return datetime.now() - timedelta(days=number)
        elif 'semaine' in match.group(0):
            return datetime.now() - timedelta(weeks=number)
    return None
```

**Probabilité de succès** : 85% (texte visible généralement)

---

### 3️⃣ Luxhome.lu

**Scraper** : `scrapers/luxhome_scraper.py`

**Analyse** :
```python
# JSON embarqué peut contenir:
pattern = r'\{"title":"...","published":"2026-02-26T...",\s*...'
# Chercher clé "published", "date", "createdAt", etc.
```

**Actions nécessaires** :
1. ✅ Analyser regex JSON pour clés de date
2. ✅ Extraire et parser en datetime
3. ✅ Fallback à `time_ago` si présent

**Probabilité de succès** : 60%

---

### 4️⃣ VIVI.lu

**Scraper** : `scrapers/vivi_scraper_selenium.py`

**Analyse** :
```python
# Selenium accède au DOM complet
# Date peut être dans:
# - <span class="date">26/02/2026</span>
# - <time datetime="2026-02-26T09:45:00"></time>
# - Texte: "Publié le 26 février 2026"
```

**Actions nécessaires** :
1. ✅ Chercher `<time>` element avec datetime
2. ✅ Ou chercher span/div avec classe "date", "published", etc.
3. ✅ Parser en datetime

**Exemple** :
```python
from selenium.webdriver.common.by import By

# Dans _extract_listing():
try:
    time_elem = card.find_element(By.CSS_SELECTOR, 'time[datetime]')
    datetime_str = time_elem.get_attribute('datetime')
    published_at = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
except:
    published_at = None
```

**Probabilité de succès** : 70%

---

### 5️⃣ Nextimmo.lu

**Scraper** : `scrapers/nextimmo_scraper.py`

**Analyse** :
```python
# API JSON peut retourner:
item = {
    'id': 123,
    'createdAt': '2026-02-26T09:45:00Z',  # ← À chercher
    'publishedAt': '2026-02-26T09:45:00Z', # ← À chercher
    'updatedAt': '2026-02-26T10:30:00Z',  # ← À chercher (attention: mise à jour, pas création)
    'created': 1708934700,                 # ← Timestamp Unix?
}
```

**Actions nécessaires** :
1. ✅ Analyser JSON API pour clés date
2. ✅ Extraire `createdAt` ou `publishedAt` (pas `updatedAt`)
3. ✅ Parser en datetime (format ISO 8601)

**Exemple** :
```python
# Dans _extract_from_json():
published_at = None
date_str = item.get('createdAt') or item.get('publishedAt')
if date_str:
    try:
        published_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        pass
```

**Probabilité de succès** : 80% (API généralement propre)

---

### 6️⃣ Newimmo.lu

**Scraper** : `scrapers/newimmo_scraper_real.py`

**Analyse** :
```python
# Extraction depuis page_source (regex sur HTML)
# Chercher texte visible: "Publié le 26/02/2026"
# Ou attribut data-date="2026-02-26"
pattern = r'publi[ée]?\s*(?:le\s+)?(\d{1,2}/\d{1,2}/\d{4})'
```

**Actions nécessaires** :
1. ✅ Regex pour "Publié le DD/MM/YYYY"
2. ✅ Parser en datetime

**Probabilité de succès** : 50% (regex fragile)

---

### 7️⃣ Unicorn.lu

**Scraper** : `scrapers/unicorn_scraper_real.py`

**Analyse** :
```python
# Extraction depuis page_source (regex sur HTML)
# Chercher dans contexte HTML: attributs data-date, texte visible, etc.
pattern = r'<time[^>]*>([^<]+)</time>'
pattern = r'[Dd]epuis?\s*(\d+\s*(?:heures|jours|semaines))'
```

**Actions nécessaires** :
1. ✅ Chercher `<time>` dans contexte
2. ✅ Ou extraire "depuis X jours" et calculer datetime
3. ✅ Parser en datetime

**Probabilité de succès** : 55%

---

## Stratégie de fallback garantie

### Architecture robuste

```
Chaque scraper :
1. Tente extraire published_at du site
2. Si échoue : published_at = None (pas d'erreur)
3. Avant retour : fallback à datetime.now()

result = {
    'listing_id': ...,
    'published_at': published_at or datetime.now()  # ← FALLBACK GARANTIE
}
```

### Logique en pseudocode

```python
def extract_with_fallback_date(item, scraper_name):
    """Extraire annonce avec date, GARANTIE fallback"""

    # 1. Extraire annonce (prix, titre, etc.)
    listing = {
        'listing_id': ...,
        'site': scraper_name,
        'title': ...,
        'price': ...,
        ...
    }

    # 2. TOUJOURS extraire date de publication
    published_at = extract_date_from_item(item)  # Peut retourner None

    # 3. FALLBACK GARANTI
    if published_at is None:
        published_at = datetime.now()  # Date du scraping = date min sûre

    # 4. VALIDATION: date ne peut pas être dans le futur
    if published_at > datetime.now():
        published_at = datetime.now()  # Correction à maintenant

    listing['published_at'] = published_at
    return listing
```

### Tableau: Fiabilité par scraper

| Scraper | Chance date | Fallback | Fiabilité |
|---------|-----------|----------|-----------|
| Nextimmo | 85% | ✅ Oui | 100% |
| Athome | 60% | ✅ Oui | 100% |
| Immotop | 85% | ✅ Oui | 100% |
| VIVI | 70% | ✅ Oui | 100% |
| Luxhome | 60% | ✅ Oui | 100% |
| Newimmo | 50% | ✅ Oui | 100% |
| Unicorn | 55% | ✅ Oui | 100% |

**Conclusion** : Tous les scrapers auront 100% de couverture de date (published_at jamais None)

---

## Modifications à la base de données

### Schéma nouvelle colonne

**Fichier** : `database.py`

**Ajouter colonne** :
```sql
ALTER TABLE listings ADD COLUMN published_at TIMESTAMP;
CREATE INDEX idx_published_at ON listings(published_at);
```

**Ou dans init_db()** (pour nouvelles instances) :
```python
def init_db(self):
    ...
    self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            ...
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP,  # ← NOUVELLE: date publication du site
            notified BOOLEAN DEFAULT 0
        )
    ''')

    self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_published_at
        ON listings(published_at)
    ''')
```

### Modifications à add_listing()

```python
def add_listing(self, listing_data):
    """Ajouter une nouvelle annonce avec date de publication"""
    try:
        self.cursor.execute('''
            INSERT INTO listings
            (listing_id, site, title, city, price, rooms, surface,
             url, latitude, longitude, distance_km, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing_data.get('listing_id', ''),
            listing_data.get('site', 'Inconnu'),
            listing_data.get('title', 'Sans titre'),
            listing_data.get('city', 'N/A'),
            listing_data.get('price', 0),
            listing_data.get('rooms', 0),
            listing_data.get('surface', 0),
            listing_data.get('url', '#'),
            listing_data.get('latitude'),
            listing_data.get('longitude'),
            listing_data.get('distance_km'),
            listing_data.get('published_at')  # ← NOUVEAU
        ))
        self.conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        logger.error(f"❌ Erreur ajout annonce: {e}")
        return False
```

### Nouvelle méthode pour query par date

```python
def get_listings_by_date(self, hours=24, limit=50):
    """Récupérer annonces publiées dans les X dernières heures"""
    try:
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=hours)

        self.cursor.execute('''
            SELECT listing_id, site, title, city, price, published_at
            FROM listings
            WHERE published_at >= ?
            ORDER BY published_at DESC
            LIMIT ?
        ''', (cutoff, limit))

        return self.cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"❌ Erreur query: {e}")
        return []
```

---

## Modifications aux scrapers

### Fonction CRITIQUE : ensure_published_at()

**⭐ AJOUTER** d'abord cette fonction en `utils.py` :

```python
from datetime import datetime, timedelta
import re

def ensure_published_at(published_at=None):
    """
    ⭐⭐⭐ FONCTION CRITIQUE ⭐⭐⭐
    Garantir que published_at a TOUJOURS une valeur valide.
    C'est le fallback central pour TOUS les scrapers.

    Logique:
    1. Si published_at valide et <= now() → retourner
    2. Si None ou invalide ou future → retourner now()

    Retourne TOUJOURS une datetime (jamais None).
    """
    if published_at is None:
        return datetime.now()

    # Vérifier type
    if not isinstance(published_at, datetime):
        return datetime.now()

    # Vérifier que pas dans le futur (correction bug)
    now = datetime.now()
    if published_at > now:
        # Annonce avec date future → corriger à maintenant
        return now

    # OK: retourner date valide
    return published_at

def parse_relative_date(text):
    """
    Parser texte "il y a X jours" et retourner datetime

    Gère:
    - "Il y a 2 heures" → datetime.now() - 2h
    - "Il y a 1 jour" → datetime.now() - 1 jour
    - "Récemment" → datetime.now()
    - "Aujourd'hui" → datetime.now()
    """
    if not text:
        return None

    text_lower = text.lower()

    # "Récemment", "Aujourd'hui"
    if 'récemment' in text_lower or 'aujourd' in text_lower or 'recent' in text_lower:
        return datetime.now()

    # "Il y a X heures/jours/semaines"
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

def parse_absolute_date(date_str, format_str="%d/%m/%Y"):
    """Parser date absolue (ex: "26/02/2026")"""
    try:
        return datetime.strptime(date_str, format_str)
    except:
        return None

def parse_iso_date(date_str):
    """Parser ISO 8601 (ex: "2026-02-26T09:45:00Z")"""
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        return None
```

### Exemple pour Athome.lu (avec fallback)

**Fichier** : `scrapers/athome_scraper_json.py`

```python
from utils import ensure_published_at, parse_iso_date, parse_relative_date

def _extract_listing(self, item):
    """Extraire données + DATE DE PUBLICATION avec fallback"""
    ...
    # À la fin de la fonction, avant return:

    # Étape 1: Chercher date de publication (peut être None)
    published_at = None
    for key in ['publishDate', 'createdAt', 'timestamp', 'time_ago']:
        if key in item:
            value = item[key]
            if key == 'timestamp' and isinstance(value, (int, float)):
                # Timestamp Unix
                try:
                    published_at = datetime.fromtimestamp(value / 1000)  # /1000 si en ms
                    break
                except:
                    pass
            elif isinstance(value, str):
                # ISO date ou texte relatif
                published_at = parse_iso_date(value) or parse_relative_date(value)
                if published_at:
                    break

    # Étape 2: FALLBACK GARANTI (jamais None après cette ligne)
    published_at = ensure_published_at(published_at)

    return {
        'listing_id': f'athome_{id_val}',
        'site': 'Athome.lu',
        'title': title,
        'city': city,
        'price': price,
        'rooms': rooms,
        'surface': surface,
        'url': url,
        'image_url': image_url,
        'latitude': lat,
        'longitude': lng,
        'distance_km': distance_km,
        'time_ago': 'Récemment',
        'published_at': published_at  # ← JAMAIS None (fallback à datetime.now())
    }
```

### Exemple pour Immotop.lu

**Fichier** : `scrapers/immotop_scraper_real.py`

```python
def scrape(self):
    ...
    for match in matches:
        titre_raw, type_raw, prix_raw, url_rel, id_str, lat, lng, thumb_raw = match

        # Extraire date depuis le texte carte
        # Format: <div class="date">Il y a 2 heures</div>
        # À chercher dans page_source via regex
        date_pattern = rf'id["\']={id_str}[^>]*>.*?[Ii]l y a (\d+\s*\w+)'
        date_match = re.search(date_pattern, self.page_source, re.DOTALL)

        published_at = None
        if date_match:
            date_text = date_match.group(1)
            published_at = parse_relative_date(f"Il y a {date_text}")

        listing = {
            ...
            'published_at': published_at  # ← NOUVEAU
        }
```

---

## Intégration dans le dashboard

### Requête SQL pour dashboard

```python
# main.py ou dashboard.py
def get_dashboard_data():
    """Récupérer annonces pour dashboard"""
    from database import db
    from datetime import datetime, timedelta

    # Annonces publiées dans les 24 dernières heures
    listings = db.get_listings_by_date(hours=24, limit=100)

    # Formater pour dashboard
    data = []
    for listing in listings:
        listing_id, site, title, city, price, published_at = listing

        if published_at:
            # Formater temps écoulé
            now = datetime.now()
            delta = now - published_at
            if delta.total_seconds() < 3600:
                time_str = f"{int(delta.total_seconds() / 60)} min"
            elif delta.total_seconds() < 86400:
                time_str = f"{int(delta.total_seconds() / 3600)} h"
            else:
                time_str = f"{int(delta.total_seconds() / 86400)} j"
        else:
            time_str = "N/A"
            published_at = "N/A"

        data.append({
            'published_at': published_at,
            'time_str': time_str,
            'site': site,
            'title': title,
            'city': city,
            'price': price,
        })

    return sorted(data, key=lambda x: x['published_at'] or datetime.min, reverse=True)
```

### Format HTML pour dashboard

```html
<table class="listings">
  <thead>
    <tr>
      <th>📅 Publié</th>
      <th>Site</th>
      <th>Titre</th>
      <th>Ville</th>
      <th>Prix</th>
    </tr>
  </thead>
  <tbody>
    {% for listing in listings %}
    <tr class="{% if listing.time_str|contains('min') %}new-today{% elif listing.time_str|contains('h') %}today{% else %}older{% endif %}">
      <td>
        <span title="{{ listing.published_at }}">{{ listing.time_str }}</span>
      </td>
      <td>{{ listing.site }}</td>
      <td>{{ listing.title }}</td>
      <td>{{ listing.city }}</td>
      <td>{{ listing.price }}€</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
```

### CSS pour highlight nouvelles annonces

```css
tr.new-today {
    background-color: #fff3cd;  /* Jaune clair */
    font-weight: bold;
}

tr.today {
    background-color: #f8f9fa;  /* Gris très clair */
}

tr.older {
    background-color: #fff;
}

/* Colorer par site */
tr[data-site="Nextimmo.lu"] { border-left: 4px solid #FF6B35; }
tr[data-site="Athome.lu"] { border-left: 4px solid #004E89; }
tr[data-site="VIVI.lu"] { border-left: 4px solid #A23B72; }
```

---

## Plan d'exécution (étapes)

### Phase 1 : Analyse détaillée (2h)

**Objectif** : Déterminer exactement où est la date dans chaque scraper

```bash
# Pour chaque scraper, faire test manuel:

# 1. Athome.lu
python3 << 'EOF'
from scrapers.athome_scraper_json import athome_scraper_json
import json

listings = athome_scraper_json.scrape()
if listings:
    print("Premier listing Athome:")
    print(json.dumps(listings[0], indent=2, default=str))
EOF

# 2. Nextimmo.lu
python3 << 'EOF'
from scrapers.nextimmo_scraper import nextimmo_scraper
import json

listings = nextimmo_scraper.scrape()
if listings:
    print("Premier listing Nextimmo:")
    print(json.dumps(listings[0], indent=2, default=str))
EOF

# Même chose pour tous les 7 scrapers
# Chercher : publishDate, createdAt, timestamp, time_ago, date, etc.
```

**Livrable** : Document "DATE_SOURCES_FOUND.md" listant clé + format pour chaque scraper

---

### Phase 2 : Créer fonctions utilitaires (1h)

**Fichier** : `utils.py`

**Ajouter** :
```python
def parse_relative_date(text)
def parse_absolute_date(date_str, format_str)
def parse_iso_date(date_str)
```

**Tester** :
```bash
python test_date_parsing.py
# ✅ Tester avec:
#   - "Il y a 2 heures" → datetime.now() - 2h
#   - "Il y a 1 jour" → datetime.now() - 1j
#   - "26/02/2026" → datetime(2026, 2, 26)
#   - "2026-02-26T09:45:00Z" → datetime(2026, 2, 26, 9, 45)
```

---

### Phase 3 : Modifier base de données (30 min)

**Fichier** : `database.py`

```python
# 1. Ajouter colonne published_at dans init_db()
# 2. Ajouter published_at dans add_listing()
# 3. Créer index idx_published_at
# 4. Ajouter méthode get_listings_by_date()
```

**Migrate existing DB** (optionnel) :
```bash
sqlite3 listings.db << 'EOF'
ALTER TABLE listings ADD COLUMN published_at TIMESTAMP;
CREATE INDEX idx_published_at ON listings(published_at);
EOF
```

---

### Phase 4 : Modifier 7 scrapers (3h)

**Pour chaque scraper** :

```bash
# 1. Éditer scrapers/xxx_scraper.py
# 2. Ajouter extraction date dans _extract_listing() ou équivalent
# 3. Ajouter 'published_at': published_at au return

# 2. Tester scraper:
python3 << 'EOF'
from scrapers.xxx_scraper import xxx_scraper
listings = xxx_scraper.scrape()
if listings:
    print(f"✅ {len(listings)} listings")
    print(f"Sample published_at: {listings[0].get('published_at')}")
EOF
```

**Ordre de priorité** :
1. Nextimmo (API propre) — 20 min
2. Immotop (texte visible) — 20 min
3. VIVI (Selenium HTML) — 20 min
4. Athome (JSON) — 20 min
5. Newimmo (regex) — 15 min
6. Unicorn (regex) — 15 min
7. Luxhome (regex/JSON) — 15 min

---

### Phase 5 : Tester qualité données (1h)

```bash
# Créer test_date_quality.py
python test_date_quality.py

# Vérifie:
# ✅ Toutes les annonces ont published_at
# ✅ published_at <= created_at (DB timestamp)
# ✅ published_at dans les 30 jours (pas ancien)
# ✅ Pas de published_at dans le futur
```

---

### Phase 6 : Intégrer dans dashboard (2h)

**Fichier** : `dashboard.py` (créer si absent)

```python
from database import db
from datetime import datetime, timedelta

def render_dashboard():
    """Afficher annonces par date"""
    listings = db.get_listings_by_date(hours=24*7)  # 7 derniers jours

    # Grouper par date
    by_date = {}
    for listing in listings:
        date_key = listing['published_at'].date()
        if date_key not in by_date:
            by_date[date_key] = []
        by_date[date_key].append(listing)

    # Afficher HTML
    html = "<table>..."
    for date in sorted(by_date.keys(), reverse=True):
        html += f"<h3>{date.strftime('%d/%m/%Y')}</h3>"
        for listing in by_date[date]:
            html += f"<tr>...</tr>"

    return html
```

---

### Phase 7 : Validation et déploiement (30 min)

```bash
# 1. Vérifier toutes les données en BD
sqlite3 listings.db << 'EOF'
SELECT COUNT(*), COUNT(published_at) FROM listings;
SELECT MIN(published_at), MAX(published_at) FROM listings;
SELECT site, COUNT(*) FROM listings GROUP BY site;
EOF

# 2. Tester dashboard
python main.py  # Vérifier logs

# 3. Committer
git add utils.py database.py scrapers/ dashboard.py
git commit -m "Add publication date tracking for all listings"
```

---

## Récapitulatif timeline

| Phase | Tâche | Temps | Dépendances |
|-------|-------|-------|-------------|
| **1** | Analyser sources date | 2h | - |
| **2** | Fonctions utilitaires date | 1h | Phase 1 |
| **3** | Modifier base de données | 30 min | Phase 2 |
| **4** | Modifier 7 scrapers | 3h | Phase 2-3 |
| **5** | Tests qualité | 1h | Phase 4 |
| **6** | Intégrer dashboard | 2h | Phase 5 |
| **7** | Validation | 30 min | Phase 6 |
| **TOTAL** | | **10h** | |

---

## 🎯 Résultat final

### Dashboard avec date

```
📅 TABLEAU ANNONCES TRIÉES PAR DATE

Aujourd'hui (26/02/2026)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ⏰ 09:45  │ Athome  │ 2ch, 1250€ │ Luxembourg │ ✨ À peine 5 min
 ⏰ 08:15  │ Nextimmo│ 3ch, 1800€ │ Esch │ ✨ 3h ago
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hier (25/02/2026)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ⏰ 19:30  │ VIVI    │ 2ch, 1500€ │ Differdange │
 ⏰ 14:20  │ Luxhome │ 1ch, 900€  │ Dudelange │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Il y a 2 jours (24/02/2026)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ⏰ 10:00  │ Immotop │ 2ch, 1400€ │ Luxembourg │
```

### Filtrage possible

```
Filter: Dernières 24h ✅ → 2 annonces
Filter: Dernières 48h ✅ → 4 annonces
Filter: Dernière semaine ✅ → 5 annonces
```

### Bot + Notification

```
"Nouvelle annonce trouvée!
 Publiée il y a 5 minutes
 Athome.lu | 2ch, 1250€, Luxembourg"
```

---

**Créé** : 2026-02-26
**Étapes** : 7 phases, 10h total
**Statut** : Prêt pour exécution

