
# =============================================================================
# main.py — Orchestrateur principal du bot immobilier Luxembourg
# =============================================================================
# Point d'entree du projet. Contient la classe ImmoBot qui :
#   1. Charge les 9 scrapers au demarrage (imports dynamiques try/except)
#   2. Execute des cycles de scraping PARALLELES (ThreadPoolExecutor)
#   3. Deduplique les annonces cross-sites (prix + ville + surface)
#   4. Filtre selon les criteres config.py (prix, rooms, surface, distance, mots exclus)
#   5. Stocke en SQLite et envoie les notifications Telegram
#
# Modes d'execution :
#   python main.py               → mode continu (boucle toutes les CHECK_INTERVAL secondes)
#   python main.py --once        → mode test (1 seul cycle)
#   python main.py --no-notify   → desactiver les notifications Telegram (test local)
#   python main.py --once --no-notify → test sans notification
#
# Parallelisme : MAX_CONCURRENT_SCRAPERS workers simultanes
#   - Scrapers HTTP (Athome, Immotop, Luxhome, Nextimmo, Sigelux) : tres legers
#   - Scrapers Selenium (VIVI, Newimmo, Unicorn, Remax) : ~300 Mo RAM chacun
#   - Recommande : 4 workers (RAM OK sur 4 Go), 3 si serveur limite
#
# Voir architecture.md pour le flux de donnees complet.
# =============================================================================
import logging
import logging.handlers
import time
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Forcer UTF-8 sur stdout/stderr (evite UnicodeEncodeError sur Windows cp1252)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Nombre max de scrapers en parallele
# 4 = bon equilibre perf/RAM (4 Firefox simultanes ~ 1.2 Go)
# Reduire a 3 si le serveur a moins de 3 Go de RAM libre
MAX_CONCURRENT_SCRAPERS = 4

# Stabilite : retry automatique si un scraper leve une exception
# (erreur inattendue non geree dans le scraper lui-meme)
SCRAPER_RETRIES = 2          # nombre max de tentatives par scraper
SCRAPER_RETRY_DELAY = 10     # secondes entre deux tentatives

