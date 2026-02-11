from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
import time
import re
import logging
from config import MAX_PRICE, MIN_ROOMS

logger = logging.getLogger(__name__)

class LuxhomeScraperReal:
    def __init__(self):
        self.search_url = "https://www.luxhome.lu/recherche/?status%5B%5D=location"
    
    def scrape(self):
        driver = None
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            driver = webdriver.Firefox(options=options)
            
            driver.get(self.search_url)
            time.sleep(8)
            
            cards = driver.find_elements(By.CLASS_NAME, 'rh-ultra-list-card')
            logger.info(f"Cartes trouvées: {len(cards)}")
            
            listings = []
            for card in cards[:10]:
                try:
                    text = card.text
                    
                    # Vérifier "À Louer"
                    if 'louer' not in text.lower():
                        continue
                    
                    # URL
                    link = card.find_element(By.TAG_NAME, 'a')
                    url = link.get_attribute('href')
                    
                    # Titre
                    title_elem = card.find_element(By.CLASS_NAME, 'rh-ultra-property-title')
                    title = title_elem.text.strip()
                    
                    # Prix (chercher nombre suivi €)
                    price_match = re.search(r'([\d\s\.]+)€', text)
                    price = int(re.sub(r'[^\d]', '', price_match.group(1))) if price_match else 0
                    
                    if price > MAX_PRICE or price <= 0:
                        continue
                    
                    # ID depuis URL
                    id_match = re.search(r'/(\d+)/', url)
                    listing_id = id_match.group(1) if id_match else str(hash(url))[-6:]
                    
                    # Chambres (depuis texte ou titre)
                    rooms_match = re.search(r'(\d+)\s*chambre', text + title, re.IGNORECASE)
                    rooms = int(rooms_match.group(1)) if rooms_match else 2
                    
                    if rooms < MIN_ROOMS:
                        continue
                    
                    # Ville
                    city_match = re.search(r'(Luxembourg|Esch|Differdange|Bertrange|Merl)', text + title, re.IGNORECASE)
                    city = city_match.group(1).title() if city_match else 'Luxembourg'
                    
                    listing = {
                        'listing_id': f'luxhome_{listing_id}',
                        'site': 'Luxhome.lu',
                        'title': title[:70],
                        'city': city,
                        'price': price,
                        'rooms': rooms,
                        'surface': 65,
                        'url': url,
                        'time_ago': 'Récemment'
                    }
                    listings.append(listing)
                    
                except Exception as e:
                    logger.debug(f"Parse error: {e}")
                    continue
            
            logger.info(f"✅ {len(listings)} annonces après filtrage")
            return listings
            
        except Exception as e:
            logger.error(f"❌ Scraping: {e}")
            return []
        finally:
            if driver:
                driver.quit()

luxhome_scraper_real = LuxhomeScraperReal()
