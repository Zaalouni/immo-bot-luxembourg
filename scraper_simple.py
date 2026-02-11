
#!/usr/bin/env python3
import requests
import re
import json

url = "https://www.luxhome.lu/recherche/?status%5B%5D=location"

print("📡 Téléchargement...")
response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
html = response.text

print("🔍 Recherche du tableau d'annonces...")

# Pattern précis pour trouver le tableau des propriétés (celui qui commence avec les données d'annonces)
# Chercher le début du tableau avec le premier objet d'annonce
pattern = r'\[\s*\{\s*"title":"[^"]+",\s*"propertyType":"[^"]+",\s*"price":"[^"]+",\s*"url":"[^"]+",\s*"id":\d+'

match = re.search(pattern, html)

if match:
    # Trouver le début du tableau
    start_pos = html.rfind('[', 0, match.start())
    if start_pos == -1:
        start_pos = match.start()

    # Trouver la fin du tableau (jusqu'au prochain ]; qui termine le tableau)
    # Nous cherrons la fin après le début
    bracket_count = 1
    end_pos = start_pos + 1

    while bracket_count > 0 and end_pos < len(html):
        if html[end_pos] == '[':
            bracket_count += 1
        elif html[end_pos] == ']':
            bracket_count -= 1
        end_pos += 1

    json_str = html[start_pos:end_pos]
    print(f"✅ Tableau trouvé ({len(json_str)} caractères)")

    # Sauvegarder pour vérification
    with open('tableau_complet.txt', 'w', encoding='utf-8') as f:
        f.write(json_str[:5000])
    print("💾 Extrait sauvegardé: tableau_complet.txt")

else:
    print("❌ Pattern initial non trouvé, recherche alternative...")

    # Chercher les données plus spécifiquement
    # Les annonces sont dans une variable JavaScript
    lines = html.split('\n')
    for i, line in enumerate(lines):
        if '"title":' in line and '"price":' in line and 'propertyType' in line:
            print(f"✅ Ligne {i} contient des données: {line[:100]}...")

            # Chercher le début du tableau sur cette ligne
            start_idx = line.find('[')
            if start_idx != -1:
                # Extraire à partir de ce point
                partial_json = line[start_idx:]

                # Trouver la fin
                bracket_count = 1
                end_idx = 1
                while bracket_count > 0 and end_idx < len(partial_json):
                    if partial_json[end_idx] == '[':
                        bracket_count += 1
                    elif partial_json[end_idx] == ']':
                        bracket_count -= 1
                    end_idx += 1

                json_str = partial_json[:end_idx]
                print(f"   Tableau partiel trouvé ({len(json_str)} caractères)")
                break

# Version simplifiée : extraire chaque annonce individuellement
print("\n🎯 EXTRACTION INDIVIDUELLE DES ANNONCES")

# Pattern pour chaque objet annonce
annonce_pattern = r'\{\s*"title":"([^"]+)",\s*"propertyType":"([^"]+)",\s*"price":"([^"]+)",\s*"url":"([^"]+)",\s*"id":(\d+),\s*"lat":"([^"]+)",\s*"lng":"([^"]+)",\s*"thumb":"([^"]+)",'

annonces = re.findall(annonce_pattern, html, re.DOTALL)

print(f"✅ {len(annonces)} annonces extraites")

