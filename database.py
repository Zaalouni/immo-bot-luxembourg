# database.py
import sqlite3
import logging
from datetime import datetime

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
        """Ajouter une nouvelle annonce"""
        try:
            self.cursor.execute('''
                INSERT INTO listings
                (listing_id, site, title, city, price, rooms, surface, url, latitude, longitude, distance_km)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                listing_data.get('listing_id', ''),
                listing_data.get('site', 'Inconnu'),
                listing_data.get('title', 'Sans titre'),
                listing_data.get('city', 'N/A'),
                listing_data.get('price', 0),
                listing_data.get('rooms', 0),
                listing_data.get('surface', 0),
                listing_data.get('url', '#'),
                listing_data.get('latitude'),
                listing_data.get('longitude'),
                listing_data.get('distance_km')
            ))
            self.conn.commit()

            listing_id = listing_data.get('listing_id', 'N/A')
            logger.info(f"✅ Annonce ajoutée: {listing_id}")
            return True

        except sqlite3.IntegrityError:
            # Annonce déjà existante
            return False
        except sqlite3.Error as e:
            logger.error(f"❌ Erreur ajout annonce: {e}")
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

    def close(self):
        """Fermer la connexion"""
        if self.conn:
            self.conn.close()

# Instance globale
db = Database()
