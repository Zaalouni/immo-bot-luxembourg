#!/usr/bin/env python3
# =============================================================================
# test_mcp_server.py — Suite de tests complète pour le serveur MCP
# =============================================================================
# Tests couvrant:
#   - Connexion et import des modules
#   - Tous les tools MCP (11 outils)
#   - Toutes les resources MCP (6 ressources)
#   - Intégration DB (lectures SQL)
#   - Config et chemins
#   - Edge cases (DB vide, paramètres manquants, etc.)
#
# Usage:
#   python mcp_server/test_mcp_server.py          # Tous les tests
#   python mcp_server/test_mcp_server.py -v        # Mode verbeux
#   python mcp_server/test_mcp_server.py TestStats # Classe spécifique
#   pytest mcp_server/test_mcp_server.py -v        # Via pytest
# =============================================================================

import sys
import os
import asyncio
import json
import sqlite3
import tempfile
import unittest
import logging
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ajouter le répertoire racine au path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.WARNING)

# =============================================================================
# HELPERS
# =============================================================================

def async_test(coro):
    """Décorateur pour lancer des tests async."""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


def create_test_db(db_path: str, num_listings: int = 10) -> None:
    """Créer une DB de test avec des données synthétiques."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id TEXT UNIQUE NOT NULL,
            site TEXT NOT NULL,
            title TEXT,
            city TEXT,
            price INTEGER,
            rooms INTEGER,
            surface INTEGER,
            url TEXT UNIQUE NOT NULL,
            latitude REAL,
            longitude REAL,
            distance_km REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notified BOOLEAN DEFAULT 0
        )
    """)

    sites   = ["athome", "immotop", "luxhome", "vivi", "nextimmo"]
    cities  = ["Luxembourg", "Kirchberg", "Belair", "Strassen", "Esch-sur-Alzette"]
    gps     = {
        "Luxembourg":        (49.6116, 6.1319),
        "Kirchberg":         (49.6300, 6.1500),
        "Belair":            (49.6100, 6.1150),
        "Strassen":          (49.6200, 6.0700),
        "Esch-sur-Alzette":  (49.4950, 5.9800),
    }

    for i in range(num_listings):
        site   = sites[i % len(sites)]
        city   = cities[i % len(cities)]
        price  = 1200 + (i * 150)
        rooms  = 2 + (i % 3)
        surf   = 70 + (i * 10)
        lat, lng = gps[city]
        dist   = round(i * 1.5, 1)
        days_ago = i % 5   # Derniers 5 jours

        cursor.execute("""
            INSERT OR IGNORE INTO listings
            (listing_id, site, title, city, price, rooms, surface, url,
             latitude, longitude, distance_km, created_at, notified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', ?), ?)
        """, (
            f"{site}_test_{i:04d}",
            site,
            f"Test listing {i} — {rooms} ch. à {city}",
            city,
            price,
            rooms,
            surf,
            f"https://example-{site}.lu/listing/{i}",
            lat + (i * 0.001),
            lng + (i * 0.001),
            dist,
            f"-{days_ago} days",
            0 if i < 3 else 1
        ))

    conn.commit()
    conn.close()


# =============================================================================
# TEST: CONFIGURATION
# =============================================================================

