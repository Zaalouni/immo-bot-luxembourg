# Analyse détaillée des Scrapers — Identification des bugs et problèmes de qualité

> Ce fichier analyse chaque scraper actif, identifie les bugs de collecte de données,
> et propose des corrections pour améliorer la qualité des annonces.

---

## 📊 Résumé des 7 scrapers actifs

| # | Scraper | Site | Méthode | Pages | Qualité | Problèmes |
|---|---------|------|---------|-------|---------|-----------|
| 1 | athome_scraper_json.py | Athome.lu | JSON __INITIAL_STATE__ | 12 | 🟠 Moyenne | JSON dict imbriqués, prix/rooms peuvent être None |
| 2 | immotop_scraper_real.py | Immotop.lu | HTML regex | 5 | 🟠 Moyenne | Extraction ville fragile, pas de GPS |
| 3 | luxhome_scraper.py | Luxhome.lu | JSON/Regex | 1 | 🟢 Bonne | GPS, bonne extraction, peu de chambres/surface |
| 4 | vivi_scraper_selenium.py | VIVI.lu | Selenium | 3 | 🟠 Moyenne | Extraction prix peut être faussée si multi-lignes |
| 5 | nextimmo_scraper.py | Nextimmo.lu | API JSON | 10 | 🟢 Bonne | API stable, bon fallback HTML, GPS |
| 6 | newimmo_scraper_real.py | Newimmo.lu | Selenium + regex | 3 | 🟠 Moyenne | Extraction prix/rooms/surface fragile (regex) |
| 7 | unicorn_scraper_real.py | Unicorn.lu | Selenium + regex | 2 | 🟠 Moyenne | CAPTCHA intermittent, peu d'annonces |

---

## 🔍 Problèmes identifiés par scraper

### 1️⃣ Athome.lu (athome_scraper_json.py) — 📝 330 lignes

**Méthode** : Extrait JSON `window.__INITIAL_STATE__` depuis le HTML

**Structures de données complexes** :
```python
item = {
  'price': {'value': 2500} ou int(2500),
  'immotype': {'label': 'apartment'} ou str('apartment'),
  'geo': {'cityName': 'Luxembourg', 'lat': 49.6, 'lon': 6.1},
  'roomsCount': int ou {'value': 2},
  'characteristic': {'bedrooms_count': 2},
  'photos': [{'url': '...'}, ...] ou [],
  'mainPhoto': {'url': '...'}
}
```

**Problèmes identifiés** :

| # | Problème | Cause | Impact | Sévérité |
|----|----------|--------|--------|----------|
| A1 | Prix = 0 si structure JSON change | `price_raw = item.get('price', 0)` puis conversion | Annonce filtrée ❌ | 🔴 HAUTE |
| A2 | Ville par défaut "Luxembourg" si geo manquant | Pas de fallback géocodage | Résultats imprécis | 🟠 MOYENNE |
| A3 | Chambres = 0 si dans `characteristic.bedrooms_count` et non `roomsCount` | Deux sources conflictuelles | Résultats filtrés ❌ | 🟠 MOYENNE |
| A4 | Surface peut être None ou dict imbriqué | Extraction `propertySurface.value` fragile | Filtre surface échoue | 🟠 MOYENNE |
| A5 | Image URL peut être None si photos/mainPhoto manquent | 6 fallbacks mais tous peuvent échouer | Pas de photo 📸 | 🟡 BASSE |
| A6 | URL construite manuellement peut ne pas matcher le lien réel | URL pattern peut avoir changé | Lien mort ❌ | 🟠 MOYENNE |

**Tests nécessaires** :
- ✅ JSON avec price=null (devrait être filtré)
- ✅ JSON avec geo=null (ville = "Luxembourg")
- ✅ JSON avec roomsCount=0 mais characteristic.bedrooms_count=2 (résultat?)
- ✅ JSON avec surface décimale (52.5 m2)
- ✅ Vérifier que URL construite existe vraiment

---

### 2️⃣ Immotop.lu (immotop_scraper_real.py) — 📝 146 lignes

**Méthode** : Regex sur HTML brut (prix + URL + titre)

