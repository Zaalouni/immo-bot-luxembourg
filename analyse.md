# Analyse technique — Immo-Bot Luxembourg

> Ce fichier documente l'analyse du projet, les corrections effectuees,
> les problemes connus et les ameliorations possibles. Il sert de journal
> technique pour tout outil IA ou developpeur reprenant le projet.

## Historique des corrections

### v1.0 → v1.5 (17-18 janvier 2025)

#### Commit initial (31aee57)
- Bot basique avec scrapers simples
- Filtrage : prix max + rooms min uniquement
- Notifications texte brut Telegram

#### Corrections successives (5209e6a → 49dabb7)
- **Athome.lu JSON crash** : les champs `immotype`, `price`, `city`, `description` peuvent etre des `dict` au lieu de `str` — ajout de `_safe_str()` pour gerer tous les types
- **Unicorn URL corrigee** : l'URL de recherche avait change
- **Immoweb timeout** : augmente le timeout Selenium
- **Immotop filtrage** : le regex ne capturait pas certains formats de prix
- **Wortimmo Selenium** : le site charge par AJAX, necessite Selenium + scroll
- **Filtrage trop strict** : les scrapers rejetaient les annonces avec rooms=0 (inconnu) — corrige pour ne filtrer que si rooms > 0

### v2.0 (12 fevrier 2025) — Commit 0ecf93b

#### main.py — Ameliorations majeures
| Correction | Probleme | Solution |
|------------|----------|----------|
| Dedup cross-sites | Meme annonce sur 2-3 sites = 2-3 notifications | `_deduplicate()` avec cle prix+ville+surface, garde le meilleur (score qualite) |
| Dedup DB | Annonces similaires reinserees apres restart | `similar_listing_exists()` en DB avant insertion |
| Compteur echecs | Scraper en panne silencieuse | `scraper_failures{}` + alerte Telegram apres 3 echecs |
| Nettoyage DB | Base qui grossit indefiniment | `cleanup_old_listings(30)` tous les 10 cycles |
| Delai inter-scrapers | Sites bloquent les requetes rapides | `time.sleep(5)` entre chaque scraper |
| Filtrage enrichi | Seulement prix max + rooms min | + MIN_PRICE, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS, MAX_DISTANCE |

#### Scrapers — Corrections communes
| Correction | Probleme | Solution |
|------------|----------|----------|
| Multi-type | Seulement appartements | Ajout maisons, duplex, penthouse sur tous les scrapers |
| Images | Aucune photo dans les notifications | Extraction image_url depuis chaque scraper |
| Filtrage complet | Chaque scraper avait son propre filtrage partiel | Uniformise : tous importent MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS |
| Surface decimale | "52.00 m2" non parse | Regex `(\d+(?:[.,]\d+)?)\s*m[²2]` |
| Rooms default | rooms=1 par defaut (VIVI) | rooms=0 (inconnu) pour ne pas fausser le filtrage |

#### Scrapers — Reecritures
| Scraper | Raison | Nouvelle approche |
|---------|--------|-------------------|
| Unicorn | Elements Selenium retournaient texte vide | Extraction regex depuis page_source |
| Wortimmo | Site AJAX complexe, cartes introuvables | 3 methodes cascade : JSON embarque → liens HTML → elements prix |

#### notifier.py — Ameliorations
| Correction | Avant | Apres |
|------------|-------|-------|
| Types champs | price/rooms/surface = 'N/A' (str) | = 0 (int), formate a l'affichage |
| Photos | Absent | `send_photo()` avec fallback texte |
| Google Maps | Absent | Lien cliquable si GPS disponible |
| Prix/m2 | Absent | Calcul et affichage automatique |
| Hashtags | 3 hashtags fixes | Dynamiques : #PrixBas, #Proche, #GrandeSurface, #Ville |
| Rate limit | sleep(1.5) | sleep(5) entre envois |

#### Autres fichiers
| Fichier | Correction |
|---------|-----------|
| config.py | EXCLUDED_WORDS et CITIES nettoyes (strip, filtre vides) |
| database.py | + `similar_listing_exists()`, + `cleanup_old_listings()` |
| utils.py | "< 1 km" → "moins de 1 km" |
| selenium_template.py | Fallback Chrome si Firefox indisponible, surface decimale |
| test_scrapers.py | Affiche filtres actifs avant tests |

### v2.2 (15 fevrier 2025) — Nettoyage et optimisation

#### Fichiers supprimes (~40 fichiers, ~2.5 Mo)
| Categorie | Fichiers supprimes |
|-----------|-------------------|
| Backups racine | main.py.backup, main.py.123, main.py.1801, main.py.backup_avant_phase2, main.py.sauvvv, config.py.backup_final, notifier.py.backup_old, 0, except |
| Dossier scrapers.sauv/ | ~26 fichiers (copie complete de scrapers/) |
| Scrapers legacy | athome_scraper_simple.py, athome_scraper_real.py, luxhome_scraper_simple.py, luxhome_scraper_stealth.py, luxhome_scraper_real.py, vivi_scraper_real.py, selenium_template_fixed.py |
| Debug/data | photolog.txt (1.4 Mo), page.html, page_raw.html, json_raw.txt, json_cleaned.txt, raw.json, debug_error.json, annonces.*, luxhome_annonces.*, tableau_complet.txt, script_31.txt |
| Scripts oneshot | aa.sh, correct_new_sites.sh, fix_scrapers.py, explore_selectors.py, diagnostic*.py (x3), bot_simple.py, scraper_simple.py, athome.py |
| Anciens tests | test.py, test_installation.py, test_installation_v2.py, test_athome_scraper.py, test_groupe.py |

