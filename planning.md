# Planning Immo-Bot Luxembourg

## Version actuelle : v2.7 (2026-02-20)

---

## Actions terminees

| ID  | Action                                      | Version | Date       | Statut |
|-----|---------------------------------------------|---------|------------|--------|
| A14 | Scraper Remax.lu (Selenium React, 5 ann.)   | v2.7    | 2026-02-20 | DONE   |
| A15 | auto_contact_remax.py (--url direct + DB)   | v2.7    | 2026-02-20 | DONE   |
| A16 | auto_contact_athome.py (login + contact)    | v2.7    | 2026-02-20 | DONE   |
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

## Scrapers actifs (8/10)

| Scraper                   | Site        | Methode                | Pages | Contact auto         |
|---------------------------|-------------|------------------------|-------|----------------------|
| athome_scraper_json.py    | Athome.lu   | JSON __INITIAL_STATE__ | 12    | ACTIF v2.7           |
| immotop_scraper_real.py   | Immotop.lu  | HTML regex             | 5     | Pas de formulaire    |
| luxhome_scraper.py        | Luxhome.lu  | JSON/Regex + GPS       | 1     | Pas de formulaire    |
| vivi_scraper_selenium.py  | VIVI.lu     | Selenium               | 3     | reCAPTCHA — skip     |
| nextimmo_scraper.py       | Nextimmo.lu | API JSON               | 10    | ACTIF v2.7           |
| newimmo_scraper_real.py   | Newimmo.lu  | Selenium               | 3     | Pas de formulaire    |
| unicorn_scraper_real.py   | Unicorn.lu  | Selenium               | 2     | Pas de formulaire    |
| remax_scraper.py          | Remax.lu    | Selenium React         | 5     | ACTIF v2.7           |

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
  Athome.lu    → ACTIF (v2.7) — login ATHOME_EMAIL + ATHOME_PASSWORD
  Remax.lu     → ACTIF (v2.7) — direct + --url pour URLs manuelles
  VIVI.lu      → reCAPTCHA — impossible
  Newimmo.lu   → pas de formulaire de contact visible
  Luxhome.lu   → pas de formulaire de contact visible
  Immotop.lu   → pas de formulaire de contact visible
  Unicorn.lu   → pas de formulaire de contact visible
```
