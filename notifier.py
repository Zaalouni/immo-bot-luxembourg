# notifier.py - VERSION COMPLÈTE CORRIGÉE AVEC GPS
import logging
import requests
import time
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Gestionnaire de notifications Telegram pour groupes/individus"""

    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"

        # Gérer plusieurs Chat IDs (séparés par virgules) ou un seul
        if isinstance(TELEGRAM_CHAT_ID, str) and ',' in TELEGRAM_CHAT_ID:
            self.chat_ids = [cid.strip() for cid in TELEGRAM_CHAT_ID.split(',')]
        elif isinstance(TELEGRAM_CHAT_ID, list):
            self.chat_ids = TELEGRAM_CHAT_ID
        else:
            self.chat_ids = [str(TELEGRAM_CHAT_ID)]

        # Nettoyer les IDs (s'assurer qu'ils sont strings)
        self.chat_ids = [str(cid) for cid in self.chat_ids]

        logger.info(f"✅ Notifier initialisé pour {len(self.chat_ids)} destinataire(s)")
        logger.info(f"   IDs: {', '.join([f'{cid[:10]}...' if len(cid) > 10 else cid for cid in self.chat_ids])}")

        # Tester la connexion
        self.test_connection()

    def test_connection(self):
        """Tester la connexion au bot et aux chats"""
        try:
            # Test 1: Le bot existe-t-il ?
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            if response.status_code == 200:
                bot_info = response.json()['result']
                logger.info(f"🤖 Bot: @{bot_info.get('username', 'N/A')} ({bot_info.get('first_name', 'N/A')})")
            else:
                logger.error(f"❌ Erreur bot: {response.json()}")
                return False

            # Test 2: Chaque chat est-il accessible ?
            success_count = 0
            for chat_id in self.chat_ids:
                try:
                    chat_response = requests.post(
                        f"{self.base_url}/getChat",
                        json={"chat_id": chat_id},
                        timeout=10
                    )

                    if chat_response.status_code == 200:
                        chat_info = chat_response.json().get('result', {})
                        chat_type = chat_info.get('type', 'inconnu')
                        chat_name = chat_info.get('title', chat_info.get('first_name', 'N/A'))

                        logger.info(f"   💬 Chat {chat_id}: {chat_name} ({chat_type})")
                        success_count += 1
                    else:
                        logger.warning(f"   ⚠️  Chat {chat_id}: inaccessible ({chat_response.json().get('description', 'N/A')})")

                except Exception as e:
                    logger.warning(f"   ⚠️  Chat {chat_id}: erreur test - {e}")

            if success_count > 0:
                logger.info(f"✅ {success_count}/{len(self.chat_ids)} chats accessibles")
                return True
            else:
                logger.error("❌ Aucun chat accessible!")
                return False

        except Exception as e:
            logger.error(f"❌ Erreur test connexion: {e}")
            return False

    def send_message(self, text, parse_mode='HTML', silent=False, retry_count=3):
        """Envoyer un message à tous les chats configurés"""
        success_count = 0
        total_chats = len(self.chat_ids)

        for chat_id in self.chat_ids:
            for attempt in range(retry_count):
                try:
                    url = f"{self.base_url}/sendMessage"
                    data = {
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": False,
                        "disable_notification": silent
                    }

                    response = requests.post(url, json=data, timeout=10)

                    if response.status_code == 200:
                        success_count += 1
                        if attempt > 0:
                            logger.debug(f"   ✅ Chat {chat_id}: envoyé (tentative {attempt+1})")
                        break

                    else:
                        error_data = response.json()
                        error_desc = error_data.get('description', 'Unknown error')

                        if "Too Many Requests" in error_desc:
                            wait_time = 2 ** attempt
                            logger.warning(f"   ⚠️  Chat {chat_id}: Rate limit, attente {wait_time}s...")
                            time.sleep(wait_time)
                            continue

                        elif "chat not found" in error_desc or "bot was kicked" in error_desc:
                            logger.error(f"   ❌ Chat {chat_id}: inaccessible - {error_desc}")
                            break

                        else:
                            logger.warning(f"   ⚠️  Chat {chat_id}: erreur {response.status_code} - {error_desc}")
                            if attempt < retry_count - 1:
                                time.sleep(1)

                except requests.exceptions.Timeout:
                    logger.warning(f"   ⚠️  Chat {chat_id}: timeout (tentative {attempt+1}/{retry_count})")
                    if attempt < retry_count - 1:
                        time.sleep(2)

                except Exception as e:
                    logger.error(f"   ❌ Chat {chat_id}: exception - {e}")
                    break

        # Résumé
        if success_count == total_chats:
            logger.debug(f"📨 Messages envoyés: {success_count}/{total_chats}")
            return True
        elif success_count > 0:
            logger.info(f"📨 Messages envoyés: {success_count}/{total_chats} (partiel)")
            return True
        else:
            logger.error(f"❌ Aucun message envoyé (0/{total_chats})")
            return False

    @staticmethod
    def _escape_html(text):
        """Échapper les caractères spéciaux HTML pour Telegram"""
        if not text:
            return ''
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))

    def send_listing(self, listing):
        """Envoyer une annonce immobilière formatée avec distance GPS"""
        try:
            # Extraire et nettoyer les données (échapper HTML)
            site = self._escape_html(listing.get('site', 'Site inconnu').strip())
            title = self._escape_html(listing.get('title', 'Sans titre').strip())
            city = self._escape_html(listing.get('city', 'N/A').strip())
            price = listing.get('price', 0)
            rooms = listing.get('rooms', 0)
            surface = listing.get('surface', 0)
            url = listing.get('url', '#').strip()
            time_ago = listing.get('time_ago', 'récemment').strip()
            distance_km = listing.get('distance_km')

            # Formater le prix
            try:
                price_formatted = f"{int(price):,}€".replace(',', ' ')
            except:
                price_formatted = f"{price}€"

            # Créer le message HTML
            message = f"""