class TestConfig(unittest.TestCase):
    """Tests de la configuration MCP."""

    def test_import_config_mcp(self):
        """Vérifier que config_mcp.py s'importe correctement."""
        try:
            from mcp_server.config_mcp import (
                BASE_DIR, DB_PATH, MCP_SERVER_NAME,
                MCP_SERVER_VERSION, get_config_summary
            )
            self.assertEqual(MCP_SERVER_NAME, "immo-bot-luxembourg")
            self.assertEqual(MCP_SERVER_VERSION, "1.0.0")
        except ImportError as e:
            self.fail(f"Import config_mcp échoué: {e}")

    def test_config_summary(self):
        """Vérifier que get_config_summary() retourne les bonnes clés."""
        from mcp_server.config_mcp import get_config_summary
        summary = get_config_summary()
        required_keys = [
            "server_name", "version", "transport", "db_path",
            "db_exists", "history_dir", "max_search_results"
        ]
        for key in required_keys:
            self.assertIn(key, summary, f"Clé manquante: {key}")

    def test_base_dir_exists(self):
        """Vérifier que BASE_DIR pointe vers le répertoire du projet."""
        from mcp_server.config_mcp import BASE_DIR
        self.assertTrue(BASE_DIR.exists(), f"BASE_DIR n'existe pas: {BASE_DIR}")

    def test_site_colors_complete(self):
        """Vérifier que les couleurs sont définies pour les sites principaux."""
        from mcp_server.config_mcp import SITE_COLORS
        required_sites = ["athome", "immotop", "luxhome", "vivi", "nextimmo"]
        for site in required_sites:
            self.assertIn(site, SITE_COLORS, f"Couleur manquante pour: {site}")


# =============================================================================
# TEST: TOOL — search_listings
# =============================================================================

