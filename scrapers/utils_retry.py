# =============================================================================
# scrapers/utils_retry.py — Session HTTP avec retry automatique
# =============================================================================
# Fournit make_session() : requests.Session configuree avec HTTPAdapter + Retry
# Utilisee par tous les scrapers HTTP (Athome, Nextimmo, Sigelux, Immotop, Luxhome)
#
# Comportement retry :
#   - Jusqu'a 3 tentatives par requete (configurable)
#   - Backoff exponentiel : 0.5s, 1s, 2s entre tentatives
#   - Retry sur codes HTTP : 429 (rate limit), 500, 502, 503, 504
#   - Retry sur erreurs connexion (timeout, DNS, reset)
#   - NO retry sur 4xx (sauf 429) car ce sont des erreurs permanentes
# =============================================================================
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def make_session(retries=3, backoff=0.5, headers=None):
    """Retourne une requests.Session avec retry automatique sur erreurs reseau.

    Args:
        retries  : nombre max de tentatives (defaut 3)
        backoff  : facteur backoff — attente = backoff * (2 ** (tentative - 1))
                   ex: backoff=0.5 → 0.5s, 1s, 2s (defaut 0.5)
        headers  : dict headers a ajouter a la session (optionnel)

    Returns:
        requests.Session configuree avec retry adapter
    """
    session = requests.Session()

    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET', 'HEAD'],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.mount('http://', adapter)

    if headers:
        session.headers.update(headers)

    return session
