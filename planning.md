# Planning Immo-Bot Luxembourg

## Version actuelle : v3.0 (2026-02-20)

---

## Actions terminees

| ID  | Action                                           | Version | Date       | Statut |
|-----|--------------------------------------------------|---------|------------|--------|
| A01 | Scrapers HTTP : requests.Session()               | v2.5    | 2026-02-15 | DONE   |
| A02 | Pagination tous scrapers (+309 annonces)         | v2.6    | 2026-02-17 | DONE   |
| A03 | URLs filtrees Athome (annonces only)             | v2.6    | 2026-02-17 | DONE   |
| A04 | Fix images Athome (CDN media.items[].uri)        | v2.6    | 2026-02-17 | DONE   |
| A05 | Fix images VIVI (lazy load + data-src)           | v2.6    | 2026-02-17 | DONE   |
| A06 | Notifier : log WARNING si sendPhoto echoue      | v2.6    | 2026-02-17 | DONE   |
| A07 | Dashboard HTML (Bootstrap+Leaflet+DataTables)    | v2.6    | 2026-02-17 | DONE   |
| A08 | Filtrage centralise (filters.py)                 | v2.6    | 2026-02-17 | DONE   |
| A09 | Tests pytest (38 tests utils/db/filters)         | v2.6    | 2026-02-17 | DONE   |
| A10 | Desactiver SothebysRealty (Cloudflare)           | v2.6    | 2026-02-19 | DONE   |
| A11 | auto_contact.py v2.7 (WebDriverWait, dry-run)    | v2.7    | 2026-02-20 | DONE   |
| A12 | AUTO_CONTACT.md (guide utilisation)              | v2.7    | 2026-02-20 | DONE   |
| A13 | recon_contact.py (reconnaissance formulaires)    | v2.7    | 2026-02-20 | DONE   |
| A14 | Scraper Remax.lu (Selenium React)                | v2.7    | 2026-02-20 | DONE   |
| A15 | auto_contact_remax.py                            | v2.7    | 2026-02-20 | DONE   |
| A16 | auto_contact_athome.py (login + contact)         | v2.7    | 2026-02-20 | DONE   |
| A17 | Fix images VIVI (background-image CSS)           | v2.8    | 2026-02-20 | DONE   |
| A18 | Fix images Remax (ancetres DOM React)            | v2.8    | 2026-02-20 | DONE   |
| A19 | DB colonne image_url + migration auto            | v2.8    | 2026-02-20 | DONE   |
| A20 | Notifier : download image cote serveur (CDN)     | v2.8    | 2026-02-20 | DONE   |
| A21 | Dashboard PWA (manifest + sw.js + icon.svg)      | v2.8    | 2026-02-20 | DONE   |
| A22 | Dashboard : carte geo restauree en haut (520px)  | v2.8    | 2026-02-20 | DONE   |
| A23 | Scraper Sigelux.lu (HTTP+BS4, 9eme scraper)      | v2.9    | 2026-02-20 | DONE   |
| A24 | Scrapers paralleles (ThreadPoolExecutor, ~4 min) | v3.0    | 2026-02-20 | DONE   |

---

## Actions planifiees

| ID  | Action                                          | Priorite | Version cible |
|-----|-------------------------------------------------|----------|---------------|
| C01 | Nouveaux scrapers (remplacer Wortimmo/Immoweb)  | Moyenne  | v3.1          |
| C02 | Retry auto sur erreurs reseau scrapers          | Basse    | v3.1          |
| C03 | Tests automatises (pytest scrapers live)        | Basse    | v3.1          |

---

## Scrapers actifs (9/11)

| Scraper                   | Site        | Methode       | Pages | Images | Contact auto    |
|---------------------------|-------------|---------------|-------|--------|-----------------|
| athome_scraper_json.py    | Athome.lu   | JSON          | 12    | CDN OK | auto_contact_athome.py |
| immotop_scraper_real.py   | Immotop.lu  | HTML regex    | 5     | ?      | —               |
| luxhome_scraper.py        | Luxhome.lu  | JSON/Regex    | 1     | ?      | —               |
| vivi_scraper_selenium.py  | VIVI.lu     | Selenium      | 3     | bg-CSS | reCAPTCHA skip  |
| nextimmo_scraper.py       | Nextimmo.lu | API JSON      | 10    | OK     | auto_contact.py |
| newimmo_scraper_real.py   | Newimmo.lu  | Selenium      | 3     | ?      | —               |
| unicorn_scraper_real.py   | Unicorn.lu  | Selenium      | 2     | ?      | —               |
| remax_scraper.py          | Remax.lu    | Selenium React| 5     | DOM OK | auto_contact_remax.py |
| sigelux_scraper.py        | Sigelux.lu  | HTTP+BS4      | 5     | CDN OK | —               |

## Scrapers desactives (2/11)

| Scraper              | Site        | Raison                         |
|----------------------|-------------|--------------------------------|
| wortimmo_scraper.py  | Wortimmo.lu | Cloudflare (prix non lisibles) |
| immoweb_scraper.py   | Immoweb.be  | CAPTCHA bloque page 1          |

---

## Validation prod v3.0 (2026-02-20 21:08)

```
Scrapers     : 11 charges (9 actifs + 2 desactives)
Parallelisme : 4 workers simultanes
Cycle #1     : 108 annonces trouvees, 69 notifiees (100%)
Temps cycle  : ~14 min (vs ~25 min avant)
Par site     : Athome 61, Nextimmo 25, Immotop 5, Remax 5, VIVI 7, Newimmo 3, Sigelux 2
```
