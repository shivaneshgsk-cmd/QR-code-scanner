"""
video_decoder.py — Video Processing Workflow Orchestrator

Implements the complete video QR decode pipeline:
1. Read video frame by frame
2. Extract frames at configurable intervals
3. Score and rank frames by quality
4. Decode best frame → if fail → enhance best frame → try top N frames
"""

import time
import logging
from pathlib import Path
from typing import Optional, Callable, List, Tuple

import cv2
import numpy as np

from core.zxing_decoder import ZXingDecoder, DecodeResult
from core.enhancer import ImageEnhancer
from core.frame_selector import FrameSelector
from core.qr_detector import QRDetector

logger = logging.getLogger(__name__)


class VideoDecoder:
    """
    Orchestrates QR code decoding from videos.

    Workflow:
    1. Open video, extract frames at configurable intervals
    2. Score each frame (sharpness, contrast, QR visibility, brightness)
    3. Rank frames, select best
    4. Attempt direct decode on best frame
    5. If failed → apply enhancement pipeline to best frame
    6. If still failed → try top N frames with enhancement
    """

    DEFAULT_FRAME_INTERVAL = 0.5  # seconds
    TOP_N_FRAMES = 10

    def __init__(self):
        """Initialize video decoder with sub-components."""
        self.zxing = ZXingDecoder()
        self.enhancer = ImageEnhancer()
        self.frame_selector = FrameSelector()
        self.detector = QRDetector()
        self._processing = False
        self._cancel_flag = False
        logger.info("VideoDecoder initialized")

    @property
    def is_processing(self) -> bool:
        return self._processing

    def cancel(self):
        """Request cancellation of current processing."""
        self._cancel_flag = True

    def decode_file(self, file_path: str,
                    frame_interval: float = None,
                    top_n: int = None,
                    progress_callback: Optional[Callable] = None,
                    status_callback: Optional[Callable] = None) -> dict:
        """
        Decode QR code(s) from a video file.

        Args:
            file_path: Path to video file
            frame_interval: Seconds between sampled frames
            top_n: Number of top frames to try
            progress_callback: Optional callback(progress_percent)
            status_callback: Optional callback(status_message)

        Returns:
            Dict with keys: results, best_frame_idx, frame_score,
            enhancement_used, processing_time, total_frames, success
        """
        self._processing = True
        self._cancel_flag = False
        start_time = time.time()

        if frame_interval is None:
            frame_interval = self.DEFAULT_FRAME_INTERVAL
        if top_n is None:
            top_n = self.TOP_N_FRAMES

        result = {
            'results': [],
            'best_frame_idx': -1,
            'frame_score': 0.0,
            'enhancement_used': 'None',
            'processing_time': 0.0,
            'total_frames': 0,
            'frames_analyzed': 0,
            'success': False,
            'file_path': file_path,
        }

        try:
            # Step 1: Open video and extract frames
            if status_callback:
                status_callback("Opening video...")
            if progress_callback:
                progress_callback(5)

            cap = cv2.VideoCapture(str(file_path))
            if not cap.isOpened():
                result['enhancement_used'] = 'ERROR: Could not open video'
                if status_callback:
                    status_callback("❌ Failed to open video file")
                return result

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            result['total_frames'] = total_frames

            frame_step = max(1, int(fps * frame_interval))

            if status_callback:
                status_callback(f"Video: {total_frames} frames @ {fps:.1f} FPS")

            # Step 2: Extract frames at intervals
            if status_callback:
                status_callback("Extracting frames...")

            frames = []
            frame_idx = 0

            while True:
                if self._cancel_flag:
                    result['enhancement_used'] = 'CANCELLED'
                    return result

                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_step == 0:
                    frames.append((frame_idx, frame.copy()))

                frame_idx += 1

                # Progress update
                if progress_callback and total_frames > 0:
                    pct = 5 + int((frame_idx / total_frames) * 25)
                    progress_callback(min(pct, 30))

            cap.release()
            result['frames_analyzed'] = len(frames)

            if not frames:
                result['enhancement_used'] = 'ERROR: No frames extracted'
                if status_callback:
                    status_callback("❌ No frames could be extracted")
                return result

            if status_callback:
                status_callback(f"Extracted {len(frames)} frames, ranking...")
            if progress_callback:
                progress_callback(35)

            # Step 3: Score and rank frames
            ranked = self.frame_selector.rank_frames(frames, top_n=top_n)

            if not ranked:
                result['enhancement_used'] = 'ERROR: Frame ranking failed'
                return result

            best_idx, best_score, best_frame = ranked[0]
            result['best_frame_idx'] = best_idx
            result['frame_score'] = best_score

            h, w = best_frame.shape[:2]
            result['image_resolution'] = f"{w}x{h}"

            if status_callback:
                status_callback(f"Best frame: #{best_idx} (score: {best_score:.3f})")
            if progress_callback:
                progress_callback(40)

            # Step 4: Attempt direct decode on best frame
            if status_callback:
                status_callback("Decoding best frame...")

            direct_results = self.zxing.decode(best_frame, try_harder=True)
            if direct_results:
                for r in direct_results:
                    r.frame_number = best_idx
                result['results'] = direct_results
                result['enhancement_used'] = 'None (direct decode)'
                result['success'] = True
                result['processing_time'] = round(time.time() - start_time, 3)
                if status_callback:
                    status_callback(f"✅ Decoded from frame #{best_idx}")
                if progress_callback:
                    progress_callback(100)
                return result

            # Step 5: Enhancement pipeline on best frame
            if status_callback:
                status_callback("Enhancing best frame...")
            if progress_callback:
                progress_callback(50)

            enhancements = self.enhancer.enhance_progressively(best_frame)
            total_enh = len(enhancements)

            for i, (name, enhanced) in enumerate(enhancements):
                if self._cancel_flag:
                    result['enhancement_used'] = 'CANCELLED'
                    return result

                decode_results = self.zxing.decode_single(enhanced, name)
                if decode_results:
                    for r in decode_results:
                        r.frame_number = best_idx
                    result['results'] = decode_results
                    result['enhancement_used'] = f"Frame#{best_idx} + {name}"
                    result['success'] = True
                    result['processing_time'] = round(time.time() - start_time, 3)
                    if status_callback:
                        status_callback(f"✅ Decoded: Frame #{best_idx} + {name}")
                    if progress_callback:
                        progress_callback(100)
                    return result

                if progress_callback:
                    pct = 50 + int((i / max(total_enh, 1)) * 25)
                    progress_callback(min(pct, 75))

            # Step 6: Try top N frames with enhancement
            if status_callback:
                status_callback(f"Trying top {len(ranked)} frames...")
            if progress_callback:
                progress_callback(80)

            for rank, (fidx, fscore, frame) in enumerate(ranked[1:], start=2):
                if self._cancel_flag:
                    result['enhancement_used'] = 'CANCELLED'
                    return result

                if status_callback:
                    status_callback(f"Frame #{fidx} (rank {rank}, score {fscore:.3f})...")

                # Direct decode
                direct = self.zxing.decode(frame, try_harder=True)
                if direct:
                    for r in direct:
                        r.frame_number = fidx
                    result['results'] = direct
                    result['enhancement_used'] = f'Frame#{fidx} (direct)'
                    result['success'] = True
                    result['processing_time'] = round(time.time() - start_time, 3)
                    if status_callback:
                        status_callback(f"✅ Decoded from frame #{fidx}")
                    if progress_callback:
                        progress_callback(100)
                    return result

                # Enhanced decode
                frame_enhancements = self.enhancer.enhance_progressively(frame)
                for name, enhanced in frame_enhancements:
                    if self._cancel_flag:
                        result['enhancement_used'] = 'CANCELLED'
                        return result

                    enh_results = self.zxing.decode_single(enhanced, name)
                    if enh_results:
                        for r in enh_results:
                            r.frame_number = fidx
                        result['results'] = enh_results
                        result['enhancement_used'] = f"Frame#{fidx} + {name}"
                        result['success'] = True
                        result['processing_time'] = round(time.time() - start_time, 3)
                        if status_callback:
                            status_callback(f"✅ Decoded: Frame #{fidx} + {name}")
                        if progress_callback:
                            progress_callback(100)
                        return result

                if progress_callback:
                    pct = 80 + int((rank / len(ranked)) * 18)
                    progress_callback(min(pct, 98))

            # Failed all attempts
            result['processing_time'] = round(time.time() - start_time, 3)
            result['enhancement_used'] = 'All frames and enhancements attempted'
            if status_callback:
                status_callback("❌ QR code could not be decoded from video")
            if progress_callback:
                progress_callback(100)
            return result

        except Exception as e:
            logger.error(f"Video decode error: {e}", exc_info=True)
            result['enhancement_used'] = f'ERROR: {str(e)}'
            result['processing_time'] = round(time.time() - start_time, 3)
            if status_callback:
                status_callback(f"❌ Error: {str(e)}")
            return result

        finally:
            self._processing = False
            self._cancel_flag = False

    def get_video_info(self, file_path: str) -> dict:
        """Get basic video information."""
        try:
            cap = cv2.VideoCapture(str(file_path))
            if not cap.isOpened():
                return {'error': 'Could not open video'}

            info = {
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'total_frames': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1),
            }
            cap.release()
            return info
        except Exception as e:
            return {'error': str(e)}
