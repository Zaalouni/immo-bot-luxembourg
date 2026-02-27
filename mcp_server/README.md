# MCP Server — Immo-Bot Luxembourg

**Version:** 1.0.0 | **Protocol:** Model Context Protocol (MCP) | **Transport:** stdio

Serveur MCP qui expose les données et capacités de l'Immo-Bot Luxembourg directement à Claude.
Permet d'interroger le marché immobilier luxembourgeois en langage naturel.

---

## Démarrage rapide

```bash
# 1. Installer le SDK MCP
pip install mcp>=1.0.0

# 2. Lancer le serveur
python mcp_server/mcp_server.py

# 3. Tester
python mcp_server/test_mcp_server.py -v
```

Config Claude Desktop (`~/.config/claude/claude_desktop_config.json`) :
```json
{
  "mcpServers": {
    "immo-bot-luxembourg": {
      "command": "python",
      "args": ["/home/user/immo-bot-luxembourg/mcp_server/mcp_server.py"],
      "env": {"PYTHONPATH": "/home/user/immo-bot-luxembourg"}
    }
  }
}
```

---

## 11 Tools disponibles

| Tool | Description |
|------|-------------|
| `search_listings` | Recherche avec filtres (prix, ville, chambres, surface, distance) |
| `get_stats` | Statistiques complètes du marché (prix moy/med/min/max, par site/ville) |
| `run_scraper` | Lancer un scraper à la demande (`athome`, `all`, etc.) |
| `list_scrapers` | Lister les 20+ scrapers avec statut et compteurs DB |
| `analyze_market` | Tendances sur N jours, comparaison archives historiques |
| `detect_anomalies` | Détecter prix aberrants, doublons, données manquantes |
| `find_nearby` | Annonces dans un rayon GPS (lat/lng ou nom de ville) |
| `geocode_city` | Convertir ville luxembourgeoise en GPS (120+ villes) |
| `generate_dashboard` | Régénérer les fichiers statiques du dashboard |
| `send_alert` | Envoyer alerte Telegram pour des annonces spécifiques |
| `test_connection` | Vérifier la connexion Telegram (bot + chats) |

## 6 Resources disponibles

| Resource URI | Contenu |
|-------------|---------|
| `listings://all` | Toutes les annonces en JSON |
| `listings://new` | Annonces des dernières 24h |
| `listings://by-site` | Annonces regroupées par site |
| `stats://current` | Snapshot statistiques temps réel |
| `stats://by-city` | Prix moy/min/max par ville |
| `history://YYYY-MM-DD` | Archives journalières |

---

## Exemples de questions à Claude

```
"Montre-moi les annonces < 1800€ avec 3 chambres à Luxembourg"
"Quel est le prix moyen du marché ce mois-ci ?"
"Lance le scraper athome et dis-moi les nouveautés"
"Y a-t-il des anomalies de prix dans la base ?"
"Trouve les appartements dans un rayon de 3 km de Kirchberg"
"Compare le marché cette semaine vs la semaine dernière"
"Génère les dashboards et envoie une alerte pour les 2 moins chères"
```

---

## Documentation complète

- `INSTALL.md` — Guide d'installation pas-à-pas
- `MANUAL.md` — Manuel utilisateur complet
- `ARCHITECTURE.md` — Architecture technique détaillée
- `TOOLS_REFERENCE.md` — Référence API de tous les tools
- `USAGE_EXAMPLES.md` — Cas d'usage et exemples experts
