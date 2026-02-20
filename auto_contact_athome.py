# =============================================================================
# auto_contact_athome.py — Contact automatique des agences via Athome.lu
# =============================================================================
# Flux :
#   1. Connexion unique au compte Athome en debut de session
#   2. Pour chaque annonce : clic "Contacter" → formulaire → envoi
#
# Config : lit ATHOME_EMAIL + ATHOME_PASSWORD + CONTACT_* depuis .env
#
# Usage :
#   python auto_contact_athome.py --list           → annonces en attente
#   python auto_contact_athome.py --send 1,3       → contacter #1 et #3
#   python auto_contact_athome.py --send all       → tout contacter
#   python auto_contact_athome.py --send all --dry-run → simuler
#   python auto_contact_athome.py --history        → annonces deja contactees
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

ATHOME_EMAIL      = os.getenv('ATHOME_EMAIL', '').strip()
ATHOME_PASSWORD   = os.getenv('ATHOME_PASSWORD', '').strip()
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
    handlers = [logging.FileHandler('auto_contact_athome.log', encoding='utf-8')]
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
        WHERE site = 'Athome.lu'
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
        WHERE site = 'Athome.lu'
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
        path = os.path.join(SCREENSHOTS_DIR, f"athome_{label}_{int(time.time())}.png")
        driver.save_screenshot(path)
        print(f"     Screenshot: {path}")
        logger.info(f"   Screenshot: {path}")
    except Exception:
        pass


def find_form_field(form, selectors):
    for sel in selectors:
        try:
            return form.find_element(By.CSS_SELECTOR, sel)
        except NoSuchElementException:
            continue
    return None


def accept_cookies(driver):
    for text in ['Autoriser', 'Accepter', 'Allow All', 'Accept']:
        try:
            btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(), '{text}')]"))
            )
            btn.click()
            time.sleep(1)
            return
        except TimeoutException:
            continue


# ─── Login Athome ─────────────────────────────────────────────────────────────

def login_athome(driver):
    """Se connecter a Athome.lu. Retourne True si succes."""
    print("  Connexion a Athome.lu...")
    logger.info("Connexion Athome.lu")

    try:
        driver.get('https://www.athome.lu')
        time.sleep(3)
        accept_cookies(driver)

        wait = WebDriverWait(driver, 10)

        # Cliquer sur "Connectez-vous" dans le header
        login_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Connectez-vous')]"))
        )
        login_btn.click()
        time.sleep(2)

        # Remplir le formulaire de login
        _fill_login_form(driver, wait)

        # Verifier connexion : le bouton "Connectez-vous" doit disparaitre
        try:
            WebDriverWait(driver, 8).until_not(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(), 'Connectez-vous')]")
                )
            )
            print("  Connecte!")
            logger.info("Connexion reussie")
            return True
        except TimeoutException:
            # Verifier si un avatar/nom apparait (indicateur de connexion)
            page = driver.find_element(By.TAG_NAME, 'body').text
            if ATHOME_EMAIL.split('@')[0].lower() in page.lower():
                print("  Connecte!")
                return True
            logger.warning("Connexion incertaine")
            print("  Connexion incertaine (verification manuelle recommandee)")
            save_screenshot(driver, 'login_result')
            return True  # On continue quand meme

    except Exception as e:
        logger.error(f"Erreur login: {e}")
        print(f"  Erreur login: {str(e)[:80]}")
        save_screenshot(driver, 'login_error')
        return False


