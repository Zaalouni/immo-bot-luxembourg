"""
Regression Testing Suite for Dashboard Generator
Tests core functions, filters, exports, and data integrity
"""
import unittest
import os
import json
from datetime import datetime
from dashboard_generator import (
    read_listings, calc_stats, calculate_price_anomalies,
    calculate_market_stats_detailed, calculate_time_ago
)


class TestDashboardCore(unittest.TestCase):
    """Test core data processing functions"""

    @classmethod
    def setUpClass(cls):
        """Load test data once for all tests"""
        cls.listings = read_listings()
        cls.stats = calc_stats(cls.listings)
        cls.anomalies = calculate_price_anomalies(cls.listings, cls.stats)
        cls.market_stats = calculate_market_stats_detailed(cls.listings, cls.stats)

    def test_read_listings_returns_list(self):
        """Verify listings is a list"""
        self.assertIsInstance(self.listings, list)
        self.assertGreater(len(self.listings), 0, "Must have at least one listing")

    def test_read_listings_has_required_keys(self):
        """Verify each listing has all required keys"""
        required_keys = [
            'listing_id', 'site', 'title', 'city', 'price', 'rooms',
            'surface', 'url', 'latitude', 'longitude', 'published_at',
            'price_m2', 'time_ago'
        ]
        for listing in self.listings[:5]:  # Check first 5
            for key in required_keys:
                self.assertIn(key, listing, f"Missing key '{key}' in listing {listing.get('listing_id')}")

    def test_read_listings_price_is_positive(self):
        """Verify all prices are positive numbers"""
        for listing in self.listings[:10]:
            self.assertIsInstance(listing['price'], (int, float))
            self.assertGreater(listing['price'], 0, f"Price must be positive: {listing['listing_id']}")

    def test_read_listings_surface_is_non_negative(self):
        """Verify surface is non-negative"""
        for listing in self.listings[:10]:
            if listing['surface']:
                self.assertGreaterEqual(listing['surface'], 0)

    def test_calc_stats_has_required_keys(self):
        """Verify stats object has all required keys"""
        required_keys = ['total', 'avg_price', 'min_price', 'max_price', 'avg_surface', 'by_city', 'by_site']
        for key in required_keys:
            self.assertIn(key, self.stats, f"Missing key '{key}' in stats")

    def test_calc_stats_total_is_positive(self):
        """Verify total is positive"""
        self.assertGreater(self.stats['total'], 0)

    def test_calc_stats_prices_are_logical(self):
        """Verify min <= avg <= max"""
        self.assertLessEqual(self.stats['min_price'], self.stats['avg_price'])
        self.assertLessEqual(self.stats['avg_price'], self.stats['max_price'])

    def test_calc_stats_by_city_completeness(self):
        """Verify all cities are in stats"""
        cities_in_listings = set(l['city'] for l in self.listings)
        cities_in_stats = set(self.stats['by_city'].keys())
        self.assertEqual(cities_in_listings, cities_in_stats)

    def test_calc_stats_by_site_count_matches(self):
        """Verify site counts add up to total"""
        site_total = sum(self.stats['by_site'].values())
        self.assertEqual(site_total, self.stats['total'])

    def test_time_ago_is_string(self):
        """Verify time_ago is a readable string"""
        for listing in self.listings[:5]:
            self.assertIsInstance(listing['time_ago'], str)
            self.assertGreater(len(listing['time_ago']), 0)

    def test_price_m2_calculated(self):
        """Verify price_m2 is calculated for all listings"""
        for listing in self.listings[:10]:
            if listing['surface'] and listing['surface'] > 0:
                self.assertIsInstance(listing['price_m2'], (int, float))
                self.assertGreater(listing['price_m2'], 0)

    def test_anomalies_flags_are_valid(self):
        """Verify anomaly flags are one of: HIGH, GOOD_DEAL, None"""
        valid_flags = {None, 'HIGH', 'GOOD_DEAL'}
        for listing in self.listings[:20]:
            flag = listing.get('price_anomaly')
            self.assertIn(flag, valid_flags, f"Invalid anomaly flag: {flag}")

    def test_market_stats_per_city_structure(self):
        """Verify each city has required stats"""
        required_keys = ['count', 'avg_price', 'median_price', 'min_price', 'max_price', 'avg_price_m2']
        for city in list(self.market_stats.keys())[:3]:  # Check first 3 cities
            stats = self.market_stats[city]
            for key in required_keys:
                self.assertIn(key, stats, f"Missing '{key}' in city {city} stats")

    def test_market_stats_count_is_positive(self):
        """Verify city count is positive"""
        for city in list(self.market_stats.keys())[:3]:
            self.assertGreater(self.market_stats[city]['count'], 0)


