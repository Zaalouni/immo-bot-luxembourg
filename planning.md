# Planning Immo-Bot Luxembourg

## Version actuelle : v2.7 (2026-02-20)

---

## Actions terminees

| ID  | Action                                      | Version | Date       | Statut |
|-----|---------------------------------------------|---------|------------|--------|
| A01 | Scrapers HTTP : requests.Session()          | v2.5    | 2026-02-15 | DONE   |
| A02 | Pagination tous scrapers (+309 annonces)    | v2.6    | 2026-02-17 | DONE   |
| A03 | URLs filtrees Athome (annonces only)        | v2.6    | 2026-02-17 | DONE   |
| A04 | Fix images Athome (CDN media.items[].uri)   | v2.6    | 2026-02-17 | DONE   |
| A05 | Fix images VIVI (lazy load + data-src)      | v2.6    | 2026-02-17 | DONE   |
| A06 | Notifier : log WARNING si sendPhoto echoue | v2.6    | 2026-02-17 | DONE   |
| A07 | Dashboard HTML (Bootstrap+Leaflet+DataTables)| v2.6   | 2026-02-17 | DONE   |
| A08 | Filtrage centralise (filters.py)            | v2.6    | 2026-02-17 | DONE   |
| A09 | Tests pytest (38 tests utils/db/filters)    | v2.6    | 2026-02-17 | DONE   |
| A10 | Desactiver SothebysRealty (Cloudflare)      | v2.6    | 2026-02-19 | DONE   |
| A11 | auto_contact.py v2.7 (WebDriverWait, dry-run, screenshots, form selector) | v2.7 | 2026-02-20 | DONE |
| A12 | AUTO_CONTACT.md (guide utilisation)         | v2.7    | 2026-02-20 | DONE   |
| A13 | recon_contact.py (reconnaissance formulaires) | v2.7  | 2026-02-20 | DONE   |

---

## Actions en cours

| ID  | Action                                             | Priorite | Statut     |
|-----|----------------------------------------------------|----------|------------|
| B01 | Multi-site contact (VIVI, Luxhome, Immotop, Athome) | HAUTE   | EN ATTENTE recon |

### B01 — Multi-site contact : etapes

```
1. [USER]  Lancer recon_contact.py sur 1 annonce par site
           python recon_contact.py https://www.vivi.lu/annonce/XXX
           python recon_contact.py https://www.luxhome.lu/annonces/XXX
           python recon_contact.py https://www.immotop.lu/annonces/XXX
           python recon_contact.py https://www.newimmo.lu/annonces/XXX
           python recon_contact.py https://www.athome.lu/annonces/XXX

2. [USER]  Envoyer les recon.txt a Claude

3. [CLAUDE] Analyser : boutons, champs formulaire, CAPTCHA

4. [CLAUDE] Classer sites par faisabilite (simple → difficile)

5. [CLAUDE] Etendre auto_contact.py pour couvrir les sites faisables
```

---

## Actions planifiees

| ID  | Action                                          | Priorite | Version cible |
|-----|-------------------------------------------------|----------|---------------|
| C01 | Nouveaux scrapers (remplacer Wortimmo/Immoweb)  | Moyenne  | v3.1          |
| C02 | Scrapers async (execution parallele)            | Basse    | v3.0          |
| C03 | Retry auto sur erreurs reseau scrapers          | Basse    | v3.0          |

---

## Scrapers actifs (7/9)

| Scraper          | Site          | Methode              | Pages | Contact auto |
|------------------|---------------|----------------------|-------|--------------|
| athome_scraper_json.py    | Athome.lu  | JSON __INITIAL_STATE__ | 12  | A analyser   |
| immotop_scraper_real.py   | Immotop.lu | HTML regex           | 5     | A analyser   |
| luxhome_scraper.py        | Luxhome.lu | JSON/Regex + GPS     | 1     | A analyser   |
| vivi_scraper_selenium.py  | VIVI.lu    | Selenium             | 3     | A analyser   |
| nextimmo_scraper.py       | Nextimmo.lu| API JSON             | 10    | ACTIF v2.7   |
| newimmo_scraper_real.py   | Newimmo.lu | Selenium             | 3     | A analyser   |
| unicorn_scraper_real.py   | Unicorn.lu | Selenium             | 2     | A analyser   |

## Scrapers desactives (2/9)

| Scraper              | Site          | Raison                        |
|----------------------|---------------|-------------------------------|
| wortimmo_scraper.py  | Wortimmo.lu   | Cloudflare (prix non lisibles)|
| immoweb_scraper.py   | Immoweb.be    | CAPTCHA bloque page 1         |

---

## Objectif court terme

```
Contact auto multi-sites :
  Nextimmo.lu  → ACTIF (v2.7)
  VIVI.lu      → apres recon
  Luxhome.lu   → apres recon
  Immotop.lu   → apres recon
  Newimmo.lu   → apres recon
  Athome.lu    → apres recon (probablement protege)
```
