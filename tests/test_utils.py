# tests/test_utils.py — Tests unitaires pour utils.py
import pytest
from utils import haversine_distance, geocode_city, format_distance, get_distance_emoji


class TestHaversine:
    def test_meme_point(self):
        assert haversine_distance(49.6116, 6.1319, 49.6116, 6.1319) == 0.0

    def test_luxembourg_strassen(self):
        # Luxembourg-Ville → Strassen ≈ 4-5 km
        d = haversine_distance(49.6116, 6.1319, 49.6200, 6.0700)
        assert 3.0 < d < 7.0

    def test_valeur_arrondie(self):
        d = haversine_distance(49.6116, 6.1319, 49.6200, 6.0700)
        assert isinstance(d, float)
        assert round(d, 1) == d  # arrondi a 1 decimale

    def test_valeurs_invalides(self):
        assert haversine_distance(None, None, 49.0, 6.0) is None
        assert haversine_distance('x', 6.0, 49.0, 6.0) is None


class TestGeocodeCity:
    def test_luxembourg_exact(self):
        coords = geocode_city('luxembourg')
        assert coords is not None
        lat, lng = coords
        assert 49.5 < lat < 49.7
        assert 6.0 < lng < 6.3

    def test_majuscules(self):
        assert geocode_city('LUXEMBOURG') is not None

    def test_avec_accents(self):
        coords = geocode_city('Esch-sur-Alzette')
        assert coords is not None

    def test_ville_inconnue(self):
        assert geocode_city('VillePasExistante12345') is None

    def test_none(self):
        assert geocode_city(None) is None

    def test_vide(self):
        assert geocode_city('') is None

    def test_belair_quartier(self):
        assert geocode_city('Belair') is not None

    def test_kirchberg(self):
        assert geocode_city('kirchberg') is not None


class TestFormatDistance:
    def test_moins_1km(self):
        assert format_distance(0.5) == 'moins de 1 km'

    def test_entre_1_et_10(self):
        assert '3.5' in format_distance(3.5)

    def test_plus_10km(self):
        r = format_distance(12.7)
        assert '12' in r
        assert '.' not in r  # entier

    def test_none(self):
        assert format_distance(None) == 'N/A'


class TestDistanceEmoji:
    def test_tres_proche(self):
        assert get_distance_emoji(1.0) == '🟢'

    def test_proche(self):
        assert get_distance_emoji(3.0) == '🟡'

    def test_moyen(self):
        assert get_distance_emoji(7.0) == '🟠'

    def test_loin(self):
        assert get_distance_emoji(20.0) == '🔴'

    def test_none(self):
        assert get_distance_emoji(None) == '📍'