```python
pattern = r'<span>€?\s*([\d\s\u202f]+)/mois</span>.*?<a href="(https://www\.immotop\.lu/annonces/(\d+)/)"[^>]*title="([^"]+)"'
```

**Problèmes identifiés** :

| # | Problème | Cause | Impact | Sévérité |
|----|----------|--------|--------|----------|
| I1 | Prix avec espaces insécables (U+202F) | Regex `[\d\s\u202f]` puis `replace('\u202f', '')` | Mauvais prix possible | 🔴 HAUTE |
| I2 | Ville extraite depuis titre (dernière partie après virgule) | Format titre: "2ch, 75m², Ville" → fonctionne mal si titre mal formaté | Ville incorrecte | 🟠 MOYENNE |
| I3 | GPS non disponible | Site n'expose pas coords | Filtre distance inutile | 🟡 BASSE |
| I4 | Chambres depuis titre regex naïf | `r'(\d+)\s*chambre'` → capture "1 chambre" OK, mais "studio 1 pièce" ? | Faux positif | 🟠 MOYENNE |
| I5 | Surface depuis titre avec `m[²2]` | Peut matcher "m²" ou "m2" mais pas format décimal (52.00) | Surface incomplète | 🟠 MOYENNE |
| I6 | Image extraction par data-src fragile | Regex `data-src="(https://[^"]*immotop[^"]*)"` peut échouer si format change | Pas de photo | 🟡 BASSE |

**Tests nécessaires** :
- ✅ Prix avec espaces insécables : "1 250 €" vs "1 250€"
- ✅ Prix avec points (format européen) : "1.250 €/mois"
- ✅ Titre sans virgule (fallback ville?)
- ✅ Surface décimale (52.00 m²)
- ✅ Annonce sans image (fallback?)

---

### 3️⃣ Luxhome.lu (luxhome_scraper.py) — 📝 205 lignes

**Méthode** : Regex sur JSON embarqué dans HTML + GPS Haversine

```python
pattern = r'\{\s*"title":"([^"]+)",\s*"propertyType":"([^"]+)",\s*"price":"([^"]+)",'
```

**Problèmes identifiés** :

| # | Problème | Cause | Impact | Sévérité |
|----|----------|--------|--------|----------|
| L1 | Prix extraction naïve (regex `\d+`) | `prix_raw = "2.500€"` → `prix_clean.replace('.', '')` → "2500€" OK, mais "2 500 €" (avec espace) ? | Faux prix possible | 🔴 HAUTE |
| L2 | Chambres/surface extraites depuis titre | Regex heuristique, peut échouer si titre mal formaté | Données incomplètes | 🟠 MOYENNE |
| L3 | Localisation (ville) seulement si dans PREFERRED_CITIES | Si ville présente mais pas dans liste → localisation vide | Ville vide | 🟠 MOYENNE |
| L4 | GPS fournie (lat/lng) mais pas d'erreur si invalide | Pas de validation `float(lat)` | Crash possible en Haversine | 🟠 MOYENNE |
| L5 | URL correction /fr/ manuelle | Si Luxhome change format URL → peut devenir invalide | Lien mort | 🟡 BASSE |

**Tests nécessaires** :
- ✅ Prix avec point (européen) : "2.500 €/mois"
- ✅ Prix avec espace : "2 500 €/mois"
- ✅ Chambres/surface non détectées
- ✅ Ville non dans PREFERRED_CITIES
- ✅ GPS invalide (lat="49.6abc", lng=None)

---

### 4️⃣ VIVI.lu (vivi_scraper_selenium.py) — 📝 215 lignes

**Méthode** : Selenium avec scroll + extraction texte cartes

**Problèmes identifiés** :

| # | Problème | Cause | Impact | Sévérité |
|----|----------|--------|--------|----------|
| V1 | Prix extraction naïve (première ligne avec €) | Boucle sur `text.split('\n')`, prend première ligne avec € | Peut capturer prix de charges (ex: "Loyer 1500€ + charges 200€") | 🔴 HAUTE |
| V2 | Pas de GPS | Selenium extrait juste texte, pas coords | Filtre distance inutile | 🟡 BASSE |
| V3 | Texte extraire de `card.text` peut être tronqué ou vide | Selenium peut retourner `''` si JS tard | Annonces perdues | 🟠 MOYENNE |
| V4 | Chambres = 0 par défaut (correct) | Regex `r'(\d+)\s*chambres?'` OK | ✅ Bon | 🟢 |
| V5 | Surface extraction OK | Regex `r'(\d+)\s*m[²2]'` OK | ✅ Bon | 🟢 |