🏠 <b>NOUVELLE ANNONCE • {site}</b>

<b>{title}</b>

📍 <b>Ville:</b> {city if city else 'N/A'}
"""

            # Distance GPS + lien Google Maps
            from utils import format_distance, get_distance_emoji
            from config import REFERENCE_NAME, MAX_DISTANCE
            lat = listing.get('latitude')
            lng = listing.get('longitude')
            if distance_km is not None:
                emoji = get_distance_emoji(distance_km)
                dist_str = format_distance(distance_km)
                dist_line = f"{emoji} <b>Distance:</b> {dist_str} de {self._escape_html(REFERENCE_NAME)}"
                if lat and lng:
                    dist_line += f' (<a href="https://www.google.com/maps?q={lat},{lng}">Maps</a>)'
                message += dist_line + "\n"
            else:
                message += f"📍 <b>Distance:</b> N/A\n"

            rooms_str = f"{rooms}" if rooms and rooms > 0 else "N/A"
            surface_str = f"{surface}m²" if surface and surface > 0 else "N/A"

            # Prix par m²
            prix_m2_str = ""
            if surface and surface > 0 and price and price > 0:
                prix_m2 = round(price / surface, 1)
                prix_m2_str = f" ({prix_m2}€/m²)"

            message += f"""💰 <b>Prix:</b> {price_formatted}/mois{prix_m2_str}
🛏️ <b>Chambres:</b> {rooms_str}
📏 <b>Surface:</b> {surface_str}

🔗 <a href="{url}">Voir l'annonce</a>
"""

            # Hashtags dynamiques
            hashtags = []
            if city and 'luxembourg' in city.lower():
                hashtags.append('#Luxembourg')
            elif city and city.strip():
                hashtags.append(f'#{self._escape_html(city.replace(" ", ""))}')
            if 'appartement' in title.lower():
                hashtags.append('#Appartement')
            elif 'maison' in title.lower():
                hashtags.append('#Maison')
            elif 'duplex' in title.lower() or 'triplex' in title.lower():
                hashtags.append('#Duplex')
            if price and price <= 1500:
                hashtags.append('#PrixBas')
            if distance_km is not None and distance_km < 5:
                hashtags.append('#Proche')
            if surface and surface >= 100:
                hashtags.append('#GrandeSurface')

            if hashtags:
                message += f"\n{' '.join(hashtags)}"

            # Envoyer avec photo si disponible, sinon texte
            image_url = listing.get('image_url')
            if image_url:
                success = self.send_photo(image_url, message, silent=False)
                if not success:
                    # Fallback texte si photo échoue
                    success = self.send_message(message, silent=False)
            else:
                success = self.send_message(message, silent=False)

            if success:
                logger.info(f"✅ Annonce envoyée: {title[:50]}...")
                time.sleep(5)
            else:
                logger.error(f"❌ Échec envoi annonce: {title[:50]}...")

            return success

        except Exception as e:
            logger.error(f"❌ Erreur formatage annonce: {e}")
            fallback_msg = f"🏠 Nouvelle annonce {listing.get('site', '')}: {listing.get('title', '')} - {listing.get('url', '#')}"
            return self.send_message(fallback_msg)

    def send_photo(self, photo_url, caption, parse_mode='HTML', silent=False, retry_count=2):
        """Envoyer une photo avec légende à tous les chats"""
        success_count = 0

        # Telegram limite caption à 1024 caractères
        if len(caption) > 1024:
            caption = caption[:1020] + '...'

        for chat_id in self.chat_ids:
            for attempt in range(retry_count):
                try:
                    url = f"{self.base_url}/sendPhoto"
                    data = {
                        "chat_id": chat_id,
                        "photo": photo_url,
                        "caption": caption,
                        "parse_mode": parse_mode,
                        "disable_notification": silent
                    }
                    response = requests.post(url, json=data, timeout=15)

                    if response.status_code == 200:
                        success_count += 1
                        break
                    else:
                        error_desc = response.json().get('description', '')
                        logger.debug(f"sendPhoto erreur: {error_desc}")
                        if attempt < retry_count - 1:
                            time.sleep(2)
                except Exception as e:
                    logger.debug(f"sendPhoto exception: {e}")
                    break

        return success_count > 0

    def send_startup_message(self, bot_info):
        """Envoyer message de démarrage du bot"""
        message = f"""
