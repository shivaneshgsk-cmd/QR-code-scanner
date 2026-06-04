"""
image_decoder.py — Image Processing Workflow Orchestrator

Implements the complete image QR decode pipeline:
1. Direct decode attempt
2. Smart quality assessment
3. Progressive enhancement pipeline with decode after each step
4. ROI extraction and targeted decode
5. Batch processing support
"""

import time
import logging
from pathlib import Path
from typing import List, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import numpy as np
from PIL import Image

from core.zxing_decoder import ZXingDecoder, DecodeResult
from core.enhancer import ImageEnhancer
from core.qr_detector import QRDetector

logger = logging.getLogger(__name__)


class ImageDecoder:
    """
    Orchestrates QR code decoding from images.

    Workflow:
    1. Load image
    2. Attempt direct ZXing decode
    3. If successful → return immediately (no enhancement)
    4. If failed → assess quality → apply smart enhancement pipeline
    5. After each enhancement → attempt decode
    6. If still failed → extract ROIs and decode each region
    """

    def __init__(self):
        """Initialize image decoder with all sub-components."""
        self.zxing = ZXingDecoder()
        self.enhancer = ImageEnhancer()
        self.detector = QRDetector()
        self._processing = False
        logger.info("ImageDecoder initialized")

    @property
    def is_processing(self) -> bool:
        return self._processing

    def decode_file(self, file_path: str,
                    progress_callback: Optional[Callable] = None,
                    status_callback: Optional[Callable] = None) -> dict:
        """
        Decode QR code(s) from an image file.

        Args:
            file_path: Path to image file
            progress_callback: Optional callback(progress_percent)
            status_callback: Optional callback(status_message)

        Returns:
            Dict with keys: results, quality, enhancement_used, processing_time,
            image_resolution, success
        """
        self._processing = True
        start_time = time.time()
        result = {
            'results': [],
            'quality': {},
            'enhancement_used': 'None',
            'processing_time': 0.0,
            'image_resolution': '',
            'success': False,
            'file_path': file_path,
        }

        try:
            # Load image
            if status_callback:
                status_callback("Loading image...")
            if progress_callback:
                progress_callback(5)

            image = self._load_image(file_path)
            if image is None:
                result['enhancement_used'] = 'ERROR: Failed to load image'
                return result

            h, w = image.shape[:2]
            result['image_resolution'] = f"{w}x{h}"

            # Step 1: Direct decode
            if status_callback:
                status_callback("Attempting direct decode...")
            if progress_callback:
                progress_callback(10)

            direct_results = self.zxing.decode(image, try_harder=True)
            if direct_results:
                result['results'] = direct_results
                result['enhancement_used'] = 'None (direct decode)'
                result['success'] = True
                result['processing_time'] = round(time.time() - start_time, 3)
                if status_callback:
                    status_callback("✅ Decoded successfully (direct)")
                if progress_callback:
                    progress_callback(100)
                return result

            # Step 2: Quality assessment
            if status_callback:
                status_callback("Assessing image quality...")
            if progress_callback:
                progress_callback(15)

            quality = self.enhancer.get_quality_assessment(image)
            result['quality'] = quality

            # Step 3: Enhancement pipeline
            if status_callback:
                status_callback("Starting enhancement pipeline...")

            total_steps = self.enhancer.get_step_count()

            def enhancement_callback(name, step, total):
                pct = 15 + int((step / total) * 70)
                if progress_callback:
                    progress_callback(min(pct, 85))
                if status_callback:
                    status_callback(f"Enhancement {step}/{total}: {name}")

            enhancements = self.enhancer.enhance_progressively(image, enhancement_callback)

            # Try decoding each enhanced version
            for i, (name, enhanced) in enumerate(enhancements):
                decode_results = self.zxing.decode_single(enhanced, name)
                if decode_results:
                    result['results'] = decode_results
                    result['enhancement_used'] = name
                    result['success'] = True
                    result['processing_time'] = round(time.time() - start_time, 3)
                    if status_callback:
                        status_callback(f"✅ Decoded with: {name}")
                    if progress_callback:
                        progress_callback(100)
                    return result

            # Step 4: ROI extraction & decode
            if status_callback:
                status_callback("Extracting QR regions...")
            if progress_callback:
                progress_callback(90)

            crops = self.detector.detect_and_crop(image, padding=30)
            for j, crop in enumerate(crops):
                # Try direct decode on crop
                crop_results = self.zxing.decode(crop, try_harder=True)
                if crop_results:
                    for r in crop_results:
                        r.enhancement_used = f"ROI Crop #{j+1}"
                    result['results'] = crop_results
                    result['enhancement_used'] = f"ROI Crop #{j+1}"
                    result['success'] = True
                    result['processing_time'] = round(time.time() - start_time, 3)
                    if status_callback:
                        status_callback(f"✅ Decoded from ROI #{j+1}")
                    if progress_callback:
                        progress_callback(100)
                    return result

                # Try enhancements on crop
                crop_enhancements = self.enhancer.enhance_progressively(crop)
                for name, enhanced_crop in crop_enhancements:
                    ec_results = self.zxing.decode_single(enhanced_crop, f"ROI#{j+1}+{name}")
                    if ec_results:
                        result['results'] = ec_results
                        result['enhancement_used'] = f"ROI#{j+1}+{name}"
                        result['success'] = True
                        result['processing_time'] = round(time.time() - start_time, 3)
                        if status_callback:
                            status_callback(f"✅ Decoded from ROI #{j+1} + {name}")
                        if progress_callback:
                            progress_callback(100)
                        return result

            # Failed all attempts
            result['processing_time'] = round(time.time() - start_time, 3)
            result['enhancement_used'] = 'All enhancements attempted'
            if status_callback:
                status_callback("❌ QR code could not be decoded")
            if progress_callback:
                progress_callback(100)
            return result

        except Exception as e:
            logger.error(f"Image decode error: {e}", exc_info=True)
            result['enhancement_used'] = f'ERROR: {str(e)}'
            result['processing_time'] = round(time.time() - start_time, 3)
            if status_callback:
                status_callback(f"❌ Error: {str(e)}")
            return result

        finally:
            self._processing = False

    def decode_batch(self, file_paths: List[str],
                     progress_callback: Optional[Callable] = None,
                     status_callback: Optional[Callable] = None,
                     max_workers: int = 4) -> List[dict]:
        """
        Decode QR codes from multiple image files.

        Args:
            file_paths: List of file paths
            progress_callback: Optional progress callback
            status_callback: Optional status callback
            max_workers: Maximum concurrent workers

        Returns:
            List of result dicts
        """
        results = []
        total = len(file_paths)

        for i, path in enumerate(file_paths):
            if status_callback:
                status_callback(f"Processing file {i+1}/{total}: {Path(path).name}")
            if progress_callback:
                progress_callback(int((i / total) * 100))

            result = self.decode_file(path)
            results.append(result)

        if progress_callback:
            progress_callback(100)
        if status_callback:
            status_callback(f"Batch complete: {sum(1 for r in results if r['success'])}/{total} decoded")

        return results

    def _load_image(self, file_path: str) -> Optional[np.ndarray]:
        """Load image from file path with error handling."""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return None

            # Try OpenCV first
            image = cv2.imread(str(path))
            if image is not None:
                return image

            # Fallback: PIL
            pil_img = Image.open(str(path))
            pil_img = pil_img.convert('RGB')
            image = np.array(pil_img)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            return image

        except Exception as e:
            logger.error(f"Failed to load image {file_path}: {e}")
            return None
