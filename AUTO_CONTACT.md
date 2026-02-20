# auto_contact.py — Guide d'utilisation

Script pour contacter automatiquement les agences Nextimmo.lu via leur formulaire de contact.

---

## Prerequis

### 1. Firefox + geckodriver installes
Le script utilise Selenium avec Firefox. Verifier que Firefox est installe et que `geckodriver` est dans le PATH.

### 2. Variables dans `.env`

Ajouter ces lignes dans le fichier `.env` a la racine du projet :

```env
CONTACT_FIRSTNAME=Hamdi
CONTACT_LASTNAME=Nom
CONTACT_EMAIL=tonemail@example.com
CONTACT_PHONE=+352 621 123 456
CONTACT_MESSAGE=Bonjour, je suis interesse par votre annonce de location. Pouvez-vous me contacter pour organiser une visite ? Merci.
```

| Variable           | Obligatoire | Description                        |
|--------------------|-------------|------------------------------------|
| CONTACT_FIRSTNAME  | Oui         | Prenom affiché dans le formulaire  |
| CONTACT_LASTNAME   | Oui         | Nom de famille                     |
| CONTACT_EMAIL      | Oui         | Email de reponse de l'agence       |
| CONTACT_PHONE      | Non         | Telephone (si le champ existe)     |
| CONTACT_MESSAGE    | Oui         | Message envoye a l'agence          |

---

## Workflow en 2 etapes

### Etape 1 — Voir les annonces disponibles

```bash
python auto_contact.py --list
```

Affiche un tableau numerote de toutes les annonces Nextimmo.lu non encore contactees, triees par prix croissant.

Exemple de sortie :
```
================================================================
  ANNONCES NEXTIMMO EN ATTENTE DE CONTACT (12)
================================================================
  #    Prix     Ville                Ch    m2   Titre                                    URL
  ─    ─────    ──────────────────   ─    ───   ──────────────────────────────────────   ──────
  1   1500€     Luxembourg           2     75   Appartement lumineux centre-ville        https://...
  2   1750€     Strassen             3     90   Maison avec jardin                       https://...
  3   1800€     Kirchberg            2     80   Studio moderne                           https://...
  ...
```

### Etape 2 — Contacter les annonces choisies

Contacter des annonces specifiques par numero :
```bash
python auto_contact.py --send 1,3,5
```

Contacter toutes les annonces en attente :
```bash
python auto_contact.py --send all
```

---

## Options disponibles

| Commande                          | Action                                           |
|-----------------------------------|--------------------------------------------------|
| `--list`                          | Lister les annonces en attente                   |
| `--send 1,3,5`                    | Contacter les annonces #1, #3 et #5              |
| `--send all`                      | Contacter toutes les annonces en attente         |
| `--send all --dry-run`            | Simuler sans envoyer (pour tester la config)     |
| `--history`                       | Voir les annonces deja contactees                |

---

## Mode simulation (dry-run)

Avant un envoi massif, tester avec `--dry-run` pour verifier la config sans envoyer de messages :

```bash
python auto_contact.py --send all --dry-run
```

Sortie :
```
  (1/5) [DRY-RUN] 1500€ Luxembourg — Appartement lumineux centre-ville...
     → Expediteur : Hamdi Nom <tonemail@example.com>
     → Telephone  : +352 621 123 456
     → Message    : "Bonjour, je suis interesse par votre annonce..."
     [OK] Simulation uniquement — pas envoye
```

Aucun message n'est envoye, aucune annonce n'est marquee comme contactee.

---

## Historique des contacts

Voir toutes les annonces deja contactees :

```bash
python auto_contact.py --history
```

---

## Fichiers generes

| Fichier                          | Contenu                                          |
|----------------------------------|--------------------------------------------------|
| `auto_contact.log`               | Log complet de toutes les sessions               |
| `contact_screenshots/`           | Screenshots automatiques en cas d'erreur         |

Les screenshots sont utiles pour comprendre pourquoi un contact a echoue (page bloquee, captcha, formulaire different...).

---

## Comportement technique

- **Firefox headless** : le navigateur tourne en arriere-plan (invisible)
- **Timeout** : 30 secondes maximum par page
- **Delai** : 10 secondes entre chaque contact (evite le blocage IP)
- **Formulaire** : rempli automatiquement (prenom, nom, email, telephone, message)
- **Cookies** : acceptes automatiquement si une banniere apparait
- **emailOffers** : NON coche (evite les emails marketing non souhaites)
- **Marquage** : une annonce n'est marquee "contactee" que si l'envoi est confirme

---

## Problemes courants

### "Bouton contact non trouve"
Le site a peut-etre change son interface. Un screenshot est sauvegarde dans `contact_screenshots/`. Ouvrir l'annonce manuellement pour verifier.

### "Formulaire non apparu"
La page a mis trop de temps a charger le modal. Reessayer plus tard ou verifier la connexion.

### "Variables CONTACT_* manquantes"
Verifier que le fichier `.env` existe et contient bien les 4 variables obligatoires.

### L'annonce est marquee comme "envoyee" mais je n'ai rien recu
Verifier que `CONTACT_EMAIL` est correct dans `.env`. Verifier aussi les spams.

---

## Notes

- Le script fonctionne **uniquement sur Nextimmo.lu**
- Une annonce contactee ne peut pas etre recontactee (protection contre les doublons)
- Pour "remettre a zero" une annonce : `UPDATE listings SET contacted=0 WHERE listing_id='...'`