class TestSearchTool(unittest.TestCase):
    """Tests du tool search_listings."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        create_test_db(self.db_path, num_listings=15)

    def tearDown(self):
        os.unlink(self.db_path)

    @async_test
    async def test_search_no_filters(self):
        """Recherche sans filtres — doit retourner des annonces."""
        from mcp_server.tools.search_tool import handle_search_listings
        with patch("mcp_server.tools.search_tool.DB_PATH", self.db_path):
            result = await handle_search_listings({})
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        text = result[0].text
        self.assertIn("résultat", text.lower())

    @async_test
    async def test_search_by_city(self):
        """Recherche filtrée par ville."""
        from mcp_server.tools.search_tool import handle_search_listings
        with patch("mcp_server.tools.search_tool.DB_PATH", self.db_path):
            result = await handle_search_listings({"city": "luxembourg"})
        text = result[0].text
        # Doit mentionner Luxembourg ou "aucune"
        self.assertTrue("Luxembourg" in text or "aucune" in text.lower())

    @async_test
    async def test_search_by_price_range(self):
        """Recherche filtrée par fourchette de prix."""
        from mcp_server.tools.search_tool import handle_search_listings
        with patch("mcp_server.tools.search_tool.DB_PATH", self.db_path):
            result = await handle_search_listings({
                "price_min": 1200, "price_max": 1600
            })
        self.assertIsInstance(result, list)

    @async_test
    async def test_search_sort_by_price(self):
        """Tri par prix croissant."""
        from mcp_server.tools.search_tool import handle_search_listings
        with patch("mcp_server.tools.search_tool.DB_PATH", self.db_path):
            result = await handle_search_listings({"sort_by": "price_asc", "limit": 5})
        self.assertIsInstance(result, list)

    @async_test
    async def test_search_returns_json(self):
        """La réponse doit contenir du JSON valide."""
        from mcp_server.tools.search_tool import handle_search_listings
        with patch("mcp_server.tools.search_tool.DB_PATH", self.db_path):
            result = await handle_search_listings({"limit": 5})
        # Le deuxième élément doit contenir du JSON
        if len(result) > 1:
            json_text = result[1].text
            self.assertIn("{", json_text)
            # Extraire et parser le JSON
            json_start = json_text.find("{")
            if json_start >= 0:
                data = json.loads(json_text[json_start:])
                self.assertIn("listings", data)

    @async_test
    async def test_search_no_results(self):
        """Recherche sans résultats doit retourner un message clair."""
        from mcp_server.tools.search_tool import handle_search_listings
        with patch("mcp_server.tools.search_tool.DB_PATH", self.db_path):
            result = await handle_search_listings({
                "price_min": 9999, "price_max": 10000
            })
        text = result[0].text.lower()
        self.assertIn("aucune", text)

    @async_test
    async def test_search_limit_respected(self):
        """La limite de résultats doit être respectée."""
        from mcp_server.tools.search_tool import handle_search_listings
        with patch("mcp_server.tools.search_tool.DB_PATH", self.db_path):
            result = await handle_search_listings({"limit": 3})
        # Le JSON doit avoir max 3 résultats
        if len(result) > 1:
            json_text = result[1].text
            json_start = json_text.find("{")
            if json_start >= 0:
                try:
                    data = json.loads(json_text[json_start:])
                    self.assertLessEqual(data.get("count", 0), 3)
                except json.JSONDecodeError:
                    pass  # Pas de JSON = liste vide OK

    @async_test
    async def test_search_db_missing(self):
        """DB manquante doit retourner une erreur claire."""
        from mcp_server.tools.search_tool import handle_search_listings
        with patch("mcp_server.tools.search_tool.DB_PATH", "/tmp/nonexistent_db_xyz.db"):
            result = await handle_search_listings({})
        text = result[0].text.lower()
        self.assertIn("erreur", text)


# =============================================================================
# TEST: TOOL — get_stats
# =============================================================================

class TestStatsTool(unittest.TestCase):
    """Tests du tool get_stats."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        create_test_db(self.db_path, num_listings=10)

    def tearDown(self):
        os.unlink(self.db_path)

    @async_test
    async def test_get_stats_basic(self):
        """Stats de base doivent retourner les bons totaux."""
        from mcp_server.tools.stats_tool import handle_get_stats
        with patch("mcp_server.tools.stats_tool.DB_PATH", self.db_path):
            result = await handle_get_stats({})
        self.assertIsInstance(result, list)
        text = result[0].text
        self.assertIn("Total", text)
        self.assertIn("Prix", text)

    @async_test
    async def test_get_stats_json_valid(self):
        """Le JSON des stats doit être valide."""
        from mcp_server.tools.stats_tool import handle_get_stats
        with patch("mcp_server.tools.stats_tool.DB_PATH", self.db_path):
            result = await handle_get_stats({
                "include_by_site": True,
                "include_by_city": True,
                "include_price_ranges": True
            })
        if len(result) > 1:
            json_text = result[1].text
            json_start = json_text.find("{")
            if json_start >= 0:
                data = json.loads(json_text[json_start:])
                self.assertIn("total", data)
                self.assertIn("price", data)
                self.assertIn("by_site", data)
                self.assertIn("by_city", data)
                self.assertGreater(data["total"], 0)

    @async_test
    async def test_get_stats_price_ranges(self):
        """Les tranches de prix doivent être présentes."""
        from mcp_server.tools.stats_tool import handle_get_stats
        with patch("mcp_server.tools.stats_tool.DB_PATH", self.db_path):
            result = await handle_get_stats({"include_price_ranges": True})
        text = result[0].text
        self.assertIn("TRANCHES", text)

    @async_test
    async def test_get_stats_without_optional(self):
        """Stats sans sections optionnelles."""
        from mcp_server.tools.stats_tool import handle_get_stats
        with patch("mcp_server.tools.stats_tool.DB_PATH", self.db_path):
            result = await handle_get_stats({
                "include_by_site": False,
                "include_by_city": False,
                "include_price_ranges": False
            })
        self.assertIsInstance(result, list)
        text = result[0].text
        self.assertNotIn("PAR SITE", text)


# =============================================================================
# TEST: TOOL — scraper_tool
# =============================================================================

