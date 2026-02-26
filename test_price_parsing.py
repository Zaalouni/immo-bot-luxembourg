#!/usr/bin/env python3
# =============================================================================
# test_price_parsing.py — Tests spécifiques pour extraction de prix
# =============================================================================
# Teste les cas problématiques d'extraction de prix pour chaque scraper:
# - Espaces insécables (U+202F)
# - Format décimal européen (1.250 vs 1,250)
# - Format mixte (1.250,50)
# - Charges supplémentaires (loyer + charges)
#
# Usage : python test_price_parsing.py
# =============================================================================

import unittest
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# HELPER FUNCTIONS FOR PRICE PARSING
# =============================================================================

def parse_price_immotop(price_text):
    """Simule parsing Immotop.lu avec espaces insécables"""
    price_clean = price_text.replace(' ', '').replace('\u202f', '').replace(',', '')
    try:
        return int(price_clean)
    except ValueError:
        return 0

def parse_price_luxhome(prix_raw):
    """Simule parsing Luxhome.lu avec point européen"""
    prix_clean = prix_raw.replace('\\u20ac', '').replace('€', '').replace(' ', '').replace('.', '').replace(',', '')
    prix_match = re.search(r'(\d+)', prix_clean)
    if prix_match:
        try:
            return int(prix_match.group(1))
        except:
            pass
    return 0

def parse_price_vivi(text):
    """Simule parsing VIVI.lu (multi-lignes)"""
    price = 0
    for line in text.split('\n'):
        if '€' in line:
            price_digits = re.sub(r'[^\d]', '', line)
            if price_digits:
                try:
                    price = int(price_digits)
                    break
                except ValueError:
                    continue
    return price

def parse_price_newimmo(text):
    """Simule parsing Newimmo.lu"""
    price_match = re.search(r'([\d\s\.]+)\s*€', text)
    if price_match:
        price_str = price_match.group(1).strip().replace(' ', '').replace('.', '')
        try:
            return int(price_str)
        except ValueError:
            pass
    return 0

def parse_price_unicorn(text):
    """Simule parsing Unicorn.lu (même que Newimmo)"""
    price_match = re.search(r'([\d\s\.]+)\s*€', text)
    if price_match:
        price_str = price_match.group(1).strip().replace(' ', '').replace('.', '')
        try:
            return int(price_str)
        except ValueError:
            pass
    return 0

# =============================================================================
# TEST CASES
# =============================================================================

class TestPriceParsing(unittest.TestCase):
    """Tests d'extraction de prix problématiques"""

    # ========= IMMOTOP =========
    def test_immotop_normal_price(self):
        """Immotop: prix normal"""
        result = parse_price_immotop("1250")
        self.assertEqual(result, 1250, "Prix normal OK")

    def test_immotop_space(self):
        """Immotop: prix avec espace"""
        result = parse_price_immotop("1 250")
        self.assertEqual(result, 1250, "Prix avec espace")

    def test_immotop_insecable(self):
        """Immotop: prix avec espace insécable U+202F"""
        result = parse_price_immotop("1\u202f250")  # U+202F
        self.assertEqual(result, 1250, "Prix avec espace insécable")

    def test_immotop_euro_symbol(self):
        """Immotop: prix avec symbole €"""
        result = parse_price_immotop("1 250€")
        self.assertEqual(result, 1250, "Prix avec €")

    # ========= LUXHOME (problématique!) =========
    def test_luxhome_normal_price(self):
        """Luxhome: prix normal"""
        result = parse_price_luxhome("2500€")
        self.assertEqual(result, 2500, "Prix normal OK")

    def test_luxhome_european_decimal(self):
        """Luxhome: prix avec point européen (2.500€ = 2500)"""
        result = parse_price_luxhome("2.500€")
        self.assertEqual(result, 2500, "Prix point européen")

    def test_luxhome_space_european(self):
        """Luxhome: prix avec espace et point (2 500€)"""
        result = parse_price_luxhome("2 500€")
        # Problème: "2 500€" → "2500€" après replace('.', '') = "2500"
        self.assertEqual(result, 2500, "Prix espace")

    def test_luxhome_mixed_decimal(self):
        """Luxhome: prix mixte (2.500,50€) — PROBLÈME!"""
        # Format: 2.500,50€ (point = séparateur milliers, virgule = décimal)
        result = parse_price_luxhome("2.500,50€")
        # Naïf: "2.500,50€" → remove '.' → "2500,50€" → "250050" ❌ MAUVAIS
        # Attendu: 2500 (on ignore décimal)
        logger.warning(f"  Luxhome mixte: {result} (attendu 2500, problématique si format change)")

    # ========= VIVI (multi-lignes) =========
    def test_vivi_single_line_price(self):
        """VIVI: prix sur une ligne"""
        result = parse_vivi_single_line("Loyer : 1250€")
        self.assertEqual(result, 1250, "Prix simple")

    def test_vivi_multiline_loyer_charges(self):
        """VIVI: prix multi-lignes (Loyer + Charges) — PROBLÈME!"""
        text = """Studio\n1 250€/mois\nLoyer: 1250\nCharges: 150€"""
        result = parse_price_vivi(text)
        # Résultat: prend première ligne avec € = 1250 OK
        # Mais si format change: "Charges: 150€" d'abord → 150 ❌ FAUX
        self.assertEqual(result, 1250, "Prend première ligne avec €")

    def test_vivi_charges_before_loyer(self):
        """VIVI: charges avant loyer (risque!)"""
        text = """Studio\nCharges: 150€\nLoyer: 1250€"""
        result = parse_price_vivi(text)
        # ❌ PROBLÈME: prend "Charges: 150€" en premier = 150 au lieu de 1250
        self.assertNotEqual(result, 150, "Dangereux: capture charges au lieu de loyer")
        logger.warning(f"  VIVI charges avant loyer: {result} (attendu 1250) — BUG!")

    # ========= NEWIMMO / UNICORN (décimal) =========
    def test_newimmo_normal_price(self):
        """Newimmo: prix normal"""
        result = parse_price_newimmo("1 250€")
        self.assertEqual(result, 1250, "Prix normal")

    def test_newimmo_decimal_point(self):
        """Newimmo: prix avec point décimal (1.250€ = 1250, pas 1.25!)"""
        # Format: "1.250€" (point = séparateur milliers)
        result = parse_price_newimmo("1.250€")
        # Naïf: "1.250€" → replace(' ', '') → "1.250€" → replace('.', '') → "1250€" ✅ OK
        self.assertEqual(result, 1250, "Point européen")

    def test_newimmo_decimal_comma(self):
        """Newimmo: prix avec virgule décimale (1.250,00€)"""
        # Format mixte: "1.250,00€"
        result = parse_price_newimmo("1.250,00€")
        # Naïf: remove '.' → "1250,00€" → replace(',', '') → "125000€" ❌ MAUVAIS!
        logger.warning(f"  Newimmo décimal: {result} (attendu ~1250, format mixte problématique)")

    def test_unicorn_similar_to_newimmo(self):
        """Unicorn: même problème que Newimmo"""
        result = parse_price_unicorn("1.250,00€")
        logger.warning(f"  Unicorn décimal: {result} (même problème que Newimmo)")

