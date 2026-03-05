# 🔍 Data Loading Debugging Guide

## Quick Diagnosis

When the v2 dashboard pages don't show data, follow these steps:

### Step 1: Open Browser Console
- **Chrome/Firefox/Edge:** Press `F12` or `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Shift+I` (Mac)
- **Safari:** Enable Developer Menu in Preferences, then press `Cmd+Option+I`

### Step 2: Look for Debug Messages

The following debug messages should appear in the console when pages load:

#### ✅ SUCCESS (Everything is working)
```
[DEBUG] listings.js loaded successfully, LISTINGS array has 166 items
[DEBUG] LISTINGS available: object (array of 166 items)
✓ ImmoLux Dashboard v2 initialized
```

#### ❌ PROBLEM (Data not loading)
```
[DEBUG] listings.js loaded successfully, LISTINGS array has 166 items
[DEBUG] LISTINGS available: undefined
LISTINGS data not available
```

---

## What Each Message Means

### `[DEBUG] listings.js loaded successfully, LISTINGS array has 166 items`
- **Status:** ✅ **GOOD** - The data file was loaded and parsed correctly
- **Location:** dashboards/v2/data/listings.js
- **Number:** Should be 166 (or current count)

### `[DEBUG] LISTINGS available: object (array of 166 items)`
- **Status:** ✅ **GOOD** - JavaScript can access the LISTINGS variable
- **Type:** Should be "object" and show array size
- **Next Step:** Check if charts/maps render

### `[DEBUG] LISTINGS available: undefined`
- **Status:** ❌ **PROBLEM** - LISTINGS variable is not defined
- **Possible Causes:**
  1. Network request failed (404 error)
  2. Browser cache issue
  3. File corruption during transfer
  4. Relative path is wrong

### `LISTINGS data not available`
- **Status:** ❌ **PROBLEM** - init() function checked and LISTINGS is not available
- **Result:** Dashboard pages won't display data
- **Fix:** Check console for the debug message above to find root cause

---

## Debugging Checklist

### 1. Network Tab (Most Important)
- Open **Developer Tools** → **Network** tab
- **Reload the page** (Ctrl+R or Cmd+R)
- Look for requests to `data/listings.js`
- **Status should be: 200 (OK)**
  - If **404**: File not found on server
  - If **403**: Permission denied
  - If **500**: Server error
  - If **pending**: File is still loading

### 2. Console Tab
- Check for any red error messages
- Look for the debug messages listed above
- Note any error details

### 3. Application Tab (For localStorage)
- **Chrome/Edge:** Developer Tools → **Application**
- **Firefox:** Developer Tools → **Storage**
- Check **localStorage** for:
  - `darkMode` value
  - `sortCol` value
  - `priceAlerts` value
- If these don't exist, localStorage might be blocked

### 4. File Structure (For Developers)
Verify files exist:
```
dashboards/
├── v2/
│   ├── data/
│   │   ├── listings.js ← Must exist
│   │   ├── stats.js
│   │   └── city-transports.json
│   ├── index.html ← References data/listings.js
│   ├── trends.html
│   └── ...
├── styles.css ← v2/index.html references ../styles.css
├── dark-mode.js
└── icon.svg
```

---

## Common Issues & Solutions

### Issue: 404 Error on data/listings.js

**Cause:** Browser can't find the file

**Solutions:**
1. **Check file exists:** Run in terminal:
   ```bash
   ls -l dashboards/v2/data/listings.js
   ```
2. **Check permissions:**
   ```bash
   chmod 644 dashboards/v2/data/listings.js
   ```
3. **Clear browser cache:**
   - Chrome: Settings → Privacy → Clear browsing data
   - Firefox: History → Clear Recent History
4. **Hard refresh:**
   - Chrome/Firefox: `Ctrl+Shift+R` or `Cmd+Shift+R`

### Issue: LISTINGS undefined but no 404 error

