# Guide d'Installation — MCP Server Immo-Bot Luxembourg

## Prérequis

| Composant | Version minimale | Vérification |
|-----------|-----------------|--------------|
| Python | 3.10+ | `python --version` |
| pip | 23.0+ | `pip --version` |
| Bot principal | configuré avec `.env` | `python config.py` |
| listings.db | existante | `ls -la listings.db` |

---

## Étape 1 — Vérifier Python

```bash
python --version
# → Python 3.10.x ou supérieur requis

# Si Python 3.7 mais pas 3.10, vérifier avec python3
python3 --version
```

> **Note:** Le SDK MCP requiert Python 3.10+ pour les type hints modernes (`X | Y`).
> Si votre serveur tourne Python 3.7-3.9, voir la section **Compatibility Mode** ci-dessous.

---

## Étape 2 — Installer le SDK MCP

```bash
# Depuis le répertoire racine du projet
cd /home/user/immo-bot-luxembourg

# Installation dans le venv existant (recommandé)
source venv/bin/activate
pip install mcp>=1.0.0

# OU installation système (si pas de venv)
pip install mcp>=1.0.0

# OU avec toutes les dépendances MCP
pip install -r mcp_server/requirements_mcp.txt
```

Vérifier l'installation :

```bash
python -c "import mcp; print('MCP version:', mcp.__version__)"
# → MCP version: 1.x.x
```

---

## Étape 3 — Tester le démarrage du serveur

```bash
cd /home/user/immo-bot-luxembourg

# Test de démarrage (Ctrl+C pour arrêter)
python mcp_server/mcp_server.py
# → Affiche les logs de démarrage sur stderr
# → Attend les requêtes MCP sur stdin/stdout
```

Sortie attendue :
```
2026-02-27 10:00:00 [INFO] mcp_server.main: ============================================================
2026-02-27 10:00:00 [INFO] mcp_server.main: Immo-Bot Luxembourg MCP Server v1.0.0
2026-02-27 10:00:00 [INFO] mcp_server.main: ============================================================
2026-02-27 10:00:00 [INFO] mcp_server.main: Transport: stdio
```

---

## Étape 4 — Configurer Claude Desktop

### Trouver le fichier de config Claude

```bash
# Linux
cat ~/.config/claude/claude_desktop_config.json

# Si le fichier n'existe pas
mkdir -p ~/.config/claude
echo '{"mcpServers": {}}' > ~/.config/claude/claude_desktop_config.json
```

### Ajouter la configuration MCP

Ouvrir `~/.config/claude/claude_desktop_config.json` et ajouter :

```json
{
  "mcpServers": {
    "immo-bot-luxembourg": {
      "command": "python",
      "args": [
        "/home/user/immo-bot-luxembourg/mcp_server/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/home/user/immo-bot-luxembourg"
      }
    }
  }
}
```

> La configuration complète est disponible dans `mcp_server/mcp_config.json`.

### Si vous utilisez le venv

```json
{
  "mcpServers": {
    "immo-bot-luxembourg": {
      "command": "/home/user/immo-bot-luxembourg/venv/bin/python",
      "args": [
        "/home/user/immo-bot-luxembourg/mcp_server/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/home/user/immo-bot-luxembourg"
      }
    }
  }
}
```

---

## Étape 5 — Vérifier avec l'inspecteur MCP (optionnel)

```bash
# Installer l'inspecteur MCP (Node.js requis)
npx @modelcontextprotocol/inspector python mcp_server/mcp_server.py

# → Ouvre une interface web sur http://localhost:5173
# → Permet de tester chaque tool manuellement
```

---

## Étape 6 — Lancer les tests

```bash
cd /home/user/immo-bot-luxembourg

# Tests complets
python mcp_server/test_mcp_server.py -v

# Tests via pytest
pytest mcp_server/test_mcp_server.py -v

# Classe spécifique
python mcp_server/test_mcp_server.py TestSearchTool -v
```

