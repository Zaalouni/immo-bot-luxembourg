# Architecture Technique — MCP Server Immo-Bot Luxembourg

## Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────────┐
│                     CLAUDE (Client MCP)                         │
│   "Quelles annonces < 2000€ avec 3 ch. à Luxembourg ?"        │
└──────────────────────────┬───────────────────────────────────────┘
                           │  MCP Protocol over stdio
                           │  (JSON-RPC 2.0 messages)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                mcp_server/mcp_server.py                         │
│                                                                  │
│   Server("immo-bot-luxembourg")                                 │
│   ├── @server.list_tools()    → 11 tools déclarés              │
│   ├── @server.call_tool()     → dispatcher vers tools/          │
│   ├── @server.list_resources()→ 6 resources déclarées          │
│   └── @server.read_resource() → dispatcher vers resources/      │
└──────────────────────────┬───────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────────┐
          ▼                ▼                    ▼
   ┌─────────────┐  ┌─────────────┐   ┌──────────────────┐
   │  tools/     │  │ resources/  │   │  Modules du bot  │
   │             │  │             │   │                  │
   │ search_tool │  │ listings_   │   │  database.py     │
   │ stats_tool  │  │ _resource   │   │  utils.py        │
   │ scraper_tool│  │             │   │  notifier.py     │
   │ market_tool │  │ stats_      │   │  config.py       │
   │ geo_tool    │  │ _resource   │   │  filters.py      │
   │ dashboard_  │  │             │   │  scrapers/*.py   │
   │ _tool       │  │ history_    │   │  dashboard_      │
   │ notify_tool │  │ _resource   │   │  generator.py    │
   └──────┬──────┘  └──────┬──────┘   └──────────────────┘
          │                │
          └────────┬───────┘
                   ▼
         ┌─────────────────┐
         │  listings.db    │
         │  (SQLite3)      │
         │                 │
         │  122+ annonces  │
         │  65+ villes     │
         └─────────────────┘
```

---

## Protocole MCP

### Transport: stdio (standard input/output)

Le serveur communique via stdin/stdout en JSON-RPC 2.0.
Chaque message est une ligne JSON terminée par `\n`.

```
Client → Serveur (stdin):
  {"jsonrpc":"2.0","id":1,"method":"tools/call",
   "params":{"name":"search_listings","arguments":{"city":"Luxembourg"}}}

Serveur → Client (stdout):
  {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"..."}]}}
```

### Cycle de vie

```
1. Claude démarre le processus (via subprocess)
2. Échange capabilities (initialize/initialized)
3. Claude liste les tools (tools/list)
4. Claude liste les resources (resources/list)
5. Claude appelle des tools (tools/call) ou lit des resources (resources/read)
6. Processus reste actif jusqu'à fin de session
```

---

## Structure des données

### Tool Input/Output

Chaque tool reçoit un `dict` d'arguments et retourne `list[types.TextContent]`.

```python
# Input (extrait de mcp_server.py)
types.Tool(
    name="search_listings",
    inputSchema={
        "type": "object",
        "properties": {
            "price_max": {"type": "integer"},
            "city": {"type": "string"},
            ...
        }
    }
)

# Output (retourné par handle_search_listings)
[
    types.TextContent(type="text", text="=== RÉSULTATS ===\n..."),
    types.TextContent(type="text", text="--- JSON ---\n{...}")
]
```

### Resource Output

Les resources retournent une `str` JSON.

```python
# listings://all retourne:
{
    "resource": "listings://all",
    "count": 122,
    "generated": "2026-02-27T10:00:00",
    "listings": [
        {
            "listing_id": "athome_12345",
            "site": "athome",
            "title": "...",
            "city": "Luxembourg",
            "price": 1800,
            "rooms": 3,
            "surface": 95,
            "url": "https://...",
            "latitude": 49.6116,
            "longitude": 6.1319,
            "distance_km": 2.3,
            "price_per_m2": 18.9,
            "created_at": "2026-02-27T09:30:00",
            "notified": 0
        },
        ...
    ]
}
```

---

## Flux de données par tool

### `search_listings`

```
Arguments → Validation → SQL WHERE dynamique → SQLite3 → Format texte + JSON
```

```sql
SELECT listing_id, site, title, city, price, rooms, surface,
       url, latitude, longitude, distance_km,
       strftime('%d/%m/%Y %H:%M', created_at), notified
FROM listings
WHERE price >= ? AND price <= ?
  AND LOWER(city) LIKE ?
  AND (rooms IS NULL OR rooms >= ?)
  AND (distance_km IS NULL OR distance_km <= ?)
ORDER BY created_at DESC
LIMIT ?
```

### `run_scraper`

```
scraper_name → SCRAPER_REGISTRY lookup → importlib.import_module()
            → loop.run_in_executor(scrape_func)  ← thread pool (non-bloquant)
            → _save_listings_to_db()
            → Rapport résultats
```

### `analyze_market`

```
period_days → Requêtes SQL temporelles → Chargement archives JSON
           → Calcul deltas (prix, volume) → Détection opportunités
           → Rapport texte + JSON
```

### `find_nearby`

```
city_name → geocode_city() → (lat, lng)
         → Toutes annonces avec GPS depuis DB
         → _haversine(center, listing) pour chaque annonce
         → Filtrer dist <= radius_km
         → Trier par distance ASC
         → Rapport
```

---

## Gestion des erreurs

Chaque handler suit le pattern :

```python
async def handle_xxx(args: dict) -> list[types.TextContent]:
    # 1. Validation des args
    if not required_param:
        return [types.TextContent(type="text", text="Erreur: ...")]

    # 2. Vérification DB/fichiers
    if not os.path.exists(DB_PATH):
        return [types.TextContent(type="text", text="Erreur: DB introuvable...")]

    # 3. Exécution dans try/except
    try:
        # ... logique métier ...
    except sqlite3.Error as e:
        logger.error(f"Erreur DB: {e}")
        return [types.TextContent(type="text", text=f"Erreur base de données: {e}")]
    except Exception as e:
        logger.error(f"Erreur: {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"Erreur: {e}")]
```

Le dispatcher central (`mcp_server.py:call_tool`) enveloppe également tout dans un try/except global.

---

## Thread Safety

- SQLite: Chaque connexion est ouverte/fermée dans le handler (pas de connexion partagée)
- Scrapers: Lancés via `loop.run_in_executor()` (thread pool d'asyncio)
- Pas d'état partagé entre handlers

---

## Chemins et imports

```python
# BASE_DIR = /home/user/immo-bot-luxembourg/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# DB
DB_PATH = os.path.join(BASE_DIR, "listings.db")

# Scrapers importés dynamiquement
sys.path.insert(0, BASE_DIR)
module = importlib.import_module("scrapers.athome_scraper_json")

# Modules bot
from utils import geocode_city, haversine_distance
from notifier import TelegramNotifier
from config import REFERENCE_LAT, REFERENCE_LNG
```

---

## Performance

| Opération | Temps typique |
|-----------|--------------|
| `search_listings` (20 résultats) | < 50ms |
| `get_stats` complet | < 100ms |
| `analyze_market` (7 jours) | < 200ms |
| `find_nearby` (tous GPS) | < 100ms |
| `run_scraper athome` | 5-30s |
| `run_scraper all` | 5-15 min |
| `generate_dashboard` | 5-30s |

---

## Sécurité

- **Pas d'injection SQL**: Toutes les requêtes utilisent des paramètres `?`
- **Limites**: `MAX_SEARCH_RESULTS=100`, `MAX_SCRAPER_TIMEOUT=120s`
- **Validation**: Chaque argument est validé avant exécution
- **Pas d'accès réseau direct**: Sauf `run_scraper` et `send_alert`/`test_connection` (Telegram)
- **Lecture seule**: Tous les handlers sauf `run_scraper` et `send_alert` sont en lecture seule

---

## Extension

### Ajouter un nouveau tool

1. Créer `mcp_server/tools/mon_tool.py` avec `async def handle_mon_tool(args)`
2. Importer dans `mcp_server.py`: `from mcp_server.tools.mon_tool import handle_mon_tool`
3. Ajouter `types.Tool(name="mon_tool", ...)` dans `list_tools()`
4. Ajouter `elif name == "mon_tool": return await handle_mon_tool(arguments)` dans `call_tool()`

### Ajouter une nouvelle resource

1. Créer la fonction dans `mcp_server/resources/` ou un nouveau module
2. Importer dans `mcp_server.py`
3. Ajouter `types.Resource(uri="mon://resource", ...)` dans `list_resources()`
4. Ajouter `elif uri == "mon://resource": return await ma_fonction()` dans `read_resource()`

### Ajouter un nouveau scraper

1. Créer `scrapers/mon_scraper.py` avec `def scrape() -> list[dict]`
2. Ajouter dans `SCRAPER_REGISTRY` de `scraper_tool.py`:
   ```python
   "monsite": ("scrapers.mon_scraper", "scrape"),
   ```