**Tests nécessaires** :
- ✅ Texte carte multi-lignes avec plusieurs prix (loyer + charges)
- ✅ Carte avec texte vide (Selenium timeout)
- ✅ Pas de chambres/surface detectable

---

### 5️⃣ Nextimmo.lu (nextimmo_scraper.py) — 📝 280 lignes

**Méthode** : API JSON directe + fallback HTML

**Problèmes identifiés** :

| # | Problème | Cause | Impact | Sévérité |
|----|----------|--------|--------|----------|
| N1 | Prix dans structure nested `price: {value: int}` ou `int` | Gère bien les deux cas | ✅ Bon | 🟢 |
| N2 | Surface dans `area: {value: int}` ou `int` | Gère bien les deux cas | ✅ Bon | 🟢 |
| N3 | Chambres = max(bedrooms, rooms) | Si bedrooms=0 et rooms=0 → 0 | ✅ Correct | 🟢 |
| N4 | Titre par défaut si vide | `f"Appartement {city}"` ou `f"Appartement {room_count}ch..."` | ✅ Bon fallback | 🟢 |
| N5 | Image depuis `pictures.thumb[]` | Peut être vide ou `None` | Pas de photo | 🟡 BASSE |
| N6 | GPS disponible (latitude/longitude) | ✅ Bon | ✅ Bon | 🟢 |
| N7 | Fallback HTML si API échoue | Extrait `__NEXT_DATA__` depuis React | ✅ Bon backup | 🟢 |

**État** : ✅ Meilleur scraper, peu de problèmes

**Tests nécessaires** :
- ✅ API retourne 0 résultats → fallback HTML fonctionne
- ✅ Titre vide → génération correcte
- ✅ Image vide → pas de crash

---

### 6️⃣ Newimmo.lu (newimmo_scraper_real.py) — 📝 197 lignes

**Méthode** : Selenium + regex sur page_source

**Problèmes identifiés** :

| # | Problème | Cause | Impact | Sévérité |
|----|----------|--------|--------|----------|
| NW1 | Prix extraction naïve sur contexte HTML | `re.search(r'([\d\s\.]+)\s*€', text)` → capture "1 250.00€" mais "1.250€" (point décimal) ? | Faux prix possible | 🔴 HAUTE |
| NW2 | Contexte de 1500 chars avant position du lien | Si lien au début de page, contexte incomplet | Données manquantes | 🟠 MOYENNE |
| NW3 | Ville depuis URL index 3 | Pattern `/fr/louer/type/VILLE/id` — si URL format change → faux | Ville incorrecte | 🟠 MOYENNE |
| NW4 | Chambres extraction naïve | `r'(\d+)\s*(?:chambre|pièce|room|ch\.)'` OK mais peut matcher numéros parasites | Faux positif | 🟠 MOYENNE |
| NW5 | Surface décimale gérée | `int(float(surface_match.group(1).replace(',', '.')))` ✅ Bon | ✅ Bon | 🟢 |
| NW6 | Pas de GPS | Selenium page_source n'expose pas coords | Filtre distance inutile | 🟡 BASSE |

**Tests nécessaires** :
- ✅ Prix avec point européen (1.250€)
- ✅ Prix multi-lignes dans contexte
- ✅ Surface décimale (52.50 m²)
- ✅ URL format change (fallback?)
- ✅ Chambres non détectable

---

### 7️⃣ Unicorn.lu (unicorn_scraper_real.py) — 📝 225 lignes

**Méthode** : Selenium + regex sur page_source (2 fallbacks de recherche prix)

**Problèmes identifiés** :