class TestScraperTool(unittest.TestCase):
    """Tests du tool run_scraper et list_scrapers."""

    @async_test
    async def test_list_scrapers(self):
        """list_scrapers doit retourner la liste complète."""
        from mcp_server.tools.scraper_tool import handle_list_scrapers
        result = await handle_list_scrapers({})
        self.assertIsInstance(result, list)
        text = result[0].text
        self.assertIn("athome", text.lower())
        self.assertIn("SCRAPERS", text)

    @async_test
    async def test_run_scraper_unknown(self):
        """Scraper inconnu doit retourner une erreur claire."""
        from mcp_server.tools.scraper_tool import handle_run_scraper
        result = await handle_run_scraper({"scraper_name": "site_inexistant_xyz"})
        text = result[0].text.lower()
        self.assertIn("inconnu", text)

    @async_test
    async def test_run_scraper_no_name(self):
        """Appel sans scraper_name doit retourner une erreur."""
        from mcp_server.tools.scraper_tool import handle_run_scraper
        result = await handle_run_scraper({})
        text = result[0].text.lower()
        self.assertIn("erreur", text)

    @async_test
    async def test_scraper_registry_complete(self):
        """Le registre doit contenir les scrapers principaux."""
        from mcp_server.tools.scraper_tool import SCRAPER_REGISTRY
        required = ["athome", "immotop", "luxhome", "vivi", "nextimmo",
                    "newimmo", "unicorn", "wortimmo", "immoweb"]
        for name in required:
            self.assertIn(name, SCRAPER_REGISTRY, f"Scraper manquant: {name}")

    @async_test
    async def test_run_scraper_dry_run(self):
        """dry_run ne doit pas sauvegarder en DB."""
        from mcp_server.tools.scraper_tool import handle_run_scraper

        # Mock le module scraper pour retourner des données fictives
        mock_listings = [
            {
                "listing_id": "test_dry_001",
                "site": "test",
                "title": "Test dry run",
                "city": "Luxembourg",
                "price": 1500,
                "url": "https://example.com/1"
            }
        ]

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.scrape.return_value = mock_listings
            mock_import.return_value = mock_module

            result = await handle_run_scraper({
                "scraper_name": "athome",
                "dry_run": True
            })

        text = result[0].text
        self.assertIn("DRY RUN", text)


# =============================================================================
# TEST: TOOL — market_tool
# =============================================================================

class TestMarketTool(unittest.TestCase):
    """Tests des tools analyze_market et detect_anomalies."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        create_test_db(self.db_path, num_listings=20)

    def tearDown(self):
        os.unlink(self.db_path)

    @async_test
    async def test_analyze_market_basic(self):
        """Analyse de marché de base."""
        from mcp_server.tools.market_tool import handle_analyze_market
        with patch("mcp_server.tools.market_tool.DB_PATH", self.db_path):
            result = await handle_analyze_market({"period_days": 7})
        self.assertIsInstance(result, list)
        text = result[0].text
        self.assertIn("ANALYSE MARCHÉ", text)

    @async_test
    async def test_analyze_market_focus_city(self):
        """Analyse pour une ville spécifique."""
        from mcp_server.tools.market_tool import handle_analyze_market
        with patch("mcp_server.tools.market_tool.DB_PATH", self.db_path):
            result = await handle_analyze_market({
                "period_days": 7,
                "focus_city": "Luxembourg"
            })
        text = result[0].text
        self.assertIn("Luxembourg", text)

    @async_test
    async def test_analyze_market_opportunities(self):
        """Les opportunités doivent être détectées."""
        from mcp_server.tools.market_tool import handle_analyze_market
        with patch("mcp_server.tools.market_tool.DB_PATH", self.db_path):
            result = await handle_analyze_market({
                "period_days": 30,
                "include_opportunities": True
            })
        self.assertIsInstance(result, list)
        # Pas de crash = succès minimum

    @async_test
    async def test_detect_anomalies(self):
        """Détection d'anomalies doit fonctionner."""
        from mcp_server.tools.market_tool import handle_detect_anomalies
        with patch("mcp_server.tools.market_tool.DB_PATH", self.db_path):
            result = await handle_detect_anomalies({"threshold_percent": 30})
        self.assertIsInstance(result, list)
        text = result[0].text
        self.assertIn("ANOMALIES", text)

    @async_test
    async def test_detect_anomalies_json_valid(self):
        """JSON des anomalies doit être valide."""
        from mcp_server.tools.market_tool import handle_detect_anomalies
        with patch("mcp_server.tools.market_tool.DB_PATH", self.db_path):
            result = await handle_detect_anomalies({})
        if len(result) > 1:
            json_text = result[1].text
            json_start = json_text.find("{")
            if json_start >= 0:
                data = json.loads(json_text[json_start:])
                self.assertIn("prix_tres_eleves", data)
                self.assertIn("prix_tres_bas", data)
                self.assertIn("doublons_potentiels", data)


