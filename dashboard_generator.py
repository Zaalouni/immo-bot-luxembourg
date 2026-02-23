# =============================================================================
# dashboard_generator.py — DEPRECATED: Backward compatibility wrapper (v3.0)
# =============================================================================
#
# ⚠️  DEPRECATED - À utiliser seulement pour la compatibilité rétroactive
#
# Depuis v3.0, le dashboard a été refactorisé en 3 modules:
#   - data_processor.py:   Logique métier (données, stats, exports)
#   - template_generator.py: Templates (HTML, CSS, JS, manifest)
#   - generator.py:        Orchestrateur principal
#
# Ce fichier est un wrapper qui importe depuis generator.py
#
# MIGRATION:
# - Ancien code: from dashboard_generator import main, read_listings, generate_html
# - Nouveau code: from generator import main
#                 from data_processor import read_listings
#                 from template_generator import generate_html
#
# Pour nouvelle développement, utiliser generator.py directement.
# =============================================================================

# Import tout depuis generator (backward compat)
from generator import main

# Import depuis les modules spécialisés (pour accès direct si nécessaire)
from data_processor import (
    read_listings,
    calc_stats,
    generate_qr_code_url,
    enrich_listings_with_metadata,
    compute_price_heatmap_by_city,
    compute_timeline_data,
    export_data
)

from template_generator import (
    generate_manifest,
    generate_html
)

# Garder l'interface originale pour les anciens scripts
__all__ = [
    'main',
    'read_listings',
    'calc_stats',
    'generate_qr_code_url',
    'enrich_listings_with_metadata',
    'compute_price_heatmap_by_city',
    'compute_timeline_data',
    'export_data',
    'generate_manifest',
    'generate_html'
]

if __name__ == '__main__':
    main()
