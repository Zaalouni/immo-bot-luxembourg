# Planning Immo-Bot Luxembourg

## Version actuelle : v3.2 (2026-02-21)

---

## Actions terminees

**A01-A24 DONE v2.5-v3.0** : sessions, requests, pagination, filtrage centralise, images, dashboard, Remax, Sigelux, parallelisme ThreadPoolExecutor. Voir git log pour detail.

---

## Priorites v3.1-v3.2 (2026-02-21)

| ID  | Action                                              | Priorite | Version | Statut |
|-----|-----------------------------------------------------|----------|---------|--------|
| D00 | Fix dashboard_generator : image_url dans SELECT     | HAUTE    | v3.1    | DONE 2026-02-21 |
| D01 | Fix ImmoStar : rejeter villes hors Luxembourg       | HAUTE    | v3.1    | DONE 2026-02-21 |
| D02 | Fix VIVI : GPS depuis nom de ville (geocode_city)   | HAUTE    | v3.1    | DONE 2026-02-21 |
| D03 | Fix Luxhome : extraire surface + images             | HAUTE    | v3.1    | SKIP (site hors ligne) |
| D04 | Fix Immotop : GPS manquant sur certaines annonces   | HAUTE    | v3.1    | DONE 2026-02-21 |
| D05 | Fix Nextimmo : enrichir titre depuis description    | MOYENNE  | v3.1    | DONE 2026-02-21 |
| D06 | Normaliser villes (casse uniforme)                  | BASSE    | v3.1    | DONE 2026-02-21 |
| D07 | Dashboard : indicateurs qualite par site            | MOYENNE  | v3.1    | DONE 2026-02-21 |
| D08 | available_from : extraction date dispo tous scrapers| HAUTE    | v3.2    | DONE 2026-02-21 |
| D09 | Fix Newimmo/Unicorn : prix greedy regex → specifique| HAUTE    | v3.2    | DONE 2026-02-21 |
| D10 | Fix geocode_city : retour tuple (None,None) toujours| HAUTE    | v3.2    | DONE 2026-02-21 |
| D11 | main.py : option --no-notify (test sans Telegram)   | MOYENNE  | v3.2    | DONE 2026-02-21 |
| C02 | Retry auto sur erreurs reseau scrapers              | BASSE    | v3.3    | A FAIRE |
| C03 | Tests automatises (pytest scrapers live)            | BASSE    | v3.3    | A FAIRE |

> Bot tourne sur serveur Linux. Ne pas lancer localement.

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

## Validation prod v3.0 (2026-02-20)

```
Scrapers     : 11 charges (9 actifs + 2 desactives)
Parallelisme : ThreadPoolExecutor 4 workers
Cycle #1     : 108 annonces trouvees, 69 notifiees (100%)
Temps cycle  : ~14 min (vs ~25 min avant)
Par site     : Athome 61, Nextimmo 25, Immotop 5, Remax 5, VIVI 7, Newimmo 3, Sigelux 2
```
