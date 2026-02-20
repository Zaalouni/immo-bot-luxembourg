# Handover — Immo-Bot Luxembourg

Derniere mise a jour : 2026-02-20

---

## Etat actuel : v2.7

**8 scrapers actifs**, **3 scripts de contact auto** fonctionnels.

---

## Ce qui a ete fait (cette session)

### Scrapers
| Action | Fichier | Statut |
|--------|---------|--------|
| Ajout scraper RE/MAX.lu (Selenium React, 15s wait) | `scrapers/remax_scraper.py` | DONE |
| Integration RE/MAX dans main.py | `main.py` | DONE |

### Contact automatique
| Action | Fichier | Statut |
|--------|---------|--------|
| auto_contact.py v2.7 (WebDriverWait, dry-run, screenshots) | `auto_contact.py` | DONE + TESTE |
| auto_contact_athome.py (login modal + formulaire) | `auto_contact_athome.py` | DONE — a tester |
| auto_contact_remax.py (formulaire direct MUI) | `auto_contact_remax.py` | DONE — a tester |
| Guide utilisation contact | `AUTO_CONTACT.md` | DONE |

### Infrastructure
| Action | Fichier | Statut |
|--------|---------|--------|
| Filtrage centralise | `filters.py` | DONE |
| Dashboard HTML | `dashboard_generator.py` | DONE |
| Tests pytest (38 tests) | `tests/` | DONE |
| Script reconnaissance formulaires | `recon_contact.py` | DONE (local only) |
| planning.md remis a jour | `planning.md` | DONE |

---

## En cours / A tester en priorite

### 1. auto_contact_athome.py — test reel

```bash
python auto_contact_athome.py --send 1
```

**Prerequis** : `.env` contient `ATHOME_EMAIL` + `ATHOME_PASSWORD`

**Comportement attendu** :
- Charge la page de l'annonce
- Clique "Contacter"
- Modal login apparait → remplit email + password → soumet
- Apres login, re-clique "Contacter"
- Remplit formulaire contact (prenom, nom, email, message)
- Soumet

**Si ca echoue** : regarder `contact_screenshots/athome_*.png` pour comprendre ou ca bloque.

**Corrections deja appliquees** :
- Login via modal de l'annonce (pas via homepage — ca plantait)
- Fix stale element apres login (re-trouve le bouton Contacter)

---

### 2. auto_contact_remax.py — test reel

```bash
python auto_contact_remax.py --send 1
```

**Comportement attendu** :
- Charge la page
- Attend disparition banniere CookieBot
- Formulaire deja visible (pas de modal)
- Remplit firstName, lastName, phone, email (id=contactmeemail), comments
- Utilise JS click avant send_keys (fix MUI React)
- Soumet

**Si ca echoue** : regarder `contact_screenshots/remax_*.png`

**Corrections deja appliquees** :
- `fill_input_js()` : JS scroll+click avant send_keys (fix ElementClickIntercepted)
- Attente `invisibility_of_element_located(CybotCookiebotDialog)` avant interaction

---

### 3. RE/MAX scraper — valider en production

Le scraper fonctionne en test (5 annonces). A valider dans le cycle complet :

```bash
python main.py
python auto_contact_remax.py --list   # doit montrer les annonces RE/MAX
```

---

## Scripts de contact disponibles

| Script | Site | Commande test |
|--------|------|---------------|
| `auto_contact.py` | Nextimmo.lu | `python auto_contact.py --send 1` |
| `auto_contact_athome.py` | Athome.lu | `python auto_contact_athome.py --send 1` |
| `auto_contact_remax.py` | Remax.lu | `python auto_contact_remax.py --send 1` |

**Toujours tester avec `--dry-run` d'abord :**
```bash
python auto_contact_athome.py --send 1 --dry-run
python auto_contact_remax.py --send 1 --dry-run
```

---

## Variables .env requises

```env
# Contact (tous les scripts)
CONTACT_FIRSTNAME=...
CONTACT_LASTNAME=...
CONTACT_EMAIL=...
CONTACT_PHONE=...
CONTACT_MESSAGE=...

# Athome uniquement
ATHOME_EMAIL=...
ATHOME_PASSWORD=...
```

---

## Scrapers actifs (8/10)

| Site | Fichier | Contact auto |
|------|---------|--------------|
| Athome.lu | `athome_scraper_json.py` | `auto_contact_athome.py` |
| Nextimmo.lu | `nextimmo_scraper.py` | `auto_contact.py` |
| Remax.lu | `remax_scraper.py` | `auto_contact_remax.py` |
| Immotop.lu | `immotop_scraper_real.py` | — pas de formulaire |
| Luxhome.lu | `luxhome_scraper.py` | — pas de formulaire |
| VIVI.lu | `vivi_scraper_selenium.py` | — reCAPTCHA |
| Newimmo.lu | `newimmo_scraper_real.py` | — pas de formulaire |
| Unicorn.lu | `unicorn_scraper_real.py` | — pas de formulaire |

---

## Prochaines actions suggérees

| Priorite | Action |
|----------|--------|
| HAUTE | Tester auto_contact_athome.py en reel (--send 1) |
| HAUTE | Tester auto_contact_remax.py en reel (--send 1) |
| MOYENNE | Ajouter scrapers pour remplacer Wortimmo/Immoweb (v3.1) |
| BASSE | Scrapers async / execution parallele (v3.0) |
