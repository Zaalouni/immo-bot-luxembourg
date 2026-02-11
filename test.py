# test_final.py
import requests

TOKEN = "8593077858:AAH7ThCEohEJHCR6RTz_9qX6SBis6-gvLg4"
CHAT_ID = "6948826866"

print("🧪 Test d'envoi de message...")

response = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    json={
        "chat_id": CHAT_ID,
        "text": "✅ Bot immobilier Luxembourg configuré avec succès !\n\nPrêt à rechercher des biens 🏠",
        "parse_mode": "HTML"
    }
)

if response.status_code == 200:
    print("🎉 Message envoyé avec succès !")
    print(f"📱 Vérifiez votre Telegram : @immo_luxembourg_bot")
else:
    print(f"❌ Erreur: {response.json()}")
