# ✅ REGRESSION VALIDATION CHECKLIST

Use this checklist **before every commit/push** to ensure no functionality has been broken.

## 🧪 Automated Tests

Run the regression test suite:

```bash
python -m pytest test_dashboard_regression.py -v
```

**Expected Result**: ✅ All tests pass (20+ tests)

## 📊 Data Integrity

- [ ] Total listings > 0
- [ ] All listings have required keys (listing_id, site, city, price, surface, url, published_at)
- [ ] No duplicate listing IDs
- [ ] All prices are positive numbers
- [ ] All URLs are valid (start with http)
- [ ] All cities have names (not empty)
- [ ] All published_at dates are valid ISO format

## 📈 Statistics Validation

- [ ] Total count matches actual listings
- [ ] avg_price is between min_price and max_price
- [ ] avg_surface is > 0 and reasonable
- [ ] By-city stats: all cities appear
- [ ] By-site stats: all sites counted, totals match

## 🔧 Filters Working

Test each filter manually:

- [ ] **City Filter**: Dropdown shows all unique cities (dropdown should match number of cities)
- [ ] **Price Filter**: Min/max inputs work, filters correctly
- [ ] **Site Filter**: Checkboxes show all sites, multi-select works
- [ ] **Surface Filter**: Minimum surface filter works (shows only listings >= value)
- [ ] **Date Filter**: Date range picker works (if implemented)

**Test Command**:
```bash
python dashboard_generator.py  # Regenerate data
# Then open dashboards/index.html in browser
```

## 📁 Export Files

Verify all data files are generated:

- [ ] `dashboards/data/listings.json` (valid JSON, has listings)
- [ ] `dashboards/data/stats.js` (has const STATS = {...})
- [ ] `dashboards/data/anomalies.js` (has const ANOMALIES = {...})
- [ ] `dashboards/data/market-stats.js` (has const MARKET_STATS = {...})
- [ ] `dashboards/data/new-listings.json` (has recent listings)
- [ ] `dashboards/data/listings.js` (has const LISTINGS = [...])

## 🌐 Dashboard Pages

Open each page in browser and verify:

- [ ] **index.html** - Renders without JS errors, shows all 4 stats cards
- [ ] **new-listings.html** - Shows newest listings first, time_ago badges work
- [ ] **anomalies.html** - Shows HIGH (>2.5x median) and GOOD_DEAL (<0.7x median) flags
- [ ] **stats-by-city.html** - Shows per-city statistics table

## 🎨 UI/UX Checks

- [ ] All pages load without JavaScript errors (console clean)
- [ ] Tables are sortable (click column headers)
- [ ] Filters update results in real-time
- [ ] Mobile responsive (tested on mobile or dev tools)
- [ ] All external links work (click 3+ listings)

## 📦 Performance

- [ ] Page load time < 2 seconds
- [ ] No console errors or warnings
- [ ] Service worker loads (Network tab shows sw.js)
- [ ] PWA manifest valid (check Application tab)

## Dashboard2 (Vue App)

If Dashboard2 is being used:

```bash
cd dashboards2
npm install
npm run build
npm run dev  # or serve dist/
```

- [ ] Vue app builds without errors
- [ ] All 5 filters work (city, price, site, surface, date)
- [ ] All 8 tabs display (Table, City, Price, Map, New, Anomalies, Stats, Photos)
- [ ] Sorting works in table view
- [ ] Map loads when tab clicked
- [ ] No console JavaScript errors

## 🔄 Data Sync (Dashboard2)

- [ ] Data synced to `dashboards2/public/data/` after running `dashboard_generator.py`
- [ ] Files match: listings.json, stats.js, anomalies.js, market-stats.js
- [ ] Dashboard2 loads data correctly from `/data/` folder

## 📝 Pre-Commit Checklist

Before committing:

```bash
# Run tests
python -m pytest test_dashboard_regression.py -v

# Check syntax
python -m py_compile dashboard_generator.py
python -m py_compile test_dashboard_regression.py

# If modified Dashboard2:
cd dashboards2
npm run build  # Should complete successfully
cd ..

# Add files
git add dashboard_generator.py
git add test_dashboard_regression.py REGRESSION_CHECK.md
git add dashboards/  # If modified
git add dashboards2/ # If modified

# Commit
git commit -m "Fix: <description>"

# Push
git push origin main
```

## 🚨 If Tests Fail

**Do NOT commit if tests fail**. Instead:

1. Check error messages
2. Review recent changes
3. Fix the issue
4. Re-run tests
5. Only commit when ✅ all pass

## 📞 Common Issues

| Issue | Solution |
|-------|----------|
| "No module named 'dashboard_generator'" | Run from repo root: `cd immo-bot-luxembourg-fresh` |
| "STATS not found in stats.js" | Regenerate: `python dashboard_generator.py` |
| Filters not working | Clear browser cache, reload page |
| Map not loading | Check Leaflet CDN is accessible |
| Service worker failing | Check network permissions, check console for HTTPS requirement |

## ✅ Validation Passed!

If all checks pass, the release is safe:

```bash
✅ Automated tests: 20/20 pass
✅ Data integrity: All checks passed
✅ Filters: All 5 working
✅ Exports: All 6 files generated
✅ Dashboards: 4 pages rendering
✅ Performance: Load time acceptable
✅ No console errors
✅ Service worker active

→ Ready to git push origin main ✅
```

---

**Last Updated**: 2026-02-27
**Test Count**: 20+ regression tests
**Maintained By**: Claude Code
