# 🔄 REFACTORISATION DASHBOARD v2.0 → v3.0

## 📅 Date
- **Démarrage** : 2026-02-23
- **Branch** : `claude/review-dashboard-ideas-A2IRB`
- **Version avant** : v2.0 (monolithe)
- **Version après** : v3.0 (modulaire)

---

## 📊 STRUCTURE AVANT vs APRÈS

### AVANT (v2.0) - Monolithe
```
dashboard_generator.py (980 lignes)
├── Imports (32-39)
│   ├── sqlite3, json, os, shutil
│   ├── base64, hashlib ⚠️ INUTILISÉS
│   ├── datetime, urlencode
│
├── Logique Métier (7 fonctions, 280 lignes)
│   ├── read_listings() - ligne 42
│   ├── calc_stats() - ligne 53
│   ├── generate_qr_code_url() - ligne 138
│   ├── enrich_listings_with_metadata() - ligne 149
│   ├── compute_price_heatmap_by_city() - ligne 183
│   ├── compute_timeline_data() - ligne 212
│   └── export_data() - ligne 227
│
├── Templates (2 fonctions, 600+ lignes)
│   ├── generate_manifest() - ligne 288
│   └── generate_html() - ligne 327 (665 lignes de strings HTML/CSS/JS!)
│
└── Main (1 fonction, 47 lignes)
    └── main() - ligne 933
```

### APRÈS (v3.0) - Modulaire
```
data_processor.py (280+ lignes)
├── Imports : sqlite3, json, datetime, urlencode (NO base64, hashlib)
├── read_listings()
├── calc_stats()
├── generate_qr_code_url()
├── enrich_listings_with_metadata()
├── compute_price_heatmap_by_city()
├── compute_timeline_data()
└── export_data()

template_generator.py (600+ lignes)
├── Imports : json, datetime, os
├── generate_manifest()
└── generate_html()

generator.py (50 lignes)
├── Imports : data_processor, template_generator
└── main() [orchestrateur]

dashboard_generator.py (WRAPPER, backward compatibility)
├── from generator import *
└── if __name__ == '__main__': main()
```

---

## 🔗 MAPPING DES FONCTIONS

### data_processor.py
| Fonction | Ligne (old) | Responsabilité |
|----------|---|---|
| `read_listings(db_path)` | 42-50 | Lecture SQLite, calcul price_m2 |
| `calc_stats(listings)` | 53-135 | Stats globales + qualité données + anomalies |
| `generate_qr_code_url(text)` | 138-146 | URL QR code via API externe |
| `enrich_listings_with_metadata(listings)` | 149-180 | Ajoute QR codes, share_urls, flags |
| `compute_price_heatmap_by_city(listings)` | 183-209 | Heatmap prix/m² par ville |
| `compute_timeline_data(listings)` | 212-224 | Timeline dates d'annonces |
| `export_data(listings, stats, data_dir)` | 227-285 | Exporte JS/JSON + archives |

**Imports nécessaires** (ligne 32-39):
- `sqlite3` ✅ (utilisé)
- `json` ✅ (utilisé)
- `os` ✅ (utilisé)
- `shutil` ❌ DÉPLACER à generator.py
- `base64` ❌ SUPPRIMER (inutilisé)
- `hashlib` ❌ SUPPRIMER (inutilisé)
- `datetime` ✅ (utilisé)
- `urlencode` ✅ (utilisé)

### template_generator.py
| Fonction | Ligne (old) | Responsabilité |
|----------|---|---|
| `generate_manifest(dashboards_dir)` | 288-171 | Crée manifest.json PWA |
| `generate_html(stats, site_colors)` | 327-876 | Génère HTML+CSS+JS complet |

**Imports nécessaires**:
- `json` ✅
- `os` ✅
- `datetime` ✅

### generator.py (NEW - orchestrateur)
| Fonction | Responsabilité |
|----------|---|
| `main()` | Coordonne le flux complet |

**Imports nécessaires**:
- `shutil` (pour copy2)
- `datetime` (pour strftime)
- `os` (os.path.join, makedirs)
- `from data_processor import *`
- `from template_generator import *`

---

## 📋 CHECKLIST D'IMPLÉMENTATION

### Phase 1 : Extraction données
- [ ] Créer `data_processor.py`
- [ ] Copier fonctions: read_listings, calc_stats, generate_qr_code_url, enrich_listings_with_metadata, compute_price_heatmap_by_city, compute_timeline_data, export_data
- [ ] Ajouter imports minimaux: `import sqlite3, json, os, datetime, urlencode`
- [ ] **Ajouter docstrings pour chaque fonction**
- [ ] Tester: `python3 -m py_compile data_processor.py`

### Phase 2 : Extraction templates
- [ ] Créer `template_generator.py`
- [ ] Copier fonctions: generate_manifest, generate_html
- [ ] Ajouter imports: `import json, os, datetime`
- [ ] **Ajouter docstrings**
- [ ] Tester: `python3 -m py_compile template_generator.py`

### Phase 3 : Orchestrateur
- [ ] Créer `generator.py`
- [ ] Copier `main()` du fichier original
- [ ] Ajouter imports: `from data_processor import ..., from template_generator import ...`
- [ ] Garder la logique identique
- [ ] Tester: `python generator.py` (doit générer dashboard)

### Phase 4 : Backward compatibility
- [ ] Mettre à jour `dashboard_generator.py`
- [ ] Remplacer tout par: `from generator import *`
- [ ] Ajouter commentaire DEPRECATED
- [ ] Garder: `if __name__ == '__main__': main()`

