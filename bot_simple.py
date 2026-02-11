
# bot_simple.py
import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class SimpleImmoBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

    def send_message(self, text):
        """Envoyer un message Telegram"""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except:
            return False

    def check_athome(self):
        """Vérifier athome.lu (version simple)"""
        try:
            # Simuler la recherche
            listings = [
                {
                    "title": "Appartement Luxembourg-Ville",
                    "price": 1800,
                    "rooms": 2,
                    "surface": 75,
                    "url": "https://www.athome.lu/12345"
                },
                {
                    "title": "Studio Esch-sur-Alzette",
                    "price": 1200,
                    "rooms": 1,
                    "surface": 45,
                    "url": "https://www.athome.lu/67890"
                }
            ]

            new_listings = []
            for listing in listings:
                if listing['price'] <= int(os.getenv('MAX_PRICE', 2000)):
                    new_listings.append(listing)

            return new_listings

        except Exception as e:
            print(f"Erreur: {e}")
            return []

    def format_listing_message(self, listing):
        """Formatter une annonce pour Telegram"""
        return f"""
🏠 *{listing['title']}*
📍 *Lieu*: Luxembourg
💰 *Prix*: {listing['price']}€/mois
🛏️ *Chambres*: {listing['rooms']}
📏 *Surface*: {listing['surface']}m²

🔗 [Voir l'annonce]({listing['url']})
        """

    def run(self):
        """Lancer le bot"""
        print("🤖 Bot immobilier démarré!")
        print(f"👤 Chat ID: {self.chat_id}")

        # Message de démarrage
        self.send_message("🤖 *Bot immobilier Luxembourg démarré!*")

        # Boucle principale
        while True:
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Recherche en cours...")

                # Vérifier les nouvelles annonces
                listings = self.check_athome()

                if listings:
                    print(f"✅ {len(listings)} nouvelle(s) annonce(s)")

                    for listing in listings:
                        message = self.format_listing_message(listing)
                        self.send_message(message)
                        time.sleep(1)  # Éviter le rate limiting
                else:
                    print("📭 Aucune nouvelle annonce")

                # Attendre avant la prochaine vérification
                interval = int(os.getenv('CHECK_INTERVAL', 600))
                print(f"⏰ Prochaine vérification dans {interval//60} minutes...")
                time.sleep(interval)

            except KeyboardInterrupt:
                print("\n\n⏹️ Arrêt du bot...")
                self.send_message("⏹️ *Bot immobilier arrêté*")
                break

            except Exception as e:
                print(f"❌ Erreur: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = SimpleImmoBot()
    bot.run()
