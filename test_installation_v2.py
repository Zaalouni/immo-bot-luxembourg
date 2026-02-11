
# test_installation_v2.py
import sys

print(f"Python version: {sys.version}")
print(f"Python path: {sys.executable}")

packages = [
    ("requests", "2.28.2"),
    ("telegram", None),  # python-telegram-bot
    ("bs4", None),       # beautifulsoup4
    ("feedparser", None),
    ("dotenv", None),
    ("schedule", None),
    ("lxml", None),
]

for package, _ in packages:
    try:
        __import__(package)
        print(f"✅ {package} - OK")
    except ImportError:
        print(f"❌ {package} - MANQUANT")

print("\n" + "="*50)
print("Pour installer les packages manquants :")
print("source venv/bin/activate")
print('pip install "python-telegram-bot<20" requests beautifulsoup4 feedparser python-dotenv schedule lxml')
