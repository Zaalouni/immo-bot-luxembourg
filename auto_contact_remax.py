# =============================================================================
# auto_contact_remax.py — Contact automatique des agences via RE/MAX.lu
# =============================================================================
# Formulaire direct sur la page (pas de login requis, pas de CAPTCHA).
#
# Usage :
#   python auto_contact_remax.py --list           → annonces en attente (DB)
#   python auto_contact_remax.py --send 1,3       → contacter #1 et #3
#   python auto_contact_remax.py --send all       → tout contacter
#   python auto_contact_remax.py --send all --dry-run → simuler
#   python auto_contact_remax.py --history        → annonces deja contactees
#   python auto_contact_remax.py --url https://...  → contacter une URL directe
#
# Version : v1.0 (2026-02-20)
# =============================================================================
import sqlite3
import time
import logging
import argparse
import os
import sys
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

load_dotenv()

CONTACT_FIRSTNAME = os.getenv('CONTACT_FIRSTNAME', '').strip()
CONTACT_LASTNAME  = os.getenv('CONTACT_LASTNAME', '').strip()
CONTACT_PHONE     = os.getenv('CONTACT_PHONE', '').strip()
CONTACT_EMAIL     = os.getenv('CONTACT_EMAIL', '').strip()
CONTACT_MESSAGE   = os.getenv('CONTACT_MESSAGE', '').strip()

DB_PATH         = 'listings.db'
CONTACT_TIMEOUT = 30
DELAY_BETWEEN   = 10
SCREENSHOTS_DIR = 'contact_screenshots'

logger = logging.getLogger(__name__)


def setup_logging(verbose=False):
    handlers = [logging.FileHandler('auto_contact_remax.log', encoding='utf-8')]
    if verbose:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


# ─── DB ──────────────────────────────────────────────────────────────────────

def ensure_contacted_column():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT contacted FROM listings LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE listings ADD COLUMN contacted BOOLEAN DEFAULT 0")
        conn.commit()
    conn.close()


def get_pending_listings():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, title, city, price, rooms, surface, url, created_at
        FROM listings
        WHERE site = 'Remax.lu'
          AND (contacted IS NULL OR contacted = 0)
        ORDER BY price ASC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_contacted_listings():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, title, city, price, rooms, surface, url, created_at
        FROM listings
        WHERE site = 'Remax.lu'
          AND contacted = 1
        ORDER BY created_at DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def mark_contacted(listing_id):
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    cursor.execute("UPDATE listings SET contacted = 1 WHERE listing_id = ?", (listing_id,))
    conn.commit()
    conn.close()


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


# ─── Helpers Selenium ─────────────────────────────────────────────────────────

def save_screenshot(driver, label):
    try:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        path = os.path.join(SCREENSHOTS_DIR, f"remax_{label}_{int(time.time())}.png")
        driver.save_screenshot(path)
        print(f"     Screenshot: {path}")
    except Exception:
        pass


def find_form_field(form, selectors):
    for sel in selectors:
        try:
            return form.find_element(By.CSS_SELECTOR, sel)
        except NoSuchElementException:
            continue
    return None


def find_remax_form(driver):
    """Trouver le formulaire RE/MAX (contient firstName + comments)"""
    for form in driver.find_elements(By.TAG_NAME, 'form'):
        try:
            form.find_element(By.CSS_SELECTOR, "input[name='firstName']")
            form.find_element(By.CSS_SELECTOR, "textarea[name='comments']")
            return form
        except NoSuchElementException:
            continue
    return None


# ─── Contact une annonce RE/MAX ───────────────────────────────────────────────