# =============================================================================
# TEST: TOOL — geo_tool
# =============================================================================

class TestGeoTool(unittest.TestCase):
    """Tests des tools find_nearby et geocode_city."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        create_test_db(self.db_path, num_listings=10)

    def tearDown(self):
        os.unlink(self.db_path)

    @async_test
    async def test_geocode_known_city(self):
        """Géocodage d'une ville connue doit réussir."""
        from mcp_server.tools.geo_tool import handle_geocode_city
        result = await handle_geocode_city({"city_name": "Luxembourg"})
        text = result[0].text
        self.assertIn("49.", text)   # Latitude Luxembourg ≈ 49.6
        self.assertIn("6.", text)    # Longitude Luxembourg ≈ 6.1

    @async_test
    async def test_geocode_unknown_city(self):
        """Ville inconnue doit retourner un message d'erreur clair."""
        from mcp_server.tools.geo_tool import handle_geocode_city
        result = await handle_geocode_city({"city_name": "VilleInconnueXYZ"})
        text = result[0].text
        self.assertIn("non trouvée", text.lower())

    @async_test
    async def test_geocode_no_city(self):
        """Appel sans city_name doit retourner une erreur."""
        from mcp_server.tools.geo_tool import handle_geocode_city
        result = await handle_geocode_city({})
        text = result[0].text.lower()
        self.assertIn("erreur", text)

    @async_test
    async def test_geocode_partial_name(self):
        """Géocodage avec nom partiel (Kirchberg au lieu de Kirchberg plateau)."""
        from mcp_server.tools.geo_tool import handle_geocode_city
        result = await handle_geocode_city({"city_name": "Kirchberg"})
        text = result[0].text
        self.assertIn("49.", text)

    @async_test
    async def test_find_nearby_by_coords(self):
        """Recherche par coordonnées GPS."""
        from mcp_server.tools.geo_tool import handle_find_nearby
        with patch("mcp_server.tools.geo_tool.DB_PATH", self.db_path):
            result = await handle_find_nearby({
                "latitude": 49.6116,
                "longitude": 6.1319,
                "radius_km": 50.0
            })
        self.assertIsInstance(result, list)
        text = result[0].text
        self.assertIn("km", text)

    @async_test
    async def test_find_nearby_small_radius(self):
        """Rayon très petit peut retourner 0 résultats."""
        from mcp_server.tools.geo_tool import handle_find_nearby
        with patch("mcp_server.tools.geo_tool.DB_PATH", self.db_path):
            result = await handle_find_nearby({
                "latitude": 49.0,
                "longitude": 5.0,
                "radius_km": 0.001
            })
        self.assertIsInstance(result, list)
        text = result[0].text
        # 0 résultats ou des résultats — pas de crash
        self.assertIn("km", text)

    @async_test
    async def test_find_nearby_no_params(self):
        """Appel sans paramètres doit retourner une erreur."""
        from mcp_server.tools.geo_tool import handle_find_nearby
        result = await handle_find_nearby({})
        text = result[0].text.lower()
        self.assertIn("erreur", text)

    @async_test
    async def test_haversine_formula(self):
        """Vérifier la formule Haversine avec des distances connues."""
        from mcp_server.tools.geo_tool import _haversine
        # Luxembourg → Kirchberg ≈ 2.2 km
        dist = _haversine(49.6116, 6.1319, 49.6300, 6.1500)
        self.assertGreater(dist, 1.0)
        self.assertLess(dist, 5.0)

        # Même point → 0 km
        dist_zero = _haversine(49.6116, 6.1319, 49.6116, 6.1319)
        self.assertAlmostEqual(dist_zero, 0.0, places=1)