def _fill_login_form(driver, wait):
    """Remplir le formulaire email/password (modal ou page)"""
    # Attendre le champ email
    wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "input[type='email'], input[name='email']")
    ))

    # Chercher dans tous les formulaires
    forms = driver.find_elements(By.TAG_NAME, 'form')
    login_form = None
    for form in forms:
        try:
            form.find_element(By.CSS_SELECTOR, "input[type='password']")
            login_form = form
            break
        except NoSuchElementException:
            continue

    if not login_form:
        # Essayer "Continuer avec un Email" si les champs ne sont pas visibles
        try:
            email_btn = driver.find_element(
                By.XPATH, "//button[contains(text(), 'Continuer avec un Email')]"
            )
            email_btn.click()
            time.sleep(1)
            # Reessayer apres le clic
            forms = driver.find_elements(By.TAG_NAME, 'form')
            for form in forms:
                try:
                    form.find_element(By.CSS_SELECTOR, "input[type='password']")
                    login_form = form
                    break
                except NoSuchElementException:
                    continue
        except NoSuchElementException:
            pass

    if not login_form:
        raise Exception("Formulaire de login introuvable")

    email_field = find_form_field(login_form, [
        "input[type='email']", "input[name='email']"
    ])
    pwd_field = login_form.find_element(By.CSS_SELECTOR, "input[type='password']")

    if email_field:
        email_field.clear()
        email_field.send_keys(ATHOME_EMAIL)

    pwd_field.clear()
    pwd_field.send_keys(ATHOME_PASSWORD)

    # Soumettre
    try:
        submit = login_form.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit.click()
    except NoSuchElementException:
        pwd_field.send_keys('\n')

    time.sleep(3)


# ─── Contact une annonce Athome ───────────────────────────────────────────────

def contact_listing(driver, listing, dry_run=False):
    """Contacter une agence Athome. Retourne True si succes."""
    url        = listing['url']
    listing_id = listing['listing_id']
    wait       = WebDriverWait(driver, 15)

    logger.info(f"Contact: {listing['title'][:50]} — {listing['price']}€ — {listing['city']}")
    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"  {prefix}{listing['price']}€ {listing['city']} — {listing['title'][:40]}...")

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

        # 1. Cliquer sur "Contacter"
        contact_btn = None
        for text in ["Contacter", "Contact", "Contacter l'agence"]:
            try:
                contact_btn = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//button[contains(@class,'contact') or text()='{text}']")
                    )
                )
                break
            except TimeoutException:
                continue

        if not contact_btn:
            # Fallback : chercher par classe
            try:
                contact_btn = driver.find_element(
                    By.CSS_SELECTOR, "button.detail-page__contact-agency-button"
                )
            except NoSuchElementException:
                pass

        if not contact_btn:
            logger.warning(f"   Bouton contact non trouve: {listing_id}")
            print(f"     Bouton contact non trouve")
            save_screenshot(driver, listing_id)
            return False

        # JS click direct (scrollIntoView bloque sur Athome — conteneur overflow)
        driver.execute_script("arguments[0].click();", contact_btn)
        time.sleep(3)

        # 2. Verifier si le modal de login apparait (non connecte)
        try:
            driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            # Login requis : remplir email + password dans le modal
            logger.info("   Login requis via modal...")
            print(f"     Login requis, connexion...")
            _fill_login_form(driver, WebDriverWait(driver, 10))
            time.sleep(3)
            # Re-trouver le bouton Contacter (stale element apres login)
            try:
                new_btn = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button.detail-page__contact-agency-button")
                    )
                )
                driver.execute_script("arguments[0].click();", new_btn)
                time.sleep(3)
            except Exception:
                pass  # Le modal a peut-etre deja transition vers le formulaire
        except NoSuchElementException:
            pass  # Deja connecte, formulaire contact direct

        # 3. Trouver le formulaire de contact
        contact_form = None
        for form in driver.find_elements(By.TAG_NAME, 'form'):
            try:
                # Chercher un form avec champ message ou prenom (pas le form login)
                fields = form.find_elements(By.CSS_SELECTOR,
                    "textarea, input[name='message'], input[name='firstName']"
                )
                if fields:
                    contact_form = form
                    break
            except Exception:
                continue

        if not contact_form:
            logger.warning(f"   Formulaire contact non trouve: {listing_id}")
            print(f"     Formulaire contact non trouve")
            save_screenshot(driver, listing_id)
            return False

        # 4. Remplir le formulaire
        field = find_form_field(contact_form, [
            "input[name='firstName']", "input[name='firstname']"
        ])
        if field:
            field.clear()
            field.send_keys(CONTACT_FIRSTNAME)

        field = find_form_field(contact_form, [
            "input[name='lastName']", "input[name='lastname']"
        ])
        if field:
            field.clear()
            field.send_keys(CONTACT_LASTNAME)

        if CONTACT_PHONE:
            field = find_form_field(contact_form, [
                "input[name='phone']", "input[type='tel']"
            ])
            if field:
                field.clear()
                field.send_keys(CONTACT_PHONE)

        field = find_form_field(contact_form, [
            "input[name='email']", "input[type='email']"
        ])
        if field:
            try:
                field.clear()
                field.send_keys(CONTACT_EMAIL)
            except Exception:
                pass  # Peut etre pre-rempli et readonly

        textarea = find_form_field(contact_form, [
            "textarea[name='message']", "textarea"
        ])
        if textarea:
            textarea.clear()
            textarea.send_keys(CONTACT_MESSAGE)

        # Checkbox confidentialite
        try:
            cb = find_form_field(contact_form, [
                "input[name='privacyPolicy']", "input[name='privacy']",
                "input[type='checkbox']"
            ])
            if cb and not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
        except Exception:
            pass

        # 5. Soumettre
        submit = contact_form.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit.click()
        time.sleep(4)

        # 6. Verifier confirmation
        page_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
        if any(w in page_text for w in ['envoy', 'merci', 'sent', 'thank', 'succ']):
            logger.info("   Envoye avec succes!")
            print(f"     OK Envoye!")
            return True
        elif any(w in page_text for w in ['erreur', 'error', 'echec']):
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
    print(f"  ANNONCES ATHOME EN ATTENTE DE CONTACT ({len(listings)})")
    print(f"{'='*120}")
    print_listings_table(listings, show_number=True)
    print(f"\n  Pour contacter : python auto_contact_athome.py --send 1,3,5")
    print(f"  Pour tout contacter : python auto_contact_athome.py --send all\n")


