"""
zxing_decoder.py — ZXing-CPP Wrapper for QR Code Decoding

Provides a robust wrapper around zxing-cpp with:
- Direct NumPy array / PIL Image input
- Multi-QR code support
- Fallback decode attempts (original, rotated, scaled, cropped)
- Structured DecodeResult output
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

try:
    import zxingcpp
except ImportError:
    raise ImportError(
        "zxing-cpp is required. Install with: pip install zxing-cpp"
    )

logger = logging.getLogger(__name__)


@dataclass
class DecodeResult:
    """Structured result from QR code decoding."""
    text: str
    format: str = "QR_CODE"
    confidence: float = 1.0
    position: Optional[str] = None
    processing_time: float = 0.0
    enhancement_used: str = "None"
    frame_number: int = -1
    image_resolution: str = ""


class ZXingDecoder:
    """
    Robust ZXing-CPP decoder with multi-strategy fallback.

    Attempts decoding in multiple ways:
    1. Direct decode on original image
    2. Decode on grayscale conversion
    3. Decode on rotated variants
    4. Decode on scaled variants
    5. Decode on cropped ROI regions
    """

    # Rotation angles to attempt
    ROTATION_ANGLES = [0, 90, 180, 270, 45, 135, 225, 315]

    # Scale factors to attempt
    SCALE_FACTORS = [1.0, 1.5, 2.0, 3.0, 4.0]

    def __init__(self):
        """Initialize the ZXing decoder."""
        self._decode_count = 0
        logger.info("ZXingDecoder initialized (zxing-cpp backend)")

    def decode(self, image: np.ndarray, try_harder: bool = False) -> List[DecodeResult]:
        """
        Decode QR codes from a NumPy image array.

        Args:
            image: BGR or grayscale NumPy array
            try_harder: If True, attempt rotation and scaling fallbacks

        Returns:
            List of DecodeResult objects for all detected QR codes
        """
        start_time = time.time()
        h, w = image.shape[:2]
        resolution = f"{w}x{h}"

        # Strategy 1: Direct decode
        results = self._attempt_decode(image)
        if results:
            return self._build_results(results, time.time() - start_time, "Direct", resolution)

        # Strategy 2: Grayscale decode
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            results = self._attempt_decode(gray)
            if results:
                return self._build_results(results, time.time() - start_time, "Grayscale", resolution)

        if not try_harder:
            return []

        # Strategy 3: Rotation fallback
        for angle in self.ROTATION_ANGLES:
            if angle == 0:
                continue
            rotated = self._rotate_image(image, angle)
            results = self._attempt_decode(rotated)
            if results:
                return self._build_results(
                    results, time.time() - start_time, f"Rotation {angle}°", resolution
                )

        # Strategy 4: Scale fallback
        for scale in self.SCALE_FACTORS:
            if scale == 1.0:
                continue
            scaled = self._scale_image(image, scale)
            results = self._attempt_decode(scaled)
            if results:
                return self._build_results(
                    results, time.time() - start_time, f"Scale {scale}x", resolution
                )

        return []

    def decode_pil(self, pil_image: Image.Image, try_harder: bool = False) -> List[DecodeResult]:
        """Decode from a PIL Image."""
        np_image = np.array(pil_image)
        if len(np_image.shape) == 3 and np_image.shape[2] == 3:
            np_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
        return self.decode(np_image, try_harder)

    def decode_single(self, image: np.ndarray, enhancement: str = "None") -> List[DecodeResult]:
        """
        Single-attempt decode without fallbacks.
        Used during enhancement pipeline where the caller handles strategy.

        Args:
            image: NumPy array
            enhancement: Name of enhancement applied (for result metadata)

        Returns:
            List of DecodeResult
        """
        start_time = time.time()
        h, w = image.shape[:2]
        resolution = f"{w}x{h}"

        results = self._attempt_decode(image)
        if results:
            return self._build_results(results, time.time() - start_time, enhancement, resolution)
        return []

    def _attempt_decode(self, image: np.ndarray) -> list:
        """
        Core decode attempt using zxing-cpp.

        Args:
            image: NumPy array (BGR or grayscale)

        Returns:
            Raw zxingcpp result list
        """
        try:
            self._decode_count += 1
            results = zxingcpp.read_barcodes(image)
            return [r for r in results if r.text.strip()]
        except Exception as e:
            logger.debug(f"ZXing decode attempt failed: {e}")
            return []

    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by given angle while preserving content."""
        h, w = image.shape[:2]
        center = (w // 2, h // 2)

        # Calculate new bounding dimensions
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        cos_a = abs(M[0, 0])
        sin_a = abs(M[0, 1])
        new_w = int(h * sin_a + w * cos_a)
        new_h = int(h * cos_a + w * sin_a)

        # Adjust the rotation matrix
        M[0, 2] += (new_w - w) / 2
        M[1, 2] += (new_h - h) / 2

        rotated = cv2.warpAffine(
            image, M, (new_w, new_h),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255) if len(image.shape) == 3 else 255
        )
        return rotated

    def _scale_image(self, image: np.ndarray, scale: float) -> np.ndarray:
        """Scale image by given factor."""
        h, w = image.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        interpolation = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
        return cv2.resize(image, (new_w, new_h), interpolation=interpolation)

    def _build_results(
        self, raw_results: list, proc_time: float,
        enhancement: str, resolution: str
    ) -> List[DecodeResult]:
        """Convert raw zxing-cpp results to DecodeResult objects."""
        decoded = []
        for r in raw_results:
            pos_str = str(r.position) if hasattr(r, 'position') else "N/A"
            fmt_str = str(r.format).replace("BarcodeFormat.", "") if hasattr(r, 'format') else "QR_CODE"
            decoded.append(DecodeResult(
                text=r.text,
                format=fmt_str,
                confidence=1.0 if r.valid else 0.5,
                position=pos_str,
                processing_time=round(proc_time, 4),
                enhancement_used=enhancement,
                image_resolution=resolution,
            ))
        return decoded

    @property
    def total_attempts(self) -> int:
        """Total number of decode attempts made."""
        return self._decode_count

    def reset_counter(self):
        """Reset the decode attempt counter."""
        self._decode_count = 0
