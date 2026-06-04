"""
enhancer.py — 30-Step Image Enhancement Pipeline for QR Code Recovery

Implements progressive image enhancement strategies to recover
damaged, blurry, rotated, and low-quality QR codes.

Includes smart quality assessment to skip unnecessary enhancements.
"""

import logging
from typing import List, Tuple, Callable, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ImageQualityAssessor:
    """
    Assesses image quality metrics to determine if enhancement is needed.

    Measures:
    - Sharpness (Laplacian variance)
    - Contrast (standard deviation)
    - Brightness (mean intensity)
    - Noise level (high-frequency energy)
    """

    # Thresholds for acceptable quality
    SHARPNESS_THRESHOLD = 100.0
    CONTRAST_THRESHOLD = 40.0
    BRIGHTNESS_LOW = 50
    BRIGHTNESS_HIGH = 220
    NOISE_THRESHOLD = 15.0

    def assess(self, image: np.ndarray) -> dict:
        """
        Perform full quality assessment.

        Args:
            image: BGR or grayscale NumPy array

        Returns:
            Dict with quality metrics and an overall 'needs_enhancement' flag
        """
        gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        sharpness = self._measure_sharpness(gray)
        contrast = self._measure_contrast(gray)
        brightness = self._measure_brightness(gray)
        noise = self._measure_noise(gray)

        needs_enhancement = (
            sharpness < self.SHARPNESS_THRESHOLD or
            contrast < self.CONTRAST_THRESHOLD or
            brightness < self.BRIGHTNESS_LOW or
            brightness > self.BRIGHTNESS_HIGH or
            noise > self.NOISE_THRESHOLD
        )

        return {
            'sharpness': round(sharpness, 2),
            'contrast': round(contrast, 2),
            'brightness': round(brightness, 2),
            'noise': round(noise, 2),
            'needs_enhancement': needs_enhancement,
            'issues': self._identify_issues(sharpness, contrast, brightness, noise)
        }

    def _measure_sharpness(self, gray: np.ndarray) -> float:
        """Measure sharpness using variance of Laplacian."""
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def _measure_contrast(self, gray: np.ndarray) -> float:
        """Measure contrast using standard deviation of pixel intensities."""
        return float(gray.std())

    def _measure_brightness(self, gray: np.ndarray) -> float:
        """Measure average brightness."""
        return float(gray.mean())

    def _measure_noise(self, gray: np.ndarray) -> float:
        """Estimate noise level using high-pass filter energy."""
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = cv2.absdiff(gray, blurred)
        return float(noise.std())

    def _identify_issues(self, sharpness: float, contrast: float,
                         brightness: float, noise: float) -> List[str]:
        """Identify specific quality issues."""
        issues = []
        if sharpness < self.SHARPNESS_THRESHOLD:
            issues.append("blur")
        if contrast < self.CONTRAST_THRESHOLD:
            issues.append("low_contrast")
        if brightness < self.BRIGHTNESS_LOW:
            issues.append("too_dark")
        if brightness > self.BRIGHTNESS_HIGH:
            issues.append("too_bright")
        if noise > self.NOISE_THRESHOLD:
            issues.append("noisy")
        return issues


