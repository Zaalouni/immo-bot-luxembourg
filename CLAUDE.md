# 🤖 Configuration Claude Code — Immo-Bot Luxembourg

**Projet:** Immo-Bot Luxembourg - Real Estate Dashboard
**Version:** 2.1 (Local-Only Mode on Linux Server)
**Mode:** ✅ Auto-Approve (Trusted Environment - LOCAL WORK ONLY)

---

## ⚠️  MODE SERVEUR LINUX + GITHUB PAGES POUR DASHBOARDS

**Configuration pour travailler EN LOCAL sur le serveur Linux + Push dashboards/ à GitHub:**
- ✅ Tous les commandes locales auto-approvées
- ✅ Test python, grep, curl, tous les outils → AUTORISÉ
- ✅ Build, test, generate dashboards → AUTORISÉ
- ✅ **PUSH À GITHUB AUTORISÉ** - dossier dashboards/ uniquement (GitHub Pages)
- 🔒 Autres dossiers restent en local (scrapers, main.py, etc.)
- 📌 Fonctionne comme environnement de production local + GitHub Pages
- 📋 **PLAN OBLIGATOIRE** avant de commencer les travaux

### 📋 WORKFLOW AVEC PLAN

1. **Avant de commencer**: Présenter un PLAN CLAIR
   - Quoi faire?
   - Comment?
   - Quels fichiers modifier?
   - Quelles tests lancer?

2. **Utilisateur approuve le plan** ✅

3. **Claude exécute SANS demander de validation**
   - Modifie les fichiers
   - Lance les tests
   - Génère les dashboards
   - Commit en local

4. **Rapport final** avec résumé des changements

```bash
# ✅ AUTORISÉ (local work + dashboards/ push)
python dashboard_generator.py     # Générer dashboards
npm run build                     # Build Dashboard2
python -m pytest                  # Tests locaux
python test_*.py                  # Tests spécifiques
grep -r "pattern" .              # Chercher patterns
curl https://...                 # Requêtes HTTP
git add ... / git commit ...      # Commit local

# ✅ PUSH AUTORISÉ - dashboards/ UNIQUEMENT
git push origin main -- dashboards/   # ✅ Push dashboards/ à GitHub Pages

# ❌ INTERDIT (autres dossiers)
git push origin main              # ❌ JAMAIS! (autres fichiers/dossiers)
git push ...                      # ❌ JAMAIS! (autres dossiers/branches)
```

---

## 🟢 PERMISSIONS AUTOMATIQUES (Sans validation)

### Git Operations (AUTO-APPROVED)

```bash
git add .                          # ✅ Ajouter tous les fichiers
git add dashboards/                # ✅ Ajouter dashboards
git add CLAUDE.md                 # ✅ Ajouter config
git add *.md                      # ✅ Ajouter docs
git add *.py                      # ✅ Ajouter scripts Python
git status                        # ✅ Vérifier état
git log --oneline -10             # ✅ Voir historique
git commit -m "message"           # ✅ Créer commit
git stash                         # ✅ Stash changements
git push origin main -- dashboards/  # ✅ AUTORISÉ - Push dashboards/ uniquement
git push origin main              # ❌ INTERDIT - PAS DE PUSH (autres dossiers)
git push ...                      # ❌ INTERDIT - AUCUN PUSH (autres)
```

### Build & Package Commands (AUTO-APPROVED)

```bash
npm install                       # ✅ Installer dépendances
npm run build                     # ✅ Build Dashboard2
npm run dev                       # ✅ Dev server Dashboard2
npm run preview                   # ✅ Prévisualiser build
npm cache clean                   # ✅ Nettoyer cache npm
```

### Tous les Commandes de Test (AUTO-APPROVED)

```bash
python dashboard_generator.py     # ✅ Générer dashboards
python test_*.py                  # ✅ Tester n'importe quel fichier
python -m pytest                  # ✅ Tests pytest
python -m py_compile *.py         # ✅ Vérifier syntax
python -c "code"                  # ✅ Scripts Python courts
grep -r "pattern" .              # ✅ Chercher patterns
curl https://url                  # ✅ Requêtes HTTP
timeout 600 python test_long.py   # ✅ Tests longs
find . -name "*.py"              # ✅ Chercher fichiers
```

### Python Testing & Execution (AUTO-APPROVED)

```bash
python dashboard_generator.py     # ✅ Générer dashboards
python test_dashboard_regression.py  # ✅ Lancer tests
python -m pytest                  # ✅ Tests pytest
python -m py_compile             # ✅ Vérifier syntax
python -c "..."                  # ✅ Exécuter code court
timeout 600 python test_*.py      # ✅ Tests longs (10min max)
```

### File Operations (AUTO-APPROVED)

