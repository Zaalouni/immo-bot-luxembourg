# Analyse technique — Immo-Bot Luxembourg (v3.2)

## Historique condense

| Version | Date | Changements cles |
|---------|------|-----------------|
| v1.0-v1.5 | janv 2025 | Bot basique, fixes Athome JSON (_safe_str), Unicorn URL, rooms=0 inconnu |
| v2.0 | fevr 2025 | Dedup cross-sites + DB, compteur echecs, nettoyage DB, filtrage enrichi |
| v2.2 | fevr 2025 | Suppression ~40 fichiers legacy, RotatingFileHandler, .gitignore 55 lignes |
| v2.5 | 16/02 | requests.Session, rejet villes frontalieres |
| v2.6 | 17/02 | Pagination (Athome 12p, Nextimmo 10p), filtrage centralise filters.py, dashboard HTML |
| v2.7 | 19-20/02 | auto_contact.py, Remax scraper Selenium React, Luxhome/VIVI/Sothebys fixes |
| v2.8 | 20/02 | Fix images VIVI (bg-CSS) + Remax (ancetres DOM), DB image_url, dashboard PWA |
| v2.9 | 20/02 | Scraper Sigelux.lu (HTTP+BS4, 9e scraper) |
| v3.0 | 20/02 | Scrapers paralleles ThreadPoolExecutor 4 workers (~14 min vs ~25 min) |
| v3.1 | 21/02 | Fix ImmoStar hors-LU, VIVI GPS, Immotop GPS, Nextimmo titres, dashboard qualite |
| v3.2 | 21/02 | available_from tous scrapers, fix prix regex Newimmo/Unicorn, geocode_city tuple, --no-notify |

---

## Corrections importantes v3.x

### geocode_city — TypeError NoneType not iterable
- **Cause** : `geocode_city()` retournait `None` si ville inconnue ; `lat, lng = geocode_city(city)` crashait
- **Fix** : tous les `return None` → `return (None, None)` ; `enrich_listing_gps` : `if lat is not None` au lieu de `if coords:`

### Prix regex greedy (Newimmo/Unicorn)
- **Cause** : `[\d\s\.]+€` capturait l'ID de l'URL (ex: 127171) fusionne avec le prix
- **Fix** : `re.finditer(r'(?<!\d)(\d{1,2}[\s\u202f\xa0]\d{3}|\d{3,5})(?!\d)\s*€', text)` + plage 300-20000€

### Images VIVI
- **Cause** : images en background-image CSS, pas dans `<img>` (icones SVG uniquement)
- **Fix** : cherche `[style*="background-image"]` en priorite 1

### Images Remax
- **Cause** : structure React — l'image est dans un div parent/frere du `<a>`, pas dans le lien
- **Fix** : remonte aux ancetres DOM du lien pour trouver l'img

### available_from extraction
- **Methode** : `extract_available_from(text)` dans utils.py
- **Detecte** : DD/MM/YYYY, YYYY-MM-DD, mois francais (mars 2026), "immediatement/disponible"
- **Source par scraper** : description (Athome), texte carte (VIVI/Remax), container (Sigelux), titre (Immotop)

---

## Metriques prod

```
Cycle v3.0 : 108 annonces trouvees, 69 notifiees (100% envoyees)
Temps cycle : ~14 min (4 workers) vs ~25 min (sequentiel)
Scrapers    : 9 actifs / 11 charges
```

---

## Points d'attention pour modifications futures

- **Ajouter un scraper** : creer `scrapers/nouveau.py`, exposer instance + `.scrape()`, importer dans `main.py`
- **Modifier criteres** : editer `.env` uniquement — tout est charge dynamiquement par `config.py`
- **Changer format Telegram** : `notifier.py:send_listing()`
- **Ajouter champ DB** : `database.py:init_db()` — ajouter dans la boucle migration ALTER TABLE
- **Git conflict** : serveur Linux auto-push les dashboards → utiliser `git merge -X ours origin/main`
- **Tester sans spam Telegram** : `python main.py --once --no-notify`
