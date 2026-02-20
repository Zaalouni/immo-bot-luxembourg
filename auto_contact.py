# =============================================================================
# auto_contact.py — Contact automatique des agences via Nextimmo.lu
# =============================================================================
# Script autonome en 2 etapes :
#   1. --list : affiche les annonces Nextimmo non contactees avec numeros
#   2. --send 1,3,5 : contacte uniquement les annonces choisies
#
# Securite : timeout 30s par annonce, delai 10s entre contacts
# Config : lit CONTACT_* depuis .env
#
# Usage :
#   python auto_contact.py --list           → lister les annonces en attente
#   python auto_contact.py --send 1,3       → contacter les annonces #1 et #3
#   python auto_contact.py --send all       → contacter toutes les annonces
#   python auto_contact.py --history        → voir les annonces deja contactees
#   python auto_contact.py --send all --dry-run → simuler sans envoyer
#
# Version : v2.7 (2026-02-20)
# =============================================================================
import sqlite3
import time
import logging
import argparse
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Config
load_dotenv()

# Parametres contact depuis .env
CONTACT_FIRSTNAME = os.getenv('CONTACT_FIRSTNAME', '').strip()
CONTACT_LASTNAME  = os.getenv('CONTACT_LASTNAME', '').strip()
CONTACT_PHONE     = os.getenv('CONTACT_PHONE', '').strip()
CONTACT_EMAIL     = os.getenv('CONTACT_EMAIL', '').strip()
CONTACT_MESSAGE   = os.getenv('CONTACT_MESSAGE', '').strip()

DB_PATH         = 'listings.db'
CONTACT_TIMEOUT = 30   # timeout chargement page (secondes)
DELAY_BETWEEN   = 10   # delai entre deux contacts (secondes)
SCREENSHOTS_DIR = 'contact_screenshots'  # dossier screenshots erreurs

logger = logging.getLogger(__name__)


def setup_logging(verbose=False):
    handlers = [logging.FileHandler('auto_contact.log', encoding='utf-8')]
    if verbose:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def ensure_contacted_column():
    """Ajouter la colonne 'contacted' si elle n'existe pas"""
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
    """Recuperer les annonces Nextimmo non contactees"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, title, city, price, rooms, surface, url, created_at
        FROM listings
        WHERE site = 'Nextimmo.lu'
          AND (contacted IS NULL OR contacted = 0)
        ORDER BY price ASC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_contacted_listings():
    """Recuperer les annonces deja contactees"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, title, city, price, rooms, surface, url, created_at
        FROM listings
        WHERE site = 'Nextimmo.lu'
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


def print_listings_table(listings, show_number=True):
    """Afficher les annonces en tableau lisible"""
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


# ─── Helpers Selenium ────────────────────────────────────────────────────────

def save_screenshot(driver, listing_id):
    """Sauvegarder un screenshot en cas d'erreur pour debug"""
    try:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        path = os.path.join(SCREENSHOTS_DIR, f"error_{listing_id}_{int(time.time())}.png")
        driver.save_screenshot(path)
        logger.info(f"   Screenshot sauvegarde: {path}")
        print(f"     Screenshot: {path}")
    except Exception as e:
        logger.warning(f"   Screenshot impossible: {e}")


def find_form_field(form, selectors):
    """Essayer plusieurs selecteurs CSS pour un champ (gere les variations de nommage)"""
    for sel in selectors:
        try:
            return form.find_element(By.CSS_SELECTOR, sel)
        except NoSuchElementException:
            continue
    return None


def find_contact_form(driver):
    """Trouver le formulaire de contact parmi tous les formulaires de la page.
    Identifie le bon formulaire en cherchant celui qui contient un champ email,
    ce qui evite de cibler un formulaire de recherche."""
    forms = driver.find_elements(By.TAG_NAME, 'form')
    for form in forms:
        try:
            form.find_element(By.CSS_SELECTOR, "input[name='email'], input[type='email']")
            return form
        except NoSuchElementException:
            continue
    return None


# ─── Logique contact ─────────────────────────────────────────────────────────

