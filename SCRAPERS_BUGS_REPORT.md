# 🐛 Rapport des bugs trouvés dans les scrapers

> Rapport généré après exécution des tests test_price_parsing.py
> **2 bugs critiques confirmés** qui causent des fausses annonces

---

## 🔴 Bugs critiques confirmés

### Bug #1 : VIVI.lu — Loyer vs Charges (CRITIQUE)

**Sévérité** : 🔴 CRITIQUE

**Symptôme** : Annonce avec prix = charges au lieu du loyer
- Exemple : Annonce avec loyer 1250€ + charges 150€
- Si charges apparaissent en premier dans le texte → capture 150€ ❌
- Résultat : annonce filtrée ou fausse

**Cause** : Boucle prend **première ligne avec €**, pas spécifiquement le loyer
```python
# MAUVAIS (vivi_scraper_selenium.py ligne 123-133)
for line in text.split('\n'):
    if '€' in line:
        price_digits = re.sub(r'[^\d]', '', line)
        if price_digits:
            try:
                price = int(price_digits)
                break  # ← Prend PREMIÈRE ligne avec €
            except ValueError:
                continue
```

**Test qui le démontre** :
```
text = """Studio\nCharges: 150€\nLoyer: 1250€"""
result = parse_price_vivi(text)
# Résultat: 150 au lieu de 1250 ❌ FAUX
```

**Impact** :
- ❌ Annonces loyer=150€ créées (filtrées ou acceptées selon config)
- ❌ Utilisateur voit loyer incorrect

**Fix recommandé** :
```python
# BON : chercher spécifiquement "loyer"
price = 0
for line in text.split('\n'):
    if '€' in line and 'loyer' in line.lower():
        price_digits = re.sub(r'[^\d]', '', line)
        if price_digits:
            price = int(price_digits)
            break

# Fallback si pas trouvé
if price == 0:
    for line in text.split('\n'):
        if '€' in line and any(keyword in line.lower() for keyword in ['loyer', 'rent', 'price']):
            price_digits = re.sub(r'[^\d]', '', line)
            if price_digits:
                price = int(price_digits)
                break
```

---

### Bug #2 : Immotop.lu — Symbole € non nettoyé (MOYENNE)

**Sévérité** : 🟠 MOYENNE

**Symptôme** : Prix avec `€` directement attaché n'est pas traité
- Exemple : "1250€" (sans espace avant €)
- Parsing échoue silencieusement → prix = 0
- Résultat : annonce filtrée

**Cause** : Fonction `parse_price_immotop` ne retire pas `€`
```python
# MAUVAIS (immotop_scraper_real.py ligne 85-92)
price_clean = price_text.replace(' ', '').replace('\u202f', '').replace(',', '')
try:
    price = int(price_clean)  # ← Si price_clean = "1250€", int() échoue
except ValueError:
    logger.debug(f"Prix invalide: {price_text}")
    continue
```

**Test qui le démontre** :
```
price_text = "1 250€"
result = parse_price_immotop(price_text)
# Résultat: 0 (ValueError) au lieu de 1250 ❌ FAUX
```

**Impact** :
- ❌ Annonces avec "€" attaché ne sont pas scrapées
- ⚠️ Peu courant (site généralement ajoute espace) mais possible

**Fix recommandé** :
```python
price_clean = price_text.replace(' ', '').replace('\u202f', '').replace(',', '').replace('€', '')
try:
    price = int(price_clean)
except ValueError:
    logger.debug(f"Prix invalide: {price_text}")
    continue
```

---

## 🟠 Bugs détectés par tests (non confirmés en production)

### Bug #3 : Luxhome.lu — Format prix mixte (THÉORIQUE)

**Sévérité** : 🟠 MOYENNE (théorique, non confirmé)

**Symptôme** : Prix avec format mixte (1.250,50€) maltraité
- Cause : `replace('.', '')` puis `replace(',', '')` → "125050" ❌

**Probabilité** : Basse (Luxhome utilise probablement format cohérent)

**Fix recommandé** : Voir scrapers_analysis.md section "Bug L1"

---

### Bug #4 : Newimmo.lu / Unicorn.lu — Format décimal mixte (THÉORIQUE)

**Sévérité** : 🔴 CRITIQUE (si format change)

**Symptôme** : Prix "1.250,00€" (point milliers + virgule décimale)
- Cause : `replace('.', '')` → "1250,00€" puis `replace(',', '')` → "125000€" ❌
- Résultat : prix 125 000€ au lieu de 1250€

**Probabilité** : Basse (sites utilisent probablement format simple)

**Test** :
```
parse_price_newimmo("1.250,00€")
# Résultat: 0 (regex ne matche pas "1.250,00€" sans espace)
```

---

## 📊 Tableau récapitulatif

| # | Scraper | Bug | Sévérité | Test | Fix |
|----|---------|-----|----------|------|-----|
| 1 | VIVI.lu | Loyer vs Charges | 🔴 CRITIQUE | ✅ Confirmé | Chercher "loyer" spécifiquement |
| 2 | Immotop | € non nettoyé | 🟠 MOYENNE | ✅ Confirmé | Remove € de price_clean |
| 3 | Luxhome | Format mixte (1.250,50€) | 🟠 MOYENNE | ⚠️ Théorique | Parser Europe format smart |
| 4 | Newimmo/Unicorn | Décimal mixte | 🔴 CRITIQUE | ✅ Test fail | Parser décimal robuste |

---

## 🔧 Plan de corrections recommandé

### Priorité 1 : FIX IMMÉDIAT (2h)

**Bug #1 (VIVI)** : Modifier `vivi_scraper_selenium.py` ligne 123-133
```python
# Chercher spécifiquement "loyer" ou équivalent
```

**Bug #2 (Immotop)** : Modifier `immotop_scraper_real.py` ligne 85
```python
price_clean = ... .replace('€', '')
```

### Priorité 2 : FIX ROBUSTESSE (4h)

**Bug #3 + #4** : Créer fonction centralisée `parse_price_robust()` dans `utils.py`
```python
def parse_price_robust(price_text):
    """
    Parse prix robuste pour tous les scrapers.
    Gère: espaces, €, virgule, point, décimales.
    Retourne: int (arrondi) ou 0 si invalide.
    """
    # Implementation...
```

Utiliser partout au lieu de regex locales.

---

## ✅ Prochaines étapes

1. **Lancer tests** : `python test_price_parsing.py` — voir état actuel
2. **Lancer tests scrapers** : `python test_scrapers_quality.py --all` — vérifier qualité données réelles
3. **Committer** : Committer cette analyse + tests
4. **Corriger bugs** : Appliquer fixes Phase 1 + 2
5. **Retester** : Relancer tests pour confirmer

---

**Généré** : 2026-02-26
**Auteur** : Test suite
**Statut** : Prêt pour corrections
