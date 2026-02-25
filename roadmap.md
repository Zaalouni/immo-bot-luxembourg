# 🎯 Roadmap Immo-Bot — Recommandations Claude Code

> Analyse complète de l'état actuel, corrections hier (24 fév), et direction future

---

## 📊 État Actuel (25 février 2026)

### Dashboard
- **Status:** MVP ~75% (fonctionnel, features avancées incomplètes)
- **Données:** 132 annonces, 77 villes, 6 sites, 94.7% GPS coverage
- **Hier (24 fév):** 81 corrections bugs HTML/syntaxe (accolades, Jinja2)

### Bot Scraping
- **Status:** v2.6 production (7/9 scrapers actifs)
- **Dernière action:** Pagination tous scrapers (+309 annonces)
- **Problèmes:** 2/9 sites bloqués (Wortimmo, Immoweb)

### Architecture
- **2 générateurs redondants:** `dashboard_generator.py` vs `dashboard.py` (confusion)
- **Filtrage dupliqué:** Dans 9 scrapers + main.py (maintenance cauchemar)
- **Pas d'async:** Boucle scraping = 2-3 min (séquentiel)
- **Pas de tests:** Zéro couverture (risque régression)

---

## 🔧 Correction Hier (24 février) — Analyse

**Symptôme:** 81 commits = "regenerer dashboard - TOUS les bugs fixes 1-81"

**Diagnostic probable:**
- Template HTML avait accolades mal fermées (`{{}}` malformé)
- Variables Jinja2 non échappées
- Syntaxe Bootstrap/Leaflet incohérente
- Résultat: HTML impossible à parser → correction massive

**Leçon:** Préférer `dashboard_generator.py` (Python-safe) vs `dashboard.py` (template error-prone)

---

## ✅ Recommandations — Démarche ACTUELLE (Dashboard)

### Phase 1: Stabilisation & Nettoyage (2-3 jours)

| Action | Effort | Priorité | Raison |
|--------|--------|----------|--------|
| **Supprimer `dashboard.py`** | 5 min | 🔴 URGENT | Redondant + confusing |
| **Supprimer `templates/dashboard.html`** | 5 min | 🔴 URGENT | Conçu pour API inexistant |
| **Supprimer `templates/` dir vide** | 2 min | 🟡 MOYEN | Cleanup |
| **Valider 100% listings sans erreur HTML** | 10 min | 🔴 URGENT | QA pipeline |
| **Test end-to-end:** `python dashboard_generator.py` → ouvrir HTML | 15 min | 🔴 URGENT | Validation workflow |

**Résultat:** Codebase propre, une seule source de vérité (`dashboard_generator.py`)

---

### Phase 2: Compléter Features (3-5 jours)

Actuellement 8 tabs, dont 3 incomplets:

| Tab | Status | Effort | Action |
|-----|--------|--------|--------|
| 📋 **Tableau** | ✅ Complet | — | Rien |
| 📊 **Sites (Charts)** | ❌ Manquant | 30min | Initialiser Chart.js doughnut |
| 📍 **Villes (Charts)** | ❌ Manquant | 30min | Initialiser Chart.js bar |
| 💰 **Par prix** | ✅ Complet | — | Rien |
| 🗺️ **Carte** | ✅ Complet | — | Rien |
| 🔥 **Densité** | ❌ Manquant | 45min | Heatmap canvas + calculs |
| 📈 **Timeline** | ❌ Manquant | 1h | Slider interactif dates historiques |
| 🚨 **Anomalies** | ❌ Manquant | 1h | Detection + flagging outliers |

**MVP minimum:** Chart.js (2 tabs) + Timeline (1 tab) = 2h
**Complet:** + Heatmap + Anomalies = 4h supplémentaires

**Priorisation recommandée:**
1. Chart.js (haute valeur, facile)
2. Timeline (moyenne valeur, facile)
3. Heatmap (bonus, moyen effort)
4. Anomalies (bonus, moyen effort)

---

### Phase 3: Production-Ready (1 semaine)