class TestDashboardFilters(unittest.TestCase):
    """Test filter logic"""

    @classmethod
    def setUpClass(cls):
        """Load test data"""
        cls.listings = read_listings()

    def test_filter_by_city(self):
        """Test filtering by city"""
        if not self.listings:
            self.skipTest("No listings to test")
        city = self.listings[0]['city']
        filtered = [l for l in self.listings if l['city'] == city]
        self.assertGreater(len(filtered), 0)
        for l in filtered:
            self.assertEqual(l['city'], city)

    def test_filter_by_price_range(self):
        """Test price range filter"""
        min_p, max_p = 1000, 2000
        filtered = [l for l in self.listings if min_p <= l['price'] <= max_p]
        for l in filtered:
            self.assertGreaterEqual(l['price'], min_p)
            self.assertLessEqual(l['price'], max_p)

    def test_filter_by_site(self):
        """Test site filter"""
        sites = set(l['site'] for l in self.listings)
        if not sites:
            self.skipTest("No sites to test")
        test_site = list(sites)[0]
        filtered = [l for l in self.listings if l['site'] == test_site]
        self.assertGreater(len(filtered), 0)

    def test_filter_by_surface_minimum(self):
        """Test surface minimum filter"""
        min_surface = 50
        filtered = [l for l in self.listings if l['surface'] >= min_surface]
        for l in filtered:
            self.assertGreaterEqual(l['surface'], min_surface)


class TestDashboardExports(unittest.TestCase):
    """Test that export files are generated correctly"""

    def test_listings_json_exists(self):
        """Verify listings.json exists"""
        path = 'dashboards/data/listings.json'
        self.assertTrue(os.path.exists(path), f"File missing: {path}")

    def test_listings_json_is_valid(self):
        """Verify listings.json is valid JSON"""
        path = 'dashboards/data/listings.json'
        if not os.path.exists(path):
            self.skipTest("listings.json not found")
        with open(path) as f:
            data = json.load(f)
            self.assertIsInstance(data, list)
            self.assertGreater(len(data), 0)

    def test_stats_js_exists(self):
        """Verify stats.js exists"""
        path = 'dashboards/data/stats.js'
        self.assertTrue(os.path.exists(path), f"File missing: {path}")

    def test_anomalies_js_exists(self):
        """Verify anomalies.js exists"""
        path = 'dashboards/data/anomalies.js'
        self.assertTrue(os.path.exists(path), f"File missing: {path}")

    def test_market_stats_js_exists(self):
        """Verify market-stats.js exists"""
        path = 'dashboards/data/market-stats.js'
        self.assertTrue(os.path.exists(path), f"File missing: {path}")

    def test_dashboard_html_exists(self):
        """Verify dashboard HTML files exist"""
        files = [
            'dashboards/index.html',
            'dashboards/new-listings.html',
            'dashboards/anomalies.html',
            'dashboards/stats-by-city.html'
        ]
        for f in files:
            self.assertTrue(os.path.exists(f), f"Dashboard file missing: {f}")

    def test_manifest_json_exists(self):
        """Verify PWA manifest exists"""
        path = 'dashboards/manifest.json'
        self.assertTrue(os.path.exists(path), f"Manifest missing: {path}")


class TestDataIntegrity(unittest.TestCase):
    """Test overall data integrity"""

    @classmethod
    def setUpClass(cls):
        """Load test data"""
        cls.listings = read_listings()
        cls.stats = calc_stats(cls.listings)

    def test_no_duplicate_listing_ids(self):
        """Verify no duplicate listing IDs"""
        listing_ids = [l['listing_id'] for l in self.listings]
        unique_ids = set(listing_ids)
        self.assertEqual(len(listing_ids), len(unique_ids), "Found duplicate listing IDs")

    def test_all_urls_are_valid(self):
        """Verify all URLs start with http"""
        for listing in self.listings[:10]:
            self.assertTrue(listing['url'].startswith('http'), f"Invalid URL: {listing['url']}")

    def test_cities_not_empty(self):
        """Verify no empty city names"""
        for listing in self.listings:
            self.assertIsNotNone(listing['city'])
            self.assertGreater(len(listing['city']), 0)

    def test_published_at_is_valid_datetime(self):
        """Verify published_at is a valid datetime string"""
        for listing in self.listings[:10]:
            try:
                datetime.fromisoformat(listing['published_at'].replace('Z', '+00:00'))
            except ValueError:
                self.fail(f"Invalid datetime format: {listing['published_at']}")

    def test_stats_total_equals_listing_count(self):
        """Verify stats.total matches listing count"""
        self.assertEqual(self.stats['total'], len(self.listings))

    def test_avg_price_is_in_range(self):
        """Verify avg_price is between min and max"""
        self.assertGreaterEqual(self.stats['avg_price'], self.stats['min_price'])
        self.assertLessEqual(self.stats['avg_price'], self.stats['max_price'])

    def test_avg_surface_is_reasonable(self):
        """Verify avg_surface is reasonable (> 0)"""
        self.assertGreater(self.stats['avg_surface'], 0)


if __name__ == '__main__':
    unittest.main()
