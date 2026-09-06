"""
Video processing utilities wrapping OpenCV functionality.
"""
import cv2
import numpy as np
from typing import Generator, Optional
from pathlib import Path
from core.logger import setup_logger

logger = setup_logger(__name__)

class VideoProcessor:
    """
    Utility class for reading from and writing to video files using OpenCV.
    Abstracts away the low-level cv2 VideoCapture and VideoWriter details.
    """
    
    def __init__(self, input_path: str):
        self.input_path = input_path
        self._cap: Optional[cv2.VideoCapture] = None
        self._writer: Optional[cv2.VideoWriter] = None
        
        # Video properties
        self.fps = 0.0
        self.width = 0
        self.height = 0
        self.frame_count = 0
        
    def open(self) -> bool:
        """Opens the video file for reading and populates properties."""
        self._cap = cv2.VideoCapture(self.input_path)
        if not self._cap.isOpened():
            logger.error(f"Failed to open video at: {self.input_path}")
            return False
            
        self.fps = self._cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"Opened video: {self.input_path} ({self.width}x{self.height} @ {self.fps}fps)")
        return True
        
    def setup_writer(self, output_path: str) -> bool:
        """
        Sets up the OpenCV VideoWriter.
        
        Args:
            output_path: Path where the output video will be saved.
            
        Returns:
            bool: True if writer was successfully initialized, False otherwise.
        """
        if self.width == 0 or self.height == 0:
            logger.error("Cannot setup writer: video properties not initialized. Call open() first.")
            return False
            
        # Target 480p width for stability and memory efficiency on long videos
        target_width = min(self.width, 854)
        if target_width < self.width:
            scale = target_width / self.width
            self.width = target_width
            self.height = int(self.height * scale)
            logger.info(f"Output video will be downscaled to {self.width}x{self.height} (480p max) for stability.")
            
        # Fallback codec strategy: try 'mp4v' first, then 'avc1', then 'XVID'
        for codec_str in ('mp4v', 'avc1', 'XVID'):
            fourcc = cv2.VideoWriter_fourcc(*codec_str)
            self._writer = cv2.VideoWriter(output_path, fourcc, self.fps, (self.width, self.height))
            if self._writer.isOpened():
                logger.info(f"Writer setup complete for: {output_path} (Codec: {codec_str})")
                return True
            logger.warning(f"Video writer failed with codec {codec_str}, trying next codec.")

        logger.error(f"Failed to create video writer at: {output_path} with available codecs.")
        return False
            
        logger.info(f"Writer setup complete for: {output_path} (Codec: {codec_str})")
        return True
        
    def write_frame(self, frame: np.ndarray) -> None:
        """Writes a single frame to the output video."""
        if self._writer is None or not self._writer.isOpened():
            logger.warning("Writer is not open. Skipping frame write.")
            return
            
        self._writer.write(frame)

    def close_writer(self) -> None:
        """Releases the video writer resource so the output file is flushed and finalized."""
        if self._writer is not None:
            self._writer.release()
            self._writer = None
            logger.info("Video writer released.")
        
    def rewind(self) -> bool:
        """Seeks the capture back to the first frame."""
        if self._cap is None:
            logger.warning("Cannot rewind: capture is not initialized.")
            return False
        res = self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        current_pos = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES)) if self._cap else -1
        if not res or current_pos != 0:
            if self._cap is not None:
                self._cap.release()
            self._cap = cv2.VideoCapture(self.input_path)
            return self._cap.isOpened()
        return True

    def generate_frames(self) -> Generator[np.ndarray, None, None]:
        """
        Yields frames from the video sequentially.
        
        Yields:
            np.ndarray: The video frame as a NumPy array (BGR format).
        """
        if self._cap is None or not self._cap.isOpened():
            logger.error("Video capture is not open. Cannot generate frames.")
            return
            
        frame_idx = 0
        while True:
            ret, frame = self._cap.read()
            if not ret:
                break
                
            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_AREA)
                
            yield frame
            frame_idx += 1
            
            if frame_idx % 100 == 0:
                logger.debug(f"Processed {frame_idx}/{self.frame_count} frames")
                
    def close(self) -> None:
        """Releases video capture and writer resources."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            
        if self._writer is not None:
            self._writer.release()
            self._writer = None
            
        logger.info("Video resources released.")

    @staticmethod
    def ensure_browser_compatible_mp4(output_path: str, duration_seconds: Optional[float] = None) -> tuple[bool, str]:
        """
        Transcodes an OpenCV output video to web-compatible H.264 (avc1) format with +faststart
        so that modern browsers (Chrome, Edge, Firefox) can stream and play it natively.
        
        Returns:
            tuple[bool, str]: (is_h264_success, codec_description)
        """
        import shutil
        import subprocess
        
        path_obj = Path(output_path)
        if not path_obj.exists() or path_obj.stat().st_size < 5 * 1024:
            return False, "Invalid / Empty File"

        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            logger.warning("[VIDEO] FFmpeg binary not found in PATH. Retaining raw OpenCV MP4 format.")
            return False, "mp4v (OpenCV Fallback, FFmpeg unavailable)"

        temp_h264 = path_obj.with_name(f"{path_obj.stem}_h264.mp4")
        cmd = [
            ffmpeg_bin, "-y", "-nostdin", "-i", str(path_obj),
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(temp_h264)
        ]
        
        # Dynamic timeout: scale with duration (e.g. at least 30s, or 3x duration)
        calc_timeout = max(30, int((duration_seconds or 0) * 3))
        
        try:
            res = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=calc_timeout,
                check=False
            )
            if res.returncode == 0 and temp_h264.exists() and temp_h264.stat().st_size > 5 * 1024:
                temp_h264.replace(path_obj)
                logger.info(f"[VIDEO] Video successfully transcoded to web-optimized H.264 format: {output_path}")
                return True, "H.264 (avc1)"
            else:
                if temp_h264.exists():
                    try:
                        temp_h264.unlink(missing_ok=True)
                    except Exception:
                        pass
                logger.warning(f"[VIDEO] H.264 transcoding produced invalid output (exit code {res.returncode}). Retaining raw OpenCV MP4 fallback: {output_path}")
                return False, "mp4v (OpenCV Fallback)"
        except subprocess.TimeoutExpired:
            logger.warning(f"[VIDEO] H.264 transcoding timed out after {calc_timeout}s for: {output_path}. Retaining raw OpenCV MP4 fallback.")
            if temp_h264.exists():
                try:
                    temp_h264.unlink(missing_ok=True)
                except Exception:
                    pass
            return False, "mp4v (OpenCV Fallback, Transcoding Timed Out)"
        except Exception as e:
            logger.warning(f"[VIDEO] H.264 transcoding encountered an error: {str(e)}. Retaining raw OpenCV MP4 fallback.")
            if temp_h264.exists():
                try:
                    temp_h264.unlink(missing_ok=True)
                except Exception:
                    pass
            return False, f"mp4v (OpenCV Fallback: {e})"

    @staticmethod
    def validate_export(output_path: str) -> bool:
        """
        Validates that the exported video file is functional.
        Attempts H.264 web transcoding and validates the resulting file with OpenCV.
        
        Args:
            output_path: The file path to validate.
            
        Returns:
            bool: True if valid and playable, False if broken or empty.
        """
        import os
        path_obj = Path(output_path)
        
        # 1. Check initial file exists
        if not path_obj.exists():
            logger.error(f"Export validation failed: File does not exist at {output_path}")
            return False
            
        # 2. Check initial file size (> 5 KB)
        initial_size = os.path.getsize(output_path)
        if initial_size < 5 * 1024:
            logger.error(f"Export validation failed: File size is only {initial_size} bytes (too small).")
            return False
            
        # 3. Verify initial video can be opened by OpenCV before running transcoding
        initial_cap = cv2.VideoCapture(output_path)
        if not initial_cap.isOpened():
            logger.error(f"Export validation failed: cv2.VideoCapture cannot open initial file {output_path}")
            return False

        fc = int(initial_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = initial_cap.get(cv2.CAP_PROP_FPS)
        dur = fc / fps if fps > 0 else 0.0
        ret, frame = initial_cap.read()
        initial_cap.release()

        if fc <= 0 or dur <= 0 or not ret or frame is None:
            logger.error(f"Export validation failed: File has invalid frames (count={fc}, duration={dur:.2f}s, readable={ret}).")
            return False

        # 4. Attempt H.264 web transcoding on valid video
        is_h264, codec_desc = VideoProcessor.ensure_browser_compatible_mp4(output_path, duration_seconds=dur)
        
        # 5. Verify the final file with OpenCV
        cap = cv2.VideoCapture(output_path)
        if not cap.isOpened():
            logger.error(f"Export validation failed: cv2.VideoCapture cannot reopen final file {output_path}")
            return False
            
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = frame_count / fps if fps > 0 else 0
        
        # Test reading the first frame
        ret, frame = cap.read()
        cap.release()
        
        if frame_count <= 0 or duration <= 0 or not ret or frame is None:
            logger.error("Export validation failed: Final file is unreadable.")
            return False
            
        final_size_bytes = os.path.getsize(output_path)
        logger.info(f"Export validation passed. Codec: {codec_desc}, Size: {final_size_bytes / (1024*1024):.2f} MB, Frames: {frame_count}, Duration: {duration:.2f}s")
        return True

    def __enter__(self):
        """Context manager support."""
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.close()

class VideoPreprocessor:
    """Applies optional auto exposure, contrast enhancement, and stabilization."""
    def __init__(self):
        self.prev_gray = None
        self.prev_transform = np.eye(3, dtype=np.float32)
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def preprocess(self, frame: np.ndarray, auto_exposure: bool = True,
                   auto_contrast: bool = True, stabilization: bool = False,
                   clahe_clip_limit: float = 2.0) -> np.ndarray:
        if frame is None:
            return frame

        processed = frame.copy()
        if auto_exposure or auto_contrast:
            processed = self._apply_clahe(processed, clahe_clip_limit)

        if stabilization:
            processed = self._stabilize_frame(processed)

        return processed

    def _apply_clahe(self, frame: np.ndarray, clip_limit: float) -> np.ndarray:
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        cl = self.clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def _stabilize_frame(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.prev_gray is None:
            self.prev_gray = gray
            return frame

        prev_pts = cv2.goodFeaturesToTrack(
            self.prev_gray, maxCorners=200, qualityLevel=0.01, minDistance=32, blockSize=7
        )
        if prev_pts is None:
            self.prev_gray = gray
            return frame

        next_pts, status, _ = cv2.calcOpticalFlowPyrLK(self.prev_gray, gray, prev_pts, None)
        if next_pts is None or status is None:
            self.prev_gray = gray
            return frame

        good_prev = prev_pts[status.flatten() == 1]
        good_next = next_pts[status.flatten() == 1]
        if len(good_prev) < 8 or len(good_next) < 8:
            self.prev_gray = gray
            return frame

        transform, inliers = cv2.estimateAffinePartial2D(good_prev, good_next)
        if transform is None:
            self.prev_gray = gray
            return frame

        stabilized = cv2.warpAffine(frame, transform, (frame.shape[1], frame.shape[0]), flags=cv2.INTER_LINEAR)
        self.prev_gray = gray
        return stabilized


def get_video_info(video_path: str) -> dict:
    """
    Extracts basic video information (fps, width, height, frame_count) using OpenCV.
    
    Args:
        video_path: Absolute path to the video file.
        
    Returns:
        dict: containing 'fps', 'width', 'height', 'frame_count'
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"fps": 0.0, "width": 0, "height": 0, "frame_count": 0}
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    
    return {
        "fps": fps,
        "width": width,
        "height": height,
        "frame_count": frame_count
    }

def prepare_static_video(output_video_path: str, st_base_dir: str) -> str:
    """
    Copies the processed video to the Streamlit static directory for HTML5 playback
    and sanitizes the filename.
    
    Args:
        output_video_path: Absolute path to the generated MP4 file.
        st_base_dir: Absolute path to the streamlit application directory.
        
    Returns:
        str: The URL path suitable for HTML5 `<video src="...">`.
    """
    import os
    import re
    import shutil
    
    if not output_video_path or not os.path.exists(output_video_path):
        return ""
        
    static_dir = os.path.join(st_base_dir, "static")
    os.makedirs(static_dir, exist_ok=True)
    
    basename = os.path.basename(output_video_path)
    # Sanitize basename to remove spaces/special chars
    safe_basename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', basename)
    
    # Optional timestamp to bypass browser cache
    import time
    ts = int(time.time())
    safe_basename = f"{ts}_{safe_basename}"
    
    static_video_path = os.path.join(static_dir, safe_basename)
    
    try:
        shutil.copy2(output_video_path, static_video_path)
        logger.info(f"Copied {output_video_path} to {static_video_path}")
        return f"app/static/{safe_basename}"
    except Exception as e:
        logger.error(f"Failed to copy video to static directory: {e}")
        return ""