- [ ] Ajouter **logging** dans `dashboard_generator.py` (fichier JSON avec timestamps)
- [ ] Ajouter **tests pytest** (vérifier HTML valide, données complètes, pas d'erreurs JS)
- [ ] **Monitoring:** GPS coverage alert si <90%
- [ ] **Archiving:** Cleanup automatique archives >30 jours
- [ ] **PWA versioning:** Service worker timestamp auto-update
- [ ] **Documentation:** Ajouter section Dashboard dans architecture.md

---

## 🚀 Recommandations — Démarche FUTURE

### Timeline Proposé

```
Semaine 1   : Dashboard stabilisation + Chart.js
Semaine 2   : Dashboard complet (Timeline, Heatmap, Anomalies) + Tests
PAUSE BREAK : Valider dashboard en production

Semaine 3   : Async scrapers (PRIORITÉ HAUTE)
Semaine 4   : Centraliser filtrage + tests scrapers
Semaine 5-6 : Remplacer Wortimmo/Immoweb + tests intégration
Semaine 7-8 : Tests end-to-end complets
```

---

### Async Scrapers (Semaine 3) — PRIORITÉ 🔴 HAUTE

**Problème actuel:** Boucle scraping = 2-3 minutes (séquentiel)
```
Athome (15s) → Immotop (10s) → Luxhome (8s) → VIVI (20s) → ...
→ Total: 60-120s = attendre longtemps entre cycles
```

**Solution async:**
```
Athome (15s)    ┐
Immotop (10s)   │ En parallèle
Luxhome (8s)    │ = <30sec total
VIVI (20s)      ┤
Nextimmo (12s)  │
...             ┘
```

**Effort:** 1 semaine (3-4 jours refactoring + tests)
**Impact:** 🔴 CRITIQUE (UX, réactivité, Telegram notifications plus rapides)
**Technique:** `asyncio` + `aiohttp` (drop Selenium → Playwright async pour durée)

**Étapes:**
1. Refactor scrapers HTTP (Athome, Immotop, Nextimmo, Luxhome) → async
2. Garder Selenium (VIVI, Newimmo, Unicorn) synchrone (complexe async)
3. Lancer mix async + sync en parallèle dans main.py
4. Mesurer before/after timing
5. Progressivement migrer Selenium → Playwright async

---

### Centraliser Filtrage (Semaine 4) — PRIORITÉ 🟡 MOYEN

**Problème:** `_matches_criteria()` dupliqué dans 9 scrapers + main.py
```
athome_scraper.py:       if price < MIN_PRICE: continue
immotop_scraper.py:      if price < MIN_PRICE: continue
luxhome_scraper.py:      if price < MIN_PRICE: continue
...
main.py:                 if not _matches_criteria(listing): continue
```
→ Maintenance cauchemar, inconsistances, hard à tester

**Solution:**
```python
# utils.py — CENTRALISÉ
def apply_criteria(listing):
    """Filtre unique pour tous scrapers + main.py"""
    if listing['price'] < MIN_PRICE: return False
    if listing['rooms'] < MIN_ROOMS: return False
    ...
    return True

# Utilisation:
for listing in scraper.scrape():
    if apply_criteria(listing):
        db.insert(listing)
```

**Effort:** 2-3 jours
**Impact:** 🟡 MOYEN (maintenance + robustesse)

**Étapes:**
1. Créer `utils.py:apply_criteria()` centralisé (copiée de main.py)
2. Importer dans tous 9 scrapers (remplacer code local)
3. Main.py applique au 2e level (double-check + dedup)
4. Tests: vérifier même résultat avant/après

---

### Remplacer Wortimmo/Immoweb (Semaine 5-6) — PRIORITÉ 🟡 MOYEN

**Blocage:** 2/9 sites inaccessibles
- **Wortimmo:** Cloudflare bloque donnees listing (prix = dropdown filtres)
- **Immoweb:** CAPTCHA bloque page 1

**Objectif:** Trouver 2 nouveaux sites luxembourgeois (10-20% annonces de plus)

**Recherche recommandée:**
- Portails immobiliers luxembourgeois non-scrapés
- Sites "proprios" (direct propriétaires) ou agences taille moyenne
- Vérifier robots.txt + ToS (légalité scraping)
- Éviter Cloudflare/CAPTCHA

**Candidats potentiels:**
- Portails immobiliers régionaux (Lorraine/Wallonie avec prix LU)
- Annonces "Facebook Marketplace Luxembourg"
- Agences indépendantes JSON APIs (si publiques)

**Effort par site:** 3-5 jours (exploration + dev + tests)
**Impact:** 🟡 MOYEN (+15-20% annonces)

---

### Tests Automatisés (Semaine 7-8) — PRIORITÉ 🟡 MOYEN/LONG-TERME

**Status actuel:** Zéro tests (risk 🔴 CRITIQUE)

**Couverture recommandée:**

| Module | Tests | Effort | Impact |
|--------|-------|--------|--------|
| **Scrapers** | Unit tests (mock API + HTML) | 1 jour | Haut |
| **Database** | Integration tests (SQLite temp) | 1 jour | Haut |
| **Dedup** | Edge cases (similar listings) | 1 jour | Haut |
| **Notifier** | Mock Telegram API | 1 jour | Moyen |
| **Utils** | GPS distance, geocoding | 1 jour | Bas |
| **Dashboard** | HTML validation, JS errors | 1 jour | Moyen |

**Framework:** pytest (standard Python)
**Minimum viable:** 60% couverture (scrapers + DB + dedup)

---

## 📈 Matrice Priorités

### Impact vs Effort (Bulle plot)

```
HIGH IMPACT, LOW EFFORT (DO NOW):
  ✅ Dashboard Chart.js              (30min, haute valeur)
  ✅ Dashboard Timeline              (1h, haute valeur)
  ✅ Supprimer code legacy           (10min, critique cleanup)

HIGH IMPACT, HIGH EFFORT (DO SOON):
  ⚠️ Async scrapers                 (3-4 jours, critique perf)
  ⚠️ Tests pytest                   (5-6 jours, critique robustesse)

MEDIUM IMPACT, MEDIUM EFFORT:
  🟡 Centraliser filtrage           (2-3 jours, maintenance)
  🟡 Remplacer Wortimmo/Immoweb     (5-6 jours, +annonces)

LOW IMPACT, HIGH EFFORT (SKIP):
  ❌ Dashboard Heatmap              (45min, insight bonus)
  ❌ Dashboard Anomalies            (1h, insight bonus)
```

---

## 📋 Action Items — Prêt à Exécuter

### IMMÉDIAT (2-3 jours)
- [ ] Supprimer `dashboard.py` (5 min)
- [ ] Supprimer `templates/dashboard.html` (5 min)
- [ ] Valider HTML sans erreurs (10 min)
- [ ] Test end-to-end dashboard_generator.py (15 min)
- [ ] Ajouter Chart.js initialisation (30 min)
- [ ] Ajouter Timeline interactif (1h)

**Commit:** `dashboard: cleanup legacy + chart.js + timeline`

---

### COURT-TERME (4-5 jours)
- [ ] Ajouter Heatmap visualization (45 min)
- [ ] Ajouter Anomalies detection (1h)
- [ ] Ajouter tests pytest (1-2 jours)
- [ ] Ajouter logging/monitoring (2h)
- [ ] Mettre à jour CLAUDE.md version dashboard (30 min)

**Commits:**
- `dashboard: add heatmap`
- `dashboard: add anomalies detection`
- `dashboard: add pytest coverage`
- `dashboard: v1.0 production-ready`

---

### MOYEN-TERME (Semaines 3-4)
- [ ] Async scrapers implementation
- [ ] Centraliser filtrage
- [ ] Tests scrapers unit

**Commits:**
- `scrapers: async http implementation`
- `utils: centralize criteria filtering`
- `tests: add pytest scrapers coverage`

---

### LONG-TERME (Semaines 5-8)
- [ ] Trouver + implémenter 2 nouveaux scrapers
- [ ] Tests integration DB + dedup
- [ ] Tests end-to-end dashboard + bot

---

## 🎯 Succès Criteria

### Dashboard (Fin Semaine 2)
- ✅ Zéro code legacy
- ✅ Chart.js fonctionne (2 charts)
- ✅ Timeline fonctionne (10 dates archive)
- ✅ 100% listings affichés sans erreur
- ✅ Tests pytest passing (>80% couverture)
- ✅ Production-ready (logging + monitoring)

### Bot (Fin Semaine 8)
- ✅ Async scrapers: <30 sec par cycle (vs 2-3 min actuellement)
- ✅ Centralized filtering (1 source de vérité)
- ✅ 9/9 scrapers actifs (remplacer 2 bloqués)
- ✅ Tests coverage >70% (tous modules)
- ✅ Zéro régression (tests régression + monitoring)

---

## 📚 Documents Liés

- **CLAUDE.md** — Contexte bot + instructions Claude Code
- **analyse.md** — Historique corrections + problèmes connus
- **architecture.md** — Flux technique complet
- **planning.md** — Dashboard HTML brief (ACTUEL)

---

## 💡 Notes Finales

### Philosophie de dev
1. **Stabiliser d'abord** (dashboard MVP 100%)
2. **Puis optimiser** (async scrapers)
3. **Puis tester** (pytest coverage)
4. **Puis scaler** (nouveaux scrapers)

### Parallélisation
- ✅ Dashboard + Async scrapers PEUVENT tourner en parallèle (domaines indépendants)
- ❌ Dashboard + Centraliser filtrage = dépendance (filtrage affecte scrapers)
- ❌ Ne pas commencer async tant que tests scrapers manquent (risque régression)

### Maintenance long-terme
- Lire CLAUDE.md + analyse.md à chaque session
- Lancer diagnostic avant chaque action (scripts diagnostic)
- Tester avant committer
- Documenter corrections dans analyse.md

---

**Dernière mise à jour:** 25 février 2026 — Claude Code analysis
**Branche:** claude/list-markdown-files-6PVxa
**Prêt à exécuter après approbation**