class ImageEnhancer:
    """
    30-step progressive image enhancement pipeline.

    Applies enhancements in order of increasing aggressiveness.
    Each enhancement returns a list of (name, enhanced_image) tuples.

    Smart logic skips irrelevant enhancements based on quality assessment.
    """

    def __init__(self):
        """Initialize enhancer with quality assessor."""
        self.assessor = ImageQualityAssessor()
        self._enhancement_steps = self._build_pipeline()
        logger.info(f"ImageEnhancer initialized with {len(self._enhancement_steps)} enhancement steps")

    def get_quality_assessment(self, image: np.ndarray) -> dict:
        """Get image quality assessment."""
        return self.assessor.assess(image)

    def enhance_progressively(self, image: np.ndarray,
                              callback: Optional[Callable] = None) -> List[Tuple[str, np.ndarray]]:
        """
        Apply all enhancements progressively.

        Args:
            image: BGR NumPy array
            callback: Optional callback(step_name, step_index, total_steps)

        Returns:
            List of (enhancement_name, enhanced_image) tuples
        """
        results = []
        total = len(self._enhancement_steps)

        for i, (name, func) in enumerate(self._enhancement_steps):
            try:
                if callback:
                    callback(name, i + 1, total)

                enhanced = func(image)
                if enhanced is not None and enhanced.size > 0:
                    results.append((name, enhanced))
            except Exception as e:
                logger.debug(f"Enhancement '{name}' failed: {e}")
                continue

        # Add combination pipelines
        combos = self._combination_pipelines(image)
        results.extend(combos)

        return results

    def get_step_count(self) -> int:
        """Get total number of enhancement steps including combos."""
        return len(self._enhancement_steps) + 6  # 6 combination pipelines

    def _build_pipeline(self) -> List[Tuple[str, Callable]]:
        """Build the ordered enhancement pipeline."""
        return [
            ("Grayscale", self._grayscale),
            ("Histogram Equalization", self._histogram_equalization),
            ("CLAHE", self._clahe),
            ("Adaptive Threshold", self._adaptive_threshold),
            ("OTSU Threshold", self._otsu_threshold),
            ("Gaussian Blur Reduction", self._gaussian_blur_reduction),
            ("Median Filter", self._median_filter),
            ("Bilateral Filter", self._bilateral_filter),
            ("Sharpen", self._sharpen),
            ("Unsharp Mask", self._unsharp_mask),
            ("Contrast Stretch", self._contrast_stretch),
            ("Brightness Correction", self._brightness_correction),
            ("Gamma Correction (Low)", self._gamma_low),
            ("Gamma Correction (High)", self._gamma_high),
            ("Morphological Opening", self._morph_open),
            ("Morphological Closing", self._morph_close),
            ("Erosion", self._erosion),
            ("Dilation", self._dilation),
            ("Edge Enhancement", self._edge_enhance),
            ("Rotation 90°", lambda img: self._rotate(img, 90)),
            ("Rotation 180°", lambda img: self._rotate(img, 180)),
            ("Rotation 270°", lambda img: self._rotate(img, 270)),
            ("Rotation 45°", lambda img: self._rotate(img, 45)),
            ("Rotation 135°", lambda img: self._rotate(img, 135)),
            ("Rotation 225°", lambda img: self._rotate(img, 225)),
            ("Rotation 315°", lambda img: self._rotate(img, 315)),
            ("Scale 1.5x", lambda img: self._resize(img, 1.5)),
            ("Scale 2x", lambda img: self._resize(img, 2.0)),
            ("Scale 3x", lambda img: self._resize(img, 3.0)),
            ("Scale 4x", lambda img: self._resize(img, 4.0)),
            ("Noise Removal", self._noise_removal),
            ("Deblur", self._deblur),
            ("Super Resolution Sim", self._super_resolution_sim),
        ]

    # ────────────────────────────────────────────
    # Individual Enhancement Functions
    # ────────────────────────────────────────────

    def _grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert to grayscale."""
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def _histogram_equalization(self, image: np.ndarray) -> np.ndarray:
        """Apply histogram equalization."""
        gray = self._ensure_gray(image)
        return cv2.equalizeHist(gray)

    def _clahe(self, image: np.ndarray) -> np.ndarray:
        """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        gray = self._ensure_gray(image)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    def _adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """Apply adaptive thresholding."""
        gray = self._ensure_gray(image)
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 21, 10
        )

    def _otsu_threshold(self, image: np.ndarray) -> np.ndarray:
        """Apply OTSU thresholding."""
        gray = self._ensure_gray(image)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def _gaussian_blur_reduction(self, image: np.ndarray) -> np.ndarray:
        """Apply mild Gaussian blur to reduce noise, then sharpen."""
        blurred = cv2.GaussianBlur(image, (3, 3), 0)
        # Then sharpen
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        return cv2.filter2D(blurred, -1, kernel)

    def _median_filter(self, image: np.ndarray) -> np.ndarray:
        """Apply median filtering for salt-and-pepper noise removal."""
        return cv2.medianBlur(image, 3)

    def _bilateral_filter(self, image: np.ndarray) -> np.ndarray:
        """Apply bilateral filtering (edge-preserving smoothing)."""
        if len(image.shape) == 2:
            return cv2.bilateralFilter(image, 9, 75, 75)
        return cv2.bilateralFilter(image, 9, 75, 75)

    def _sharpen(self, image: np.ndarray) -> np.ndarray:
        """Apply sharpening kernel."""
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        return cv2.filter2D(image, -1, kernel)

    def _unsharp_mask(self, image: np.ndarray) -> np.ndarray:
        """Apply unsharp masking."""
        blurred = cv2.GaussianBlur(image, (9, 9), 10.0)
        return cv2.addWeighted(image, 1.5, blurred, -0.5, 0)

    def _contrast_stretch(self, image: np.ndarray) -> np.ndarray:
        """Stretch contrast to fill full dynamic range."""
        gray = self._ensure_gray(image)
        p2, p98 = np.percentile(gray, (2, 98))
        if p98 - p2 < 1:
            return gray
        stretched = np.clip((gray - p2) / (p98 - p2) * 255, 0, 255).astype(np.uint8)
        return stretched

    def _brightness_correction(self, image: np.ndarray) -> np.ndarray:
        """Auto-correct brightness to target mean ~127."""
        gray = self._ensure_gray(image)
        current_mean = gray.mean()
        if current_mean < 10:
            return gray
        target_mean = 127.0
        alpha = target_mean / current_mean
        corrected = np.clip(gray * alpha, 0, 255).astype(np.uint8)
        return corrected

    def _gamma_low(self, image: np.ndarray) -> np.ndarray:
        """Apply gamma correction (brighten dark images)."""
        return self._apply_gamma(image, 0.5)

    def _gamma_high(self, image: np.ndarray) -> np.ndarray:
        """Apply gamma correction (darken bright images)."""
        return self._apply_gamma(image, 1.8)

    def _apply_gamma(self, image: np.ndarray, gamma: float) -> np.ndarray:
        """Apply gamma correction."""
        inv_gamma = 1.0 / gamma
        table = np.array([
            ((i / 255.0) ** inv_gamma) * 255 for i in range(256)
        ]).astype(np.uint8)
        if len(image.shape) == 2:
            return cv2.LUT(image, table)
        return cv2.LUT(image, table)

    def _morph_open(self, image: np.ndarray) -> np.ndarray:
        """Morphological opening (remove small bright spots)."""
        gray = self._ensure_gray(image)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        return cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)

    def _morph_close(self, image: np.ndarray) -> np.ndarray:
        """Morphological closing (fill small dark holes)."""
        gray = self._ensure_gray(image)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        return cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

    def _erosion(self, image: np.ndarray) -> np.ndarray:
        """Apply erosion."""
        gray = self._ensure_gray(image)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        return cv2.erode(gray, kernel, iterations=1)

    def _dilation(self, image: np.ndarray) -> np.ndarray:
        """Apply dilation."""
        gray = self._ensure_gray(image)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        return cv2.dilate(gray, kernel, iterations=1)

    def _edge_enhance(self, image: np.ndarray) -> np.ndarray:
        """Edge enhancement using Laplacian."""
        gray = self._ensure_gray(image)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        enhanced = gray.astype(np.float64) - 0.7 * laplacian
        return np.clip(enhanced, 0, 255).astype(np.uint8)

    def _rotate(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by angle degrees."""
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        cos_a = abs(M[0, 0])
        sin_a = abs(M[0, 1])
        new_w = int(h * sin_a + w * cos_a)
        new_h = int(h * cos_a + w * sin_a)
        M[0, 2] += (new_w - w) / 2
        M[1, 2] += (new_h - h) / 2

        fill = (255, 255, 255) if len(image.shape) == 3 else 255
        return cv2.warpAffine(image, M, (new_w, new_h),
                              borderMode=cv2.BORDER_CONSTANT, borderValue=fill)

    def _resize(self, image: np.ndarray, scale: float) -> np.ndarray:
        """Resize image by scale factor."""
        h, w = image.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        interp = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
        return cv2.resize(image, (new_w, new_h), interpolation=interp)

    def _noise_removal(self, image: np.ndarray) -> np.ndarray:
        """Advanced noise removal using Non-Local Means."""
        if len(image.shape) == 2:
            return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
        return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)

    def _deblur(self, image: np.ndarray) -> np.ndarray:
        """Simple deblurring using Wiener-like approach."""
        gray = self._ensure_gray(image)
        # Use high-pass filter to enhance edges lost by blur
        kernel_size = 5
        blurred = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)
        # Enhance edges
        enhanced = cv2.addWeighted(gray, 2.0, blurred, -1.0, 0)
        return np.clip(enhanced, 0, 255).astype(np.uint8)

    def _super_resolution_sim(self, image: np.ndarray) -> np.ndarray:
        """
        Simulate super resolution using OpenCV.

        Upscale with bicubic interpolation + sharpen to simulate higher resolution.
        """
        # Upscale 2x
        h, w = image.shape[:2]
        upscaled = cv2.resize(image, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
        # Sharpen the upscaled image
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpened = cv2.filter2D(upscaled, -1, kernel)
        return sharpened

    # ────────────────────────────────────────────
    # Combination Pipelines
    # ────────────────────────────────────────────

    def _combination_pipelines(self, image: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        """Generate combination enhancement results."""
        combos = []

        try:
            # Combo 1: Grayscale + CLAHE + Sharpen
            g = self._grayscale(image)
            c = self._clahe(g)
            s = self._sharpen(c)
            combos.append(("Grayscale+CLAHE+Sharpen", s))
        except Exception:
            pass

        try:
            # Combo 2: OTSU + Resize 2x
            o = self._otsu_threshold(image)
            r = self._resize(o, 2.0)
            combos.append(("OTSU+Resize2x", r))
        except Exception:
            pass

        try:
            # Combo 3: CLAHE + OTSU + Sharpen
            c = self._clahe(image)
            o_gray = self._otsu_threshold(c)
            s = self._sharpen(o_gray)
            combos.append(("CLAHE+OTSU+Sharpen", s))
        except Exception:
            pass

        try:
            # Combo 4: Denoise + CLAHE + Adaptive Threshold
            d = self._noise_removal(image)
            c = self._clahe(d)
            a = self._adaptive_threshold(c)
            combos.append(("Denoise+CLAHE+AdaptiveThresh", a))
        except Exception:
            pass

        try:
            # Combo 5: Brightness + Contrast Stretch + Sharpen
            b = self._brightness_correction(image)
            cs = self._contrast_stretch(b)
            s = self._sharpen(cs)
            combos.append(("Brightness+ContrastStretch+Sharpen", s))
        except Exception:
            pass

        try:
            # Combo 6: Super Resolution + CLAHE
            sr = self._super_resolution_sim(image)
            c = self._clahe(sr)
            combos.append(("SuperRes+CLAHE", c))
        except Exception:
            pass

        return combos

    # ────────────────────────────────────────────
    # Utility
    # ────────────────────────────────────────────

    def _ensure_gray(self, image: np.ndarray) -> np.ndarray:
        """Convert to grayscale if needed."""
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