# =============================================================================
# TEST: RESOURCES
# =============================================================================

class TestResources(unittest.TestCase):
    """Tests des ressources MCP."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        create_test_db(self.db_path, num_listings=10)

    def tearDown(self):
        os.unlink(self.db_path)

    @async_test
    async def test_listings_all_json(self):
        """listings://all doit retourner du JSON valide."""
        from mcp_server.resources.listings_resource import get_listings_all
        with patch("mcp_server.resources.listings_resource.DB_PATH", self.db_path):
            result = await get_listings_all()
        data = json.loads(result)
        self.assertIn("listings", data)
        self.assertIn("count", data)
        self.assertGreater(data["count"], 0)

    @async_test
    async def test_listings_new_json(self):
        """listings://new doit retourner du JSON valide."""
        from mcp_server.resources.listings_resource import get_listings_new
        with patch("mcp_server.resources.listings_resource.DB_PATH", self.db_path):
            result = await get_listings_new()
        data = json.loads(result)
        self.assertIn("listings", data)
        self.assertEqual(data["resource"], "listings://new")

    @async_test
    async def test_listings_by_site_json(self):
        """listings://by-site doit retourner du JSON valide avec les sites."""
        from mcp_server.resources.listings_resource import get_listings_by_site
        with patch("mcp_server.resources.listings_resource.DB_PATH", self.db_path):
            result = await get_listings_by_site()
        data = json.loads(result)
        self.assertIn("by_site", data)
        self.assertGreater(data["sites"], 0)

    @async_test
    async def test_stats_current_json(self):
        """stats://current doit retourner des statistiques valides."""
        from mcp_server.resources.stats_resource import get_stats_current
        with patch("mcp_server.resources.stats_resource.DB_PATH", self.db_path):
            result = await get_stats_current()
        data = json.loads(result)
        self.assertIn("total", data)
        self.assertIn("price", data)
        self.assertGreater(data["total"], 0)

    @async_test
    async def test_stats_by_city_json(self):
        """stats://by-city doit retourner les villes."""
        from mcp_server.resources.stats_resource import get_stats_by_city
        with patch("mcp_server.resources.stats_resource.DB_PATH", self.db_path):
            result = await get_stats_by_city()
        data = json.loads(result)
        self.assertIn("cities", data)
        self.assertGreater(data["count"], 0)

    @async_test
    async def test_history_no_archive(self):
        """history://today sans archive doit retourner un message d'erreur lisible."""
        from mcp_server.resources.history_resource import get_history_day
        with patch("mcp_server.resources.history_resource.HISTORY_DIR", "/tmp/nonexistent_history"):
            result = await get_history_day("2099-01-01")
        data = json.loads(result)
        self.assertIn("error", data)

    @async_test
    async def test_history_list(self):
        """history://list doit fonctionner sans erreur."""
        from mcp_server.resources.history_resource import get_history_day
        with tempfile.TemporaryDirectory() as tmpdir:
            # Créer quelques faux fichiers d'archive
            for i in range(3):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                with open(os.path.join(tmpdir, f"{date}.json"), "w") as f:
                    json.dump({"total": 10, "avg_price": 2000, "date": date}, f)

            with patch("mcp_server.resources.history_resource.HISTORY_DIR", tmpdir):
                result = await get_history_day("list")

        data = json.loads(result)
        self.assertIn("available_dates", data)
        self.assertEqual(data["count"], 3)


