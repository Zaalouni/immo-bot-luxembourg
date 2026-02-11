
#!/usr/bin/env python3

import requests
import re
import json
import sys
from urllib.parse import urljoin

def main():
    url = "https://www.athome.lu/location"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    print(f"🌐 Récupération de: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text

        print(f"✅ Page chargée ({len(html)} caractères)")

        # Pattern principal - chercher le JSON NUXT
        print("\n" + "="*60)
        print("RECHERCHE DE DONNÉES JSON STRUCTURÉES")
        print("="*60)

        patterns = [
            (r'window\.__NUXT__\s*=\s*(\{.*?\})\s*;', 'NUXT (probablement les données)'),
            (r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>', 'INITIAL_STATE'),
            (r'<script[^>]*id="__NUXT__"[^>]*>(\{.*?\})</script>', 'NUXT avec ID'),
            (r'<script[^>]*type="application/json"[^>]*>(\{.*?\})</script>', 'JSON-LD'),
        ]

        found_data = None
        found_name = ""

        for pattern, name in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                json_str = match.group(1)
                print(f"\n🔍 Pattern trouvé: {name}")
                print(f"   Taille: {len(json_str)} caractères")

                try:
                    data = json.loads(json_str)
                    print(f"   ✅ JSON valide")
                    print(f"   Type: {type(data)}")

                    if isinstance(data, dict):
                        print(f"   Clés racine: {list(data.keys())}")
                        # Si c'est un objet NUXT, vérifier les données
                        if name == "NUXT (probablement les données)":
                            found_data = data
                            found_name = name
                    elif isinstance(data, list):
                        print(f"   Liste de {len(data)} éléments")

                    # Sauvegarder le JSON
                    filename = f"/tmp/athome_data_{name.replace(' ', '_').lower()}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"   💾 Données sauvegardées: {filename}")

                except json.JSONDecodeError as e:
                    print(f"   ❌ Erreur de parsing JSON: {e}")
                    print(f"   Extrait (500 premiers caractères):")
                    print(f"   {json_str[:500]}...")

        # Si pas trouvé, chercher dans les balises script
        if not found_data:
            print("\n" + "="*60)
            print("ANALYSE DES BALISES <script>")
            print("="*60)

            # Chercher toutes les balises script
            script_pattern = r'<script[^>]*>(.*?)</script>'
            scripts = re.findall(script_pattern, html, re.DOTALL | re.IGNORECASE)

            print(f"Nombre de balises script trouvées: {len(scripts)}")

            for i, script_content in enumerate(scripts):
                # Filtrer les scripts courts et sans données
                if len(script_content) > 500 and ('{' in script_content or '[' in script_content):
                    # Essayer d'extraire des objets JSON
                    json_objects = re.findall(r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\})', script_content)

                    for j, obj_str in enumerate(json_objects[:3]):  # Limiter aux 3 premiers
                        if len(obj_str) > 100:
                            try:
                                data = json.loads(obj_str)
                                print(f"\n📦 Script #{i}, objet JSON #{j}:")
                                print(f"   Taille: {len(obj_str)} caractères")
                                print(f"   Type: {type(data)}")

                                if isinstance(data, dict):
                                    print(f"   Clés: {list(data.keys())[:10]}")

                                    # Vérifier si ça ressemble à des données d'annonces
                                    keys_lower = [k.lower() for k in data.keys()]
                                    real_estate_keywords = ['property', 'location', 'rent', 'sale', 'price',
                                                           'advert', 'listing', 'realestate', 'immobilier']

                                    if any(keyword in ' '.join(keys_lower) for keyword in real_estate_keywords):
                                        print(f"   🏠 Données immobilières détectées!")
                                        filename = f"/tmp/athome_script_{i}_data_{j}.json"
                                        with open(filename, 'w', encoding='utf-8') as f:
                                            json.dump(data, f, indent=2, ensure_ascii=False)
                                        print(f"   💾 Sauvegardé: {filename}")

                            except json.JSONDecodeError:
                                continue

        # Recherche d'URLs API potentielles
        print("\n" + "="*60)
        print("RECHERCHE D'APIS/ENDPOINTS")
        print("="*60)

        # Chercher des URLs API dans le JavaScript
        api_patterns = [
            r'["\'](https?://[^"\']+?/api/[^"\']+?)["\']',
            r'["\'](/api/[^"\']+?)["\']',
            r'["\'](https?://[^"\']+?/graphql[^"\']*?)["\']',
            r'["\'](/graphql[^"\']*?)["\']',
        ]

        for pattern in api_patterns:
            matches = re.findall(pattern, html)
            if matches:
                unique_matches = set(matches)
                print(f"\n🔗 URLs API trouvées ({len(unique_matches)}):")
                for api_url in list(unique_matches)[:10]:  # Limiter à 10
                    full_url = api_url if api_url.startswith('http') else urljoin(url, api_url)
                    print(f"   • {full_url}")

        # Vérifier les endpoints dans les requêtes réseau potentielles
        network_patterns = [
            r'fetch\(["\']([^"\']+?)["\']\)',
            r'axios\.get\(["\']([^"\']+?)["\']\)',
            r'\.ajax\([^)]*?url:\s*["\']([^"\']+?)["\']',
        ]

        print(f"\n🔍 Endpoints dans le code JavaScript:")
        for pattern in network_patterns:
            matches = re.findall(pattern, html)
            if matches:
                for endpoint in set(matches)[:5]:
                    if '/api/' in endpoint or 'graphql' in endpoint or 'search' in endpoint.lower():
                        print(f"   • {endpoint}")

        print("\n" + "="*60)
        print("ANALYSE TERMINÉE")
        print("="*60)

        if found_data:
            print(f"\n✅ Données principales trouvées dans: {found_name}")
            print(f"   Fichier: /tmp/athome_data_{found_name.replace(' ', '_').lower()}.json")
        else:
            print("\n⚠️  Aucune donnée structurée trouvée. Suggestions:")
            print("   1. Vérifiez si le site utilise du rendu côté client (React, Vue.js)")
            print("   2. Essayez d'utiliser Selenium ou Playwright pour le rendu JavaScript")
            print("   3. Inspectez les requêtes réseau dans les outils de développement")

    except requests.RequestException as e:
        print(f"❌ Erreur de requête: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