**Cause:** File loaded but syntax error in listings.js

**Solutions:**
1. **Check syntax:**
   ```bash
   node -c dashboards/v2/data/listings.js
   ```
2. **Look for error in console:**
   - Red error messages above the debug logs
   - Syntax errors prevent file from executing

### Issue: Only some pages show data

**Cause:** Inconsistent relative paths between pages

**Solutions:**
1. **Check all pages use same path pattern:**
   ```bash
   grep -r 'src="data/listings.js"' dashboards/v2/
   ```
2. **All pages should use:**
   - `<script src="data/listings.js">` (for pages in v2/)
   - NOT `<script src="../data/listings.js">` (wrong path)

### Issue: Works locally but not on GitHub Pages

**Cause:** Absolute paths don't work with GitHub Pages URL structure

**Solutions:**
1. **Use relative paths only:**
   - ✅ GOOD: `<script src="data/listings.js">`
   - ❌ BAD: `<script src="/dashboards/v2/data/listings.js">`
2. **Verify paths work:**
   - Test locally: `file:///home/user/.../dashboards/v2/index.html`
   - Test on server: `https://zaalouni.github.io/immo-bot-luxembourg/dashboards/v2/index.html`

---

## Message Locations in Code

### listings.js
Line at the end of the file:
```javascript
console.log('[DEBUG] listings.js loaded successfully, LISTINGS array has', LISTINGS.length, 'items');
```

### index.js
In `init()` function (line ~671):
```javascript
console.log('[DEBUG] LISTINGS available:', typeof window.LISTINGS, ...);
if (!window.LISTINGS || !Array.isArray(window.LISTINGS)) {
    console.error('LISTINGS data not available');
}
```

### trends.html & data-quality.html
In `init()` or `calculateMetrics()` function:
```javascript
console.log('[DEBUG] LISTINGS available:', typeof LISTINGS, ...);
if(!LISTINGS) {
    console.error('[DEBUG] LISTINGS is not available');
}
```

---

## For GitHub Pages Deployment

When deploying to GitHub Pages:

1. **Verify files were pushed:**
   ```bash
   git log --oneline dashboards/v2/data/listings.js | head -1
   ```

2. **Check remote has files:**
   ```bash
   git ls-tree -r origin/branch dashboards/v2/data/
   ```

3. **Test URL directly in browser:**
   - Replace `zaalouni` with your username
   - Replace `immo-bot-luxembourg` with your repo name
   - URL: `https://zaalouni.github.io/immo-bot-luxembourg/dashboards/v2/data/listings.js`
   - Should download a JavaScript file, not show 404

4. **Force cache clear on GitHub Pages:**
   - GitHub Pages can cache for up to 10 minutes
   - Wait a few minutes after push
   - Hard refresh browser (Ctrl+Shift+R)

---

## Reporting Issues

If data still doesn't load after following this guide:

1. **Collect debug info:**
   - Console screenshot (Ctrl+Shift+C)
   - Network tab screenshot
   - Browser version
   - URL you're visiting

2. **Run diagnostic:**
   ```bash
   # Check file exists and has data
   wc -l dashboards/v2/data/listings.js

   # Check syntax
   node -c dashboards/v2/data/listings.js

   # Check permissions
   ls -l dashboards/v2/data/listings.js
   ```

3. **Share findings** with the team for investigation

---

## Quick Reference

| Message | Status | Action |
|---------|--------|--------|
| `listings.js loaded successfully, LISTINGS array has 166 items` | ✅ | Check console for LISTINGS available message |
| `LISTINGS available: object (array of 166 items)` | ✅ | Dashboard should work, check for render errors |
| `LISTINGS available: undefined` | ❌ | Check Network tab for 404 error |
| `LISTINGS data not available` | ❌ | See solutions above |
| 404 error on data/listings.js | ❌ | File missing, check paths and permissions |
| No debug messages at all | ❌ | File failed to load, check Network tab |