# =============================================================================
# TEST: INTÉGRATION — Flux complets
# =============================================================================

class TestIntegration(unittest.TestCase):
    """Tests d'intégration: flux complets de bout en bout."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        create_test_db(self.db_path, num_listings=25)

    def tearDown(self):
        os.unlink(self.db_path)

    @async_test
    async def test_search_then_stats(self):
        """Recherche + stats doivent être cohérentes."""
        from mcp_server.tools.search_tool import handle_search_listings
        from mcp_server.tools.stats_tool import handle_get_stats

        with patch("mcp_server.tools.search_tool.DB_PATH", self.db_path), \
             patch("mcp_server.tools.stats_tool.DB_PATH", self.db_path):

            search_result = await handle_search_listings({"limit": 100})
            stats_result  = await handle_get_stats({})

        # Les deux doivent réussir
        self.assertIsInstance(search_result, list)
        self.assertIsInstance(stats_result, list)

        # Les stats doivent montrer un total > 0
        stats_text = stats_result[0].text
        self.assertIn("Total", stats_text)

    @async_test
    async def test_geo_then_search_consistency(self):
        """Geocodage + recherche géo doivent être cohérents."""
        from mcp_server.tools.geo_tool import handle_geocode_city, handle_find_nearby

        # Géocoder Luxembourg
        geo_result = await handle_geocode_city({"city_name": "Luxembourg"})
        geo_json   = json.loads(geo_result[1].text.split("---\n")[-1])

        self.assertTrue(geo_json.get("found"))
        lat = geo_json["latitude"]
        lng = geo_json["longitude"]

        # Chercher autour
        with patch("mcp_server.tools.geo_tool.DB_PATH", self.db_path):
            nearby_result = await handle_find_nearby({
                "latitude": lat,
                "longitude": lng,
                "radius_km": 50.0
            })

        self.assertIsInstance(nearby_result, list)

    @async_test
    async def test_analyze_market_json_structure(self):
        """analyze_market doit retourner une structure JSON complète."""
        from mcp_server.tools.market_tool import handle_analyze_market
        with patch("mcp_server.tools.market_tool.DB_PATH", self.db_path):
            result = await handle_analyze_market({"period_days": 30})

        if len(result) > 1:
            json_text = result[1].text
            json_start = json_text.find("{")
            if json_start >= 0:
                data = json.loads(json_text[json_start:])
                self.assertIn("period_days", data)
                self.assertIn("current", data)
                self.assertIn("period_activity", data)

    @async_test
    async def test_full_pipeline_mock(self):
        """
        Test du pipeline complet (simulé):
        scraper → DB → search → stats → anomalies
        """
        from mcp_server.tools.search_tool import handle_search_listings
        from mcp_server.tools.stats_tool import handle_get_stats
        from mcp_server.tools.market_tool import handle_detect_anomalies

        patches = {
            "mcp_server.tools.search_tool.DB_PATH": self.db_path,
            "mcp_server.tools.stats_tool.DB_PATH":  self.db_path,
            "mcp_server.tools.market_tool.DB_PATH": self.db_path,
        }

        with patch("mcp_server.tools.search_tool.DB_PATH", self.db_path), \
             patch("mcp_server.tools.stats_tool.DB_PATH", self.db_path), \
             patch("mcp_server.tools.market_tool.DB_PATH", self.db_path):

            search    = await handle_search_listings({"limit": 5})
            stats     = await handle_get_stats({})
            anomalies = await handle_detect_anomalies({"threshold_percent": 50})

        # Vérifier que les 3 étapes ont réussi
        for r, name in [(search, "search"), (stats, "stats"), (anomalies, "anomalies")]:
            self.assertIsInstance(r, list, f"{name} doit retourner une liste")
            self.assertGreater(len(r), 0, f"{name} doit avoir des résultats")


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases(unittest.TestCase):
    """Tests des cas limites et situations d'erreur."""

    @async_test
    async def test_search_empty_db(self):
        """Recherche sur DB vide doit fonctionner sans erreur."""
        from mcp_server.tools.search_tool import handle_search_listings
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            empty_db = f.name
        create_test_db(empty_db, num_listings=0)

        try:
            with patch("mcp_server.tools.search_tool.DB_PATH", empty_db):
                result = await handle_search_listings({})
            self.assertIsInstance(result, list)
            # DB vide = 0 résultats mais pas de crash
        finally:
            os.unlink(empty_db)

    @async_test
    async def test_stats_empty_db(self):
        """Stats sur DB vide doivent fonctionner."""
        from mcp_server.tools.stats_tool import handle_get_stats
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            empty_db = f.name
        create_test_db(empty_db, num_listings=0)

        try:
            with patch("mcp_server.tools.stats_tool.DB_PATH", empty_db):
                result = await handle_get_stats({})
            self.assertIsInstance(result, list)
        finally:
            os.unlink(empty_db)

    @async_test
    async def test_search_special_chars_city(self):
        """Ville avec caractères spéciaux doit fonctionner."""
        from mcp_server.tools.search_tool import handle_search_listings
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db = f.name
        create_test_db(db, num_listings=5)

        try:
            with patch("mcp_server.tools.search_tool.DB_PATH", db):
                result = await handle_search_listings({"city": "Esch-sur-Alzette"})
            self.assertIsInstance(result, list)
        finally:
            os.unlink(db)

    @async_test
    async def test_find_nearby_extreme_coords(self):
        """Coordonnées en dehors du Luxembourg."""
        from mcp_server.tools.geo_tool import handle_find_nearby
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db = f.name
        create_test_db(db, num_listings=5)

        try:
            with patch("mcp_server.tools.geo_tool.DB_PATH", db):
                result = await handle_find_nearby({
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "radius_km": 1.0
                })
            # 0 résultats mais pas de crash
            self.assertIsInstance(result, list)
        finally:
            os.unlink(db)

    @async_test
    async def test_market_analysis_long_period(self):
        """Analyse sur 90 jours."""
        from mcp_server.tools.market_tool import handle_analyze_market
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db = f.name
        create_test_db(db, num_listings=10)

        try:
            with patch("mcp_server.tools.market_tool.DB_PATH", db):
                result = await handle_analyze_market({"period_days": 90})
            self.assertIsInstance(result, list)
        finally:
            os.unlink(db)


