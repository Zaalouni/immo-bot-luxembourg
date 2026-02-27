# 🔍 MAIN.PY ANALYSIS - Impact on Dashboard Work

**Date:** 2026-02-27
**Status:** ✅ SAFE - No impact on dashboards/

---

## Executive Summary

**main.py is SAFE and will NOT overwrite our dashboard work.**

main.py is a data collection orchestrator that:
1. Loads 9 scrapers at startup
2. Executes scraping cycles sequentially
3. Stores listings in SQLite database (listings.db)
4. Sends Telegram notifications

**Zero interaction with:**
- `dashboards/` folder ❌
- HTML files ❌
- JSON data files in dashboards/data/ ❌

---

## What main.py Does

### 1. **Class: ImmoBot**
```python
class ImmoBot:
    def __init__(self):
        # Initialize 9 scrapers
        # Set up logging, database connection

    def check_new_listings(self):
        # 1. Clean old listings from DB (>30 days)
        # 2. Run each scraper sequentially
        # 3. Deduplicate by: price + city + surface (±15m²)
        # 4. Apply filters: price, rooms, surface, distance, keywords
        # 5. Store matching listings in SQLite
        # 6. Send Telegram notifications
```

### 2. **Data Flow**
```
Scrapers (9 sites)
    ↓
    ├─ Extract listings with: title, price, rooms, surface, url, city, GPS, image_url
    ↓
main.py ImmoBot
    ├─ Deduplicate listings
    ├─ Apply filters (config.py)
    ├─ Validate data
    ↓
database.py (SQLite)
    ├─ listings.db (14 columns including image_url)
    ↓
Dashboard Generator (separate process)
    ├─ Reads listings.db
    ├─ Exports to dashboards/data/listings.js
    └─ Generates HTML dashboards
```

---

## Code Evidence: Zero Dashboard Writes

### Search for file operations in main.py

**Query:** `grep -n "dashboards\|write\|json\|csv\|mkdir\|open(" main.py`

**Result:** No matches
- ❌ No "dashboards/" references
- ❌ No `open()` calls
- ❌ No file writes
- ❌ No JSON exports
- ❌ No CSV generation

**Conclusion:** main.py ONLY uses `db.*` (database.py) for data storage

---

## Database Operations Used

```python
# main.py Database Operations
db.cleanup_old_listings(30)           # Remove listings >30 days old
db.listing_exists(listing_id)         # Check if already stored
db.similar_listing_exists()           # Dedup by price+city+surface
db.add_listing()                      # Insert to SQLite
db.mark_as_notified()                 # Mark as sent to Telegram
db.get_stats()                        # Retrieve aggregate stats
db.close()                            # Close connection
```

**All operations confined to:** `listings.db` file only

---

## Scraper Modules Loaded

main.py loads these 9 scrapers (with fallback handling):

1. ✅ **Athome.lu** - JSON Parser
2. ✅ **Immotop.lu** - HTML/Regex
3. ✅ **Luxhome.lu** - JSON/Regex (+ Selenium fallback)
4. ✅ **VIVI.lu** - Selenium
5. ✅ **Newimmo.lu** - HTML/Regex
6. ✅ **Unicorn.lu** - Selenium
7. ✅ **Wortimmo.lu** - HTML/Regex (may fail - Cloudflare)
8. ✅ **Immoweb.lu** - Selenium (may fail - CAPTCHA)
9. ✅ **Nextimmo.lu** - HTML/Regex

**Each scraper returns:**
```python
{
    'listing_id': str,           # unique site identifier
    'site': str,                 # site name
    'title': str,                # property title
    'city': str,                 # extracted from address
    'price': int,                # monthly rent
    'rooms': int,                # bedrooms
    'surface': int,              # m²
    'url': str,                  # original listing URL
    'latitude': float,           # GPS (if available)
    'longitude': float,          # GPS (if available)
    'image_url': str or None,    # CRITICAL: Photo URL
    'created_at': datetime       # extraction timestamp
}
```

---

## Execution Modes

### Mode 1: Continuous (Default)
```bash
python main.py
# Runs infinite loop: scrape → deduplicate → store → notify
# Interval: CHECK_INTERVAL seconds (configurable in config.py)
```

### Mode 2: Test Once
```bash
python main.py --once
# Single scraping cycle for testing
# No infinite loop
```

---

## Impact Assessment

| Component | Impact | Details |
|-----------|--------|---------|
| `dashboards/index.html` | ✅ SAFE | main.py never touches |
| `dashboards/*.html` | ✅ SAFE | HTML files ignored |
| `dashboards/data/` | ✅ SAFE | Only dashboard_generator.py writes here |
| `listings.db` | ⚠️ WRITES | main.py stores all listings here |
| `CLAUDE.md` | ✅ SAFE | Not touched |
| `ACTIONS_LOG.md` | ✅ SAFE | Not touched |
| `dashboard_generator.py` | ✅ SAFE | Not modified by main.py |

---

## Recommendation

✅ **Safe to run main.py**

Our dashboard modifications are 100% safe because:
1. main.py only writes to `listings.db`
2. HTML files are in separate `dashboards/` folder
3. dashboard_generator.py (which reads listings.db) has been fixed to NOT regenerate HTML
4. Data export (listings.js, stats.js) is handled by dashboard_generator.py only

---

## When to Worry

Only if we modify these files:
- `main.py` itself
- `database.py` schema
- `config.py` filtering rules
- Scraper modules in `scrapers/`

Otherwise: **main.py is safe to run anytime.**

---

**Created:** 2026-02-27 17:15
**Verified:** Code inspection + grep search
**Status:** ✅ APPROVED FOR PRODUCTION

