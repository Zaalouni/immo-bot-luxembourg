#!/usr/bin/env python3
# =============================================================================
# tools/dashboard_tool.py — Tool MCP: generate_dashboard
# =============================================================================
# Lance dashboard_generator.py pour régénérer les fichiers statiques.
# Retourne les métriques de génération.
# =============================================================================

import os
import sys
import json
import subprocess
import logging
from datetime import datetime

import mcp.types as types

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GENERATOR = os.path.join(BASE_DIR, "dashboard_generator.py")
DATA_DIR  = os.path.join(BASE_DIR, "dashboards", "data")

logger = logging.getLogger("mcp_server.tools.dashboard")


async def handle_generate_dashboard(args: dict) -> list[types.TextContent]:
    """Handler pour generate_dashboard — régénérer les fichiers dashboard."""

    include_archive = bool(args.get("include_archive", True))

    if not os.path.exists(GENERATOR):
        return [types.TextContent(
            type="text",
            text=f"Erreur: dashboard_generator.py introuvable à {GENERATOR}"
        )]

    lines = [
        "=== GÉNÉRATION DASHBOARD ===",
        f"Démarrage: {datetime.now().strftime('%H:%M:%S')}",
        f"Générateur: {GENERATOR}",
        ""
    ]

    start_time = datetime.now()

    try:
        result = subprocess.run(
            [sys.executable, GENERATOR],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=BASE_DIR
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        if result.returncode == 0:
            lines.append(f"Statut: SUCCÈS ({elapsed:.1f}s)")

            # Lister les fichiers générés
            if os.path.exists(DATA_DIR):
                files = []
                total_size = 0
                for fname in sorted(os.listdir(DATA_DIR)):
                    fpath = os.path.join(DATA_DIR, fname)
                    if os.path.isfile(fpath):
                        size = os.path.getsize(fpath)
                        total_size += size
                        files.append({"name": fname, "size_kb": round(size / 1024, 1)})

                lines += [
                    "",
                    f"--- Fichiers générés ({len(files)} fichiers, {round(total_size/1024, 1)} KB total) ---"
                ]
                for f in files:
                    lines.append(f"  {f['name']:<30} {f['size_kb']:>8.1f} KB")

            if result.stdout:
                lines += ["", "--- Output ---", result.stdout[-1000:]]

        else:
            lines.append(f"Statut: ERREUR (code {result.returncode})")
            if result.stderr:
                lines += ["", "--- Erreurs ---", result.stderr[-2000:]]
            if result.stdout:
                lines += ["", "--- Output ---", result.stdout[-1000:]]

    except subprocess.TimeoutExpired:
        lines.append("Erreur: Timeout dépassé (120s)")
    except Exception as e:
        lines.append(f"Erreur: {e}")
        logger.error(f"Erreur génération dashboard: {e}", exc_info=True)

    return [types.TextContent(type="text", text="\n".join(lines))]