🤖 <b>BOT IMMOBILIER LANCÉ</b>

✅ Surveillance active
🕐 Démarrage: {time.strftime('%d/%m/%Y %H:%M:%S')}
🌐 Sites surveillés: {bot_info.get('sites_count', 'N/A')}
👥 Destinataires: {len(self.chat_ids)}

📊 <i>Les nouvelles annonces apparaîtront ici automatiquement.</i>
"""
        return self.send_message(message, silent=True)

    def send_shutdown_message(self, stats=None):
        """Envoyer message d'arrêt du bot"""
        message = f"""
⏹️ <b>BOT IMMOBILIER ARRÊTÉ</b>

🕐 Arrêt: {time.strftime('%d/%m/%Y %H:%M:%S')}
"""

        if stats:
            message += f"""
📊 <b>Statistiques de session:</b>
🏠 Annonces totales: {stats.get('total', 0)}
🆕 Nouvelles annonces: {stats.get('new', 0)}
🌐 Sites actifs: {stats.get('sites', 0)}
"""

        message += "\n👋 À bientôt!"
        return self.send_message(message, silent=True)

    def send_daily_summary(self, stats):
        """Envoyer résumé quotidien"""
        message = f"""
📊 <b>RÉSUMÉ QUOTIDIEN</b>

🏠 <b>Annonces totales:</b> {stats.get('total', 0)}
🆕 <b>Nouvelles aujourd'hui:</b> {stats.get('new', 0)}
👁️ <b>Annonces uniques:</b> {stats.get('unique', 0)}

<b>📈 Répartition par site:</b>
"""

        for site, count in stats.get('by_site', {}).items():
            message += f"• {site}: {count}\n"

        if 'top_cities' in stats:
            message += f"\n<b>📍 Top villes:</b>\n"
            for city, count in stats['top_cities'][:3]:
                message += f"• {city}: {count}\n"

        if 'avg_price' in stats:
            message += f"\n<b>💰 Prix moyen:</b> {stats['avg_price']:,}€".replace(',', ' ')

        return self.send_message(message, silent=True)

    def send_error_message(self, error, context=""):
        """Envoyer message d'erreur"""
        message = f"""
🚨 <b>ERREUR BOT IMMOBILIER</b>

{context}

<code>{str(error)[:300]}</code>

🕐 Heure: {time.strftime('%H:%M:%S')}
"""
        return self.send_message(message, silent=False)

    def send_test_message(self):
        """Envoyer message de test"""
        message = f"""
🧪 <b>TEST BOT IMMOBILIER</b>

✅ Connexion établie
👥 Destinataires: {len(self.chat_ids)}
🕐 Heure: {time.strftime('%H:%M:%S')}

📱 <i>Ceci est un message de test. Les annonces arriveront normalement.</i>
"""
        return self.send_message(message, silent=True)


# Instance globale singleton
_notifier_instance = None

def get_notifier():
    """Obtenir l'instance singleton du notifier"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = TelegramNotifier()
    return _notifier_instance

# Alias pour compatibilité
notifier = get_notifier()