if annonces:
    # Traiter les annonces
    resultats = []

    for i, annonce in enumerate(annonces):
        titre, type_, prix, url, id_, lat, lng, thumb = annonce

        # Décoder les caractères Unicode
        def decode_text(text):
            replacements = {
                '\\u00e9': 'é', '\\u00e8': 'è', '\\u00ea': 'ê', '\\u00e0': 'à',
                '\\u00e2': 'â', '\\u00ee': 'î', '\\u00f4': 'ô', '\\u00fb': 'û',
                '\\u00e7': 'ç', '\\u00ef': 'ï', '\\u00eb': 'ë', '\\u00fc': 'ü',
                '\\u00f9': 'ù', '\\u20ac': '€', '\\u00b2': '²', '\\u00b3': '³',
                '&#8217;': "'", '&#8211;': '-', '&#8220;': '"', '&#8221;': '"',
                '&#038;': '&', '\\/': '/'
            }

            for code, char in replacements.items():
                text = text.replace(code, char)
            return text

        titre = decode_text(titre)
        type_ = decode_text(type_).replace('<small>', '').replace('</small>', '')
        url = decode_text(url)
        thumb = decode_text(thumb)

        # Extraire surface du titre
        surface_match = re.search(r'(\d+)\s*m\s*[²2b]', titre, re.IGNORECASE)
        surface = surface_match.group(1) if surface_match else ''

        # Extraire chambres
        chambres_match = re.search(r'(\d+)\s*(chambre|chbr|chr|pi[èe]ce|room|ch|bedroom)', titre, re.IGNORECASE)
        chambres = chambres_match.group(1) if chambres_match else ''

        # Localisation
        locations = ['Luxembourg', 'Esch', 'Kirchberg', 'Belair', 'Gare', 'Merkur',
                    'Cloche d\'Or', 'Hollerich', 'Bonnevoie', 'Cessange', 'Strassen',
                    'Howald', 'Belval', 'Limpertsberg', 'Sandweiler', 'Dudelange',
                    'Mamer', 'Steinfort', 'Schifflange', 'Bridel', 'Gasparich',
                    'Alzette', 'Luxemburg']

        localisation = ''
        for loc in locations:
            if loc.lower() in titre.lower():
                localisation = loc
                break

        annonce_data = {
            'id': int(id_),
            'titre': titre,
            'type': type_,
            'prix': prix,
            'url': url,
            'latitude': lat,
            'longitude': lng,
            'image': thumb,
            'surface': surface,
            'chambres': chambres,
            'localisation': localisation
        }

        resultats.append(annonce_data)

    # Sauvegarder en JSON
    with open('luxhome_annonces.json', 'w', encoding='utf-8') as f:
        json.dump(resultats, f, indent=2, ensure_ascii=False)
    print("💾 JSON sauvegardé: luxhome_annonces.json")

    # Sauvegarder en CSV
    import csv
    with open('luxhome_annonces.csv', 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'titre', 'type', 'prix', 'surface', 'chambres', 'localisation', 'url', 'latitude', 'longitude']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for annonce in resultats:
            row = {k: annonce.get(k, '') for k in fieldnames}
            writer.writerow(row)
    print("💾 CSV sauvegardé: luxhome_annonces.csv")

    # Afficher un résumé
    print(f"\n📊 RÉSUMÉ:")
    print(f"• Total annonces: {len(resultats)}")

    # Compter par type
    types = {}
    for a in resultats:
        t = a['type'] or 'Inconnu'
        types[t] = types.get(t, 0) + 1

    print(f"\n🏠 Types de biens:")
    for t, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {t}: {count}")

    # Statistiques prix
    prix_list = []
    for a in resultats:
        prix_str = a['prix']
        if '€' in prix_str:
            nums = re.findall(r'[\d\s,.]+', prix_str)
            if nums:
                try:
                    prix_num = float(nums[0].replace(' ', '').replace(',', '.'))
                    prix_list.append(prix_num)
                except:
                    pass

    if prix_list:
        print(f"\n💰 Prix (sur {len(prix_list)} annonces avec prix):")
        print(f"  • Min: {min(prix_list):,.0f} €")
        print(f"  • Max: {max(prix_list):,.0f} €")
        print(f"  • Moyenne: {sum(prix_list)/len(prix_list):,.0f} €")

    # Afficher 5 exemples
    print(f"\n📄 5 PREMIÈRES ANNONCES:")
    for i, a in enumerate(resultats[:5]):
        print(f"\n{i+1}. {a['titre'][:80]}...")
        print(f"   💰 {a['prix']}")
        if a['surface']:
            print(f"   📐 {a['surface']} m²")
        if a['chambres']:
            print(f"   🛏️  {a['chambres']} ch.")
        if a['localisation']:
            print(f"   📍 {a['localisation']}")
        print(f"   🔗 {a['url'][:60]}...")

    # Compter les annonces par localisation
    print(f"\n🗺️  Localisations (top 10):")
    loc_counts = {}
    for a in resultats:
        loc = a['localisation']
        if loc:
            loc_counts[loc] = loc_counts.get(loc, 0) + 1

    for loc, count in sorted(loc_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  • {loc}: {count}")

else:
    print("❌ Aucune annonce trouvée")

    # Debug : chercher ce qui est présent
    print("\n🔍 Debug - Recherche de patterns...")
    print(f"Occurrences de 'title': {html.count('title')}")
    print(f"Occurrences de 'price': {html.count('price')}")
    print(f"Occurrences de 'propertyType': {html.count('propertyType')}")

    # Chercher un exemple
    sample = re.search(r'"title":"[^"]{20,100}"', html)
    if sample:
        print(f"Exemple trouvé: {sample.group()}")
