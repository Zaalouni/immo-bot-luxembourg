# test_athome_scraper.py
import logging
from scrapers.athome_scraper import AthomeScraper

logging.basicConfig(level=logging.INFO)

def test_athome_scraper():
    """Tester le scraper Athome.lu"""
    print("🧪 Test du scraper Athome.lu")
    print("=" * 50)
    
    scraper = AthomeScraper()
    
    try:
        # Test scraping
        listings = scraper.scrape()
        
        print(f"\n📊 Résultats: {len(listings)} annonces trouvées")
        
        if listings:
            print("\n📋 Exemple d'annonces:")
            for i, listing in enumerate(listings[:3]):  # Afficher 3 max
                print(f"\n{i+1}. {listing['title']}")
                print(f"   💰 Prix: {listing['price']}€")
                print(f"   🛏️ Chambres: {listing['rooms']}")
                print(f"   📍 Ville: {listing['city']}")
                print(f"   🔗 URL: {listing['url'][:50]}...")
        
        # Test parsing individuel
        print("\n🧪 Test parsing HTML simple...")
        test_html = """
        <div class="property-item" data-id="12345">
            <h2><a href="/annonce/12345">Bel appartement Centre-Ville</a></h2>
            <span class="price">1.800 €</span>
            <span class="bedrooms">3 chambres</span>
            <span class="surface">85 m²</span>
        </div>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(test_html, 'html.parser')
        card = soup.find('div')
        
        test_listing = scraper._parse_listing(card, 'Luxembourg')
        if test_listing:
            print(f"\n✅ Test parsing réussi:")
            print(f"   ID: {test_listing['listing_id']}")
            print(f"   Titre: {test_listing['title']}")
            print(f"   Prix: {test_listing['price']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_athome_scraper()
