"""
frame_selector.py — Video Frame Quality Scoring & Ranking

Implements weighted frame quality scoring for selecting the best
video frame for QR code decoding:

Score = 0.40 * Sharpness + 0.25 * Contrast + 0.20 * QR_Visibility + 0.15 * Brightness
"""

import logging
from typing import List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FrameSelector:
    """
    Scores and ranks video frames for optimal QR code decoding.

    Uses a weighted scoring algorithm combining:
    - Sharpness (40%) — Laplacian variance
    - Contrast (25%) — Pixel intensity std dev
    - QR Visibility (20%) — Square contour detection
    - Brightness (15%) — Mean intensity (penalised at extremes)
    """

    # Scoring weights
    W_SHARPNESS = 0.40
    W_CONTRAST = 0.25
    W_QR_VISIBILITY = 0.20
    W_BRIGHTNESS = 0.15

    def __init__(self):
        """Initialise frame selector."""
        self._cv_detector = cv2.QRCodeDetector()
        logger.info("FrameSelector initialized")

    def score_frame(self, frame: np.ndarray) -> float:
        """
        Calculate quality score for a single frame.

        Args:
            frame: BGR NumPy array

        Returns:
            Float score (higher = better)
        """
        gray = frame if len(frame.shape) == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        sharpness = self._sharpness_score(gray)
        contrast = self._contrast_score(gray)
        qr_vis = self._qr_visibility_score(gray)
        brightness = self._brightness_score(gray)

        score = (
            self.W_SHARPNESS * sharpness +
            self.W_CONTRAST * contrast +
            self.W_QR_VISIBILITY * qr_vis +
            self.W_BRIGHTNESS * brightness
        )
        return round(score, 4)

    def rank_frames(self, frames: List[Tuple[int, np.ndarray]],
                    top_n: int = 10) -> List[Tuple[int, float, np.ndarray]]:
        """
        Rank frames by quality score.

        Args:
            frames: List of (frame_index, frame_data) tuples
            top_n: Number of top frames to return

        Returns:
            List of (frame_index, score, frame_data) sorted by score descending
        """
        scored = []
        for idx, frame in frames:
            score = self.score_frame(frame)
            scored.append((idx, score, frame))

        scored.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Ranked {len(scored)} frames, top score: "
                    f"{scored[0][1] if scored else 0}")

        return scored[:top_n]

    def _sharpness_score(self, gray: np.ndarray) -> float:
        """
        Measure sharpness using variance of Laplacian.
        Normalised to 0-1 range.
        """
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        # Normalise: typical values range 0-2000+
        return min(lap_var / 500.0, 1.0)

    def _contrast_score(self, gray: np.ndarray) -> float:
        """
        Measure contrast using standard deviation.
        Normalised to 0-1 range.
        """
        std = float(gray.std())
        # Good contrast images have std > 50
        return min(std / 80.0, 1.0)

    def _qr_visibility_score(self, gray: np.ndarray) -> float:
        """
        Estimate QR code visibility using square contour detection
        and OpenCV QR detector.
        """
        score = 0.0

        # Check with OpenCV QR detector
        try:
            retval, _ = self._cv_detector.detect(gray)
            if retval:
                return 1.0
        except Exception:
            pass

        # Fallback: count square-like contours
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        square_count = 0
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            if len(approx) == 4:
                area = cv2.contourArea(c)
                if area > 100:
                    x, y, w, h = cv2.boundingRect(c)
                    aspect = w / max(h, 1)
                    if 0.7 < aspect < 1.3:
                        square_count += 1

        if square_count >= 3:
            score = min(square_count / 12.0, 1.0)

        return score

    def _brightness_score(self, gray: np.ndarray) -> float:
        """
        Score brightness — penalise very dark or very bright images.
        Optimal brightness is around 127.
        """
        mean_val = float(gray.mean())
        # Score peaks at 127 and drops towards 0 or 255
        distance = abs(mean_val - 127.0)
        score = max(0, 1.0 - (distance / 127.0))
        return score
