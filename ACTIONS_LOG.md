# 📋 ACTIONS LOG - Immo-Bot Luxembourg

**Purpose:** Track all changes, problems, and solutions to avoid repeating mistakes and enable quick recovery in future sessions.

**Format:** Each session creates a dated entry with full context.

---

## 🔄 Session 2026-02-27 — Fix Dashboard2 GitHub Pages Deployment

### Problem Summary
Dashboard2 Vue3 app returning 404 errors on GitHub Pages. Data files and Service Worker not loading.

### Root Causes Identified
1. **Service Worker path:** `/sw.js` absolute path → needed relative or full URL
2. **Data loading paths:** `/data/listings.json` absolute paths → needed relative or full URL
3. **Vite BASE_URL:** `import.meta.env.BASE_URL` not substituting at runtime
4. **GitHub Pages structure:** peaceiris/actions-gh-pages deploys from `dashboards2/` not `dashboards2/dist/`

### Solutions Applied

#### Step 1: Fix Service Worker Registration Path
**File:** `dashboards2/index.html`
**Before:** `navigator.serviceWorker.register('./sw.js')`
**After:** `navigator.serviceWorker.register('https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/sw.js')`
**Reason:** Absolute URL works reliably on GitHub Pages

**Commits:**
- ffba866: Fix Dashboard2 GitHub Pages deployment - Service Worker path

#### Step 2: Fix Data Loading Paths (Attempt 1 - Relative)
**File:** `dashboards2/src/services/dataLoader.js`
**Attempt:** Changed `/data/` to `./data/` (relative paths)
**Result:** ❌ Failed - browser still resolved to site root
**Reason:** Relative paths in compiled JS didn't work correctly

**Commit:** 8cd5007

#### Step 3: Use Vite BASE_URL (Attempt 2)
**File:** `vite.config.js`, `dataLoader.js`, `index.html`
**Attempt:** Used `import.meta.env.BASE_URL` with helper function
**Result:** ❌ Failed - BASE_URL not substituted in runtime JavaScript
**Reason:** Browser still looked for `/data/` at site root

**Commit:** f301cd6

#### Step 4: Hardcode GitHub Pages URLs (Solution ✅)
**File:** `dashboards2/src/services/dataLoader.js`
```javascript
const API_BASE = 'https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/';
function getDataUrl(filename) {
  return `${API_BASE}data/${filename}`
}
```

**File:** `dashboards2/index.html`
```javascript
const swUrl = 'https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/sw.js';
```

**Result:** ✅ Works - assets found, data loading correctly
**Reason:** Explicit URLs bypass all path resolution issues

**Commits:**
- 59721cf: Hardcode GitHub Pages URLs for data and Service Worker

#### Step 5: Correct URL Structure (/dist/ removed)
**Discovery:** GitHub Pages serves from `dashboards2/` NOT `dashboards2/dist/`
- peaceiris/actions-gh-pages copies `dashboards2/dist` → `deploy_temp/dashboards2`
- This becomes `/immo-bot-luxembourg/dashboards2/` on GitHub Pages
- Not `/immo-bot-luxembourg/dashboards2/dist/`

**File:** `dashboards2/src/services/dataLoader.js`
```javascript
// BEFORE (wrong)
const API_BASE = 'https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/dist/';

// AFTER (correct)
const API_BASE = 'https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/';
```

**File:** `dashboards2/index.html`
```javascript
// BEFORE (wrong)
const swUrl = 'https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/dist/sw.js';

// AFTER (correct)
const swUrl = 'https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/sw.js';
```

**Commit:** 35a5143

### Key Learnings for Future Sessions

#### ❌ What DOESN'T work on GitHub Pages:
- Relative paths in compiled JavaScript (`./data/` resolves from browser location, not asset location)
- `import.meta.env.BASE_URL` in runtime JavaScript (only available at build-time)
- Paths without full domain (get interpreted as site-root relative)

