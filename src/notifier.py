"""Simple notification service for Home Assistant and Telegram."""

import aiohttp
from typing import Optional
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
            
            if self.enabled:
                logger.info("Notifications enabled")
                if self.ha_enabled:
                    logger.info("  - Home Assistant webhook configured")
                if self.telegram_enabled:
                    logger.info("  - Telegram bot configured")

    async def send_detection(self, plate_number: str, confidence: float, image_path: Optional[str] = None):
        """Send notification when a plate is detected."""
        if not self.enabled:
            return
        
        message = f"🚗 Plate Detected: {plate_number} ({confidence:.1%} confidence)"
        
        # Send to Home Assistant
        if self.ha_enabled and self.ha_webhook:
            await self._send_to_home_assistant(plate_number, confidence, image_path)
        
        # Send to Telegram
        if self.telegram_enabled and self.telegram_token and self.telegram_chat_id:
            await self._send_to_telegram(message, image_path)

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
        """Send message to Telegram."""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            async with aiohttp.ClientSession() as session:
                data = {
                    'chat_id': self.telegram_chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }
                async with session.post(url, json=data, timeout=10) as response:
                    if response.status == 200:
                        logger.info(f"Sent to Telegram: {message}")
                    else:
                        logger.warning(f"Telegram returned status {response.status}")
        except Exception as e:
            logger.error(f"Failed to send to Telegram: {e}")

