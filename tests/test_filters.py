# tests/test_filters.py — Tests unitaires pour filters.py
import pytest
from unittest.mock import patch

# Config mockee pour les tests
MOCK_CONFIG = dict(
    MIN_PRICE=1000, MAX_PRICE=2800,
    MIN_ROOMS=2, MAX_ROOMS=3,
    MIN_SURFACE=70,
    EXCLUDED_WORDS=['parking', 'garage', 'cave'],
    MAX_DISTANCE=15.0,
)

def matches(listing):
    with patch.dict('sys.modules', {}):
        with patch('filters.matches_criteria.__globals__', {}):
            pass
    # Import direct avec config mockee
    import importlib, sys
    # Patcher config
    mock_cfg = type(sys)('config')
    for k, v in MOCK_CONFIG.items():
        setattr(mock_cfg, k, v)
    sys.modules['config'] = mock_cfg
    import filters
    importlib.reload(filters)
    return filters.matches_criteria(listing)


GOOD = {
    'price': 1800, 'rooms': 2, 'surface': 85,
    'title': 'Appartement 2ch Luxembourg',
    'full_text': '', 'distance_km': 5.0
}


def test_annonce_valide():
    assert matches(GOOD) is True

def test_prix_trop_bas():
    l = {**GOOD, 'price': 500}
    assert matches(l) is False

def test_prix_trop_haut():
    l = {**GOOD, 'price': 3500}
    assert matches(l) is False

def test_prix_zero():
    l = {**GOOD, 'price': 0}
    assert matches(l) is False

def test_prix_negatif():
    l = {**GOOD, 'price': -100}
    assert matches(l) is False

def test_rooms_trop_peu():
    l = {**GOOD, 'rooms': 1}
    assert matches(l) is False

def test_rooms_trop_beaucoup():
    l = {**GOOD, 'rooms': 5}
    assert matches(l) is False

def test_rooms_zero_accepte():
    # Rooms inconnues = acceptees
    l = {**GOOD, 'rooms': 0}
    assert matches(l) is True

def test_surface_trop_petite():
    l = {**GOOD, 'surface': 40}
    assert matches(l) is False

def test_surface_zero_acceptee():
    l = {**GOOD, 'surface': 0}
    assert matches(l) is True

def test_mot_exclu_titre():
    l = {**GOOD, 'title': 'Parking Luxembourg'}
    assert matches(l) is False

def test_mot_exclu_full_text():
    l = {**GOOD, 'full_text': 'cave incluse'}
    assert matches(l) is False

def test_distance_trop_grande():
    l = {**GOOD, 'distance_km': 20.0}
    assert matches(l) is False

def test_distance_limite_exacte():
    l = {**GOOD, 'distance_km': 15.0}
    assert matches(l) is True  # <= MAX_DISTANCE

def test_distance_none_acceptee():
    l = {**GOOD, 'distance_km': None}
    assert matches(l) is True

def test_prix_aux_limites_min():
    l = {**GOOD, 'price': 1000}
    assert matches(l) is True

def test_prix_aux_limites_max():
    l = {**GOOD, 'price': 2800}
    assert matches(l) is True