def contact_listing(driver, listing, dry_run=False):
    """Contacter une agence RE/MAX. Retourne True si succes."""
    url        = listing['url']
    listing_id = listing.get('listing_id', 'url_direct')
    wait       = WebDriverWait(driver, 15)

    logger.info(f"Contact RE/MAX: {listing.get('title','?')[:50]} — {url}")
    prefix = "[DRY-RUN] " if dry_run else ""
    price  = listing.get('price', '?')
    city   = listing.get('city', '?')
    title  = listing.get('title', url)
    print(f"  {prefix}{price}€ {city} — {str(title)[:40]}...")

    if dry_run:
        print(f"     → {CONTACT_FIRSTNAME} {CONTACT_LASTNAME} <{CONTACT_EMAIL}>")
        msg = CONTACT_MESSAGE[:80] + ('...' if len(CONTACT_MESSAGE) > 80 else '')
        print(f"     → Message: \"{msg}\"")
        print(f"     [OK] Simulation — pas envoye")
        return True

    try:
        driver.set_page_load_timeout(CONTACT_TIMEOUT)
        driver.get(url)
        time.sleep(3)

        # Accepter cookies (CookieBot)
        for text in ['Allow all', 'Allow All', 'Accepter']:
            try:
                btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//button[contains(text(), '{text}')]")
                    )
                )
                btn.click()
                time.sleep(1)
                break
            except TimeoutException:
                continue

        # Attendre que le formulaire soit charge (React/MUI)
        try:
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[name='firstName']")
            ))
        except TimeoutException:
            logger.warning(f"   Formulaire non trouve: {listing_id}")
            print(f"     Formulaire non charge")
            save_screenshot(driver, listing_id)
            return False

        # Trouver le formulaire de contact
        form = find_remax_form(driver)
        if not form:
            logger.warning(f"   Formulaire RE/MAX introuvable: {listing_id}")
            print(f"     Formulaire RE/MAX introuvable")
            save_screenshot(driver, listing_id)
            return False

        # Remplir les champs
        field = find_form_field(form, ["input[name='firstName']"])
        if field:
            field.clear()
            field.send_keys(CONTACT_FIRSTNAME)

        field = find_form_field(form, ["input[name='lastName']"])
        if field:
            field.clear()
            field.send_keys(CONTACT_LASTNAME)

        if CONTACT_PHONE:
            field = find_form_field(form, ["input[name='phone']", "input[type='tel']"])
            if field:
                field.clear()
                field.send_keys(CONTACT_PHONE)

        # Email : RE/MAX utilise id='contactmeemail'
        field = find_form_field(form, [
            "input[id='contactmeemail']", "input[name='email']", "input[type='email']"
        ])
        if field:
            field.clear()
            field.send_keys(CONTACT_EMAIL)

        # Message dans textarea[name='comments']
        textarea = find_form_field(form, ["textarea[name='comments']", "textarea"])
        if textarea:
            textarea.clear()
            textarea.send_keys(CONTACT_MESSAGE)

        # Soumettre : bouton "Envoyer message"
        submit = find_form_field(form, ["button[type='submit']"])
        if not submit:
            # Fallback : chercher par texte
            for btn in form.find_elements(By.TAG_NAME, 'button'):
                if 'envoyer' in btn.text.lower() or 'send' in btn.text.lower():
                    submit = btn
                    break

        if not submit:
            print(f"     Bouton submit introuvable")
            save_screenshot(driver, listing_id)
            return False

        driver.execute_script("arguments[0].scrollIntoView(true);", submit)
        time.sleep(0.5)
        submit.click()
        time.sleep(4)

        # Verifier confirmation
        page_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
        if any(w in page_text for w in ['envoy', 'merci', 'sent', 'thank', 'succ', 'message envoy']):
            logger.info("   Envoye avec succes!")
            print(f"     OK Envoye!")
            return True
        elif any(w in page_text for w in ['erreur', 'error', 'echec', 'failed']):
            logger.warning("   Erreur detectee")
            print(f"     Erreur detectee")
            save_screenshot(driver, listing_id)
            return False
        else:
            logger.info("   Soumis (pas d'erreur visible)")
            print(f"     OK Envoye (pas d'erreur visible)")
            return True

    except Exception as e:
        logger.error(f"   Erreur: {str(e)[:100]}")
        print(f"     Erreur: {str(e)[:80]}")
        save_screenshot(driver, listing_id)
        return False


# ─── Commandes CLI ────────────────────────────────────────────────────────────

def cmd_list():
    ensure_contacted_column()
    listings = get_pending_listings()
    print(f"\n{'='*120}")
    print(f"  ANNONCES RE/MAX EN ATTENTE DE CONTACT ({len(listings)})")
    print(f"{'='*120}")
    print_listings_table(listings, show_number=True)
    if not listings:
        print("  Note: le scraper RE/MAX doit etre actif pour avoir des annonces ici.")
    print(f"\n  Pour contacter : python auto_contact_remax.py --send 1,3,5")
    print(f"  URL directe   : python auto_contact_remax.py --url https://www.remax.lu/...\n")