# =============================================================================
# ADDITIONAL HELPER TESTS
# =============================================================================

def parse_vivi_single_line(text):
    """Helper pour un test simple"""
    price = 0
    if '€' in text:
        price_digits = re.sub(r'[^\d]', '', text)
        if price_digits:
            price = int(price_digits)
    return price

# =============================================================================
# ROOM/SURFACE PARSING TESTS
# =============================================================================

class TestRoomSurfaceParsing(unittest.TestCase):
    """Tests pour chambres et surface"""

    def test_rooms_extraction_french(self):
        """Extraction chambres en français"""
        text = "Appartement 2 chambres"
        match = re.search(r'(\d+)\s*chambres?', text, re.IGNORECASE)
        self.assertEqual(int(match.group(1)), 2, "2 chambres")

    def test_rooms_with_pieces(self):
        """Extraction avec 'pièces'"""
        text = "Studio 1 pièce"
        match = re.search(r'(\d+)\s*(?:pièce|chambre)', text, re.IGNORECASE)
        self.assertEqual(int(match.group(1)), 1, "1 pièce")

    def test_surface_normal(self):
        """Extraction surface normale"""
        text = "Surface 52 m²"
        match = re.search(r'(\d+)\s*m[²2]', text)
        self.assertEqual(int(match.group(1)), 52, "52 m²")

    def test_surface_decimal(self):
        """Extraction surface décimale"""
        text = "Surface 52.50 m²"
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', text)
        surface = int(float(match.group(1).replace(',', '.')))
        self.assertEqual(surface, 52, "52.50 m² → 52 int")

    def test_surface_comma_decimal(self):
        """Extraction surface avec virgule décimale"""
        text = "Surface 52,50 m²"
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', text)
        surface = int(float(match.group(1).replace(',', '.')))
        self.assertEqual(surface, 52, "52,50 m² → 52 int")

# =============================================================================
# CITY EXTRACTION TESTS
# =============================================================================

class TestCityExtraction(unittest.TestCase):
    """Tests pour extraction de ville"""

    def test_city_from_url_immotop(self):
        """Ville depuis titre Immotop (après virgule)"""
        title = "2 chambres, 75 m², Luxembourg"
        parts = title.split(',')
        city = parts[-1].strip() if len(parts) > 1 else 'Luxembourg'
        self.assertEqual(city, 'Luxembourg', "Ville après virgule")

    def test_city_from_url_newimmo(self):
        """Ville depuis URL Newimmo"""
        # URL: /fr/louer/appartement/beaufort/127259-...
        link_path = "/fr/louer/appartement/beaufort/127259-appartement-beaufort/"
        parts = link_path.strip('/').split('/')
        city = 'Luxembourg'
        if len(parts) >= 4:
            city = parts[3].replace('-', ' ').title()
        self.assertEqual(city, 'Beaufort', "Ville depuis URL index 3")

    def test_city_from_url_unicorn_complex(self):
        """Ville depuis URL Unicorn (regex complexe)"""
        # URL: /detail-9278-location-studio-esch-sur-alzette
        link_path = "/detail-9278-location-studio-esch-sur-alzette"
        type_words = r'(?:appartement|studio|maison|penthouse|duplex|loft|bureau|meuble|chambre|colocation|terrain|commerce|parking|garage)'
        location_match = re.search(rf'location-{type_words}(?:-{type_words})*-(.+)$', link_path)
        if location_match:
            city = location_match.group(1).replace('-', ' ').title()
        else:
            city = 'Luxembourg'
        self.assertEqual(city, 'Esch Sur Alzette', "Ville depuis regex Unicorn")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🧪 TEST PRICE/ROOM/SURFACE PARSING")
    print("="*80 + "\n")
    unittest.main(verbosity=2)
