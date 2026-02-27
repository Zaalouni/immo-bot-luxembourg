#!/usr/bin/env python3
# =============================================================================
# resources/history_resource.py — Resource MCP: history://
# =============================================================================
# Accès aux archives historiques journalières.
# Les archives sont créées par dashboard_generator.py dans:
#   dashboards/data/history/YYYY-MM-DD.json
#
# Resources:
#   history://today         → Archive d'aujourd'hui
#   history://YYYY-MM-DD    → Archive d'une date spécifique
#   history://list          → Liste toutes les dates disponibles
# =============================================================================

import json
import os
import logging
from datetime import datetime, timedelta

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HISTORY_DIR  = os.path.join(BASE_DIR, "dashboards", "data", "history")

logger = logging.getLogger("mcp_server.resources.history")


def _list_available_dates() -> list[str]:
    """Lister toutes les dates disponibles dans l'historique."""
    if not os.path.exists(HISTORY_DIR):
        return []
    dates = []
    for fname in sorted(os.listdir(HISTORY_DIR)):
        if fname.endswith(".json") and len(fname) == 15:
            dates.append(fname[:-5])
    return sorted(dates, reverse=True)


async def get_history_day(date_str: str) -> str:
    """Retourner l'archive d'une journée spécifique."""

    # Résoudre "today" et "yesterday"
    today = datetime.now().date()
    if date_str in ("today", ""):
        date_str = today.strftime("%Y-%m-%d")
    elif date_str == "yesterday":
        date_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    elif date_str == "list":
        # Cas spécial: lister toutes les dates
        dates = _list_available_dates()
        return json.dumps({
            "resource":         "history://list",
            "available_dates":  dates,
            "count":            len(dates),
            "oldest":           dates[-1] if dates else None,
            "newest":           dates[0]  if dates else None,
            "generated":        datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

    # Charger le fichier de la date demandée
    file_path = os.path.join(HISTORY_DIR, f"{date_str}.json")

    if not os.path.exists(file_path):
        # Chercher la date la plus proche disponible
        available = _list_available_dates()
        if not available:
            return json.dumps({
                "error":    f"Aucune archive disponible. Répertoire: {HISTORY_DIR}",
                "tip":      "Lancez dashboard_generator.py pour créer une archive"
            })
        # Trouver la date la plus proche
        closest = min(available, key=lambda d: abs(
            (datetime.strptime(d, "%Y-%m-%d").date() - datetime.strptime(date_str, "%Y-%m-%d").date()).days
        ) if len(d) == 10 else 9999)
        return json.dumps({
            "error":            f"Archive du {date_str} non trouvée",
            "available_count":  len(available),
            "closest_date":     closest,
            "tip":              f"Essayez history://{closest}"
        })

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Enrichir avec des métadonnées
        data["resource"]   = f"history://{date_str}"
        data["file_path"]  = file_path
        data["file_size_kb"] = round(os.path.getsize(file_path) / 1024, 1)
        data["loaded_at"]  = datetime.now().isoformat()

        return json.dumps(data, ensure_ascii=False, indent=2)

    except json.JSONDecodeError as e:
        logger.error(f"JSON invalide dans {file_path}: {e}")
        return json.dumps({"error": f"Fichier JSON invalide: {e}", "file": file_path})
    except Exception as e:
        logger.error(f"Erreur lecture archive {date_str}: {e}")
        return json.dumps({"error": str(e)})