def cmd_history():
    ensure_contacted_column()
    listings = get_contacted_listings()
    print(f"\n{'='*120}")
    print(f"  ANNONCES ATHOME DEJA CONTACTEES ({len(listings)})")
    print(f"{'='*120}")
    print_listings_table(listings, show_number=False)
    print()


def cmd_send(selection, dry_run=False):
    if not all([CONTACT_FIRSTNAME, CONTACT_LASTNAME, CONTACT_EMAIL, CONTACT_MESSAGE]):
        print("Variables CONTACT_* manquantes dans .env")
        sys.exit(1)
    if not dry_run and not all([ATHOME_EMAIL, ATHOME_PASSWORD]):
        print("Variables ATHOME_EMAIL + ATHOME_PASSWORD manquantes dans .env")
        sys.exit(1)

    ensure_contacted_column()
    all_listings = get_pending_listings()

    if not all_listings:
        print("Aucune annonce Athome en attente")
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
    print(f"  CONTACT ATHOME — {len(selected)} annonce(s){mode_label}")
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
            # Pas de pre-login : la connexion se fait directement dans le modal
            # de la premiere annonce (plus fiable que le login via homepage)

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
        description='Contact agences Athome.lu — connexion compte + formulaire',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prerequis .env :
  ATHOME_EMAIL=ton@email.com
  ATHOME_PASSWORD=tonmotdepasse
  CONTACT_FIRSTNAME / CONTACT_LASTNAME / CONTACT_EMAIL / CONTACT_MESSAGE

Exemples:
  python auto_contact_athome.py --list
  python auto_contact_athome.py --send 1,3,5
  python auto_contact_athome.py --send all
  python auto_contact_athome.py --send all --dry-run
  python auto_contact_athome.py --history
        """
    )
    parser.add_argument('--list',    action='store_true')
    parser.add_argument('--send',    type=str, default=None)
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
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