# Rotation des logs : max 5 Mo par fichier, garde 3 fichiers anciens
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler(
            'immo_bot.log', encoding='utf-8',
            maxBytes=5*1024*1024, backupCount=3
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Imports locaux
try:
    from config import CHECK_INTERVAL, MAX_PRICE, MIN_ROOMS, CITIES
    from database import db
    from notifier import notifier

    scrapers_config = []

    # ============================================
    # SITES ACTIFS
    # ============================================

    # Athome.lu (JSON PARSER)
    try:
        from scrapers.athome_scraper_json import athome_scraper_json
        scrapers_config.append(('🏠 Athome.lu', athome_scraper_json))
        logger.info("✅ Athome.lu (JSON parser)")
    except ImportError as e:
        logger.warning(f"⚠️ Athome.lu: {e}")

    # Immotop.lu
    try:
        from scrapers.immotop_scraper_real import immotop_scraper_real
        scrapers_config.append(('🏢 Immotop.lu', immotop_scraper_real))
        logger.info("✅ Immotop.lu (fonctionnel)")
    except ImportError as e:
        logger.warning(f"⚠️ Immotop.lu: {e}")

    # Luxhome.lu (JSON/Regex - version principale)
    try:
        from scrapers.luxhome_scraper import luxhome_scraper
        scrapers_config.append(('🏠 Luxhome.lu', luxhome_scraper))
        logger.info("✅ Luxhome.lu (JSON/Regex)")
    except ImportError as e:
        logger.warning(f"⚠️ Luxhome.lu: {e}")
        # Fallback vers version Selenium uniquement si la principale échoue
        try:
            from scrapers.luxhome_scraper_final import luxhome_scraper_final
            scrapers_config.append(('🏠 Luxhome.lu', luxhome_scraper_final))
            logger.info("✅ Luxhome.lu (Selenium fallback)")
        except ImportError as e2:
            logger.warning(f"⚠️ Luxhome.lu fallback: {e2}")

    # VIVI.lu (Selenium)
    try:
        from scrapers.vivi_scraper_selenium import vivi_scraper_selenium
        scrapers_config.append(('🏢 VIVI.lu', vivi_scraper_selenium))
        logger.info("✅ VIVI.lu (Selenium)")
    except ImportError as e:
        logger.warning(f"⚠️ VIVI.lu: {e}")

    # Newimmo.lu
    try:
        from scrapers.newimmo_scraper_real import newimmo_scraper_real
        scrapers_config.append(('🏘️ Newimmo.lu', newimmo_scraper_real))
        logger.info("✅ Newimmo.lu")
    except ImportError as e:
        logger.warning(f"⚠️ Newimmo.lu: {e}")

    # Unicorn.lu
    try:
        from scrapers.unicorn_scraper_real import unicorn_scraper_real
        scrapers_config.append(('🦄 Unicorn.lu', unicorn_scraper_real))
        logger.info("✅ Unicorn.lu")
    except ImportError as e:
        logger.warning(f"⚠️ Unicorn.lu: {e}")

    # ============================================
    # NOUVEAUX SITES
    # ============================================

    # Wortimmo.lu
    try:
        from scrapers.wortimmo_scraper import wortimmo_scraper
        scrapers_config.append(('📰 Wortimmo.lu', wortimmo_scraper))
        logger.info("✅ Wortimmo.lu")
    except ImportError as e:
        logger.warning(f"⚠️ Wortimmo.lu: {e}")

    # Immoweb.be (Luxembourg)
    try:
        from scrapers.immoweb_scraper import immoweb_scraper
        scrapers_config.append(('🇧🇪 Immoweb.be', immoweb_scraper))
        logger.info("✅ Immoweb.be")
    except ImportError as e:
        logger.warning(f"⚠️ Immoweb.be: {e}")

    # Nextimmo.lu
    try:
        from scrapers.nextimmo_scraper import nextimmo_scraper
        scrapers_config.append(('🏗️ Nextimmo.lu', nextimmo_scraper))
        logger.info("✅ Nextimmo.lu")
    except ImportError as e:
        logger.warning(f"⚠️ Nextimmo.lu: {e}")

    # Remax.lu
    try:
        from scrapers.remax_scraper import remax_scraper
        scrapers_config.append(('🏘️ Remax.lu', remax_scraper))
        logger.info("✅ Remax.lu")
    except ImportError as e:
        logger.warning(f"⚠️ Remax.lu: {e}")

    # Sigelux.lu
    try:
        from scrapers.sigelux_scraper import sigelux_scraper
        scrapers_config.append(('🏠 Sigelux.lu', sigelux_scraper))
        logger.info("✅ Sigelux.lu")
    except ImportError as e:
        logger.warning(f"⚠️ Sigelux.lu: {e}")

    # ImmoStar.lu
    try:
        from scrapers.immostar_scraper import immostar_scraper
        scrapers_config.append(('⭐ ImmoStar.lu', immostar_scraper))
        logger.info("✅ ImmoStar.lu")
    except ImportError as e:
        logger.warning(f"⚠️ ImmoStar.lu: {e}")

    # Apropos.lu — desactive : pagination cassee, overlap Immotop, peu d'annonces budget
    # try:
    #     from scrapers.apropos_scraper import apropos_scraper
    #     scrapers_config.append(('📋 Apropos.lu', apropos_scraper))
    #     logger.info("✅ Apropos.lu")
    # except ImportError as e:
    #     logger.warning(f"⚠️ Apropos.lu: {e}")

except ImportError as e:
    logger.error(f"❌ Erreur importation: {e}")
    sys.exit(1)

class ImmoBot:
    def __init__(self, no_notify=False):
        self.scrapers = scrapers_config
        self.cycle_count = 0
        self.scraper_failures = {}  # Compteur échecs consécutifs par site
        self.no_notify = no_notify  # Si True : aucune notification Telegram envoyee

        if no_notify:
            logger.info("🔕 Mode --no-notify actif : notifications Telegram desactivees")
        logger.info(f"🤖 Bot initialisé avec {len(self.scrapers)} sites (parallele max={MAX_CONCURRENT_SCRAPERS})")

    def _scrape_one(self, scraper_name, scraper):
        """Executer un scraper dans un thread — avec retry automatique sur exception."""
        t0 = time.time()
        last_error = None

        for attempt in range(1, SCRAPER_RETRIES + 1):
            try:
                if attempt > 1:
                    logger.info(f"🔄 {scraper_name}: tentative {attempt}/{SCRAPER_RETRIES} (attente {SCRAPER_RETRY_DELAY}s)")
                    time.sleep(SCRAPER_RETRY_DELAY)
                logger.info(f"▶️  {scraper_name} [debut]")
                listings = scraper.scrape()
                elapsed = round(time.time() - t0, 1)
                valid = [l for l in (listings or []) if l is not None]
                logger.info(f"✅ {scraper_name}: {len(valid)} annonces en {elapsed}s")
                return scraper_name, valid, None
            except Exception as e:
                elapsed = round(time.time() - t0, 1)
                last_error = str(e)
                logger.warning(f"⚠️ {scraper_name}: echec tentative {attempt}/{SCRAPER_RETRIES} ({elapsed}s): {str(e)[:80]}")

        logger.error(f"❌ {scraper_name}: abandonne apres {SCRAPER_RETRIES} tentatives")
        return scraper_name, [], last_error

    def check_new_listings(self):
        self.cycle_count += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 CYCLE #{self.cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'='*60}")

        # Nettoyage DB (annonces >30 jours)
        if self.cycle_count == 1 or self.cycle_count % 10 == 0:
            db.cleanup_old_listings(30)

        all_listings = []
        stats_per_site = {}

        # ── Scraping parallele ────────────────────────────────────────────────
        t_scrape = time.time()
        logger.info(f"🚀 Lancement {len(self.scrapers)} scrapers ({MAX_CONCURRENT_SCRAPERS} en parallele max)")

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SCRAPERS) as executor:
            futures = {
                executor.submit(self._scrape_one, name, scraper): name
                for name, scraper in self.scrapers
            }
            for future in as_completed(futures):
                scraper_name, valid_listings, error = future.result()
                if error:
                    stats_per_site[scraper_name] = 0
                    self.scraper_failures[scraper_name] = (
                        self.scraper_failures.get(scraper_name, 0) + 1
                    )
                    if self.scraper_failures[scraper_name] == 3 and not self.no_notify:
                        try:
                            notifier.send_message(
                                f"🚨 <b>ALERTE:</b> {scraper_name} a échoué 3 fois consécutives!",
                                parse_mode='HTML'
                            )
                        except Exception:
                            pass
                else:
                    all_listings.extend(valid_listings)
                    stats_per_site[scraper_name] = len(valid_listings)
                    self.scraper_failures[scraper_name] = 0

        elapsed_scrape = round(time.time() - t_scrape, 1)
        logger.info(f"⏱️  Scraping parallele termine en {elapsed_scrape}s ({len(all_listings)} annonces brutes)")

        # Enrichissement GPS : geocoder les annonces sans coordonnees
        from utils import enrich_listing_gps
        enriched_count = 0
        for listing in all_listings:
            had_gps = listing.get('latitude') is not None
            enrich_listing_gps(listing)
            if not had_gps and listing.get('latitude') is not None:
                enriched_count += 1
        if enriched_count > 0:
            logger.info(f"   📍 {enriched_count} annonces geocodees par ville")

        # Dédoublonnage cross-sites (même bien sur plusieurs sites)
        unique_listings = self._deduplicate(all_listings)
        dupes_removed = len(all_listings) - len(unique_listings)
        if dupes_removed > 0:
            logger.info(f"   🔄 {dupes_removed} doublons cross-sites supprimés")

        # Traitement des nouvelles annonces
        new_count = 0

        for listing in unique_listings:
            try:
                if self._matches_criteria(listing):
                    if not db.listing_exists(listing['listing_id']):
                        # Check doublon cross-site en DB (même prix+ville)
                        if db.similar_listing_exists(
                            listing.get('price', 0),
                            listing.get('city', ''),
                            listing.get('surface', 0)
                        ):
                            logger.debug(f"🔄 Doublon DB ignoré: {listing.get('listing_id')}")
                            continue
                        if db.add_listing(listing):
                            logger.info(f"🎉 NOUVELLE ANNONCE")
                            logger.info(f"   📝 {listing['title'][:50]}...")
                            logger.info(f"   💰 {listing['price']}€ | 🛏️ {listing['rooms']} | 📍 {listing['city']}")

                            if self.no_notify:
                                # Mode test : stocker sans notifier
                                db.mark_as_notified(listing['listing_id'])
                                new_count += 1
                                logger.info(f"   🔕 Notification ignoree (--no-notify)")
                            else:
                                # Envoyer notification (avec délai 5s entre envois)
                                if new_count > 0:
                                    time.sleep(5)
                                if notifier.send_listing(listing):
                                    db.mark_as_notified(listing['listing_id'])
                                    new_count += 1
                                    logger.info(f"   📤 Notification envoyée")
                                else:
                                    logger.warning(f"   ⚠️ Échec notification")
            except Exception as e:
                logger.error(f"   ❌ Erreur traitement annonce: {str(e)[:80]}")
                continue

        # Résumé
        stats = db.get_stats()

        logger.info(f"\n📊 RÉSUMÉ CYCLE #{self.cycle_count}")
        logger.info(f"{'-'*40}")
        logger.info(f"📈 Annonces trouvées: {len(all_listings)}")
        logger.info(f"🆕 Nouvelles annonces: {new_count}")
        logger.info(f"🗄️  Base de données: {stats.get('total', 0)} annonces")
        logger.info(f"✅ Notifiées: {stats.get('notified', 0)}")

        # Détail par site
        for site, count in stats_per_site.items():
            logger.info(f"   {site}: {count}")

        return new_count

    def _matches_criteria(self, listing):
        """Filtre central — tous les critères config.py"""
        try:
            from config import MIN_PRICE, MAX_PRICE, MIN_ROOMS, MAX_ROOMS, MIN_SURFACE, EXCLUDED_WORDS, MAX_DISTANCE

            # Prix
            price = listing.get('price', 0)
            if not isinstance(price, (int, float)) or price <= 0:
                return False
            if price < MIN_PRICE or price > MAX_PRICE:
                logger.debug(f"Rejeté prix={price} (limites {MIN_PRICE}-{MAX_PRICE}): {listing.get('listing_id')}")
                return False

            # Chambres (si connu)
            rooms = listing.get('rooms', 0) or 0
            if isinstance(rooms, (int, float)) and rooms > 0:
                if rooms < MIN_ROOMS or rooms > MAX_ROOMS:
                    logger.debug(f"Rejeté rooms={rooms} (limites {MIN_ROOMS}-{MAX_ROOMS}): {listing.get('listing_id')}")
                    return False

            # Surface (si connue)
            surface = listing.get('surface', 0) or 0
            if isinstance(surface, (int, float)) and surface > 0:
                if surface < MIN_SURFACE:
                    logger.debug(f"Rejeté surface={surface} (min {MIN_SURFACE}): {listing.get('listing_id')}")
                    return False

            # Mots exclus dans le titre + texte complet
            check_text = (str(listing.get('title', '')) + ' ' + str(listing.get('full_text', ''))).lower()
            if any(word.strip().lower() in check_text for word in EXCLUDED_WORDS if word.strip()):
                logger.debug(f"Rejeté mot exclu dans: {check_text[:50]}")
                return False

            # Distance GPS (si disponible apres enrichissement)
            distance_km = listing.get('distance_km')
            if distance_km is not None:
                try:
                    if float(distance_km) > MAX_DISTANCE:
                        logger.debug(f"Rejeté distance={distance_km:.1f}km (max {MAX_DISTANCE}): {listing.get('listing_id')}")
                        return False
                except (ValueError, TypeError):
                    pass
            else:
                # Pas de GPS meme apres geocodage → filtre par liste de villes acceptees
                from config import ACCEPTED_CITIES
                if ACCEPTED_CITIES:
                    city = self._normalize_city(listing.get('city', ''))
                    if city and not any(acc in city or city in acc for acc in ACCEPTED_CITIES):
                        logger.debug(f"Rejeté ville='{city}' pas dans ACCEPTED_CITIES: {listing.get('listing_id')}")
                        return False

            return True
        except Exception as e:
            logger.debug(f"Erreur filtre: {e}")
            return False

    @staticmethod
    def _normalize_city(city):
        """Normaliser le nom de ville pour comparaison"""
        if not city:
            return ''
        import unicodedata
        city = str(city).lower().strip()
        # Supprimer accents
        city = unicodedata.normalize('NFD', city)
        city = ''.join(c for c in city if unicodedata.category(c) != 'Mn')
        # Supprimer suffixes courants
        for suffix in ['-ville', '-gare', '-centre', '-nord', '-sud']:
            city = city.replace(suffix, '')
        return city.replace('-', ' ').replace("'", '').strip()

    def _deduplicate(self, listings):
        """Supprimer les doublons cross-sites (même bien sur plusieurs sites)

        Critères : même prix + même ville (normalisée) + surface similaire (±15m²)
        Si doublon, garder celui avec le plus d'infos (GPS, surface, chambres).
        """
        if not listings:
            return []

        seen = {}  # clé de dédup → meilleur listing
        result = []

        for listing in listings:
            price = listing.get('price', 0)
            city = self._normalize_city(listing.get('city', ''))
            surface = listing.get('surface', 0) or 0

            # Clé de dédup : prix exact + ville normalisée
            dedup_key = f"{price}_{city}"

            if dedup_key in seen:
                existing = seen[dedup_key]
                existing_surface = existing.get('surface', 0) or 0

                # Vérifier si surfaces compatibles (les deux à 0 ou écart ≤15m²)
                surfaces_match = (
                    surface == 0 or existing_surface == 0 or
                    abs(surface - existing_surface) <= 15
                )

                if surfaces_match:
                    # Garder celui avec le plus d'infos
                    new_score = self._listing_quality_score(listing)
                    old_score = self._listing_quality_score(existing)
                    if new_score > old_score:
                        seen[dedup_key] = listing
                        logger.debug(f"🔄 Doublon remplacé: {listing.get('listing_id')} > {existing.get('listing_id')}")
                    else:
                        logger.debug(f"🔄 Doublon ignoré: {listing.get('listing_id')} (garde {existing.get('listing_id')})")
                    continue

            seen[dedup_key] = listing
            result.append(listing)

        # Remplacer les listings dans result par les meilleurs de seen
        final = []
        seen_ids = set()
        for listing in result:
            price = listing.get('price', 0)
            city = self._normalize_city(listing.get('city', ''))
            dedup_key = f"{price}_{city}"
            best = seen[dedup_key]
            best_id = best.get('listing_id')
            if best_id not in seen_ids:
                final.append(best)
                seen_ids.add(best_id)

        return final

    @staticmethod
    def _listing_quality_score(listing):
        """Score de qualité d'une annonce (plus c'est haut, mieux c'est)"""
        score = 0
        if listing.get('distance_km') is not None:
            score += 3  # GPS = très utile
        if listing.get('surface', 0) and listing['surface'] > 0:
            score += 2
        if listing.get('rooms', 0) and listing['rooms'] > 0:
            score += 2
        if listing.get('city', ''):
            score += 1
        if listing.get('image_url'):
            score += 1
        return score

    def run_once(self):
        """Test unique"""
        print(f"\n{'='*60}")
        print(f"🧪 TEST UNIQUE — {len(self.scrapers)} sites actifs")
        print(f"{'='*60}")

        new_count = self.check_new_listings()

        print(f"\n{'='*60}")
        print(f"✅ TERMINÉ: {new_count} nouvelle(s) annonce(s)")
        print(f"{'='*60}")

        return new_count

    def run_continuous(self):
        """Mode production"""
        logger.info("🚀 DÉMARRAGE EN CONTINU...")

        from config import MIN_PRICE, MIN_SURFACE, MAX_DISTANCE

        if not self.no_notify:
            notifier.send_startup_message({
                'sites_count': len(self.scrapers)
            })

        while True:
            try:
                self.check_new_listings()
            except Exception as e:
                logger.error(f"❌ Erreur cycle: {e}")
                if not self.no_notify:
                    try:
                        notifier.send_error_message(str(e))
                    except Exception:
                        pass

            try:
                wait_min = CHECK_INTERVAL // 60
                logger.info(f"\n⏳ Prochain cycle dans {wait_min} minutes...")
                time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                logger.info("\n⏹️ Arrêt manuel")
                if not self.no_notify:
                    stats = db.get_stats()
                    notifier.send_shutdown_message({
                        'total': stats.get('total', 0),
                        'new': stats.get('new', 0),
                        'sites': len(self.scrapers)
                    })
                db.close()
                break

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Test unique (1 seul cycle)')
    parser.add_argument('--no-notify', action='store_true', help='Desactiver les notifications Telegram (mode test)')

    args = parser.parse_args()

    bot = ImmoBot(no_notify=args.no_notify)

    if args.once:
        bot.run_once()
    else:
        bot.run_continuous()

if __name__ == "__main__":
    main()
