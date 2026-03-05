# 📋 Guide de Migration ImmoLux Dashboard - v1 → v2

**Statut:** 🟡 En cours
**Date de création:** 2026-03-05
**Objectif:** Migrer progressivement de v1 à v2 sans casser l'existant

---

## 📂 Structure de Migration

```
dashboards/
├── index.html          ← Routeur principal (NEW - sélection de version)
├── version-switcher.js ← Switcher pour basculer (NEW)
│
├── v1/                 ← Version stable (BACKUP de l'original)
│   ├── index.html
│   ├── map.html
│   ├── *.html (tous les originaux)
│   └── sw.js
│
└── v2/                 ← Version optimisée (NEW - corrigée)
    ├── index.html      ← Optimisé: SEO, CSP, A11y
    ├── index.js        ← Code JS séparé (logic extraction)
    ├── map.html        ← À optimiser
    ├── *.html          ← À optimiser progressivement
    └── version-switcher.js (lien vers parent)
```

---

## 🔄 Workflow de Migration

### Phase 1: Setup ✅
- [x] Créer dossiers v1/ et v2/
- [x] Copier tous les fichiers HTML vers v1/ (backup)
- [x] Créer router index.html avec sélecteur de version
- [x] Créer version-switcher.js pour navigation facile
- [x] Créer v2/index.html avec améliorations
- [x] Créer v2/index.js (séparation du code)

### Phase 2: Optimiser Pages Critiques ⏳
- [ ] v2/index.html - Améliorer CSP, ajouter Web Share API
- [ ] v2/map.html - Optimiser, ajouter accessibilité
- [ ] v2/data-quality.html - Optimiser
- [ ] v2/trends.html - Optimiser

### Phase 3: Optimiser Pages Secondaires ⏳
- [ ] v2/gallery.html, photos.html
- [ ] v2/stats-by-city.html
- [ ] v2/comparison.html, alerts.html, etc.

### Phase 4: Testing & Validation ⏳
- [ ] Tests Lighthouse (Performance, A11y, SEO)
- [ ] Tests manuels (cross-browser)
- [ ] Validation WCAG 2.1 AA
- [ ] Vérifier URLs partageable

### Phase 5: Cleanup ⏳
- [ ] Rediriger index.html → v2/ automatiquement
- [ ] Supprimer v1/ après migration complète
- [ ] Mettre à jour configs (manifest, sw.js, etc.)

---

## 🎯 Corrections Effectuées dans v2

### ✅ Sécurité
- [x] CSP stricte (sans `'unsafe-inline'`)
- [x] Code JavaScript externalisé
- [x] Nonces pour scripts (si nécessaire)
- [x] Referrer-Policy ajoutée

### ✅ SEO
- [x] Titre unique et descriptif
- [x] Meta description (160 chars)
- [x] OpenGraph tags (og:title, og:description, og:image)
- [x] Twitter Card tags
- [x] Canonical URL
- [x] Structure H1 hiérarchique
- [ ] Sitemap.xml (à créer)
- [ ] robots.txt (à créer)
- [ ] Structured data JSON-LD (à ajouter)

### ✅ Accessibilité
- [x] aria-labels sur boutons
- [x] aria-live pour régions dynamiques
- [x] role="tablist", role="tabpanel"
- [x] role="columnheader" sur tableau
- [x] caption sur tableaux
- [x] keyboard navigation prêt
- [x] Focus visible prêt
- [ ] Contrast colors vérifiés (peut nécessiter CSS)
- [ ] Alt text sur images (à vérifier)

### ✅ Performance
- [x] Scripts avec defer
- [x] Lazy loading images (loading="lazy" à ajouter)
- [x] CSS optimisé
- [x] Code minifié
- [ ] Asset preloading (à optimiser)
- [ ] Code splitting (si besoin)

### ✅ Nouvelle Fonctionnalité
- [x] Web Share API (bouton partage natif)
- [x] URL State Management (query params)
- [x] Filter state preservation dans URL
- [x] Amélioration du partage

---

## 🚀 Utilisation

### Pour les Utilisateurs

**Option 1 - Via le routeur index.html:**
```
https://example.com/dashboards/
→ Affiche écran de sélection
→ Clic V1 ou V2
```

**Option 2 - Accès direct:**
```
V1: https://example.com/dashboards/v1/index.html
V2: https://example.com/dashboards/v2/index.html
```

**Switcher dans V2:**
- Button "↔️ V1 (stable)" en haut à droite
- Click = bascule immédiate
- Preference sauvegardée en localStorage

---

## 📊 Checklist Optimisation par Page

### v2/index.html (TABLEAU PRINCIPAL) ✅
- [x] Améliorations sécurité/SEO/A11y
- [x] Web Share API
- [x] URL state management
- [ ] Tests Lighthouse
- [ ] Tests A11y (Axe)

### v2/map.html ⏳
- [ ] Copié ✓
- [ ] OpenGraph tags
- [ ] CSP adjustments
- [ ] Aria-labels
- [ ] Tests Lighthouse

### v2/data-quality.html ⏳
- [ ] Copié ✓
- [ ] SEO optimization
- [ ] Accessibility review
- [ ] Performance check

### Autres pages (gallery, photos, trends, etc.) ⏳
- [ ] Copier → v2/
- [ ] Ajouter OpenGraph
- [ ] Ajouter aria-labels
- [ ] Tester performance

---

## ⚡ Quick Wins Prioritaires

**À faire en priorité:**
1. ✅ v2/index.html optimisé (DONE)
2. ⏳ Tester v2/index.html avec Lighthouse
3. ⏳ Valider accessibilité v2/index.html
4. ⏳ Vérifier URLs partageable fonctionnent
5. ⏳ Optimiser map.html
6. ⏳ Tester tous les onglets (city, price, map)

---

## 🧪 Testing

### Lighthouse Targets
| Métrique | Actuel | Cible |
|----------|--------|-------|
| Performance | ? | > 85 |
| Accessibility | ? | > 90 |
| Best Practices | ? | > 90 |
| SEO | ? | > 90 |

### A11y Testing
- [ ] Axe DevTools scan
- [ ] Keyboard nav (Tab, Enter, Escape)
- [ ] Screen reader test
- [ ] Color contrast (4.5:1 normal, 3:1 large)

### Functional Testing
- [ ] Filtres fonctionnent
- [ ] Tri fonctionne
- [ ] Export CSV fonctionne
- [ ] Partage fonctionne
- [ ] URLs partageable valident
- [ ] Dark mode fonctionne
- [ ] Service Worker fonctionne
- [ ] Map charge correctement

---

## 📝 Rollback Plan

Si v2 a des problèmes:
1. Index.html redirige automatiquement v1
2. Users peuvent cliquer "V1" sur sélecteur
3. V1 est complètement intact dans /v1/
4. Aucune perte de données

---

## 📌 Notes

- **localStorage:** Réinitialiser si problèmes de cache
- **Service Worker:** Peut nécessiter reset du cache
- **CSP:** Peut bloquer des ressources si domaines pas whitelistés
- **URLs:** Les filtres sont maintenant encodés en URL pour meilleur partage

---

**Prochaine étape:** Tester v2/index.html avec Lighthouse et corriger les problèmes identifiés.