| # | Problème | Cause | Impact | Sévérité |
|----|----------|--------|--------|----------|
| U1 | CAPTCHA intermittent bloque Selenium | Site détecte bot → erreur 403/429 | Scraper échoue silencieusement | 🔴 HAUTE |
| U2 | Extraction prix avec 2 fallbacks (data-id puis lien) | Peut capture 2x le même lien | Annonce dupliquée | 🟠 MOYENNE |
| U3 | Prix extraction: `([\d\s\.]+)\s*€` | Capture "1 250.00€" mais décimal? → `replace('.', '')` → "125000€" ❌ | Faux prix | 🔴 HAUTE |
| U4 | Ville extraction via regex complexe | Pattern `location-{type}-(.+)$` dépend de format URL | Peut échouer si format change | 🟠 MOYENNE |
| U5 | Chambres/surface regex OK | ✅ Pareil que Newimmo | ✅ Bon | 🟢 |
| U6 | Image extraction du contexte local | Peut manquer si pas dans zone ±2000 chars | Pas de photo | 🟡 BASSE |
| U7 | Peu d'annonces (MAX_PAGES=2) | Site petit ou données peu à jour | Peu d'options | 🟡 BASSE |

**Tests nécessaires** :
- ✅ CAPTCHA détection et gestion d'erreur
- ✅ Prix avec point décimal (1.250.00€)
- ✅ Annonces dupliquées (data-id vs lien)
- ✅ Ville non détectable

---

## 🐛 Bugs critiques à corriger (HAUTE priorité)

### Bug A1 : Prix extraction — Athome.lu
**Symptôme** : Annonces avec prix = 0 (filtrées)
**Cause** : `price_raw = item.get('price', 0)` puis conversion type error
**Fix** :
```python
try:
    if isinstance(price_raw, dict):
        price = int(float(price_raw.get('value') or 0))
    else:
        price = int(float(price_raw or 0))
except (ValueError, TypeError):
    return None  # Rejeter si prix invalide
```

### Bug I1 : Prix avec espaces insécables — Immotop.lu
**Symptôme** : Prix "1 250€" devient "1250€" (bon) mais "1 250 €" devient "1250€" (bon aussi)
**Réalité** : Peut échouer si `\u202f` non géré
**Fix** :
```python
price_clean = price_text.replace(' ', '').replace('\u202f', '').replace(',', '').replace('.', '')
```

### Bug L1 : Prix européen — Luxhome.lu
**Symptôme** : "2.500€" interprété comme "2.500" (mauvais, devrait être 2500)
**Cause** : `prix_clean = prix_raw.replace('\\u20ac', '').replace('€', '').replace(' ', '').replace('.', '').replace(',', '')`
**Problème** : Replace `.` AVANT chercher nombre, donc "2.500" → "2500" ✅ OK
**Vérifier** : Si prix "1.250,50€" (format mixte) → résultat "125050" ❌ MAUVAIS
**Fix** :
```python
prix_clean = prix_raw.replace('€', '').strip()
# Déterminer séparateur (virgule ou point) basé sur position
if ',' in prix_clean and '.' in prix_clean:
    if prix_clean.index('.') > prix_clean.index(','):
        prix_clean = prix_clean.replace('.', '').replace(',', '.')  # 1.000,50 → 1000.50
    else:
        prix_clean = prix_clean.replace(',', '')  # 1,000.50 → 1000.50
else:
    prix_clean = prix_clean.replace(',', '.').replace(' ', '')
try:
    prix = int(float(prix_clean))
except ValueError:
    return None
```

### Bug V1 : Prix multi-lignes — VIVI.lu
**Symptôme** : Prix capture "Loyer 1500€" + "Charges 200€"
**Cause** : Boucle prend première ligne avec €
**Fix** :
```python
price = 0
for line in text.split('\n'):
    if '€' in line and 'loyer' in line.lower():  # Chercher spécifiquement "loyer"
        price_digits = re.sub(r'[^\d]', '', line)
        if price_digits:
            price = int(price_digits)
            break
# Fallback si pas trouvé:
if price == 0:
    for line in text.split('\n'):
        if '€' in line:
            price_digits = re.sub(r'[^\d]', '', line)
            if price_digits:
                price = int(price_digits)
                break
```