def contact_listing(driver, listing, dry_run=False):
    """Contacter une agence pour une annonce donnee. Retourne True si succes."""
    url        = listing['url']
    listing_id = listing['listing_id']
    wait       = WebDriverWait(driver, 15)

    logger.info(f"Contact: {listing['title'][:50]} — {listing['price']}€ — {listing['city']}")
    logger.info(f"   URL: {url}")

    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"  {prefix}{listing['price']}€ {listing['city']} — {listing['title'][:40]}...")

    # Mode simulation : afficher ce qui serait envoye sans soumettre
    if dry_run:
        print(f"     → Expediteur : {CONTACT_FIRSTNAME} {CONTACT_LASTNAME} <{CONTACT_EMAIL}>")
        if CONTACT_PHONE:
            print(f"     → Telephone  : {CONTACT_PHONE}")
        msg_preview = CONTACT_MESSAGE[:80] + ('...' if len(CONTACT_MESSAGE) > 80 else '')
        print(f"     → Message    : \"{msg_preview}\"")
        print(f"     [OK] Simulation uniquement — pas envoye")
        return True

    try:
        # 1. Charger la page
        driver.set_page_load_timeout(CONTACT_TIMEOUT)
        driver.get(url)

        # 2. Accepter cookies si present (plusieurs variantes de texte)
        for cookie_text in ['Autoriser', 'Allow All', 'Accepter', 'Accept']:
            try:
                cookie_btn = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//button[contains(text(), '{cookie_text}')]")
                    )
                )
                cookie_btn.click()
                time.sleep(1)
                break
            except TimeoutException:
                continue

        # 3. Attendre que les boutons soient charges puis trouver "Contacter l'agence"
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'button')))
        except TimeoutException:
            pass

        contact_btn    = None
        search_texts   = ["Contact agency", "Contacter l'agence", "Contact", "Contacter"]
        all_buttons    = driver.find_elements(By.TAG_NAME, 'button')
        for target in search_texts:
            for btn in all_buttons:
                try:
                    if btn.is_displayed() and btn.text.strip() == target:
                        contact_btn = btn
                        break
                except Exception:
                    continue
            if contact_btn:
                break

        if not contact_btn:
            logger.warning(f"   Bouton contact non trouve pour {listing_id}")
            print(f"     Bouton contact non trouve")
            save_screenshot(driver, listing_id)
            return False

        driver.execute_script("arguments[0].scrollIntoView(true);", contact_btn)
        time.sleep(1)
        contact_btn.click()

        # 4. Attendre l'apparition du formulaire de contact
        try:
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[name='email'], input[type='email']")
            ))
        except TimeoutException:
            logger.warning(f"   Formulaire non apparu pour {listing_id}")
            print(f"     Formulaire non apparu apres clic")
            save_screenshot(driver, listing_id)
            return False

        # 5. Identifier le bon formulaire (pas un formulaire de recherche)
        form = find_contact_form(driver)
        if not form:
            logger.warning(f"   Formulaire de contact introuvable pour {listing_id}")
            print(f"     Formulaire de contact introuvable")
            save_screenshot(driver, listing_id)
            return False

        # 6. Remplir le formulaire (gere les variantes de nommage des champs)

        # Prenom
        field = find_form_field(form, [
            "input[name='firstName']", "input[name='firstname']", "input[name='prenom']"
        ])
        if field:
            field.clear()
            field.send_keys(CONTACT_FIRSTNAME)

        # Nom (lastName ou lastname selon le site)
        field = find_form_field(form, [
            "input[name='lastName']", "input[name='lastname']", "input[name='nom']"
        ])
        if field:
            field.clear()
            field.send_keys(CONTACT_LASTNAME)

        # Telephone (optionnel)
        if CONTACT_PHONE:
            field = find_form_field(form, [
                "input[name='phone']", "input[name='telephone']", "input[type='tel']"
            ])
            if field:
                field.clear()
                field.send_keys(CONTACT_PHONE)

        # Email
        field = find_form_field(form, [
            "input[name='email']", "input[type='email']"
        ])
        if field:
            field.clear()
            field.send_keys(CONTACT_EMAIL)

        # Message
        textarea = find_form_field(form, [
            "textarea[name='message']", "textarea"
        ])
        if textarea:
            textarea.clear()
            textarea.send_keys(CONTACT_MESSAGE)

        # Checkbox : politique de confidentialite (obligatoire)
        try:
            checkbox = find_form_field(form, [
                "input[name='privacyPolicy']", "input[name='privacy']",
                "input[name='cgv']", "input[type='checkbox']"
            ])
            if checkbox and not checkbox.is_selected():
                driver.execute_script("arguments[0].click();", checkbox)
        except Exception:
            pass

        # Note : emailOffers NON coche (evite les emails marketing non sollicites)

        # 7. Soumettre
        submit_btn = form.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()

        # 8. Attendre confirmation (max 10s)
        confirmed = False
        try:
            WebDriverWait(driver, 10).until(lambda d: any(
                w in d.find_element(By.TAG_NAME, 'body').text.lower()
                for w in ['envoy', 'merci', 'sent', 'thank', 'succ']
            ))
            confirmed = True
        except TimeoutException:
            pass

        # 9. Verifier le resultat final
        page_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
        if confirmed or any(w in page_text for w in ['envoy', 'merci', 'sent', 'thank', 'succ']):
            logger.info(f"   Message envoye avec succes!")
            print(f"     OK Envoye!")
            return True
        elif any(w in page_text for w in ['erreur', 'error', 'echec', 'failed']):
            logger.warning(f"   Erreur detectee apres envoi")
            print(f"     Erreur detectee apres envoi")
            save_screenshot(driver, listing_id)
            return False
        else:
            logger.info(f"   Formulaire soumis (pas de message d'erreur visible)")
            print(f"     OK Envoye (pas d'erreur visible)")
            return True

    except Exception as e:
        logger.error(f"   Erreur: {str(e)[:100]}")
        print(f"     Erreur: {str(e)[:80]}")
        save_screenshot(driver, listing_id)
        return False


