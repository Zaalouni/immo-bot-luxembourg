#!/usr/bin/env python3
# =============================================================================
# auto_contact_sigelux.py — Contact automatique des agences via Sigelux.lu
# =============================================================================
# Methode : HTTP POST simple (requests), pas de Selenium.
#           Formulaire HTML standard sur /contactez-nous (pas de CAPTCHA).
#           Etapes : GET /contactez-nous → extraire token CSRF hash →
#                    POST avec coordonnees + URL de l'annonce dans le message.
#
# Usage :
#   python auto_contact_sigelux.py --list           → lister les annonces en attente
#   python auto_contact_sigelux.py --send 1,3       → contacter les annonces #1 et #3
#   python auto_contact_sigelux.py --send all       → contacter toutes les annonces
#   python auto_contact_sigelux.py --send all --dry-run → simuler sans envoyer
#   python auto_contact_sigelux.py --history        → voir les annonces deja contactees
#
# Variables .env requises : CONTACT_FIRSTNAME, CONTACT_LASTNAME, CONTACT_EMAIL,
#                           CONTACT_PHONE (optionnel), CONTACT_MESSAGE
#
# Version : v1.0 (2026-02-21)
# =============================================================================
import sqlite3
import time
import logging
import argparse
import os
import sys
import re
from datetime import datetime
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

load_dotenv()

# Parametres contact depuis .env
CONTACT_FIRSTNAME = os.getenv('CONTACT_FIRSTNAME', '').strip()
CONTACT_LASTNAME  = os.getenv('CONTACT_LASTNAME',  '').strip()
CONTACT_PHONE     = os.getenv('CONTACT_PHONE',     '').strip()
CONTACT_EMAIL     = os.getenv('CONTACT_EMAIL',     '').strip()
CONTACT_MESSAGE   = os.getenv('CONTACT_MESSAGE',   '').strip()

BASE_URL        = 'https://www.sigelux.lu'
CONTACT_URL     = f'{BASE_URL}/contactez-nous'
DB_PATH         = 'listings.db'
DELAY_BETWEEN   = 12    # secondes entre deux contacts
REQUEST_TIMEOUT = 15    # timeout HTTP

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'fr-LU,fr;q=0.9,en;q=0.8',
    'Referer': CONTACT_URL,
}

logger = logging.getLogger(__name__)


def setup_logging(verbose=False):
    handlers = [logging.FileHandler('auto_contact_sigelux.log', encoding='utf-8')]
    if verbose:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


# ─── Base de donnees ──────────────────────────────────────────────────────────

def ensure_contacted_column():
    """Ajouter la colonne 'contacted' si absente"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT contacted FROM listings LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE listings ADD COLUMN contacted BOOLEAN DEFAULT 0")
        conn.commit()
        print("  Colonne 'contacted' ajoutee a la DB")
    conn.close()


def get_pending_listings():
    """Recuperer les annonces Sigelux non contactees"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, title, city, price, rooms, surface, url, created_at
        FROM listings
        WHERE site = 'Sigelux.lu'
          AND (contacted IS NULL OR contacted = 0)
        ORDER BY price ASC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_contacted_listings():
    """Recuperer les annonces Sigelux deja contactees"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, title, city, price, rooms, surface, url, created_at
        FROM listings
        WHERE site = 'Sigelux.lu'
          AND contacted = 1
        ORDER BY created_at DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def mark_contacted(listing_id):
    """Marquer une annonce comme contactee"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE listings SET contacted = 1 WHERE listing_id = ?",
        (listing_id,)
    )
    conn.commit()
    conn.close()


# ─── Logique contact HTTP ─────────────────────────────────────────────────────