#### ✅ What WORKS:
- **Absolute URLs with full domain** - Most reliable
- **Hardcoded paths matching deployment structure** - Simple and predictable
- **Testing with curl to verify files exist** - Identify missing assets early

#### 🔄 GitHub Pages Deployment Flow:
1. GitHub Actions triggers on push
2. Rebuilds Dashboard2: `npm run build` → `dashboards2/dist/`
3. Runs: `python dashboard_generator.py` → updates `dashboards/` and `dashboards2/public/data/`
4. Copies to deploy folder:
   ```
   deploy_temp/
   ├── dashboards/
   └── dashboards2/ (copied from dashboards2/dist)
       ├── index.html
       ├── assets/
       ├── data/
       └── sw.js
   ```
5. peaceiris/actions-gh-pages pushes to `gh-pages` branch
6. GitHub Pages serves from: `https://zaalouni.github.io/immo-bot-luxembourg/`
7. Final URLs:
   - `https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/index.html`
   - `https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/assets/index-XXX.js`
   - `https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/data/listings.json`

### Testing Checklist
- [ ] Hard refresh browser (Ctrl+Shift+R)
- [ ] Check console (F12) for errors
- [ ] Verify data loads (check Network tab)
- [ ] Verify Service Worker registers (check Application tab)
- [ ] Click through dashboard to verify functionality

### Commands Reference

**Local development:**
```bash
python dashboard_generator.py    # Generate dashboards + sync data
npm run build                    # Build Dashboard2 (dashboards2/)
npm run dev                      # Dev server (dashboards2/)
```

**Testing GitHub Pages:**
```bash
curl https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/dist/index.html | grep "index-"
# Check what asset hash is currently deployed
```

**Git workflow:**
```bash
git add dashboards2/src/services/dataLoader.js dashboards2/index.html
git commit -m "fix: [description]"
git pull --no-rebase origin main
git push origin main
```

### Files Modified
- `dashboards2/src/services/dataLoader.js` - Data loading with hardcoded URLs
- `dashboards2/index.html` - Service Worker registration with hardcoded URL
- `.github/workflows/deploy.yml` - GitHub Actions deployment workflow
- `.nojekyll` - GitHub Pages Jekyll disable

### Commits in This Session
- ffba866 - Fix Dashboard2 GitHub Pages deployment - Service Worker path
- 8cd5007 - Fix Dashboard2 data loading paths - use relative paths
- cdcf505 - Add GitHub Actions workflow to deploy only dashboards
- f301cd6 - Use Vite BASE_URL for all dynamic paths
- 59721cf - Hardcode GitHub Pages URLs for data and Service Worker
- 35a5143 - Correct GitHub Pages URLs - remove /dist/ from paths

### Status: ✅ RESOLVED
Expected behavior: Dashboard2 loads successfully with all data and Service Worker active.

---

## 🎯 Quick Reference for Next Session

**If Dashboard2 shows 404 errors again:**
1. Check console (F12) → identify which URL is 404
2. Verify file exists: `curl https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/{path}`
3. Check if GitHub Pages URL structure changed
4. Verify hardcoded URLs in:
   - `dashboards2/src/services/dataLoader.js` (API_BASE constant)
   - `dashboards2/index.html` (SW URL)
5. Rebuild and push: `npm run build && git push origin main`

**If Service Worker won't register:**
- Verify `sw.js` file exists on GitHub Pages
- Check Service Worker scope in index.html (should match URL)
- Clear browser cache and reload

**If data doesn't load:**
- Verify data files in `dashboards2/dist/data/` exist locally
- Check API_BASE URL in dataLoader.js matches GitHub Pages structure
- Verify file paths: `data/listings.json` not `data/listings.json` (no leading slash)

---

**Last Updated:** 2026-02-27
**Maintained By:** Claude Code
**Session Duration:** Multiple fixes and tests