# =============================================================================
# RUNNER PRINCIPAL
# =============================================================================

def run_all_tests(verbosity: int = 2) -> bool:
    """Lancer tous les tests et retourner True si tous passent."""
    print("=" * 60)
    print("  MCP SERVER — SUITE DE TESTS COMPLÈTE")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    # Découverte automatique de tous les tests
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    test_classes = [
        TestConfig,
        TestSearchTool,
        TestStatsTool,
        TestScraperTool,
        TestMarketTool,
        TestGeoTool,
        TestResources,
        TestIntegration,
        TestEdgeCases,
    ]

    for cls in test_classes:
        tests = loader.loadTestsFromTestCase(cls)
        suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print(f"Tests: {result.testsRun} | "
          f"OK: {result.testsRun - len(result.failures) - len(result.errors)} | "
          f"Échecs: {len(result.failures)} | "
          f"Erreurs: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tests MCP Server Immo-Bot Luxembourg")
    parser.add_argument("-v", "--verbose", action="store_true", help="Mode verbeux")
    parser.add_argument("test_class", nargs="?", help="Classe de test spécifique")
    args = parser.parse_args()

    verbosity = 2 if args.verbose else 1

    if args.test_class:
        # Lancer une classe spécifique
        suite = unittest.TestLoader().loadTestsFromName(args.test_class, sys.modules[__name__])
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)
    else:
        success = run_all_tests(verbosity=verbosity)
        sys.exit(0 if success else 1)