```bash
Read tool                         # ✅ Lire fichiers
Edit tool                         # ✅ Modifier fichiers existants
Write tool                        # ✅ Créer nouveaux fichiers
Glob tool                         # ✅ Chercher fichiers (patterns)
Grep tool                         # ✅ Chercher contenu (regex)
```

### Bash Commands (AUTO-APPROVED)

```bash
ls -la                            # ✅ Lister fichiers
find . -name "*.py"               # ✅ Chercher fichiers
grep -r "pattern"                 # ✅ Chercher motif
wc -l fichier.py                  # ✅ Compter lignes
head -20 fichier.py               # ✅ Voir début fichier
tail -50 fichier.py               # ✅ Voir fin fichier
pwd                               # ✅ Dossier courant
cd /path/to/dir                   # ✅ Naviguer
du -sh directory/                 # ✅ Taille dossier
```

---

## 🔴 COMMANDES INTERDITES (JAMAIS auto)

```bash
git reset --hard                  # ❌ PERTE DE DONNÉES
git push --force                  # ❌ REWRITE HISTORY
git checkout -- .                 # ❌ DISCARD CHANGES
git clean -f                      # ❌ SUPPRIMER FICHIERS
rm -rf directory/                 # ❌ DESTRUCTIF
rm fichier.py                     # ❌ DESTRUCTIF
mv fichier.py new_path/           # ❌ DÉPLACER FICHIER
pip install package               # ❌ INSTALLER DÉPENDANCE
nano .env                         # ❌ MODIFIER SECRETS
```

---

## 🚫 RÈGLE CRITIQUE — PUSH AUTORISÉ UNIQUEMENT POUR dashboards/

### ✅ GIT PUSH AUTORISÉ - DASHBOARDS/ UNIQUEMENT

```bash
git push origin main -- dashboards/    # ✅ AUTORISÉ - Push dashboards/ à GitHub Pages
git push origin main                   # ❌ JAMAIS! (autres fichiers/dossiers)
git push origin develop                # ❌ JAMAIS!
git push ...                           # ❌ AUCUN PUSH (autres dossiers)
```

### ✅ CE QUI EST AUTORISÉ

```bash
git add dashboards/               # ✅ Ajouter fichiers dashboards
git add CLAUDE.md                 # ✅ Ajouter config
git add *.md *.py                 # ✅ Ajouter docs/scripts
git commit -m "message"           # ✅ Créer commit
git status                        # ✅ Vérifier état
git log                           # ✅ Voir historique
git push origin main -- dashboards/   # ✅ Push dashboards/ uniquement
```

### 🎯 Workflow - Push dashboards/ à GitHub Pages

```bash
# 1. Travailler localement
git status                        # Vérifier état local

# 2. Ajouter modifications au dashboards/
git add dashboards/
git add CLAUDE.md

# 3. Tester OBLIGATOIREMENT avant commit
python -m pytest test_dashboard_regression.py -v

# 4. Commit
git commit -m "fix: description"

# 5. ✅ PUSH AUTORISÉ POUR dashboards/ UNIQUEMENT
git push origin main -- dashboards/

# Pour autres fichiers/dossiers:
# ❌ Ne JAMAIS pousser (autres dossiers restent en LOCAL)
```

---

## 📁 STRUCTURE COMPLÈTE (LOCAL WORK)

```
immo-bot-luxembourg/ (serveur Linux)
├── dashboards/              ✅ Modifier local
│   ├── index.html
│   ├── data/
│   ├── manifest.json
│   └── archives/
├── dashboards2/             ✅ Modifier local
│   ├── src/
│   ├── dist/
│   ├── public/
│   ├── index.html
│   └── package.json
├── scrapers/                ⚠️  Lire/modifier (pas de push)
├── dashboard_generator.py   ✅ Modifier local
├── test_dashboard_regression.py  ✅ Exécuter/modifier
├── database.py              ⚠️  Modifier local (pas de push)
├── main.py                  ⚠️  Modifier local (pas de push)
├── CLAUDE.md               ✅ Config locale
├── STATUS.md               ✅ Docs locales
├── .env                    ⚠️  Ne pas modifier
├── listings.db             ⚠️  Database locale (pas de push)
├── venv/                   ⚠️  Python env (pas de push)
└── node_modules/           ⚠️  npm deps (pas de push)
```

**NOTE:** Tout travail est ✅ EN LOCAL. Aucun push à GitHub.

---

## ⚙️  CONFIGURATION PAR DÉFAUT

```
python_version: 3.7+
node_version: 14.6+
git_branch: main
git_remote: origin
test_cmd: python -m pytest test_dashboard_regression.py -v
build_cmd: npm run build (in dashboards2/)
```

---

## 📋 RÉSUMÉ RAPIDE (dashboards/ Push Autorisé)