def cmd_history():
    ensure_contacted_column()
    listings = get_contacted_listings()
    print(f"\n{'='*120}")
    print(f"  ANNONCES RE/MAX DEJA CONTACTEES ({len(listings)})")
    print(f"{'='*120}")
    print_listings_table(listings, show_number=False)
    print()


def cmd_url(url, dry_run=False):
    """Contacter une annonce RE/MAX par URL directe (sans scraper)"""
    if not all([CONTACT_FIRSTNAME, CONTACT_LASTNAME, CONTACT_EMAIL, CONTACT_MESSAGE]):
        print("Variables CONTACT_* manquantes dans .env")
        sys.exit(1)

    listing = {
        'listing_id': 'url_direct',
        'url': url,
        'title': url,
        'city': '?',
        'price': '?',
        'rooms': '?',
        'surface': '?',
    }

    print(f"\n{'='*80}")
    print(f"  CONTACT RE/MAX — URL directe{'  [SIMULATION]' if dry_run else ''}")
    print(f"  URL: {url}")
    print(f"  Expediteur: {CONTACT_FIRSTNAME} {CONTACT_LASTNAME} <{CONTACT_EMAIL}>")
    print(f"{'='*80}\n")

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    driver = webdriver.Firefox(options=options)
    try:
        ok = contact_listing(driver, listing, dry_run=dry_run)
    finally:
        driver.quit()

    print(f"\n{'='*80}")
    print(f"  RESULTAT: {'OK Envoye' if ok else 'ECHEC'}")
    print(f"{'='*80}\n")


def cmd_send(selection, dry_run=False):
    if not all([CONTACT_FIRSTNAME, CONTACT_LASTNAME, CONTACT_EMAIL, CONTACT_MESSAGE]):
        print("Variables CONTACT_* manquantes dans .env")
        sys.exit(1)

    ensure_contacted_column()
    all_listings = get_pending_listings()

    if not all_listings:
        print("Aucune annonce RE/MAX en attente.")
        print("Note: utiliser --url pour contacter une URL directement,")
        print("      ou activer le scraper RE/MAX dans main.py.")
        return

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

    mode_label = " [SIMULATION]" if dry_run else ""
    print(f"\n{'='*80}")
    print(f"  CONTACT RE/MAX — {len(selected)} annonce(s){mode_label}")
    print(f"  Expediteur: {CONTACT_FIRSTNAME} {CONTACT_LASTNAME} <{CONTACT_EMAIL}>")
    print(f"{'='*80}")
    print_listings_table(selected, show_number=False)
    print()

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')

    driver  = None
    success = 0
    failed  = 0
    total   = len(selected)

    try:
        if not dry_run:
            driver = webdriver.Firefox(options=options)

        for i, listing in enumerate(selected, 1):
            print(f"  ({i}/{total})", end=' ')
            if i > 1 and not dry_run:
                print(f"  Attente {DELAY_BETWEEN}s...")
                time.sleep(DELAY_BETWEEN)
            try:
                ok = contact_listing(driver, listing, dry_run=dry_run)
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
                if not dry_run:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    driver = webdriver.Firefox(options=options)

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    print(f"\n{'='*80}")
    if dry_run:
        print(f"  SIMULATION : {success} annonce(s) auraient ete envoyees")
    else:
        print(f"  RESUME: OK {success} envoye(s) | ECHEC {failed} echoue(s)")
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Contact agences RE/MAX.lu — formulaire direct, pas de login',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python auto_contact_remax.py --list
  python auto_contact_remax.py --send 1,3,5
  python auto_contact_remax.py --send all
  python auto_contact_remax.py --send all --dry-run
  python auto_contact_remax.py --url https://www.remax.lu/fr-lu/mandats-de-vente/...
  python auto_contact_remax.py --history
        """
    )
    parser.add_argument('--list',    action='store_true')
    parser.add_argument('--send',    type=str, default=None)
    parser.add_argument('--url',     type=str, default=None, help='URL directe (sans scraper)')
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.url:
        setup_logging(verbose=True)
        cmd_url(args.url, dry_run=args.dry_run)
    elif args.send:
        setup_logging(verbose=True)
        cmd_send(args.send, dry_run=args.dry_run)
    elif args.history:
        cmd_history()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