#### Optimisations
| Correction | Avant | Apres |
|------------|-------|-------|
| .gitignore | 10 lignes basiques | 55 lignes, couvre backups, data, debug, IDE |
| Logs | FileHandler simple (grossit indefiniment) | RotatingFileHandler 5 Mo, 3 backups |
| requirements.txt | 9 packages (feedparser, schedule inutilises) | 6 packages utiles uniquement |
| Securite .env | Non verifie | Confirme : jamais commite dans l'historique git |

### v2.5 (16 fevrier 2026) — Fix scrapers + rejet villes frontalieres
- Fix scrapers individuels
- Rejet des villes frontalieres (hors Luxembourg)

### v2.6 (17 fevrier 2026) — Pagination tous scrapers

#### Probleme
Les scrapers ne chargeaient que la page 1 des resultats. Athome par exemple : 20 annonces sur 4841 disponibles. Des annonces valides (ex: id 8992149, Leudelange, 2000€) etaient perdues.

#### Solution : pagination + URLs filtrees
| Scraper | Avant | Apres | Gain | Methode |
|---------|-------|-------|------|---------|
| Athome | 40 | 266 | +226 | URLs filtrees (prix/chambres) + 12 pages |
| Nextimmo | 40 | 123 | +83 | API page param + 10 pages |
| Immotop | 25 | 25 | +0 | 5 pages (1 seule page de resultats) |
| Luxhome | 58 | 58 | +0 | Tout sur 1 page, pas de changement |
| VIVI | ~15 | ~15 | +0 | Pagination URL ignoree (JS scroll) |
| Newimmo | ~10 | ~10 | +0 | Pagination URL ignoree (JS scroll) |
| Unicorn | ~5 | ~5 | +0 | Pagination URL ignoree (JS scroll) |

#### Changements par fichier
| Fichier | Modification |
|---------|-------------|
| athome_scraper_json.py | URLs `?price_min=&price_max=&bedrooms_min=&bedrooms_max=` + boucle 12 pages + supprime [:30] |
| nextimmo_scraper.py | Boucle page 1..10 par type + supprime [:20] API et HTML |
| immotop_scraper_real.py | Boucle &page=1..5 + supprime [:20] + HTML accumule pour images |
| vivi_scraper_selenium.py | Boucle ?page=1..3 + supprime [:15] + dedup seen_ids |
| newimmo_scraper_real.py | Boucle ?page=1..3, break si 0 nouveaux liens |
| unicorn_scraper_real.py | Boucle ?page=1..2, conservateur (CAPTCHA) |

#### Notes
- Scrapers Selenium (VIVI, Newimmo, Unicorn) : `?page=N` ne change pas le contenu (rendu JS). La pagination break immediatement sur 0 nouvelles annonces → pas de requetes inutiles.
- Delai `time.sleep(1)` entre pages HTTP pour eviter le rate limiting.
- Tous les scrapers : break si page vide OU 0 nouveaux IDs.

## Problemes connus (apres v2.6)

### Importants
1. **Pas d'async** — Les 9 scrapers tournent sequentiellement. Avec les delais (5s entre scrapers + 8-10s Selenium), un cycle complet prend ~2-3 minutes minimum.
2. **Singletons a l'import** — `db` et `notifier` sont instancies au moment de l'import. Le notifier teste la connexion Telegram a chaque demarrage (meme en mode test).
3. **Selenium fragile** — Les sites changent regulierement leur HTML. Les selecteurs CSS et regex doivent etre mis a jour.
4. **Pas de retry scraper** — Si un scraper echoue, on passe au suivant. Pas de re-essai dans le meme cycle.
5. **Filtrage duplique** — _matches_criteria() est dans chaque scraper ET dans main.py. A centraliser (v3.0).

### Mineurs
6. **dashboard.py et web_dashboard.py** — Presents mais non integres au bot principal
7. **Pas de tests automatises** — Uniquement test_scrapers.py (test manuel)

## Metriques du projet (apres v2.2)

| Metrique | Avant v2.2 | Apres v2.2 |
|----------|-----------|------------|
| Fichiers Python actifs | 15 | 15 |
| Fichiers Python legacy | ~10 | 0 |
| Fichiers total racine | ~60 | ~18 |
| Lignes de code (actifs) | ~2500 | ~2500 |
| Dependances | 9 packages | 6 packages |
| Taille repo (hors venv/db) | ~3 Mo | ~500 Ko |

## Points d'attention pour modifications futures

- **Ajouter un scraper** : creer `scrapers/nouveau_scraper.py`, exposer une instance avec `.scrape()`, ajouter l'import dans `main.py` (section SITES ACTIFS ou NOUVEAUX SITES)
- **Modifier les criteres** : editer `.env`, tout est charge dynamiquement par `config.py`
- **Changer le format Telegram** : modifier `notifier.py:send_listing()`
- **Ajouter un champ en DB** : modifier `database.py:init_db()` (ALTER TABLE ou recreer la base)
- **Tester un scraper** : `python test_scrapers.py` ou importer directement dans un script Python
