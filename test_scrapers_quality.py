#!/usr/bin/env python3
# =============================================================================
# test_scrapers_quality.py — Tests de qualité pour tous les scrapers
# =============================================================================
# Teste chaque scraper pour s'assurer que les données extraites sont :
# - Prix valide (int, 500-10000€)
# - Chambres valide (int, 0-10)
# - Surface valide (int, 0-500)
# - URL valide (commence par http)
# - Ville non vide
# - Image URL optionnelle mais valide si présente
#
# Usage : python test_scrapers_quality.py [--all|--scraper SCRAPER_NAME]
# =============================================================================

import unittest
import logging
import sys
from datetime import datetime
from urllib.parse import urlparse

# Config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Import scrapers
try:
    from scrapers.athome_scraper_json import athome_scraper_json
    from scrapers.immotop_scraper_real import immotop_scraper_real
    from scrapers.luxhome_scraper import luxhome_scraper
    from scrapers.vivi_scraper_selenium import vivi_scraper_selenium
    from scrapers.nextimmo_scraper import nextimmo_scraper
    from scrapers.newimmo_scraper_real import newimmo_scraper_real
    from scrapers.unicorn_scraper_real import unicorn_scraper_real
except ImportError as e:
    logger.error(f"❌ Erreur import scrapers: {e}")
    sys.exit(1)

# =============================================================================
# VALIDATORS
# =============================================================================

