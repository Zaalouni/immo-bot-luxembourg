#!/usr/bin/env python3
"""
Test local des scrapers — vérifie extraction, filtrage, liens, données
Usage: python test_scrapers.py
"""
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_scraper(name, scraper):
    """Tester un scraper et afficher les résultats"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")

    try:
        listings = scraper.scrape()

        if listings is None:
            print(f"  ❌ Retourne None au lieu de []")
            return 0

        print(f"  📊 {len(listings)} annonces retournées")

        for i, listing in enumerate(listings[:5]):  # Max 5 affichés
            print(f"\n  --- Annonce #{i+1} ---")
            print(f"  ID:      {listing.get('listing_id', '???')}")
            print(f"  Titre:   {listing.get('title', '???')[:60]}")
            print(f"  Prix:    {listing.get('price', '???')}€")
            print(f"  Rooms:   {listing.get('rooms', '???')}")
            print(f"  Surface: {listing.get('surface', '???')}m²")
            print(f"  Ville:   {listing.get('city', '???')}")
            print(f"  URL:     {listing.get('url', '???')[:80]}")
            dist = listing.get('distance_km')
            if dist:
                print(f"  GPS:     {dist:.1f} km")

            # Vérifications
            errors = []
            if not listing.get('listing_id'):
                errors.append("listing_id vide!")
            if not listing.get('url') or not listing['url'].startswith('http'):
                errors.append(f"URL invalide: {listing.get('url', 'MANQUANT')}")
            if listing.get('price', 0) <= 0:
                errors.append(f"Prix invalide: {listing.get('price')}")
            if '<' in str(listing.get('title', '')):
                errors.append(f"HTML dans titre: {listing.get('title')[:50]}")
            if listing.get('rooms') is None:
                errors.append("rooms=None (devrait être 0)")

            if errors:
                for err in errors:
                    print(f"  ⚠️  {err}")

        if len(listings) > 5:
            print(f"\n  ... et {len(listings) - 5} autres annonces")

        return len(listings)

    except Exception as e:
        print(f"  ❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return -1


def main():
    print("🧪 TEST DES SCRAPERS IMMO-BOT-LUXEMBOURG")
    print(f"{'='*60}")

    results = {}

    # === SCRAPERS HTTP (pas besoin de Selenium) ===

    # 1. Athome.lu
    try:
        from scrapers.athome_scraper_json import athome_scraper_json
        results['Athome.lu'] = test_scraper('Athome.lu (JSON)', athome_scraper_json)
    except ImportError as e:
        print(f"\n❌ Athome.lu: {e}")
        results['Athome.lu'] = -1

    # 2. Immotop.lu
    try:
        from scrapers.immotop_scraper_real import immotop_scraper_real
        results['Immotop.lu'] = test_scraper('Immotop.lu', immotop_scraper_real)
    except ImportError as e:
        print(f"\n❌ Immotop.lu: {e}")
        results['Immotop.lu'] = -1

    # 3. Luxhome.lu
    try:
        from scrapers.luxhome_scraper import luxhome_scraper
        results['Luxhome.lu'] = test_scraper('Luxhome.lu (JSON/Regex)', luxhome_scraper)
    except ImportError as e:
        print(f"\n❌ Luxhome.lu: {e}")
        results['Luxhome.lu'] = -1

    # 4. Nextimmo.lu (API JSON)
    try:
        from scrapers.nextimmo_scraper import nextimmo_scraper
        results['Nextimmo.lu'] = test_scraper('Nextimmo.lu (API JSON)', nextimmo_scraper)
    except ImportError as e:
        print(f"\n❌ Nextimmo.lu: {e}")
        results['Nextimmo.lu'] = -1

    # === SCRAPERS SELENIUM (nécessitent Firefox) ===
    if '--no-selenium' not in sys.argv:
        # 5. VIVI.lu
        try:
            from scrapers.vivi_scraper_selenium import vivi_scraper_selenium
            results['VIVI.lu'] = test_scraper('VIVI.lu (Selenium)', vivi_scraper_selenium)
        except ImportError as e:
            print(f"\n❌ VIVI.lu: {e}")
            results['VIVI.lu'] = -1

        # 6. Newimmo.lu
        try:
            from scrapers.newimmo_scraper_real import newimmo_scraper_real
            results['Newimmo.lu'] = test_scraper('Newimmo.lu (Selenium)', newimmo_scraper_real)
        except ImportError as e:
            print(f"\n❌ Newimmo.lu: {e}")
            results['Newimmo.lu'] = -1

        # 7. Unicorn.lu
        try:
            from scrapers.unicorn_scraper_real import unicorn_scraper_real
            results['Unicorn.lu'] = test_scraper('Unicorn.lu (Selenium)', unicorn_scraper_real)
        except ImportError as e:
            print(f"\n❌ Unicorn.lu: {e}")
            results['Unicorn.lu'] = -1

        # 8. Immoweb.be (Selenium)
        try:
            from scrapers.immoweb_scraper import immoweb_scraper
            results['Immoweb.be'] = test_scraper('Immoweb.be (Selenium)', immoweb_scraper)
        except ImportError as e:
            print(f"\n❌ Immoweb.be: {e}")
            results['Immoweb.be'] = -1

        # 9. Wortimmo.lu (Selenium)
        try:
            from scrapers.wortimmo_scraper import wortimmo_scraper
            results['Wortimmo.lu'] = test_scraper('Wortimmo.lu (Selenium)', wortimmo_scraper)
        except ImportError as e:
            print(f"\n❌ Wortimmo.lu: {e}")
            results['Wortimmo.lu'] = -1
    else:
        print("\n⏭️  Scrapers Selenium ignorés (--no-selenium)")

    # === RÉSUMÉ ===
    print(f"\n{'='*60}")
    print("📊 RÉSUMÉ DES TESTS")
    print(f"{'='*60}")
    for site, count in results.items():
        if count < 0:
            status = "❌ ERREUR"
        elif count == 0:
            status = "⚠️  0 résultats"
        else:
            status = f"✅ {count} annonces"
        print(f"  {site:20s} {status}")

    total = sum(c for c in results.values() if c > 0)
    print(f"\n  TOTAL: {total} annonces")


if __name__ == "__main__":
    main()