# ─── Commandes CLI ────────────────────────────────────────────────────────────

def cmd_list():
    """Commande --list : afficher les annonces en attente"""
    ensure_contacted_column()
    listings = get_pending_listings()

    print(f"\n{'='*120}")
    print(f"  ANNONCES NEXTIMMO EN ATTENTE DE CONTACT ({len(listings)})")
    print(f"{'='*120}")
    print_listings_table(listings, show_number=True)
    print(f"\n  Pour contacter : python auto_contact.py --send 1,3,5")
    print(f"  Pour tout contacter : python auto_contact.py --send all")
    print(f"  Pour simuler : python auto_contact.py --send all --dry-run\n")


def cmd_history():
    """Commande --history : afficher les annonces deja contactees"""
    ensure_contacted_column()
    listings = get_contacted_listings()

    print(f"\n{'='*120}")
    print(f"  ANNONCES NEXTIMMO DEJA CONTACTEES ({len(listings)})")
    print(f"{'='*120}")
    print_listings_table(listings, show_number=False)
    print()


def cmd_send(selection, dry_run=False):
    """Commande --send : contacter les annonces selectionnees"""
    # Validation .env
    if not all([CONTACT_FIRSTNAME, CONTACT_LASTNAME, CONTACT_EMAIL, CONTACT_MESSAGE]):
        print("Variables CONTACT_* manquantes dans .env")
        print("   Requis: CONTACT_FIRSTNAME, CONTACT_LASTNAME, CONTACT_EMAIL, CONTACT_MESSAGE")
        sys.exit(1)

    ensure_contacted_column()
    all_listings = get_pending_listings()

    if not all_listings:
        print("Aucune annonce Nextimmo en attente")
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

    # Affichage recapitulatif
    mode_label = " [MODE SIMULATION — rien ne sera envoye]" if dry_run else ""
    print(f"\n{'='*80}")
    print(f"  CONTACT NEXTIMMO — {len(selected)} annonce(s){mode_label}")
    print(f"  Expediteur: {CONTACT_FIRSTNAME} {CONTACT_LASTNAME} <{CONTACT_EMAIL}>")
    print(f"{'='*80}")
    print_listings_table(selected, show_number=False)
    msg_preview = CONTACT_MESSAGE[:80] + ('...' if len(CONTACT_MESSAGE) > 80 else '')
    print(f"\n  Message: \"{msg_preview}\"")
    print()

    options = Options()
    if not dry_run:
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

    # Resume
    print(f"\n{'='*80}")
    if dry_run:
        print(f"  SIMULATION : {success} annonce(s) aurait(ent) ete envoyee(s)")
    else:
        print(f"  RESUME: OK {success} envoye(s) | ECHEC {failed} echoue(s)")
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Contact agences Nextimmo — Etape 1: --list, Etape 2: --send 1,3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python auto_contact.py --list              Lister les annonces en attente
  python auto_contact.py --send 1,3,5        Contacter les annonces #1, #3, #5
  python auto_contact.py --send all          Contacter toutes les annonces
  python auto_contact.py --send all --dry-run  Simuler sans envoyer
  python auto_contact.py --history           Voir les annonces deja contactees
        """
    )
    parser.add_argument('--list',    action='store_true', help='Lister les annonces en attente')
    parser.add_argument('--send',    type=str, default=None, help='Numeros a contacter (ex: 1,3,5 ou all)')
    parser.add_argument('--history', action='store_true', help='Voir les annonces deja contactees')
    parser.add_argument('--dry-run', action='store_true', help='Simuler sans envoyer (pour tester)')
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