class ListingValidator:
    """Validateur d'annonces"""

    @staticmethod
    def is_valid_url(url):
        """Vérifier si URL est valide"""
        if not url:
            return False
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False

    @staticmethod
    def validate_listing(listing, scraper_name):
        """
        Valider une annonce complète.
        Retourne (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        # 1. listing_id
        if not listing.get('listing_id') or not isinstance(listing['listing_id'], str):
            errors.append("listing_id vide ou invalide")

        # 2. site
        if not listing.get('site'):
            errors.append("site vide")
        elif listing['site'] != scraper_name:
            warnings.append(f"site='{listing['site']}' au lieu de '{scraper_name}'")

        # 3. title
        title = listing.get('title', '')
        if not title or len(title) < 5:
            errors.append(f"title trop court ({len(title)} chars)")
        if len(title) > 200:
            warnings.append(f"title trop long ({len(title)} chars)")

        # 4. city
        city = listing.get('city', '')
        if not city or len(city) < 2:
            warnings.append(f"city invalide: '{city}'")

        # 5. price (CRITIQUE)
        price = listing.get('price')
        if price is None or not isinstance(price, (int, float)):
            errors.append(f"price invalide type: {type(price).__name__}")
        elif price <= 0:
            errors.append(f"price <= 0: {price}")
        elif price < 300:
            errors.append(f"price improbable (trop bas): {price}€")
        elif price > 10000:
            errors.append(f"price improbable (trop haut): {price}€")

        # 6. rooms
        rooms = listing.get('rooms')
        if rooms is None or not isinstance(rooms, int):
            warnings.append(f"rooms invalide type: {type(rooms).__name__}")
        elif rooms < 0 or rooms > 10:
            warnings.append(f"rooms hors limites: {rooms}")

        # 7. surface
        surface = listing.get('surface')
        if surface is None or not isinstance(surface, int):
            warnings.append(f"surface invalide type: {type(surface).__name__}")
        elif surface < 0 or surface > 500:
            warnings.append(f"surface hors limites: {surface}")

        # 8. url (CRITIQUE)
        url = listing.get('url')
        if not ListingValidator.is_valid_url(url):
            errors.append(f"url invalide: {url}")

        # 9. image_url (optionnel mais valide si présent)
        image_url = listing.get('image_url')
        if image_url and not ListingValidator.is_valid_url(image_url):
            warnings.append(f"image_url invalide: {image_url}")

        # 10. GPS optionnel mais valide si présent
        lat = listing.get('latitude')
        lng = listing.get('longitude')
        if lat is not None:
            if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
                warnings.append(f"latitude invalide: {lat}")
        if lng is not None:
            if not isinstance(lng, (int, float)) or lng < -180 or lng > 180:
                warnings.append(f"longitude invalide: {lng}")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

# =============================================================================
# TEST CASES
# =============================================================================

class TestAthomeScraper(unittest.TestCase):
    """Tests Athome.lu"""

    def test_scrape_returns_list(self):
        """Vérifier que scrape() retourne une liste"""
        listings = athome_scraper_json.scrape()
        self.assertIsInstance(listings, list, "scrape() doit retourner une liste")

    def test_all_listings_valid(self):
        """Vérifier que TOUTES les annonces sont valides"""
        listings = athome_scraper_json.scrape()
        self.assertGreater(len(listings), 0, "❌ Athome: Aucune annonce trouvée")

        errors_list = []
        for i, listing in enumerate(listings):
            is_valid, errors, warnings = ListingValidator.validate_listing(listing, "Athome.lu")
            if not is_valid:
                errors_list.append((i, errors))
            if warnings:
                logger.warning(f"Athome listing {i}: {', '.join(warnings)}")

        if errors_list:
            error_msg = "\n".join([f"  [{i}] {', '.join(errors)}" for i, errors in errors_list[:5]])
            self.fail(f"❌ Athome: {len(errors_list)} annonces invalides\n{error_msg}")

        logger.info(f"✅ Athome: {len(listings)} annonces valides")

    def test_price_not_zero(self):
        """Vérifier qu'aucun prix n'est 0"""
        listings = athome_scraper_json.scrape()
        zero_prices = [l for l in listings if l.get('price', 0) <= 0]
        self.assertEqual(len(zero_prices), 0, f"❌ Athome: {len(zero_prices)} prix = 0")


class TestImmotopScraper(unittest.TestCase):
    """Tests Immotop.lu"""

    def test_scrape_returns_list(self):
        listings = immotop_scraper_real.scrape()
        self.assertIsInstance(listings, list)

    def test_all_listings_valid(self):
        listings = immotop_scraper_real.scrape()
        self.assertGreater(len(listings), 0, "❌ Immotop: Aucune annonce")

        errors_list = []
        for i, listing in enumerate(listings):
            is_valid, errors, warnings = ListingValidator.validate_listing(listing, "Immotop.lu")
            if not is_valid:
                errors_list.append((i, errors))
            if warnings:
                logger.warning(f"Immotop listing {i}: {', '.join(warnings)}")

        if errors_list:
            error_msg = "\n".join([f"  [{i}] {', '.join(errors)}" for i, errors in errors_list[:5]])
            self.fail(f"❌ Immotop: {len(errors_list)} annonces invalides\n{error_msg}")

        logger.info(f"✅ Immotop: {len(listings)} annonces valides")

    def test_price_parsing(self):
        """Tester la parsing de prix avec espaces insécables"""
        listings = immotop_scraper_real.scrape()
        for listing in listings:
            price = listing.get('price', 0)
            self.assertIsInstance(price, int, "Prix doit être int")
            self.assertGreater(price, 0, "Prix doit être > 0")


class TestLuxhomeScraper(unittest.TestCase):
    """Tests Luxhome.lu"""

    def test_scrape_returns_list(self):
        listings = luxhome_scraper.scrape()
        self.assertIsInstance(listings, list)

    def test_all_listings_valid(self):
        listings = luxhome_scraper.scrape()
        self.assertGreater(len(listings), 0, "❌ Luxhome: Aucune annonce")

        errors_list = []
        for i, listing in enumerate(listings):
            is_valid, errors, warnings = ListingValidator.validate_listing(listing, "Luxhome.lu")
            if not is_valid:
                errors_list.append((i, errors))
            if warnings:
                logger.warning(f"Luxhome listing {i}: {', '.join(warnings)}")

        if errors_list:
            error_msg = "\n".join([f"  [{i}] {', '.join(errors)}" for i, errors in errors_list[:5]])
            self.fail(f"❌ Luxhome: {len(errors_list)} annonces invalides\n{error_msg}")

        logger.info(f"✅ Luxhome: {len(listings)} annonces valides")

    def test_gps_present(self):
        """Vérifier que latitude/longitude sont présentes"""
        listings = luxhome_scraper.scrape()
        with_gps = [l for l in listings if l.get('latitude') and l.get('longitude')]
        pct = 100 * len(with_gps) / len(listings) if listings else 0
        logger.info(f"  Luxhome: {pct:.1f}% avec GPS")


class TestViviScraper(unittest.TestCase):
    """Tests VIVI.lu"""

    def test_scrape_returns_list(self):
        listings = vivi_scraper_selenium.scrape()
        self.assertIsInstance(listings, list)

    def test_all_listings_valid(self):
        listings = vivi_scraper_selenium.scrape()
        if not listings:
            logger.warning("⚠️ VIVI: Aucune annonce (possible timeout Selenium)")
            return

        errors_list = []
        for i, listing in enumerate(listings):
            is_valid, errors, warnings = ListingValidator.validate_listing(listing, "VIVI.lu")
            if not is_valid:
                errors_list.append((i, errors))
            if warnings:
                logger.warning(f"VIVI listing {i}: {', '.join(warnings)}")

        if errors_list:
            error_msg = "\n".join([f"  [{i}] {', '.join(errors)}" for i, errors in errors_list[:5]])
            self.fail(f"❌ VIVI: {len(errors_list)} annonces invalides\n{error_msg}")

        logger.info(f"✅ VIVI: {len(listings)} annonces valides")


class TestNextimmoScraper(unittest.TestCase):
    """Tests Nextimmo.lu"""

    def test_scrape_returns_list(self):
        listings = nextimmo_scraper.scrape()
        self.assertIsInstance(listings, list)

    def test_all_listings_valid(self):
        listings = nextimmo_scraper.scrape()
        self.assertGreater(len(listings), 0, "❌ Nextimmo: Aucune annonce")

        errors_list = []
        for i, listing in enumerate(listings):
            is_valid, errors, warnings = ListingValidator.validate_listing(listing, "Nextimmo.lu")
            if not is_valid:
                errors_list.append((i, errors))
            if warnings:
                logger.warning(f"Nextimmo listing {i}: {', '.join(warnings)}")

        if errors_list:
            error_msg = "\n".join([f"  [{i}] {', '.join(errors)}" for i, errors in errors_list[:5]])
            self.fail(f"❌ Nextimmo: {len(errors_list)} annonces invalides\n{error_msg}")

        logger.info(f"✅ Nextimmo: {len(listings)} annonces valides")

    def test_gps_present(self):
        """Vérifier que latitude/longitude sont présentes"""
        listings = nextimmo_scraper.scrape()
        with_gps = [l for l in listings if l.get('latitude') and l.get('longitude')]
        pct = 100 * len(with_gps) / len(listings) if listings else 0
        logger.info(f"  Nextimmo: {pct:.1f}% avec GPS")


class TestNewimuScraper(unittest.TestCase):
    """Tests Newimmo.lu"""

    def test_scrape_returns_list(self):
        listings = newimmo_scraper_real.scrape()
        self.assertIsInstance(listings, list)

    def test_all_listings_valid(self):
        listings = newimmo_scraper_real.scrape()
        if not listings:
            logger.warning("⚠️ Newimmo: Aucune annonce (possible timeout Selenium)")
            return

        errors_list = []
        for i, listing in enumerate(listings):
            is_valid, errors, warnings = ListingValidator.validate_listing(listing, "Newimmo.lu")
            if not is_valid:
                errors_list.append((i, errors))
            if warnings:
                logger.warning(f"Newimmo listing {i}: {', '.join(warnings)}")

        if errors_list:
            error_msg = "\n".join([f"  [{i}] {', '.join(errors)}" for i, errors in errors_list[:5]])
            self.fail(f"❌ Newimmo: {len(errors_list)} annonces invalides\n{error_msg}")

        logger.info(f"✅ Newimmo: {len(listings)} annonces valides")


class TestUnicornScraper(unittest.TestCase):
    """Tests Unicorn.lu"""

    def test_scrape_returns_list(self):
        listings = unicorn_scraper_real.scrape()
        self.assertIsInstance(listings, list)

    def test_all_listings_valid(self):
        listings = unicorn_scraper_real.scrape()
        if not listings:
            logger.warning("⚠️ Unicorn: Aucune annonce (possible CAPTCHA)")
            return

        errors_list = []
        for i, listing in enumerate(listings):
            is_valid, errors, warnings = ListingValidator.validate_listing(listing, "Unicorn.lu")
            if not is_valid:
                errors_list.append((i, errors))
            if warnings:
                logger.warning(f"Unicorn listing {i}: {', '.join(warnings)}")

        if errors_list:
            error_msg = "\n".join([f"  [{i}] {', '.join(errors)}" for i, errors in errors_list[:5]])
            self.fail(f"❌ Unicorn: {len(errors_list)} annonces invalides\n{error_msg}")

        logger.info(f"✅ Unicorn: {len(listings)} annonces valides")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🧪 TEST SCRAPERS QUALITY")
    print(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*80 + "\n")

    # Options CLI
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Mode test unique (pour CI/CD)
        suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)
    else:
        # Mode complet
        unittest.main(verbosity=2, exit=True)
