
# main.py - VERSION CORRIGÉE
import logging
import time
import sys
import argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('immo_bot.log', encoding='utf-8'),
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

except ImportError as e:
    logger.error(f"❌ Erreur importation: {e}")
    sys.exit(1)

class ImmoBot:
    def __init__(self):
        self.scrapers = scrapers_config
        self.cycle_count = 0

        logger.info(f"🤖 Bot initialisé avec {len(self.scrapers)} sites")

    def check_new_listings(self):
        self.cycle_count += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 CYCLE #{self.cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'='*60}")

        all_listings = []
        stats_per_site = {}

        for scraper_name, scraper in self.scrapers:
            try:
                logger.info(f"▶️ {scraper_name}")
                listings = scraper.scrape()

                if listings is None:
                    logger.info(f"   📭 Aucun résultat")
                    stats_per_site[scraper_name] = 0
                    continue

                valid_listings = [l for l in listings if l is not None]
                all_listings.extend(valid_listings)
                stats_per_site[scraper_name] = len(valid_listings)

                logger.info(f"   📊 {len(valid_listings)} annonces")

            except Exception as e:
                logger.error(f"   ❌ {scraper_name}: {str(e)[:100]}")
                stats_per_site[scraper_name] = 0
                continue

        # Traitement des nouvelles annonces
        new_count = 0

        for listing in all_listings:
            try:
                if self._matches_criteria(listing):
                    if not db.listing_exists(listing['listing_id']):
                        if db.add_listing(listing):
                            logger.info(f"🎉 NOUVELLE ANNONCE")
                            logger.info(f"   📝 {listing['title'][:50]}...")
                            logger.info(f"   💰 {listing['price']}€ | 🛏️ {listing['rooms']} | 📍 {listing['city']}")

                            # Envoyer notification
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
        """Critères de base"""
        try:
            price = listing.get('price', 0)
            if not isinstance(price, (int, float)) or price > MAX_PRICE or price <= 0:
                return False

            rooms = listing.get('rooms', 0)
            if not isinstance(rooms, (int, float)) or rooms < MIN_ROOMS:
                return False

            return True
        except Exception:
            return False

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

        site_names = [name for name, _ in self.scrapers]
        sites_list = '\n'.join([f'• {s}' for s in site_names])

        message = f"""
🤖 *BOT IMMOBILIER DÉMARRÉ*

📊 *Sites actifs:* {len(self.scrapers)}
💰 *Prix max:* {MAX_PRICE}€
🛏️ *Pièces min:* {MIN_ROOMS}
⏰ *Cycle:* {CHECK_INTERVAL//60} minutes

✅ *Sites:*
{sites_list}
        """
        notifier.send_message(message)

        while True:
            try:
                self.check_new_listings()
            except Exception as e:
                logger.error(f"❌ Erreur cycle: {e}")
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
                notifier.send_message("⏹️ *Bot arrêté*")
                db.close()
                break

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Test unique')

    args = parser.parse_args()

    bot = ImmoBot()

    if args.once:
        bot.run_once()
    else:
        bot.run_continuous()

if __name__ == "__main__":
    main()
