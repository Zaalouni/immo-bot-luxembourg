#!/usr/bin/env python3
"""
Utilitaires - Calcul distance GPS
"""
import math
import logging

logger = logging.getLogger(__name__)

def haversine_distance(lat1, lng1, lat2, lng2):
    """
    Calcule distance entre 2 points GPS (formule Haversine)
    
    Returns:
        Distance en kilomètres (float) ou None si erreur
    """
    try:
        R = 6371.0  # Rayon Terre en km
        
        # Convertir degrés en radians
        lat1_rad = math.radians(float(lat1))
        lng1_rad = math.radians(float(lng1))
        lat2_rad = math.radians(float(lat2))
        lng2_rad = math.radians(float(lng2))
        
        # Différences
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        # Formule Haversine
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return round(distance, 1)
    
    except (ValueError, TypeError) as e:
        logger.debug(f"Erreur calcul distance: {e}")
        return None

def format_distance(distance_km):
    """Formate distance pour affichage"""
    if distance_km is None:
        return "N/A"
    elif distance_km < 1:
        return "moins de 1 km"
    elif distance_km < 10:
        return f"{distance_km:.1f} km"
    else:
        return f"{int(distance_km)} km"

def get_distance_emoji(distance_km):
    """Retourne emoji selon distance"""
    if distance_km is None:
        return "📍"
    elif distance_km < 2:
        return "🟢"  # Très proche
    elif distance_km < 5:
        return "🟡"  # Proche
    elif distance_km < 10:
        return "🟠"  # Moyen
    else:
        return "🔴"  # Loin
