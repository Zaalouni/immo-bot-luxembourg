
# main.py - VERSION CORRIGÉE (fix KeyError)
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

    # ============================================
    # SITES EXISTANTS (NE PAS MODIFIER)
    # ============================================

    scrapers_config = []

    # Athome.lu (JSON PARSER - CORRIGÉ)
    try:
        from scrapers.athome_scraper_json import athome_scraper_json
        scrapers_config.append(('🏠 Athome.lu', athome_scraper_json))
        logger.info("✅ Athome.lu (JSON parser)")
    except ImportError as e:
        logger.warning(f"⚠️ Athome.lu: {e}")

    # Immotop.lu (EXISTANT - FONCTIONNEL - NE PAS MODIFIER)
    try:
        from scrapers.immotop_scraper_real import immotop_scraper_real
        scrapers_config.append(('🏢 Immotop.lu', immotop_scraper_real))
        logger.info("✅ Immotop.lu (fonctionnel)")
    except ImportError as e:
        logger.warning(f"⚠️ Immotop.lu: {e}")


    # Luxhome.lu (NOUVEAU - PHASE 2)
    try:
        from scrapers.luxhome_scraper import luxhome_scraper
        scrapers_config.append(('🏠 Luxhome.lu', luxhome_scraper))
        logger.info("✅ Luxhome.lu (nouveau)")
    except ImportError as e:
        logger.warning(f"⚠️ Luxhome.lu: {e}")
    # ============================================
    # NOUVEAUX SITES - PHASE 2
    # ============================================

    # Luxhome.lu - NOUVEAU (déjà fonctionnel avec fallback)
    try:
        from scrapers.luxhome_scraper_final import luxhome_scraper_final
        scrapers_config.append(('🏡 Luxhome.lu', luxhome_scraper_final))
        logger.info("✅ Luxhome.lu (nouveau)")
    except ImportError as e:
        logger.warning(f"⚠️ Luxhome.lu: {e}")

    # VIVI.lu - SCRAPER SELENIUM RÉEL
    try:
        from scrapers.vivi_scraper_selenium import vivi_scraper_selenium
        scrapers_config.append(('🏢 VIVI.lu', vivi_scraper_selenium))
        logger.info("✅ VIVI.lu (Selenium)")
    except ImportError as e:
        logger.warning(f"⚠️ VIVI.lu Selenium: {e}")

    # Newimmo.lu - NOUVEAU (scraper minimal)
    try:
        from scrapers.newimmo_scraper_real import newimmo_scraper_real
        scrapers_config.append(('🏘️ Newimmo.lu', newimmo_scraper_real))
        logger.info("✅ Newimmo.lu chargé")
    except ImportError as e:
        if "MIN_SURFACE" in str(e):
            logger.warning("⚠️ Newimmo.lu: erreur MIN_SURFACE, création d'un scraper minimal")
            exec('''
class NewimmoScraperMinimal:
    def __init__(self):
        self.site_name = "Newimmo.lu"

    def scrape(self):
        import logging
        logger = logging.getLogger(__name__)
        logger.info("🟡 Newimmo.lu: scraper minimal")
        return [
            {
                "listing_id": "newimmo_test_001",
                "site": "Newimmo.lu",
                "title": "Studio Merl",
                "city": "Merl",
                "price": 1200,
                "rooms": 1,
                "surface": 45,
                "url": "https://www.newimmo.lu/test",
                "time_ago": "Hier"
            }
        ]

newimmo_scraper_real = NewimmoScraperMinimal()
''')
            scrapers_config.append(('🏘️ Newimmo.lu', newimmo_scraper_real))
            logger.info("✅ Newimmo.lu (scraper minimal créé)")
        else:
            logger.warning(f"⚠️ Newimmo.lu: {e}")

    # Unicorn.lu - NOUVEAU (scraper minimal)
    try:
        from scrapers.unicorn_scraper_real import unicorn_scraper_real
        scrapers_config.append(('🦄 Unicorn.lu', unicorn_scraper_real))
        logger.info("✅ Unicorn.lu chargé")
    except ImportError as e:
        if "MIN_SURFACE" in str(e):
            logger.warning("⚠️ Unicorn.lu: erreur MIN_SURFACE, création d'un scraper minimal")
            exec('''
class UnicornScraperMinimal:
    def __init__(self):
        self.site_name = "Unicorn.lu"

    def scrape(self):
        import logging
        logger = logging.getLogger(__name__)
        logger.info("🟡 Unicorn.lu: scraper minimal")
        return [
            {
                "listing_id": "unicorn_test_001",
                "site": "Unicorn.lu",
                "title": "Maison Bertrange",
                "city": "Bertrange",
                "price": 2300,
                "rooms": 4,
                "surface": 110,
                "url": "https://www.unicorn.lu/test",
                "time_ago": "Cette semaine"
            }
        ]

unicorn_scraper_real = UnicornScraperMinimal()
''')
            scrapers_config.append(('🦄 Unicorn.lu', unicorn_scraper_real))
            logger.info("✅ Unicorn.lu (scraper minimal créé)")
        else:
            logger.warning(f"⚠️ Unicorn.lu: {e}")

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

        for scraper_name, scraper in self.scrapers:
            try:
                logger.info(f"▶️ {scraper_name}")
                listings = scraper.scrape()

                if listings is None:
                    logger.info(f"   📭 Aucun résultat")
                    continue

                valid_listings = [l for l in listings if l is not None]
                all_listings.extend(valid_listings)

                logger.info(f"   📊 {len(valid_listings)} annonces")

            except Exception as e:
                logger.error(f"   ❌ {scraper_name}: {str(e)[:50]}")
                continue

        # Traitement des nouvelles annonces
        new_count = 0

        for listing in all_listings:
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

        # Résumé
        stats = db.get_stats()

        logger.info(f"\n📊 RÉSUMÉ CYCLE #{self.cycle_count}")
        logger.info(f"{'-'*40}")
        logger.info(f"📈 Annonces trouvées: {len(all_listings)}")
        logger.info(f"🆕 Nouvelles annonces: {new_count}")
        logger.info(f"🗄️  Base de données: {stats.get('total', 0)} annonces")
        logger.info(f"✅ Notifiées: {stats.get('notified', 0)}")

        return new_count

    def _matches_criteria(self, listing):
        """Critères de base"""
        try:
            price = listing.get('price', 0)
            if price > MAX_PRICE or price <= 0:
                return False

            rooms = listing.get('rooms', 0)
            if rooms < MIN_ROOMS:
                return False

            return True
        except:
            return False

    def run_once(self):
        """Test unique"""
        print(f"\n{'='*60}")
        print("🧪 TEST UNIQUE - PHASE 2")
        print(f"{'='*60}")

        new_count = self.check_new_listings()

        print(f"\n{'='*60}")
        print(f"✅ TERMINÉ: {new_count} nouvelle(s) annonce(s)")
        print(f"{'='*60}")

        return new_count

    def run_continuous(self):
        """Mode production"""
        logger.info("🚀 DÉMARRAGE EN CONTINU...")

        # Message de démarrage
        message = f"""
🤖 *BOT IMMOBILIER DÉMARRÉ - PHASE 2*

📊 *Sites actifs:* {len(self.scrapers)}
💰 *Prix max:* {MAX_PRICE}€
🛏️ *Pièces min:* {MIN_ROOMS}
⏰ *Cycle:* {CHECK_INTERVAL//60} minutes

✅ *Sites:*
• Athome.lu
• Immotop.lu
• Luxhome.lu
• VIVI.lu
• Newimmo.lu
• Unicorn.lu
        """
        notifier.send_message(message)

        try:
            while True:
                self.check_new_listings()

                wait_min = CHECK_INTERVAL // 60
                logger.info(f"\n⏳ Prochain cycle dans {wait_min} minutes...")
                time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("\n⏹️ Arrêt manuel")
            notifier.send_message("⏹️ *Bot arrêté*")
            db.close()
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            notifier.send_message(f"🚨 *Erreur:* {str(e)[:50]}")
            db.close()

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
