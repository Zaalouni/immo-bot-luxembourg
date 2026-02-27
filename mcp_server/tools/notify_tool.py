#!/usr/bin/env python3
# =============================================================================
# tools/notify_tool.py — Tools MCP: send_alert + test_connection
# =============================================================================
# Envoyer des notifications Telegram via le bot existant (notifier.py).
# Permet d'alerter manuellement sur des annonces spécifiques.
#
# send_alert:
#   - Prend une liste de listing_ids
#   - Récupère les données en DB
#   - Envoie via notifier.py (photo + description)
#
# test_connection:
#   - Vérifie que le bot Telegram est actif
#   - Vérifie l'accès à chaque chat configuré
# =============================================================================

import sqlite3
import json
import os
import sys
import logging
from datetime import datetime

import mcp.types as types

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH  = os.path.join(BASE_DIR, "listings.db")

logger = logging.getLogger("mcp_server.tools.notify")


def _get_listing_by_id(listing_id: str) -> dict | None:
    """Récupérer une annonce depuis la DB par son listing_id."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT listing_id, site, title, city, price, rooms, surface,
                   url, latitude, longitude, distance_km, notified,
                   strftime('%d/%m/%Y %H:%M', created_at) as created_at
            FROM listings WHERE listing_id = ?
        """, (listing_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        cols = ["listing_id","site","title","city","price","rooms","surface",
                "url","latitude","longitude","distance_km","notified","created_at"]
        return dict(zip(cols, row))
    except sqlite3.Error as e:
        logger.error(f"Erreur DB get_listing: {e}")
        return None


async def handle_send_alert(args: dict) -> list[types.TextContent]:
    """Handler pour send_alert — envoyer alertes Telegram pour des annonces."""

    listing_ids  = args.get("listing_ids", [])
    extra_msg    = args.get("message", "").strip()

    if not listing_ids:
        return [types.TextContent(
            type="text",
            text="Erreur: 'listing_ids' requis (liste de listing_id à notifier).\n"
                 "Exemple: listing_ids=['athome_12345', 'immotop_67890']"
        )]

    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    lines = [
        "=== ENVOI ALERTES TELEGRAM ===",
        f"Annonces à notifier: {len(listing_ids)}",
        f"Démarrage: {datetime.now().strftime('%H:%M:%S')}",
        ""
    ]

    # Charger le notifier
    try:
        from notifier import TelegramNotifier
        notifier = TelegramNotifier()
    except ImportError as e:
        return [types.TextContent(
            type="text",
            text=f"Erreur import notifier.py: {e}\n"
                 "Vérifiez que notifier.py existe et que le .env est configuré."
        )]
    except SystemExit as e:
        return [types.TextContent(
            type="text",
            text=f"Erreur configuration Telegram: variables manquantes dans .env\n"
                 "Vérifiez TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID dans .env"
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Erreur initialisation notifier: {e}"
        )]

    sent_count   = 0
    failed_count = 0
    not_found    = []

    for lid in listing_ids:
        listing = _get_listing_by_id(lid)

        if not listing:
            not_found.append(lid)
            lines.append(f"✗ {lid} — introuvable en DB")
            continue

        try:
            # Construire message personnalisé si fourni
            if extra_msg:
                listing["extra_message"] = extra_msg

            # Envoyer via notifier
            notifier.send_listing(listing)

            # Marquer comme notifié en DB
            conn = sqlite3.connect(DB_PATH, timeout=5)
            conn.execute("UPDATE listings SET notified = 1 WHERE listing_id = ?", (lid,))
            conn.commit()
            conn.close()

            sent_count += 1
            lines.append(
                f"✓ {lid} — Envoyé: {listing['city']} | {listing['price']}€ | {listing['title'][:40]}"
            )

        except Exception as e:
            failed_count += 1
            lines.append(f"✗ {lid} — Erreur envoi: {e}")
            logger.error(f"Erreur envoi {lid}: {e}")

    lines += [
        "",
        "=" * 40,
        f"RÉSUMÉ: {sent_count} envoyées, {failed_count} échecs, {len(not_found)} introuvables",
    ]
    if not_found:
        lines.append(f"IDs introuvables: {', '.join(not_found)}")

    result = {
        "sent": sent_count,
        "failed": failed_count,
        "not_found": not_found,
        "total_requested": len(listing_ids)
    }

    return [
        types.TextContent(type="text", text="\n".join(lines)),
        types.TextContent(type="text", text=f"\n--- JSON ---\n{json.dumps(result, indent=2)}")
    ]


async def handle_test_connection(args: dict) -> list[types.TextContent]:
    """Handler pour test_connection — vérifier la connexion Telegram."""

    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    lines = [
        "=== TEST CONNEXION TELEGRAM ===",
        f"Heure: {datetime.now().strftime('%H:%M:%S')}",
        ""
    ]

    try:
        import requests
        from dotenv import load_dotenv
        import os as _os

        load_dotenv(os.path.join(BASE_DIR, ".env"))
        token    = _os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_ids_raw = _os.getenv("TELEGRAM_CHAT_ID", "")

        if not token:
            return [types.TextContent(
                type="text",
                text="Erreur: TELEGRAM_BOT_TOKEN manquant dans .env"
            )]

        chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()]
        base_url = f"https://api.telegram.org/bot{token}"

        # Test 1: Bot actif ?
        resp = requests.get(f"{base_url}/getMe", timeout=10)
        if resp.status_code == 200:
            bot = resp.json()["result"]
            lines.append(f"✓ Bot actif: @{bot.get('username')} ({bot.get('first_name')})")
            lines.append(f"  Bot ID: {bot.get('id')}")
        else:
            lines.append(f"✗ Bot inaccessible: {resp.json().get('description', 'Erreur inconnue')}")
            return [types.TextContent(type="text", text="\n".join(lines))]

        lines.append("")
        lines.append(f"Chats configurés: {len(chat_ids)}")

        # Test 2: Chaque chat accessible ?
        ok_chats = 0
        for chat_id in chat_ids:
            try:
                chat_resp = requests.post(
                    f"{base_url}/getChat",
                    json={"chat_id": chat_id},
                    timeout=10
                )
                if chat_resp.status_code == 200:
                    chat = chat_resp.json()["result"]
                    chat_type = chat.get("type", "?")
                    chat_name = chat.get("title", chat.get("first_name", "N/A"))
                    lines.append(f"  ✓ Chat {chat_id}: {chat_name} ({chat_type})")
                    ok_chats += 1
                else:
                    desc = chat_resp.json().get("description", "Erreur")
                    lines.append(f"  ✗ Chat {chat_id}: {desc}")
            except Exception as e:
                lines.append(f"  ✗ Chat {chat_id}: {e}")

        lines += [
            "",
            f"Résultat: {ok_chats}/{len(chat_ids)} chats accessibles",
            "✓ Connexion Telegram opérationnelle" if ok_chats > 0 else "✗ Aucun chat accessible",
        ]

        result = {
            "bot_active": True,
            "chats_ok": ok_chats,
            "chats_total": len(chat_ids),
            "operational": ok_chats > 0
        }

    except ImportError as e:
        lines.append(f"Erreur import: {e}")
        result = {"bot_active": False, "error": str(e)}
    except Exception as e:
        lines.append(f"Erreur: {e}")
        result = {"bot_active": False, "error": str(e)}

    return [
        types.TextContent(type="text", text="\n".join(lines)),
        types.TextContent(type="text", text=f"\n--- JSON ---\n{json.dumps(result, indent=2)}")
    ]
