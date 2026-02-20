# tests/test_database.py — Tests unitaires pour database.py (DB in-memory)
import pytest
import sqlite3
import sys
from unittest.mock import patch, MagicMock

# Mock config avant import database
mock_cfg = MagicMock()
mock_cfg.TELEGRAM_BOT_TOKEN = 'fake_token'
mock_cfg.TELEGRAM_CHAT_ID = '12345'
mock_cfg.TELEGRAM_CHAT_IDS = ['12345']
sys.modules.setdefault('config', mock_cfg)

import importlib
import database as db_module


@pytest.fixture
def db(tmp_path):
    """Base de données SQLite temporaire pour chaque test"""
    db_file = str(tmp_path / 'test.db')
    d = db_module.Database(db_path=db_file)
    yield d
    d.close()


SAMPLE = {
    'listing_id': 'test_123',
    'site': 'Test.lu',
    'title': 'Appartement test',
    'city': 'Luxembourg',
    'price': 1800,
    'rooms': 2,
    'surface': 85,
    'url': 'https://test.lu/annonces/123',
    'latitude': 49.6116,
    'longitude': 6.1319,
    'distance_km': 2.5,
}


class TestAddListing:
    def test_ajout_simple(self, db):
        assert db.add_listing(SAMPLE) is True

    def test_ajout_doublon_id(self, db):
        db.add_listing(SAMPLE)
        assert db.add_listing(SAMPLE) is False  # IntegrityError

    def test_ajout_doublon_url(self, db):
        db.add_listing(SAMPLE)
        l2 = {**SAMPLE, 'listing_id': 'test_456'}  # meme URL
        assert db.add_listing(l2) is False

    def test_champs_optionnels_none(self, db):
        l = {**SAMPLE, 'latitude': None, 'longitude': None, 'distance_km': None,
             'listing_id': 'test_opt', 'url': 'https://test.lu/opt'}
        assert db.add_listing(l) is True


class TestListingExists:
    def test_existe(self, db):
        db.add_listing(SAMPLE)
        assert db.listing_exists('test_123') is True

    def test_nexiste_pas(self, db):
        assert db.listing_exists('test_999') is False


class TestSimilarListing:
    def test_similaire_trouve(self, db):
        db.add_listing(SAMPLE)
        assert db.similar_listing_exists(1800, 'Luxembourg', 85) is True

    def test_similaire_surface_proche(self, db):
        db.add_listing(SAMPLE)
        assert db.similar_listing_exists(1800, 'Luxembourg', 80) is True  # ±15m²

    def test_pas_similaire_prix_diff(self, db):
        db.add_listing(SAMPLE)
        assert db.similar_listing_exists(2000, 'Luxembourg', 85) is False

    def test_pas_similaire_ville_diff(self, db):
        db.add_listing(SAMPLE)
        assert db.similar_listing_exists(1800, 'Strassen', 85) is False

    def test_prix_zero(self, db):
        db.add_listing(SAMPLE)
        assert db.similar_listing_exists(0, 'Luxembourg', 85) is False


class TestMarkNotified:
    def test_marquer_notifie(self, db):
        db.add_listing(SAMPLE)
        db.mark_as_notified('test_123')
        stats = db.get_stats()
        assert stats['notified'] == 1

    def test_id_inexistant(self, db):
        db.mark_as_notified('inexistant')  # pas d'erreur


class TestGetStats:
    def test_stats_vides(self, db):
        s = db.get_stats()
        assert s['total'] == 0
        assert s['notified'] == 0

    def test_stats_avec_annonces(self, db):
        db.add_listing(SAMPLE)
        l2 = {**SAMPLE, 'listing_id': 'test_456', 'url': 'https://test.lu/456', 'site': 'Autre.lu'}
        db.add_listing(l2)
        s = db.get_stats()
        assert s['total'] == 2
        assert 'Test.lu' in s['by_site']
        assert 'Autre.lu' in s['by_site']


class TestCleanup:
    def test_cleanup_rien_a_supprimer(self, db):
        db.add_listing(SAMPLE)
        deleted = db.cleanup_old_listings(30)
        assert deleted == 0  # annonce recente

    def test_cleanup_annonce_ancienne(self, db):
        db.add_listing(SAMPLE)
        # Forcer une date ancienne
        db.cursor.execute(
            "UPDATE listings SET created_at = datetime('now', '-40 days') WHERE listing_id = ?",
            ('test_123',)
        )
        db.conn.commit()
        deleted = db.cleanup_old_listings(30)
        assert deleted == 1
