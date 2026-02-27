# 🚀 GitHub Actions Deployment Guide

## Overview

The `.github/workflows/deploy.yml` workflow automatically builds and deploys **ONLY** the dashboard files to GitHub Pages.

### What gets deployed to GitHub Pages?
- ✅ `dashboards/` — Original HTML dashboard
- ✅ `dashboards2/dist/` — Modern Vue 3 dashboard
- ❌ Scrapers, Python files, .env, database — NOT published

### What stays in GitHub main branch?
- ✅ Everything (full repository)
- ✅ Safe: .env, DB, scrapers, all Python files are in the repo
- ❌ But GitHub Pages only shows dashboards/

## How it works

**Trigger**: When you push to `main` and these files change:
```
dashboards/
dashboards2/
dashboard_generator.py
database.py
config.py
listings.db
.github/workflows/deploy.yml
```

**Workflow steps**:
1. Clone repository
2. Install Node.js + Python dependencies
3. Build Dashboard2: `npm run build`
4. Generate dashboards: `python dashboard_generator.py`
5. Commit changes to `dashboards/` and `dashboards2/` only
6. Copy ONLY these folders to `gh-pages` branch
7. Deploy to GitHub Pages

## URLs

### GitHub Repository (main branch)
```
https://github.com/Zaalouni/immo-bot-luxembourg
- Contains: Everything (scrapers, .env simulation, DB, Python scripts)
- Private: .env, actual DB not committed
- Public: All source code
```

### GitHub Pages (gh-pages branch)
```
Dashboard 1: https://zaalouni.github.io/immo-bot-luxembourg/dashboards/index.html
Dashboard 2: https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/dist/index.html
- Contains: ONLY dashboard files
- No scrapers, no Python, no DB
```

## Manual Trigger

You can manually trigger the deployment without pushing:
```bash
# In GitHub UI:
Actions → "Deploy Dashboards to GitHub Pages" → Run workflow
```

Or via GitHub CLI:
```bash
gh workflow run deploy.yml
```

## Configuration

### Environment Variables

The workflow does NOT use `.env` (it's ignored). If you need secrets, add them as GitHub Secrets:

```bash
Settings → Secrets and variables → Actions → New repository secret
```

Then reference in workflow:
```yaml
env:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
```

### Customization

Edit `.github/workflows/deploy.yml`:
- Lines 8-13: Adjust trigger paths
- Line 28: Change Node version
- Line 33: Change Python version
- Line 48: Modify build command
- Line 52: Modify generation command

## Troubleshooting

### "Permission denied" on git push
- Check: Settings → Actions → General → Workflow permissions → "Read and write"

### Pages not updating
- Check: Settings → Pages → Source → Deploy from a branch
- Branch: `gh-pages`
- Folder: `/ (root)`

### Dashboard shows 404 on assets
- Run: Hard refresh (Ctrl+Shift+R)
- Clear: Browser cache

### Workflow fails silently
- Check: Actions tab → Recent runs
- Click run → See logs

## Security

✅ **What's safe**:
- `.env` is NOT committed (in `.gitignore`)
- Actual database is NOT committed
- API tokens stay LOCAL only

❌ **What's public on GitHub**:
- Scrapers source code
- Dashboard HTML/CSS/JS
- Configuration structure (but not actual values)

## Next Steps

1. Make a test push with dashboard changes
2. Go to Actions tab → Watch the workflow run
3. Check GitHub Pages → Should update automatically
4. Verify dashboards load without 404s

---

**Created**: 2026-02-27
**Maintenance**: Claude Code