Sortie attendue :
```
============================================================
  MCP SERVER — SUITE DE TESTS COMPLÈTE
============================================================
TestConfig ... ok (4 tests)
TestSearchTool ... ok (7 tests)
TestStatsTool ... ok (4 tests)
...
TOTAL: 40+ tests | OK: 40 | Échecs: 0 | Erreurs: 0
============================================================
```

---

## Mode Compatibility Python 3.7-3.9

Si votre serveur tourne Python < 3.10, les type hints `X | Y` et `dict | None`
ne sont pas supportés. Deux options :

### Option A — Installer Python 3.10+

```bash
# Ubuntu/Debian
sudo apt-get install python3.10
python3.10 -m pip install mcp
python3.10 mcp_server/mcp_server.py
```

### Option B — Modifier les type hints

Remplacer dans tous les fichiers `tools/*.py` et `resources/*.py` :
```python
# Avant (Python 3.10+)
def func() -> dict | None:

# Après (Python 3.7+)
from typing import Optional, Dict
def func() -> Optional[Dict]:
```

---

## Variables d'environnement MCP

| Variable | Défaut | Description |
|----------|--------|-------------|
| `PYTHONPATH` | `/home/user/immo-bot-luxembourg` | Chemin pour imports |
| `MCP_LOG_LEVEL` | `INFO` | Niveau de log (DEBUG/INFO/WARNING) |

---

## Dépannage

### Erreur: `ModuleNotFoundError: No module named 'mcp'`
```bash
pip install mcp>=1.0.0
# OU avec venv:
/home/user/immo-bot-luxembourg/venv/bin/pip install mcp>=1.0.0
```

### Erreur: `ModuleNotFoundError: No module named 'config'`
```bash
# Vérifier que PYTHONPATH est bien défini
export PYTHONPATH=/home/user/immo-bot-luxembourg
python mcp_server/mcp_server.py
```

### Erreur: `DB introuvable`
```bash
# Vérifier que listings.db existe
ls -la /home/user/immo-bot-luxembourg/listings.db

# Si absente, lancer le bot une fois en mode --once
python main.py --once
```

### Erreur: `TELEGRAM_BOT_TOKEN manquant`
```bash
# Le serveur MCP ne nécessite PAS Telegram pour search/stats/geo.
# Telegram est uniquement requis pour send_alert et test_connection.
# Vérifier .env:
cat /home/user/immo-bot-luxembourg/.env | grep TELEGRAM
```

### Logs de debug
```bash
MCP_LOG_LEVEL=DEBUG python mcp_server/mcp_server.py 2>&1 | head -50
```

---

## Structure des fichiers créés

```
mcp_server/
├── mcp_server.py          ← Point d'entrée principal
├── config_mcp.py          ← Configuration MCP
├── requirements_mcp.txt   ← Dépendances
├── mcp_config.json        ← Config pour Claude Desktop
├── test_mcp_server.py     ← Suite de tests
├── tools/
│   ├── __init__.py
│   ├── search_tool.py     ← Tool: search_listings
│   ├── stats_tool.py      ← Tool: get_stats
│   ├── scraper_tool.py    ← Tools: run_scraper, list_scrapers
│   ├── market_tool.py     ← Tools: analyze_market, detect_anomalies
│   ├── geo_tool.py        ← Tools: find_nearby, geocode_city
│   ├── dashboard_tool.py  ← Tool: generate_dashboard
│   └── notify_tool.py     ← Tools: send_alert, test_connection
├── resources/
│   ├── __init__.py
│   ├── listings_resource.py ← Resources: listings://
│   ├── stats_resource.py    ← Resources: stats://
│   └── history_resource.py  ← Resource: history://
├── INSTALL.md             ← Ce fichier
├── README.md              ← Vue d'ensemble
├── MANUAL.md              ← Manuel complet
├── ARCHITECTURE.md        ← Architecture technique
├── TOOLS_REFERENCE.md     ← Référence API des tools
└── USAGE_EXAMPLES.md      ← Exemples d'utilisation
```