def get_csrf_hash(session):
    """Recuperer le token CSRF hash depuis la page de contact"""
    try:
        resp = session.get(CONTACT_URL, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Le token est dans un <input type="hidden" name="hash">
        hidden = soup.find('input', {'name': 'hash'})
        if hidden and hidden.get('value'):
            return hidden['value']
        logger.warning("Token CSRF hash non trouve")
        return ''
    except Exception as e:
        logger.error(f"Erreur GET /contactez-nous: {e}")
        return ''


def contact_listing(session, listing, dry_run=False):
    """Contacter Sigelux pour une annonce via HTTP POST. Retourne True si succes."""
    listing_id = listing['listing_id']
    url        = listing['url']

    logger.info(f"Contact: {listing['title'][:50]} — {listing['price']}€ — {listing['city']}")
    logger.info(f"   URL: {url}")

    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"  {prefix}{listing['price']}€ {listing['city']} — {listing['title'][:40]}...")

    # Composer le message avec l'URL de l'annonce
    full_message = f"{CONTACT_MESSAGE}\n\nAnnonce : {url}"

    if dry_run:
        print(f"     → Expediteur : {CONTACT_FIRSTNAME} {CONTACT_LASTNAME} <{CONTACT_EMAIL}>")
        if CONTACT_PHONE:
            print(f"     → Telephone  : {CONTACT_PHONE}")
        print(f"     → Message    : \"{full_message[:80]}...\"")
        print(f"     [OK] Simulation uniquement — pas envoye")
        return True

    try:
        # Etape 1 : recuperer le token CSRF
        csrf_hash = get_csrf_hash(session)
        if not csrf_hash:
            print(f"     Token CSRF manquant — contact impossible")
            return False

        # Etape 2 : POST formulaire de contact
        payload = {
            'hash':      csrf_hash,
            'lastname':  CONTACT_LASTNAME,
            'firstname': CONTACT_FIRSTNAME,
            'telephone': CONTACT_PHONE,
            'email':     CONTACT_EMAIL,
            'note':      full_message,
            # Champs honeypot laisses vides (anti-bot)
            'age':       '',
            'honeypot':  '',
        }

        post_headers = {**HEADERS, 'Content-Type': 'application/x-www-form-urlencoded'}
        resp = session.post(
            CONTACT_URL,
            data=payload,
            headers=post_headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        # Etape 3 : verifier la reponse
        page_text = resp.text.lower()
        success_keywords = ['merci', 'envoy', 'message a bien', 'sent', 'succes', 'thank']
        error_keywords   = ['erreur', 'error', 'invalide', 'manquant', 'required']

        if any(k in page_text for k in success_keywords):
            logger.info(f"   Message envoye avec succes!")
            print(f"     OK Envoye!")
            return True
        elif any(k in page_text for k in error_keywords):
            logger.warning(f"   Erreur detectee dans la reponse (HTTP {resp.status_code})")
            print(f"     Erreur detectee dans la reponse")
            return False
        elif resp.status_code in (200, 302):
            logger.info(f"   Formulaire soumis (HTTP {resp.status_code}, pas d'erreur visible)")
            print(f"     OK Envoye (pas d'erreur visible)")
            return True
        else:
            logger.warning(f"   HTTP {resp.status_code} inattendu")
            print(f"     HTTP {resp.status_code} inattendu")
            return False

    except Exception as e:
        logger.error(f"   Erreur: {str(e)[:100]}")
        print(f"     Erreur: {str(e)[:80]}")
        return False


# ─── Affichage ────────────────────────────────────────────────────────────────

def print_listings_table(listings, show_number=True):
    if not listings:
        print("  Aucune annonce.")
        return
    if show_number:
        print(f"  {'#':<4} {'Prix':>7} {'Ville':<20} {'Ch':>3} {'m2':>5} {'Titre':<40} {'URL'}")
        print(f"  {'─'*4} {'─'*7} {'─'*20} {'─'*3} {'─'*5} {'─'*40} {'─'*30}")
    else:
        print(f"  {'Prix':>7} {'Ville':<20} {'Ch':>3} {'m2':>5} {'Titre':<40} {'URL'}")
        print(f"  {'─'*7} {'─'*20} {'─'*3} {'─'*5} {'─'*40} {'─'*30}")

    for i, l in enumerate(listings, 1):
        price   = f"{l['price']}€"
        city    = (l['city'] or '?')[:20]
        rooms   = str(l['rooms'] or '?')
        surface = str(l['surface'] or '?')
        title   = (l['title'] or 'Sans titre')[:40]
        url     = l['url']
        if show_number:
            print(f"  {i:<4} {price:>7} {city:<20} {rooms:>3} {surface:>5} {title:<40} {url}")
        else:
            print(f"  {price:>7} {city:<20} {rooms:>3} {surface:>5} {title:<40} {url}")


# ─── Commandes CLI ────────────────────────────────────────────────────────────

def cmd_list():
    ensure_contacted_column()
    listings = get_pending_listings()
    print(f"\n{'='*120}")
    print(f"  ANNONCES SIGELUX EN ATTENTE DE CONTACT ({len(listings)})")
    print(f"{'='*120}")
    print_listings_table(listings, show_number=True)
    print(f"\n  Pour contacter : python auto_contact_sigelux.py --send 1,3,5")
    print(f"  Pour tout contacter : python auto_contact_sigelux.py --send all")
    print(f"  Pour simuler : python auto_contact_sigelux.py --send all --dry-run\n")


def cmd_history():
    ensure_contacted_column()
    listings = get_contacted_listings()
    print(f"\n{'='*120}")
    print(f"  ANNONCES SIGELUX DEJA CONTACTEES ({len(listings)})")
    print(f"{'='*120}")
    print_listings_table(listings, show_number=False)
    print()


def cmd_send(selection, dry_run=False):
    if not all([CONTACT_FIRSTNAME, CONTACT_LASTNAME, CONTACT_EMAIL, CONTACT_MESSAGE]):
        print("Variables CONTACT_* manquantes dans .env")
        print("   Requis: CONTACT_FIRSTNAME, CONTACT_LASTNAME, CONTACT_EMAIL, CONTACT_MESSAGE")
        sys.exit(1)

    ensure_contacted_column()
    all_listings = get_pending_listings()

    if not all_listings:
        print("Aucune annonce Sigelux en attente")
        return

    # Parser la selection
    if selection.strip().lower() == 'all':
        selected = all_listings
    else:
        try:
            indices = [int(x.strip()) for x in selection.split(',') if x.strip()]
        except ValueError:
            print("Format invalide. Utiliser: --send 1,3,5 ou --send all")
            return
        selected = []
        for idx in indices:
            if idx < 1 or idx > len(all_listings):
                print(f"  Numero {idx} invalide (1-{len(all_listings)})")
                continue
            selected.append(all_listings[idx - 1])

    if not selected:
        print("Aucune annonce selectionnee")
        return

    mode_label = " [MODE SIMULATION — rien ne sera envoye]" if dry_run else ""
    print(f"\n{'='*80}")
    print(f"  CONTACT SIGELUX — {len(selected)} annonce(s){mode_label}")
    print(f"  Expediteur: {CONTACT_FIRSTNAME} {CONTACT_LASTNAME} <{CONTACT_EMAIL}>")
    print(f"{'='*80}")
    print_listings_table(selected, show_number=False)
    msg_preview = CONTACT_MESSAGE[:80] + ('...' if len(CONTACT_MESSAGE) > 80 else '')
    print(f"\n  Message: \"{msg_preview}\"")
    print()

    session = requests.Session()
    success = 0
    failed  = 0
    total   = len(selected)

    for i, listing in enumerate(selected, 1):
        print(f"  ({i}/{total})", end=' ')

        if i > 1 and not dry_run:
            print(f"  Attente {DELAY_BETWEEN}s...")
            time.sleep(DELAY_BETWEEN)

        try:
            ok = contact_listing(session, listing, dry_run=dry_run)
            if ok:
                if not dry_run:
                    mark_contacted(listing['listing_id'])
                success += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Erreur critique: {str(e)[:100]}")
            print(f"     Erreur critique: {str(e)[:80]}")
            failed += 1

    print(f"\n{'='*80}")
    if dry_run:
        print(f"  SIMULATION : {success} annonce(s) aurait(ent) ete envoyee(s)")
    else:
        print(f"  RESUME: OK {success} envoye(s) | ECHEC {failed} echoue(s)")
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Contact agences Sigelux.lu — HTTP POST simple, pas de Selenium',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python auto_contact_sigelux.py --list              Lister les annonces en attente
  python auto_contact_sigelux.py --send 1,3,5        Contacter les annonces #1, #3, #5
  python auto_contact_sigelux.py --send all          Contacter toutes les annonces
  python auto_contact_sigelux.py --send all --dry-run  Simuler sans envoyer
  python auto_contact_sigelux.py --history           Voir les annonces deja contactees
        """
    )
    parser.add_argument('--list',    action='store_true', help='Lister les annonces en attente')
    parser.add_argument('--send',    type=str, default=None, help='Numeros a contacter (ex: 1,3,5 ou all)')
    parser.add_argument('--history', action='store_true', help='Voir les annonces deja contactees')
    parser.add_argument('--dry-run', action='store_true', help='Simuler sans envoyer')
    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.send:
        setup_logging(verbose=True)
        cmd_send(args.send, dry_run=args.dry_run)
    elif args.history:
        cmd_history()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
