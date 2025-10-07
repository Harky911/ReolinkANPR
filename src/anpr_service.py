"""Main ANPR service orchestrating camera and processing."""

import asyncio
import signal
import time
from pathlib import Path
from .logger import logger
from .config import Config
from .camera_client import CameraClient
from .alpr_processor import ALPRProcessor
from .database import Database
from .notifier import Notifier


class ANPRService:
    """Main ANPR service coordinating all components."""

    def __init__(self, config_path: str = "config.yaml"):
        # Load configuration
        self.config = Config(config_path)
        self.config.ensure_directories()

        # Setup logger with config
        from .logger import setup_logger
        global logger
        logger = setup_logger(
            "ReolinkANPR",
            self.config.log_file,
            self.config.log_level
        )

        # Initialize components
        self.camera = CameraClient(self.config)
        self.alpr = ALPRProcessor(self.config)
        self.database = Database(self.config.database_path)
        self.notifier = Notifier(self.config)

        self.running = False

    async def start(self):
        """Start the ANPR service."""
        logger.info("=" * 60)
        logger.info("ReolinkANPR - Starting Service")
        logger.info("=" * 60)

        try:
            # Initialize database
            await self.database.initialize()
            logger.info("Database initialized")

            # Check if config is still default
            if self.config.camera_password == "CHANGE_ME":
                logger.warning("=" * 60)
                logger.warning("Configuration needed!")
                logger.warning("Please configure your camera at:")
                logger.warning("  http://localhost:5001/config")
                logger.warning("Then restart ReolinkANPR")
                logger.warning("=" * 60)
                # Keep running but wait for config
                self.running = True
                await self._wait_for_config()
                return

            # Connect to camera with retry logic
            connected = False
            retry_count = 0
            max_retries = 3

            while not connected and retry_count < max_retries:
                if retry_count > 0:
                    logger.info(f"Retry {retry_count}/{max_retries} - Attempting to connect...")
                    await asyncio.sleep(5)

                connected = await self.camera.connect()
                retry_count += 1

            if not connected:
                logger.error("=" * 60)
                logger.error("Failed to connect to camera after 3 attempts")
                logger.error("Please check:")
                logger.error("  - Camera IP address is correct")
                logger.error("  - Camera is powered on and connected")
                logger.error("  - Username and password are correct")
                logger.error("  - RTSP is enabled on camera")
                logger.error("")
                logger.error("Configure at: http://localhost:5001/config")
                logger.error("=" * 60)
                # Keep running but wait
                self.running = True
                await self._wait_for_config()
                return

            # Set up event-driven processing callback
            self.camera.set_processing_callback(self._handle_vehicle_detection)

            # Start monitoring
            self.running = True
            logger.info("ANPR Service started successfully")
            logger.info(f"Monitoring {self.config.camera_name} for vehicles...")
            logger.info("=" * 60)

            await self._monitoring_loop()

        except Exception as e:
            logger.error(f"Failed to start ANPR service: {e}")
            raise

    async def stop(self):
        """Stop the ANPR service gracefully."""
        logger.info("Stopping ANPR Service...")
        self.running = False

        # Disconnect from camera
        await self.camera.disconnect()

        logger.info("ANPR Service stopped")

    async def _wait_for_config(self):
        """Wait indefinitely for user to configure via web interface."""
        logger.info("Service running in configuration mode...")
        logger.info("Waiting for configuration via web interface")

        while self.running:
            await asyncio.sleep(60)

    async def _monitoring_loop(self):
        """Main monitoring loop - wait for TCP push events."""
        logger.info("Monitoring with TCP push events (Baichuan protocol)")
        logger.info("Waiting for vehicle detection events...")

        # Keep alive loop - TCP push events handled by callback
        while self.running:
            try:
                # Just keep the loop alive - events come via TCP push callback
                await asyncio.sleep(60)  # Wake up every minute to check if still running

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)

    async def _handle_vehicle_detection(self):
        """Handle TCP push event - record and process."""
        try:
            logger.info("Motion event received via TCP push - starting recording")

            # Apply before-recording settings if configured
            if hasattr(self.config, 'before_recording_enabled') and self.config.before_recording_enabled:
                await self.camera.apply_recording_settings('before')

            # Record RTSP stream
            frames = await self.camera._record_rtsp_and_extract_frames(self.config.recording_duration)

            # Apply after-recording settings if configured
            if hasattr(self.config, 'after_recording_enabled') and self.config.after_recording_enabled:
                await self.camera.apply_recording_settings('after')

            if frames:
                logger.info(f"Processing {len(frames)} frames...")
                await self._process_detection(frames)
            else:
                logger.warning("No frames captured")

        except Exception as e:
            logger.error(f"Error handling vehicle detection: {e}")

    async def _process_detection(self, frames: list):
        """Process vehicle detection frames through ALPR."""

        try:
            # Process frames with ALPR
            save_dir = Path(self.config.database_path).parent
            result = self.alpr.process_frames(frames, save_dir)

            if result:
                # Valid plate detected
                logger.info(
                    f"Plate recognized: {result['plate_number']} "
                    f"(confidence: {result['confidence']:.2%})"
                )

                # Save to database
                event_id = await self.database.add_event(result)
                logger.info(f"Event saved to database (ID: {event_id})")
                
                # Send notifications (only if it was actually saved, not a duplicate)
                if event_id:
                    await self.notifier.send_detection(
                        result['plate_number'],
                        result['confidence'],
                        result.get('image_path')
                    )
            else:
                logger.info("No valid plates found in frames")

        except Exception as e:
            logger.error(f"Error processing detection: {e}")


async def main():
    """Main entry point for the service."""
    service = ANPRService()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(service.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Service error: {e}")
        raise
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
