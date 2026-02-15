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

## Problemes connus

### Critiques
1. **`.env` commite dans le repo** — Le fichier `.env` contient les tokens Telegram. Bien qu'il soit dans `.gitignore` maintenant, il a pu etre commite dans des versions anterieures. Verifier l'historique git.

### Importants
2. **Pas d'async** — Les 9 scrapers tournent sequentiellement. Avec les delais (5s entre scrapers + 8-10s Selenium), un cycle complet prend ~2-3 minutes minimum.
3. **Singletons a l'import** — `db` et `notifier` sont instancies au moment de l'import. Le notifier teste la connexion Telegram a chaque demarrage (meme en mode test).
4. **Selenium fragile** — Les sites changent regulierement leur HTML. Les selecteurs CSS et regex doivent etre mis a jour.
5. **Pas de retry scraper** — Si un scraper echoue, on passe au suivant. Pas de re-essai dans le meme cycle.

### Mineurs
6. **Fichiers legacy** — ~10 fichiers scraper inutilises dans `scrapers/` (anciennes versions)
7. **Fichiers backup a la racine** — `main.py.backup`, `main.py.123`, `config.py.backup_final`, etc.
8. **Pas de logging structure** — Logs en fichier plat, pas de rotation
9. **feedparser et schedule** — Installes (requirements.txt) mais non utilises

## Metriques du projet

| Metrique | Valeur |
|----------|--------|
| Fichiers Python actifs | 15 |
| Fichiers Python legacy | ~10 |
| Lignes de code (actifs) | ~2500 |
| Sites scraped | 9 |
| Scrapers Selenium | 4 (VIVI, Newimmo, Unicorn, Wortimmo) |
| Scrapers HTTP | 5 (Athome, Immotop, Luxhome, Immoweb, Nextimmo) |
| Dependances | 9 packages |

## Points d'attention pour modifications futures

- **Ajouter un scraper** : creer `scrapers/nouveau_scraper.py`, exposer une instance avec `.scrape()`, ajouter l'import dans `main.py` (section SITES ACTIFS ou NOUVEAUX SITES)
- **Modifier les criteres** : editer `.env`, tout est charge dynamiquement par `config.py`
- **Changer le format Telegram** : modifier `notifier.py:send_listing()`
- **Ajouter un champ en DB** : modifier `database.py:init_db()` (ALTER TABLE ou recreer la base)
- **Tester un scraper** : `python test_scrapers.py` ou importer directement dans un script Python
