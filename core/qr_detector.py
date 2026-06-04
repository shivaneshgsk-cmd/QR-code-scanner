"""
qr_detector.py — QR Code Region Detection & ROI Extraction

Detects QR code candidate regions using:
- OpenCV QR detector for finder patterns
- Contour analysis for candidate region identification
- ROI extraction and perspective correction
"""

import logging
from typing import List, Tuple, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class QRDetector:
    """
    Detects QR code candidate regions in images.

    Uses OpenCV's built-in QR detector for finder pattern location
    and contour analysis for fallback region identification.
    """

    def __init__(self):
        """Initialize QR detector with OpenCV backend."""
        self._cv_detector = cv2.QRCodeDetector()
        logger.info("QRDetector initialized")

    def detect_regions(self, image: np.ndarray) -> List[dict]:
        """
        Detect QR code candidate regions in the image.

        Args:
            image: BGR NumPy array

        Returns:
            List of dicts with keys: bbox, center, area, cropped, confidence
        """
        regions = []

        # Strategy 1: OpenCV QR Detector
        cv_regions = self._detect_with_opencv(image)
        regions.extend(cv_regions)

        # Strategy 2: Contour-based detection
        contour_regions = self._detect_with_contours(image)
        regions.extend(contour_regions)

        # Deduplicate overlapping regions
        regions = self._deduplicate(regions)

        logger.info(f"Detected {len(regions)} QR candidate region(s)")
        return regions

    def detect_and_crop(self, image: np.ndarray, padding: int = 20) -> List[np.ndarray]:
        """
        Detect QR regions and return cropped images.

        Args:
            image: BGR NumPy array
            padding: Pixel padding around detected region

        Returns:
            List of cropped image arrays
        """
        regions = self.detect_regions(image)
        crops = []
        h, w = image.shape[:2]

        for region in regions:
            x, y, rw, rh = cv2.boundingRect(np.array(region['bbox']))
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(w, x + rw + padding)
            y2 = min(h, y + rh + padding)

            crop = image[y1:y2, x1:x2].copy()
            if crop.size > 0:
                crops.append(crop)

        return crops

    def get_qr_visibility_score(self, image: np.ndarray) -> float:
        """
        Estimate QR code visibility in the image.

        Returns a score between 0.0 and 1.0 indicating how likely
        a QR code is present and detectable.
        """
        gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Check for finder pattern-like squares
        score = 0.0

        # Look for high-contrast square contours
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        square_count = 0
        nested_count = 0

        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

            if len(approx) == 4:
                area = cv2.contourArea(contour)
                x, y, w, h = cv2.boundingRect(contour)
                aspect = w / max(h, 1)

                # Square-like with reasonable size
                if 0.7 < aspect < 1.3 and area > 100:
                    square_count += 1

        # QR codes have 3 finder patterns (nested squares)
        if square_count >= 3:
            score = min(1.0, square_count / 10.0)
        elif square_count >= 1:
            score = square_count * 0.15

        # OpenCV QR detector confirmation
        try:
            retval, points = self._cv_detector.detect(gray)
            if retval and points is not None:
                score = max(score, 0.8)
        except Exception:
            pass

        return score

    def perspective_correct(self, image: np.ndarray,
                           points: np.ndarray) -> Optional[np.ndarray]:
        """
        Apply perspective correction to straighten a skewed QR code.

        Args:
            image: Source image
            points: Four corner points of the QR code

        Returns:
            Perspective-corrected image or None on failure
        """
        try:
            points = np.array(points, dtype=np.float32)
            if points.shape[0] != 4:
                return None

            # Order points: top-left, top-right, bottom-right, bottom-left
            ordered = self._order_points(points)

            # Calculate output dimensions
            w1 = np.linalg.norm(ordered[1] - ordered[0])
            w2 = np.linalg.norm(ordered[2] - ordered[3])
            h1 = np.linalg.norm(ordered[3] - ordered[0])
            h2 = np.linalg.norm(ordered[2] - ordered[1])

            max_w = int(max(w1, w2))
            max_h = int(max(h1, h2))

            if max_w < 10 or max_h < 10:
                return None

            dst = np.array([
                [0, 0],
                [max_w - 1, 0],
                [max_w - 1, max_h - 1],
                [0, max_h - 1]
            ], dtype=np.float32)

            M = cv2.getPerspectiveTransform(ordered, dst)
            corrected = cv2.warpPerspective(image, M, (max_w, max_h))
            return corrected
        except Exception as e:
            logger.debug(f"Perspective correction failed: {e}")
            return None

    def _detect_with_opencv(self, image: np.ndarray) -> List[dict]:
        """Detect QR codes using OpenCV's built-in detector."""
        regions = []
        gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        try:
            retval, points = self._cv_detector.detect(gray)
            if retval and points is not None:
                for pts in points:
                    pts = pts.astype(np.int32)
                    x, y, w, h = cv2.boundingRect(pts)
                    center = (x + w // 2, y + h // 2)
                    area = w * h

                    # Crop the region
                    pad = 10
                    ih, iw = image.shape[:2]
                    x1, y1 = max(0, x - pad), max(0, y - pad)
                    x2, y2 = min(iw, x + w + pad), min(ih, y + h + pad)
                    cropped = image[y1:y2, x1:x2].copy()

                    regions.append({
                        'bbox': pts,
                        'center': center,
                        'area': area,
                        'cropped': cropped,
                        'confidence': 0.9,
                        'source': 'opencv'
                    })
        except Exception as e:
            logger.debug(f"OpenCV QR detect failed: {e}")

        return regions

    def _detect_with_contours(self, image: np.ndarray) -> List[dict]:
        """Detect QR candidate regions using contour analysis."""
        regions = []
        gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 51, 10
        )

        contours, hierarchy = cv2.findContours(
            binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        if hierarchy is None:
            return regions

        ih, iw = image.shape[:2]
        image_area = ih * iw

        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            # Filter by size (QR code should be reasonable size)
            if area < image_area * 0.001 or area > image_area * 0.95:
                continue

            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

            # Look for quadrilateral shapes
            if 4 <= len(approx) <= 8:
                x, y, w, h = cv2.boundingRect(contour)
                aspect = w / max(h, 1)

                # QR codes are roughly square
                if 0.5 < aspect < 2.0:
                    # Check for nested contours (finder pattern)
                    child_idx = hierarchy[0][i][2]
                    nesting_depth = 0
                    while child_idx != -1 and nesting_depth < 5:
                        nesting_depth += 1
                        child_idx = hierarchy[0][child_idx][2]

                    if nesting_depth >= 2:  # Finder patterns have nested squares
                        pad = 15
                        x1, y1 = max(0, x - pad), max(0, y - pad)
                        x2, y2 = min(iw, x + w + pad), min(ih, y + h + pad)
                        cropped = image[y1:y2, x1:x2].copy()

                        regions.append({
                            'bbox': approx.reshape(-1, 2),
                            'center': (x + w // 2, y + h // 2),
                            'area': area,
                            'cropped': cropped,
                            'confidence': min(0.3 + nesting_depth * 0.15, 0.75),
                            'source': 'contour'
                        })

        return regions

    def _deduplicate(self, regions: List[dict], overlap_threshold: float = 0.5) -> List[dict]:
        """Remove overlapping regions, keeping highest confidence."""
        if len(regions) <= 1:
            return regions

        # Sort by confidence descending
        regions.sort(key=lambda r: r['confidence'], reverse=True)

        kept = []
        for region in regions:
            x1, y1, w1, h1 = cv2.boundingRect(np.array(region['bbox']))
            is_duplicate = False

            for kept_region in kept:
                x2, y2, w2, h2 = cv2.boundingRect(np.array(kept_region['bbox']))

                # Calculate IoU
                ix1 = max(x1, x2)
                iy1 = max(y1, y2)
                ix2 = min(x1 + w1, x2 + w2)
                iy2 = min(y1 + h1, y2 + h2)

                if ix2 > ix1 and iy2 > iy1:
                    intersection = (ix2 - ix1) * (iy2 - iy1)
                    union = w1 * h1 + w2 * h2 - intersection
                    iou = intersection / max(union, 1)
                    if iou > overlap_threshold:
                        is_duplicate = True
                        break

            if not is_duplicate:
                kept.append(region)

        return kept

    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Order points as: top-left, top-right, bottom-right, bottom-left."""
        rect = np.zeros((4, 2), dtype=np.float32)

        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        d = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(d)]
        rect[3] = pts[np.argmax(d)]

        return rect