### Phase 5 : Validation
- [ ] Compiler chaque fichier
- [ ] Vérifier pas d'imports circulaires
- [ ] Tester: `python data_processor.py` (doit faire rien = OK)
- [ ] Tester: `python template_generator.py` (doit faire rien = OK)
- [ ] Tester: `python generator.py` (doit générer dashboard)
- [ ] Vérifier que `dashboards/` est créé

### Phase 6 : Git
- [ ] `git add data_processor.py && git commit`
- [ ] `git add template_generator.py && git commit`
- [ ] `git add generator.py && git commit`
- [ ] `git add REFACTORING.md && git commit`
- [ ] `git add dashboard_generator.py && git commit`
- [ ] `git push -u origin claude/review-dashboard-ideas-A2IRB`

---

## 🚨 POINTS CRITIQUES À VÉRIFIER

### 1. Imports
- [ ] `data_processor.py` : PAS de `base64`, `hashlib`, `shutil`
- [ ] `template_generator.py` : SEULEMENT `json`, `os`, `datetime`
- [ ] `generator.py` : CONTIENT `shutil` (pour copy2), `from data_processor import *`, `from template_generator import *`

### 2. Chemins fichiers
- [ ] Tous les `os.path.join()` restent identiques
- [ ] Les `os.makedirs()` restent dans `export_data()` (data_processor)
- [ ] Les `os.makedirs()` pour `archives/` restent dans `main()` (generator)

### 3. Variables partagées
```
main()
├── listings = read_listings()
├── stats = calc_stats(listings)
├── site_colors = export_data(listings, stats, data_dir)
├── generate_manifest(dashboards_dir)
├── html = generate_html(stats, site_colors)
└── Écrit HTML
```
⚠️ Important: `generate_html()` DOIT recevoir `stats` et `site_colors` (pas de changement)

### 4. Backward compatibility
- [ ] Old code appelant `python dashboard_generator.py` continue de marcher
- [ ] Old code appelant `from dashboard_generator import read_listings` continue de marcher
- [ ] Old code appelant `from dashboard_generator import main` continue de marcher

### 5. Tests
```bash
# Test 1 : Compilation
python3 -m py_compile data_processor.py
python3 -m py_compile template_generator.py
python3 -m py_compile generator.py
python3 -m py_compile dashboard_generator.py

# Test 2 : Execution
python generator.py        # Doit générer dashboard
python dashboard_generator.py  # Doit aussi générer dashboard (wrapper)
```

---

## 📝 COMMITS PRÉVUS

### Commit 1 : Extract data processing logic
```
refactor: extract data_processor.py module

- Move read_listings, calc_stats, generate_qr_code_url
- Move enrich_listings_with_metadata, compute_price_heatmap_by_city
- Move compute_timeline_data, export_data
- Remove unused imports: base64, hashlib
- Add docstrings for all functions
- Zero dependencies on template_generator
```

### Commit 2 : Extract template generation
```
refactor: extract template_generator.py module

- Move generate_manifest, generate_html
- Keep all HTML/CSS/JS strings intact
- Minimal imports: json, os, datetime
- Add docstrings for all functions
- Zero dependencies on data_processor
```

### Commit 3 : Create main orchestrator
```
refactor: create generator.py orchestrator

- Move main() from dashboard_generator.py
- Import from data_processor and template_generator
- Maintain identical logic and flow
- Single entry point for dashboard generation
```

### Commit 4 : Update documentation
```
docs: add REFACTORING.md

- Document v2.0 → v3.0 migration
- Include mapping, checklist, critical points
- Include git flow and testing steps
```

### Commit 5 : Maintain backward compatibility
```
refactor: update dashboard_generator.py as wrapper

- Import all from generator.py
- Add DEPRECATED notice
- Maintain old interface for backward compatibility
- Old imports still work
```

---

## ✅ VÉRIFICATIONS AVANT PRODUCTION

| Vérification | ✅/❌ | Notes |
|---|---|---|
| Compilation Python | ✅ | Tous les .py compilent |
| Imports circulaires | ✅ | Flow uni-directionnel |
| Backward compat | ✅ | Old imports marchent |
| Fonctionnalité | ✅ | Dashboard génère correctement |
| Chemins fichiers | ✅ | dashboards/ créé avec bonne structure |
| Docstrings | ✅ | Chaque fonction documentée |
| Git commits | ✅ | Messages clairs et atomiques |

---

## 📚 RÉFÉRENCES

- **Ancien fichier** : `dashboard_generator.py` (v2.0, 980 lignes)
- **Nouveaux fichiers** : `data_processor.py`, `template_generator.py`, `generator.py`
- **Wrapper** : `dashboard_generator.py` (updated)
- **Docs** : `REFACTORING.md` (ce fichier)

---

## 🎯 BÉNÉFICES

1. **Maintenabilité** 📈 : Chaque fichier = une responsabilité
2. **Testabilité** 🧪 : Tester data_processor indépendamment
3. **Réutilisabilité** ♻️ : Importer data_processor dans d'autres projets
4. **Évolutivité** 🚀 : Ajouter features (PDF, API, etc.) = nouveau fichier
5. **Clarté** 💡 : Code plus lisible et organisé
6. **Git** 📝 : Commits atomiques et clairs

---

**Fin du document REFACTORING.md - v3.0 Ready!**
