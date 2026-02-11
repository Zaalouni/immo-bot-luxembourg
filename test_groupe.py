
# test_groupe.py
import requests

TOKEN = "8593077858:AAH7ThCEohEJHCR6RTz_9qX6SBis6-gvLg4"
GROUP_ID = "-5249818390"

def test_groupe():
    print("🧪 Test envoi au groupe...")

    # Message test
    message = """
🤖 *TEST BOT IMMOBILIER*

✅ Le bot est maintenant configuré pour envoyer les annonces dans ce groupe!

🏠 Prochaine annonce immobilière arrivant bientôt...
    """

    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": GROUP_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
    )

    if response.status_code == 200:
        print("✅ Message envoyé au groupe!")
        print("📱 Vérifiez Telegram: Groupe 'testimmobilier2026'")
    else:
        print(f"❌ Erreur: {response.json()}")

if __name__ == "__main__":
    test_groupe()
