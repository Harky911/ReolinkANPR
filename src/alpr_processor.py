"""ALPR processing using FastALPR."""

import cv2
import numpy as np
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from .logger import logger

try:
    from fast_alpr import ALPR
    FAST_ALPR_AVAILABLE = True
except ImportError:
    FAST_ALPR_AVAILABLE = False
    logger.error("fast-alpr not available! Install with: pip install fast-alpr")


class ALPRProcessor:
    """Process images for license plate recognition using FastALPR."""

    def __init__(self, config):
        self.config = config

        if not FAST_ALPR_AVAILABLE:
            raise ImportError("fast-alpr library not available")

        # Initialize FastALPR with configured models
        self.alpr = ALPR(
            detector_model=config.detector_model,
            ocr_model=config.ocr_model,
            detector_conf_thresh=0.3  # Detection confidence (lower than recognition threshold)
        )

        logger.info(f"FastALPR initialized with {config.detector_model}")

    def process_frames(
        self,
        frame_bytes_list: List[bytes],
        save_dir: Path
    ) -> Optional[Dict]:
        """
        Process multiple frames and return the best result.

        Args:
            frame_bytes_list: List of frame bytes to process
            save_dir: Directory to save images

        Returns:
            Dict with plate info and paths, or None if no plate found
        """
        if not frame_bytes_list:
            logger.warning("No frames provided for processing")
            return None

        logger.info(f"Processing {len(frame_bytes_list)} frames...")

        best_result = None
        best_confidence = 0.0
        best_image = None
        best_plate_crop = None

        for i, frame_bytes in enumerate(frame_bytes_list):
            try:
                # Decode image
                image_array = np.frombuffer(frame_bytes, np.uint8)
                img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

                if img is None:
                    logger.warning(f"Failed to decode frame {i+1}")
                    continue

                # Run detection-only first (lighter weight)
                detections = self.alpr.detector.predict(img)

                if not detections:
                    if (i+1) % 20 == 0:  # Log every 20th frame to reduce noise
                        logger.debug(f"Frame {i+1}: No plates detected")
                    continue

                # Run full ALPR (detection + OCR) on frames with detections
                results = self.alpr.predict(img)

                if not results:
                    logger.debug(f"Frame {i+1}: Detected {len(detections)} plates but OCR failed")
                    continue

                # Process each detection
                for result in results:
                    plate_text = result.ocr.text.upper().replace(' ', '')
                    confidence = result.ocr.confidence

                    # Validate plate format
                    if not self._is_valid_plate(plate_text):
                        logger.debug(f"Frame {i+1}: Invalid plate format: {plate_text}")
                        continue

                    # Check confidence threshold
                    if confidence < self.config.min_confidence:
                        logger.debug(f"Frame {i+1}: Low confidence {confidence:.3f} for {plate_text}")
                        continue

                    logger.info(f"Frame {i+1}: {plate_text} (confidence: {confidence:.3f})")

                    # Track best result
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_result = result
                        best_image = img.copy()

                        # Crop plate region
                        bbox = result.detection.bounding_box
                        x1, y1 = int(bbox.x1), int(bbox.y1)
                        x2, y2 = int(bbox.x2), int(bbox.y2)
                        best_plate_crop = img[y1:y2, x1:x2].copy()

            except Exception as e:
                logger.error(f"Error processing frame {i+1}: {e}")
                continue

        # If no detections found, save debug frames
        if not best_result:
            logger.info("No valid plates detected - saving first and last frames for debugging")
            self._save_debug_frames(frame_bytes_list, save_dir)

        # Return best result if found
        if best_result and best_image is not None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Save full image
            image_filename = f"{timestamp}_{best_result.ocr.text.upper().replace(' ', '')}.jpg"
            image_path = save_dir / "images" / image_filename
            image_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(image_path), best_image)

            # Save plate crop
            crop_filename = f"{timestamp}_{best_result.ocr.text.upper().replace(' ', '')}_crop.jpg"
            crop_path = save_dir / "images" / crop_filename
            if best_plate_crop is not None:
                cv2.imwrite(str(crop_path), best_plate_crop)

            bbox = best_result.detection.bounding_box

            return {
                'plate_number': best_result.ocr.text.upper().replace(' ', ''),
                'confidence': best_result.ocr.confidence,
                'image_path': f"images/{image_filename}",
                'plate_crop_path': f"images/{crop_filename}",
                'box_coordinates': {
                    'xmin': bbox.x1,
                    'ymin': bbox.y1,
                    'xmax': bbox.x2,
                    'ymax': bbox.y2
                },
                'frame_count': len(frame_bytes_list)
            }

        logger.info("No valid plates detected in any frame")
        return None

    def _is_valid_plate(self, text: str) -> bool:
        """
        Validate UK license plate format.

        Args:
            text: Plate text to validate

        Returns:
            True if valid UK plate format
        """
        # Remove spaces
        text = text.replace(' ', '').upper()

        # UK plate patterns
        patterns = [
            r'^[A-Z]{2}[0-9]{2}[A-Z]{3}$',  # Current format: AB12CDE
            r'^[A-Z][0-9]{1,3}[A-Z]{3}$',   # Prefix format: A123BCD
            r'^[A-Z]{3}[0-9]{1,3}[A-Z]$',   # Suffix format: ABC123D
            r'^[A-Z]{1,3}[0-9]{1,4}$',      # Older formats
        ]

        for pattern in patterns:
            if re.match(pattern, text):
                return True

        return False

    def _save_debug_frames(self, frame_bytes_list: List[bytes], save_dir: Path):
        """Save first and last frames for debugging when no plates detected."""
        try:
            debug_dir = save_dir / "debug_frames"
            debug_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Save first frame
            if len(frame_bytes_list) > 0:
                image_array = np.frombuffer(frame_bytes_list[0], np.uint8)
                img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                if img is not None:
                    first_path = debug_dir / f"{timestamp}_first.jpg"
                    cv2.imwrite(str(first_path), img)
                    logger.info(f"Saved first frame: {first_path}")

            # Save last frame
            if len(frame_bytes_list) > 1:
                image_array = np.frombuffer(frame_bytes_list[-1], np.uint8)
                img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                if img is not None:
                    last_path = debug_dir / f"{timestamp}_last.jpg"
                    cv2.imwrite(str(last_path), img)
                    logger.info(f"Saved last frame: {last_path}")

            # Save middle frame
            if len(frame_bytes_list) > 2:
                mid_idx = len(frame_bytes_list) // 2
                image_array = np.frombuffer(frame_bytes_list[mid_idx], np.uint8)
                img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                if img is not None:
                    mid_path = debug_dir / f"{timestamp}_middle.jpg"
                    cv2.imwrite(str(mid_path), img)
                    logger.info(f"Saved middle frame: {mid_path}")

        except Exception as e:
            logger.error(f"Failed to save debug frames: {e}")
