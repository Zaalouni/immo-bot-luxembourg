
# test_installation.py
try:
    import requests
    import telegram
    import bs4
    import feedparser
    import dotenv
    import schedule
    import lxml

    print("✅ Toutes les dépendances sont installées !")
    print(f"requests version: {requests.__version__}")
    print(f"python-telegram-bot version: {telegram.__version__}")

except ImportError as e:
    print(f"❌ Dépendance manquante: {e}")
    print("\nInstallez avec: pip install requests python-telegram-bot beautifulsoup4 feedparser python-dotenv schedule lxml")
