"""Simple notification service for Home Assistant and Telegram."""

import aiohttp
from typing import Optional
from pathlib import Path
from src.logger import logger


class Notifier:
    """Handle notifications to Home Assistant and Telegram."""

    def __init__(self, config):
        self.config = config
        self.enabled = False
        self.ha_enabled = False
        self.telegram_enabled = False
        
        # Load settings
        if hasattr(config, '_config') and 'notifications' in config._config:
            notif_config = config._config['notifications']
            self.enabled = notif_config.get('enabled', False)
            
            # Home Assistant
            ha_config = notif_config.get('home_assistant', {})
            self.ha_enabled = ha_config.get('enabled', False)
            self.ha_webhook = ha_config.get('webhook_url', '')
            
            # Telegram
            tg_config = notif_config.get('telegram', {})
            self.telegram_enabled = tg_config.get('enabled', False)
            self.telegram_token = tg_config.get('bot_token', '')
            self.telegram_chat_id = tg_config.get('chat_id', '')
            
            logger.info(f"Notifications: enabled={self.enabled}, telegram={self.telegram_enabled}, ha={self.ha_enabled}")
            if self.enabled:
                logger.info("✓ Notifications enabled")
                if self.ha_enabled:
                    logger.info("  ✓ Home Assistant webhook configured")
                if self.telegram_enabled:
                    logger.info(f"  ✓ Telegram bot configured (chat_id: {self.telegram_chat_id})")
        else:
            logger.info("Notifications: not configured")

    async def send_detection(self, plate_number: str, confidence: float, image_path: Optional[str] = None):
        """Send notification when a plate is detected."""
        logger.debug(f"send_detection called: enabled={self.enabled}, plate={plate_number}")
        
        if not self.enabled:
            logger.debug("Notifications disabled - skipping")
            return
        
        message = f"🚗 Plate Detected: {plate_number} ({confidence:.1%} confidence)"
        
        # Send to Home Assistant
        if self.ha_enabled and self.ha_webhook:
            logger.debug("Sending to Home Assistant...")
            await self._send_to_home_assistant(plate_number, confidence, image_path)
        
        # Send to Telegram
        if self.telegram_enabled and self.telegram_token and self.telegram_chat_id:
            logger.debug("Sending to Telegram...")
            await self._send_to_telegram(message, image_path)
        
        if not self.ha_enabled and not self.telegram_enabled:
            logger.warning("Notifications enabled but no services configured!")

    async def _send_to_home_assistant(self, plate_number: str, confidence: float, image_path: Optional[str]):
        """Send webhook to Home Assistant."""
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    'plate_number': plate_number,
                    'confidence': confidence,
                    'image_path': image_path
                }
                async with session.post(self.ha_webhook, json=data, timeout=5) as response:
                    if response.status == 200:
                        logger.info(f"Sent to Home Assistant: {plate_number}")
                    else:
                        logger.warning(f"Home Assistant returned status {response.status}")
        except Exception as e:
            logger.error(f"Failed to send to Home Assistant: {e}")

    async def _send_to_telegram(self, message: str, image_path: Optional[str]):
        """Send message to Telegram with optional image."""
        try:
            async with aiohttp.ClientSession() as session:
                # If we have an image, send as photo with caption
                if image_path and Path(image_path).exists():
                    url = f"https://api.telegram.org/bot{self.telegram_token}/sendPhoto"
                    
                    # Read image file
                    with open(image_path, 'rb') as img_file:
                        form = aiohttp.FormData()
                        form.add_field('chat_id', self.telegram_chat_id)
                        form.add_field('caption', message, content_type='text/plain')
                        form.add_field('photo', img_file, filename='detection.jpg', content_type='image/jpeg')
                        
                        async with session.post(url, data=form, timeout=30) as response:
                            if response.status == 200:
                                logger.info(f"Sent photo to Telegram: {message}")
                            else:
                                response_text = await response.text()
                                logger.warning(f"Telegram photo returned status {response.status}: {response_text}")
                else:
                    # No image or image doesn't exist - send text only
                    url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                    data = {
                        'chat_id': self.telegram_chat_id,
                        'text': message,
                        'parse_mode': 'HTML'
                    }
                    async with session.post(url, json=data, timeout=10) as response:
                        if response.status == 200:
                            logger.info(f"Sent to Telegram: {message}")
                        else:
                            response_text = await response.text()
                            logger.warning(f"Telegram returned status {response.status}: {response_text}")
        except Exception as e:
            logger.error(f"Failed to send to Telegram: {e}")

    async def send_test(self, service: str = 'all'):
        """Send a test notification."""
        test_message = "🧪 Test notification from ReolinkANPR"
        
        if service in ['telegram', 'all'] and self.telegram_enabled:
            logger.info("Sending test to Telegram...")
            await self._send_to_telegram(test_message, None)
            return True
        
        if service in ['home_assistant', 'all'] and self.ha_enabled:
            logger.info("Sending test to Home Assistant...")
            await self._send_to_home_assistant("TEST", 1.0, None)
            return True
        
        return False