| Action | Auto? | Notes |
|--------|-------|-------|
| `git add dashboards/` | ✅ | Toujours |
| `git add CLAUDE.md` | ✅ | Config |
| `git add *.md *.py` | ✅ | Docs & scripts |
| `git commit` | ✅ | Commit LOCAL |
| `git push origin main -- dashboards/` | ✅ | Push dashboards/ seulement |
| `git push origin main` | ❌ | JAMAIS! (autres fichiers) |
| `git push ...` | ❌ | JAMAIS! (autres dossiers) |
| `npm run build` | ✅ | Toujours |
| `npm install` | ✅ | Toujours |
| `python dashboard_generator.py` | ✅ | Toujours |
| `python -m pytest` | ✅ | Toujours |
| `git reset --hard` | ❌ | JAMAIS auto |
| `git push --force` | ❌ | JAMAIS auto |
| `rm -rf` | ❌ | JAMAIS auto |

---

## 🚀 WORKFLOW AVEC PLAN (LOCAL ONLY)

### Phase 1: Plan & Approbation

```
UTILISATEUR: "Je veux faire X"
        ↓
CLAUDE: "Voici mon plan d'action:
        - Étape 1: Lire les fichiers A, B, C
        - Étape 2: Modifier le fichier D
        - Étape 3: Lancer test E
        - Étape 4: Générer dashboard F
        Autorises-tu ce plan?"
        ↓
UTILISATEUR: "Approuvé ✅" ou "Changemet X"
```

### Phase 2: Exécution Auto (Sans validation)

```bash
# Une fois plan approuvé → EXECUTION AUTOMATIQUE

# 1. Lancer Claude Code
claude code . --model claude-haiku-4-5-20251001

# 2. Claude exécute le plan SANS DEMANDER
# - Lit fichiers avec Read tool
# - Modifie avec Edit/Write tools
# - Lance tests: python -m pytest test_*.py
# - Génère dashboards: python dashboard_generator.py
# - Lance grep/curl/commandes requises

# 3. Pas d'interruption pendant l'exécution
# - Tous les commandes auto-approvées
# - Tests en parallèle si possible
# - Build & deploy automatique

# 4. Résumé final
# - Quoi a été fait
# - Résultats des tests ✅/❌
# - Fichiers modifiés
# - Commit local effectué
```

### Phase 3: Rapports & Logs

```bash
# À la fin: rapport complet
- ✅ Tâches complétées
- 📊 Résultats des tests
- 📝 Fichiers modifiés
- 🔍 Logs d'erreurs (si any)
- 💾 Commits locaux effectués
```

---

## 🔐 NOTES IMPORTANTES

1. **Ce fichier est le contrat pour LOCAL WORK + dashboards/ PUSH**
   - Serveur Linux = environnement de travail local
   - dashboards/ = poussé à GitHub Pages automatiquement
   - Autres dossiers (scrapers, main.py, etc.) restent en local uniquement

2. **PLAN-BASED WORKFLOW (OBLIGATOIRE)**
   - ✅ Claude présente un PLAN clair AVANT de commencer
   - ✅ Utilisateur approuve le plan
   - ✅ Claude exécute SANS VALIDATION sur chaque commande
   - ✅ Rapport final avec résumé des changements

3. **Auto-approve = actions safe locales + dashboards/ push**
   - ✅ git add/commit (commits locaux)
   - ✅ npm build/install
   - ✅ python tests (tous: pytest, grep, curl, etc.)
   - ✅ Générer dashboards
   - ✅ Chercher patterns, faire requêtes HTTP
   - ✅ `git push origin main -- dashboards/` (AUTORISÉ)
   - ❌ `git push origin main` (JAMAIS! autres fichiers)

4. **JAMAIS auto pour actions risquées**
   - rm -rf (destructif)
   - git reset --hard (perte de données)
   - git push --force (JAMAIS!)
   - git push origin main (JAMAIS! sans -- dashboards/)
   - .env ou secrets

5. **Avant chaque commit/push, TOUJOURS:**
   - ✅ Vérifier `git status`
   - ✅ Tests passent (python -m pytest)
   - ✅ Code valide
   - ✅ Pas de .env ou secrets dans dashboards/
   - ✅ Push dashboards/ après commit réussi

---

**Créé:** 2026-02-27
**Version:** 2.2 - Local + dashboards/ GitHub Push
**Statut:** ✅ Active

🎯 **Mode LOCAL WORK + dashboards/ GitHub Push** ✅
- Wortimmo + Immoweb bloques par Cloudflare/CAPTCHA → remplacer par nouveaux sites
- Unicorn : CAPTCHA intermittent, peu d'annonces, filtrage surface strict
- Filtrage duplique (chaque scraper + main.py) → a centraliser v3.0
- Pas de tests automatises (uniquement test_scrapers.py manuel)

## Docs detaillees
- architecture.md : flux complet, schema DB, roles fichiers
- analyse.md : historique corrections, problemes, metriques
- planning.md : toutes les actions avec statut/date/version
