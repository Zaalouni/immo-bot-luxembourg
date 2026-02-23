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
- **Crash parsing** : les champs pouvaient avoir types varies — ajout de gestion robuste des types
- **URL de recherche** : l'URL de recherche avait change
- **Timeout** : augmentation timeout pour contenu dynamique
- **Parsing prix** : correction des patterns de parsing
- **Contenu dynamique** : adaptation pour sites dynamiques
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
| Images | Aucune photo dans les notifications | Extraction image depuis chaque scraper |
| Filtrage complet | Chaque scraper avait son propre filtrage partiel | Uniformise : tous importent parametres globaux |
| Parsing surface | "52.00 m2" non parse | Parsing robuste decimal |
| Rooms default | rooms=1 par defaut | rooms=0 (inconnu) pour ne pas fausser le filtrage |

#### Scrapers — Reecritures
Certains scrapers ont ete reecrit pour adapter aux evolutions des structures cibles.

#### notifier.py — Ameliorations
| Correction | Avant | Apres |
|------------|-------|-------|
| Types champs | Valeurs manquantes | Gestion robuste avec defaults |
| Photos | Absent | Photos avec fallback texte |
| Cartographie | Absent | Lien geolocalisation si GPS disponible |
| Metriques | Absent | Calcul automatique metriques pertinentes |
| Hashtags | Fixes | Dynamiques selon caracteristiques |
| Rate limit | Sans limite | Delai entre envois |

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
| Categorie | Description |
|-----------|-------------|
| Backups | Fichiers de sauvegarde anciens |
| Legacy | Versions anterieures de scrapers et templates |
| Debug | Fichiers de debug et donnees intermediaires |
| Scripts oneshot | Scripts d'exploration et correction temporaires |
| Tests | Anciens fichiers de tests |

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

#### Solution : pagination + filtrage avance
| Scraper | Avant | Apres | Gain | Notes |
|---------|-------|-------|------|-------|
| Scraper 1 | 40 | 266 | +226 | Pagination + filtrage parametres |
| Scraper 2 | 40 | 123 | +83 | Pagination + filtrage |
| Scraper 3 | 25 | 25 | +0 | 1 seule page de resultats |
| Scraper 4 | 58 | 58 | +0 | Tout sur 1 page |
| Scraper 5 | ~15 | ~15 | +0 | Contenu dynamique sans pagination |
| Scraper 6 | ~10 | ~10 | +0 | Contenu dynamique sans pagination |
| Scraper 7 | ~5 | ~5 | +0 | Contenu dynamique sans pagination |

#### Changements par fichier
Chaque scraper : ajout pagination avec parametres avances, optimisation requetes, deduplication interne.

#### Notes
- Scrapers avec contenu dynamique : pagination optimisee pour eviter les requetes inutiles.
- Delai entre requetes pour eviter les limitations.
- Tous les scrapers : break si page vide OU 0 nouveaux IDs.

## Problemes connus (apres v2.6)

### Importants
1. **Pas d'async** — Les 9 scrapers tournent sequentiellement. Avec les delais (5s entre scrapers + 8-10s Selenium), un cycle complet prend ~2-3 minutes minimum.
2. **Singletons a l'import** — `db` et `notifier` sont instancies au moment de l'import. Le notifier teste la connexion Telegram a chaque demarrage (meme en mode test).
3. **Scraping fragile** — Les sources changent regulierement leur structure HTML/API. Les selecteurs CSS et regex doivent etre mis a jour.
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