### Bug NW1 : Prix décimal — Newimmo.lu
**Symptôme** : "1.250€" (point décimal) → `replace('.', '')` → "1250€" ✅ OK, mais "1.250.00€" (mauvais format) → "125000€" ❌
**Cause** : Naïf `replace('.', '')`
**Fix** :
```python
price_match = re.search(r'([\d\s\.]+)\s*€', text)
if price_match:
    price_str = price_match.group(1).strip()
    # Nettoyer: "1 250.00" ou "1.250,00" ou "1250"
    price_str = price_str.replace(' ', '')
    # Si présence de . et , : déterminer lequel est séparateur de milliers
    if '.' in price_str and ',' in price_str:
        if price_str.index('.') > price_str.index(','):
            price_str = price_str.replace(',', '.').replace('.', '', price_str.count('.')-1)
        else:
            price_str = price_str.replace('.', '').replace(',', '.')
    elif ',' in price_str:
        price_str = price_str.replace(',', '.')
    try:
        price = int(float(price_str))
    except ValueError:
        return None
```

### Bug U3 : Prix décimal — Unicorn.lu
**Même problème que NW1**
**Fix** : Même approche

---

## 📋 Checklist de qualité pour chaque annonce

Chaque annonce doit respecter :

| Champ | Validation | Rejection |
|-------|-----------|----------|
| `listing_id` | Non vide, unique par site | ❌ Si vide |
| `site` | Enum : Athome, Immotop, Luxhome, VIVI, Nextimmo, Newimmo, Unicorn | ❌ Si invalide |
| `title` | 5-200 chars, non vide | ❌ Si < 5 chars |
| `city` | 2-50 chars, non vide | ⚠️ Default "Luxembourg" |
| `price` | int, 500-10000 (plausible) | ❌ Si <500 ou >10000 |
| `rooms` | int, 0-10 (0=inconnu) | ⚠️ Default 0 |
| `surface` | int, 0-500 (0=inconnu) | ⚠️ Default 0 |
| `url` | URL valid, commence par http(s) | ❌ Si invalide |
| `image_url` | URL valid OU None | ⚠️ Default None |
| `latitude` | float, -90...90 OU None | ⚠️ Default None |
| `longitude` | float, -180...180 OR None | ⚠️ Default None |
| `distance_km` | float > 0 OU None | ⚠️ Default None |

---

## 📚 Résumé des problèmes par catégorie

### Extraction de prix (CRITIQUE)
- ❌ Athome : type error si dict imbriqué
- ❌ Immotop : espacesinsécables `\u202f`
- ❌ Luxhome : point européen "2.500€"
- ❌ VIVI : multi-lignes loyer+charges
- ❌ Newimmo : décimal "1.250.00€"
- ❌ Unicorn : décimal, CAPTCHA

### Extraction ville (MOYENNE)
- ❌ Immotop : depuis titre (fragile)
- ⚠️ Luxhome : seulement si dans liste
- ⚠️ VIVI : depuis URL (conversion slug)
- ⚠️ Newimmo : depuis URL index (fragile)
- ⚠️ Unicorn : regex complexe sur format URL

### GPS/Distance (BASSE)
- ⚠️ Athome : fallback default si manquant
- ❌ Immotop : pas de GPS
- ✅ Luxhome : disponible, validé
- ❌ VIVI : pas de GPS
- ✅ Nextimmo : disponible
- ❌ Newimmo : pas de GPS
- ⚠️ Unicorn : pas de GPS

### Images (BASSE)
- ⚠️ Tous : peuvent être None (OK)
- Priorité basse : 80% des cas OK

---

## ✅ Recommandations de correction (Phase prioritaire)

### Phase 1 : CRITIQUE (Jour 1)
1. ✅ Fixer prix extraction dans **tous les scrapers** (standardiser)
2. ✅ Ajouter validation prix plausible (500-10000€)
3. ✅ Ajouter tests unitaires prix pour chaque scraper

### Phase 2 : MOYENNE (Jour 2-3)
4. ✅ Fixer extraction ville (fallback config.REFERENCE_CITY si échoue)
5. ✅ Ajouter validation URL (commence par http)
6. ✅ Améliorer chambres/surface extraction (sanitaire data)

### Phase 3 : BASSE (Jour 4+)
7. ✅ Ajouter GPS validation si présent
8. ✅ Améliorer images fallback
9. ✅ Tester avec vraie base de données (listings.db)

---

**Dernière mise à jour** : 2026-02-26
**Statut** : Analyse complète, prêt pour phase de corrections
