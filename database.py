# =============================================================================
# database.py — Couche de persistence SQLite pour les annonces
# =============================================================================
# Classe Database (instance globale `db`) qui gere :
#   - Table `listings` : stocke toutes les annonces avec prix, GPS, etc.
#   - Dedup par listing_id (UNIQUE) et par URL (UNIQUE)
#   - Dedup cross-site : similar_listing_exists(prix, ville, surface ±15m2)
#   - Statistiques : total, nouvelles, notifiees, par site, distance moyenne
#   - Nettoyage automatique des annonces > N jours (cleanup_old_listings)
#
# Schema : voir architecture.md pour le detail des colonnes et index.
# Instance globale : `from database import db`
# =============================================================================
import sqlite3
import logging
import os
from datetime import datetime
from utils import validate_listing_data

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path='listings.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.init_db()

    def init_db(self):
        """Initialiser la base de données SQLite"""
        try:
            self.conn = sqlite3.connect(self.db_path, timeout=10)
            self.cursor = self.conn.cursor()

            # Table des annonces (avec colonnes GPS)
            self.cursor.execute('''
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
            ''')

            # Index pour performances
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_listing_id
                ON listings(listing_id)
            ''')

            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON listings(created_at)
            ''')

            # Index distance (pour tri par proximité)
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_distance
                ON listings(distance_km)
            ''')

            self.conn.commit()
            logger.info("✅ Base de données initialisée")

            # Set restrictive file permissions (0o600) for security
            try:
                if os.path.exists(self.db_path):
                    os.chmod(self.db_path, 0o600)
                    logger.debug("🔒 Permissions de sécurité appliquées à la base de données")
            except OSError as perm_error:
                logger.warning(f"⚠️ Impossible de définir les permissions: {perm_error}")

        except sqlite3.Error as e:
            logger.error(f"❌ Erreur initialisation DB: {e}")
            raise

    def listing_exists(self, listing_id):
        """Vérifier si une annonce existe déjà"""
        try:
            self.cursor.execute(
                'SELECT id FROM listings WHERE listing_id = ?',
                (listing_id,)
            )
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"❌ Erreur vérification existence: {e}")
            return False

    def add_listing(self, listing_data):
        """Ajouter une nouvelle annonce avec validation"""
        try:
            # Valider et nettoyer les données avant insertion
            validated_data = validate_listing_data(listing_data)

            self.cursor.execute('''
                INSERT INTO listings
                (listing_id, site, title, city, price, rooms, surface, url, latitude, longitude, distance_km)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                validated_data.get('listing_id', ''),
                validated_data.get('site', 'Inconnu'),
                validated_data.get('title', 'Sans titre'),
                validated_data.get('city', 'N/A'),
                validated_data.get('price', 0),
                validated_data.get('rooms', 0),
                validated_data.get('surface', 0),
                validated_data.get('url', '#'),
                validated_data.get('latitude'),
                validated_data.get('longitude'),
                validated_data.get('distance_km')
            ))
            self.conn.commit()

            listing_id = validated_data.get('listing_id', 'N/A')
            logger.info(f"✅ Annonce ajoutée: {listing_id}")
            return True

        except (ValueError, KeyError) as e:
            logger.warning(f"⚠️  Validation échouée: {e}")
            return False
        except sqlite3.IntegrityError:
            # Annonce déjà existante
            return False
        except sqlite3.Error as e:
            logger.error(f"❌ Erreur ajout annonce: {e}")
            return False

    def similar_listing_exists(self, price, city, surface=0):
        """Vérifier si une annonce similaire existe déjà (cross-site dedup)"""
        try:
            city_clean = city.lower().strip() if city else ''
            if not city_clean or price <= 0:
                return False

            if surface and surface > 0:
                # Même prix, ville similaire, surface ±15m²
                self.cursor.execute('''
                    SELECT listing_id FROM listings
                    WHERE price = ? AND LOWER(city) LIKE ? AND ABS(surface - ?) <= 15
                    LIMIT 1
                ''', (price, f'%{city_clean}%', surface))
            else:
                # Même prix, ville similaire
                self.cursor.execute('''
                    SELECT listing_id FROM listings
                    WHERE price = ? AND LOWER(city) LIKE ?
                    LIMIT 1
                ''', (price, f'%{city_clean}%'))

            result = self.cursor.fetchone()
            if result:
                logger.debug(f"Doublon DB trouvé: prix={price} ville={city} → {result[0]}")
            return result is not None
        except sqlite3.Error:
            return False

    def mark_as_notified(self, listing_id):
        """Marquer une annonce comme notifiée"""
        try:
            self.cursor.execute(
                'UPDATE listings SET notified = 1 WHERE listing_id = ?',
                (listing_id,)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"❌ Erreur marquage notifié: {e}")

    def get_stats(self):
        """Obtenir des statistiques"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM listings')
            total = self.cursor.fetchone()[0] or 0

            self.cursor.execute('SELECT COUNT(*) FROM listings WHERE notified = 0')
            new = self.cursor.fetchone()[0] or 0

            self.cursor.execute('SELECT COUNT(*) FROM listings WHERE notified = 1')
            notified = self.cursor.fetchone()[0] or 0

            self.cursor.execute('SELECT site, COUNT(*) FROM listings GROUP BY site')
            by_site = dict(self.cursor.fetchall())

            # Stats distance (moyenne des annonces avec distance)
            self.cursor.execute('SELECT AVG(distance_km) FROM listings WHERE distance_km IS NOT NULL')
            avg_distance = self.cursor.fetchone()[0]

            return {
                'total': total,
                'new': new,
                'notified': notified,
                'by_site': by_site,
                'avg_distance': round(avg_distance, 1) if avg_distance else None
            }

        except sqlite3.Error as e:
            logger.error(f"❌ Erreur statistiques: {e}")
            return {'total': 0, 'new': 0, 'notified': 0, 'by_site': {}, 'avg_distance': None}

    def get_closest_listings(self, limit=10):
        """Obtenir les annonces les plus proches"""
        try:
            self.cursor.execute('''
                SELECT listing_id, title, city, distance_km, url
                FROM listings
                WHERE distance_km IS NOT NULL
                ORDER BY distance_km ASC
                LIMIT ?
            ''', (limit,))

            return self.cursor.fetchall()

        except sqlite3.Error as e:
            logger.error(f"❌ Erreur récupération annonces proches: {e}")
            return []

    def cleanup_old_listings(self, days=30):
        """Supprimer les annonces de plus de N jours"""
        try:
            self.cursor.execute('''
                DELETE FROM listings
                WHERE created_at < datetime('now', ?)
            ''', (f'-{days} days',))
            deleted = self.cursor.rowcount
            self.conn.commit()
            if deleted > 0:
                logger.info(f"🧹 Nettoyage DB: {deleted} annonces de +{days}j supprimées")
                try:
                    self.conn.execute('VACUUM')
                except sqlite3.Error:
                    pass
            return deleted
        except sqlite3.Error as e:
            logger.error(f"❌ Erreur nettoyage DB: {e}")
            return 0

    def close(self):
        """Fermer la connexion"""
        if self.conn:
            self.conn.close()

# Instance globale
db = Database()
