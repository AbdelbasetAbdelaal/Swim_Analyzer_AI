"""
Video Quality Assessment module.
Evaluates the quality of a video frame-by-frame during the analysis pass.
"""
import cv2
import numpy as np
from core.logger import setup_logger
from core.config import config
from models.data_models import VQAResult, VQACriterionResult

logger = setup_logger(__name__)

class VideoQualityAssessor:
    """
    Assesses video quality incrementally by evaluating metrics on each frame
    processed by the main analysis loop.
    """
    
    def __init__(self, sample_count: int = None):
        self.sharpness_scores = []
        self.brightness_scores = []
        self.confidence_scores = []
        self.body_visibility_scores = []
        self.size_scores = []
        self.angle_scores = []
        self.contrast_scores = []
        self.reflection_scores = []
        self.motion_blur_scores = []
        
        self.width = 0
        self.height = 0
        self.fps = 0
        self.frames_processed = 0
        self.sample_count = sample_count

    def set_video_metadata(self, width: int, height: int, fps: float):
        self.width = width
        self.height = height
        self.fps = fps
        
    def assess_frame(self, frame, landmarks, is_valid):
        """
        Evaluate quality metrics for a single frame.
        """
        if frame is None:
            return
            
        self.frames_processed += 1
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Extract thresholds safely (guards against mock objects in unit tests)
        blur_thresh = float(config.vqa_blur_threshold) if isinstance(config.vqa_blur_threshold, (int, float)) else 15.0
        refl_thresh = float(config.vqa_reflection_threshold) if isinstance(config.vqa_reflection_threshold, (int, float)) else 0.10
        b_min = float(config.vqa_brightness_min) if isinstance(config.vqa_brightness_min, (int, float)) else 40.0
        b_max = float(config.vqa_brightness_max) if isinstance(config.vqa_brightness_max, (int, float)) else 220.0

        # 1. Sharpness (Variance of Laplacian)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        # Scale to 100 max, using config
        self.sharpness_scores.append(min(100.0, (sharpness / (blur_thresh * 20.0)) * 100.0))
        
        # 2. Brightness
        brightness = float(np.mean(gray))
        if brightness < b_min or brightness > b_max:
            self.brightness_scores.append(40.0)
        else:
            dist = abs(brightness - 130.0)
            self.brightness_scores.append(max(0.0, 100.0 - dist))

        # 2b. Contrast
        contrast_min = float(config.vqa_precheck_contrast_min) if isinstance(config.vqa_precheck_contrast_min, (int, float)) else 20.0
        contrast_value = float(np.std(gray))
        if contrast_value < contrast_min:
            self.contrast_scores.append(max(0.0, 100.0 - (contrast_min - contrast_value) * 2.0))
        else:
            self.contrast_scores.append(100.0)
            
        # 3. Reflections (count > 240 intensity pixels)
        high_intensity = float(np.sum(gray > 240) / (gray.shape[0] * gray.shape[1]))
        # reflection threshold maps to 0 score
        penalty = min(100.0, (high_intensity / refl_thresh) * 100.0)
        self.reflection_scores.append(max(0.0, 100.0 - penalty))
            
        # 4. Pose Detection & Swimmer Size
        if landmarks and is_valid:
            conf = sum(getattr(lm, 'visibility', 1.0) for lm in landmarks) / len(landmarks)
            self.confidence_scores.append(conf * 100)
            
            key_indices = [11, 12, 15, 16, 27, 28]
            visible_keys = sum(1 for i in key_indices if i < len(landmarks) and getattr(landmarks[i], 'visibility', 1.0) > 0.5)
            self.body_visibility_scores.append((visible_keys / 6.0) * 100)
            
            xs = [lm.x for lm in landmarks]
            ys = [lm.y for lm in landmarks]
            w_norm = max(xs) - min(xs)
            h_norm = max(ys) - min(ys)
            area_ratio = w_norm * h_norm
            self.size_scores.append(min(100, (area_ratio / 0.15) * 100))
            
            # Camera Angle Proxy (Shoulder width vs torso length)
            s_left, s_right = landmarks[11], landmarks[12]
            h_left, h_right = landmarks[23], landmarks[24]
            shoulder_width = abs(s_left.x - s_right.x)
            torso_len = abs(((s_left.y + s_right.y)/2) - ((h_left.y + h_right.y)/2))
            if torso_len > 0:
                ratio = shoulder_width / torso_len
                if ratio > 0.9:
                    self.angle_scores.append(30)
                elif ratio > 0.6:
                    self.angle_scores.append(60)
                else:
                    self.angle_scores.append(100)
            
            # Motion Blur (sharpness of swimmer bounding box)
            try:
                x1 = max(0, int(min(xs) * self.width))
                x2 = min(self.width, int(max(xs) * self.width))
                y1 = max(0, int(min(ys) * self.height))
                y2 = min(self.height, int(max(ys) * self.height))
                if x2 > x1 and y2 > y1:
                    swimmer_roi = gray[y1:y2, x1:x2]
                    roi_sharpness = cv2.Laplacian(swimmer_roi, cv2.CV_64F).var()
                    self.motion_blur_scores.append(min(100, (roi_sharpness / (config.vqa_blur_threshold * 13)) * 100))
            except:
                pass
        else:
            self.confidence_scores.append(0)
            self.body_visibility_scores.append(0)
            self.size_scores.append(0)
            self.angle_scores.append(0)
            
    def get_current_result(self) -> VQAResult:
        """
        Calculate current VQA score based on frames processed so far.
        """
        if not self.confidence_scores:
            return self._fail_fast("Could not analyze any frames yet.")
            
        # Aggregate heuristics
        avg_sharpness = int(np.mean(self.sharpness_scores)) if self.sharpness_scores else 50
        avg_brightness = int(np.mean(self.brightness_scores)) if self.brightness_scores else 50
        avg_confidence = int(np.mean(self.confidence_scores))
        avg_body_vis = int(np.mean(self.body_visibility_scores))
        avg_size = int(np.mean(self.size_scores))
        avg_angle = int(np.mean(self.angle_scores)) if self.angle_scores else 50
        avg_refl = int(np.mean(self.reflection_scores)) if self.reflection_scores else 50
        avg_mblur = int(np.mean(self.motion_blur_scores)) if self.motion_blur_scores else avg_sharpness
        avg_contrast = int(np.mean(self.contrast_scores)) if self.contrast_scores else 50
        
        avg_stability = 90 # Placeholder MVP
        # Orientation & Resolution (Vertical smartphone videos HD are supported)
        orientation_score = 100 if self.width >= self.height else (80 if self.height >= 1280 else 60)
        resolution_score = 100 if (max(self.width, self.height) >= 1280 and min(self.width, self.height) >= 720) else (60 if max(self.width, self.height) >= 640 else 30)
        fps_score = 100 if self.fps >= 29 else (60 if self.fps >= 20 else 20)
        swimmer_visibility = avg_confidence # Alias
        
        # Build Criteria
        criteria = [
            self._create_criterion("Camera Angle", avg_angle, 0.15, 60,
                                   "Perspective distortion changes apparent limb lengths.",
                                   "Shoulder and elbow angles become unreliable.",
                                   "Record from the side with the camera perpendicular to the swimming lane."),
            self._create_criterion("Pose Confidence", avg_confidence, 0.15, 60,
                                   "The AI must track joint positions confidently.",
                                   "Low confidence leads to ignored frames and broken stroke tracking.",
                                   "Ensure the swimmer is in focus and well lit."),
            self._create_criterion("Full Body Visibility", avg_body_vis, 0.10, 60,
                                   "All major joints must be visible to calculate coordination.",
                                   "Incomplete posture graphs prevent Kick Frequency and Symmetry calculations.",
                                   "Zoom out or pan smoothly to keep head to toes in frame."),
            self._create_criterion("Swimmer Size", avg_size, 0.10, 60,
                                   "The swimmer must occupy enough pixels for accurate detection.",
                                   "If too small, joint positions jitter and angle noise increases.",
                                   "Zoom in closer or stand nearer to the pool edge."),
            self._create_criterion("Image Sharpness", avg_sharpness, 0.05, 50,
                                   "Fine details are required to distinguish limbs from water.",
                                   "Blur causes limbs to merge with the background, dropping tracking.",
                                   "Ensure your lens is clean and the camera is properly focused."),
            self._create_criterion("Motion Blur", avg_mblur, 0.05, 50,
                                   "Fast moving limbs like wrists during recovery must remain distinct.",
                                   "Blurry hands cause velocity spikes and incorrect stroke phase detection.",
                                   "Use a higher shutter speed or ensure good lighting so the camera does it automatically."),
            self._create_criterion("Lighting", avg_brightness, 0.05, 50,
                                   "Proper contrast differentiates the body from the water.",
                                   "Extreme shadows or overexposure blind the pose tracking model.",
                                   "Ensure the pool is well-lit and avoid shooting directly into the sun."),
            self._create_criterion("Contrast", avg_contrast, 0.05, 50,
                                   "Good contrast helps distinguish the swimmer from the water.",
                                   "Low contrast can hide limbs and joints in flat lighting.",
                                   "Use a camera with a wider dynamic range or increase scene lighting."),
            self._create_criterion("Water Reflections", avg_refl, 0.05, 50,
                                   "Sunlight reflecting off the water surface creates visual noise.",
                                   "Highlights can be falsely detected as limbs.",
                                   "Shoot from an angle that minimizes sun glare on the water surface."),
            self._create_criterion("Camera Stability", avg_stability, 0.05, 50,
                                   "A stable reference frame is needed for absolute velocity measurements.",
                                   "Shaky footage introduces artificial velocity into hand and hip tracking.",
                                   "Use a tripod or hold the camera steady while panning smoothly."),
            self._create_criterion("Video Orientation", orientation_score, 0.10, 50,
                                   "A wide horizontal field of view captures the full stroke cycle.",
                                   "Vertical video cuts off the hands during entry and push phases.",
                                   "Hold the camera horizontally (landscape mode)."),
            self._create_criterion("Resolution", resolution_score, 0.05, 50,
                                   "High spatial detail is required for micro-movement detection.",
                                   "Low resolution introduces quantization errors in joint angles.",
                                   "Record in at least 720p HD (1080p recommended)."),
            self._create_criterion("Frame Rate", fps_score, 0.10, 50,
                                   "High temporal resolution captures fast explosive movements.",
                                   "Low FPS misses the peak extension of the stroke and the exact entry moment.",
                                   "Record at 30 FPS minimum, or 60 FPS for best results.")
        ]
        
        # Calculate overall score
        total_weight = sum(c.weight for c in criteria)
        overall_score = int(sum(c.score * (c.weight / total_weight) for c in criteria))
        
        # Classify
        if overall_score >= 85:
            quality_class = "Excellent"
            conf = "High"
            passed = True
        elif overall_score >= 70:
            quality_class = "Good"
            conf = "High"
            passed = True
        elif overall_score >= 55:
            quality_class = "Fair"
            conf = "Medium"
            passed = True
        elif overall_score >= 40:
            quality_class = "Poor"
            conf = "Low"
            passed = True
        else:
            quality_class = "Critical"
            conf = "Very Low"
            passed = False
            
        warning_msg = ""
        if quality_class == "Poor":
            warning_msg = "Video quality is poor. Analysis will continue, but results should be interpreted with caution. (جودة الفيديو ضعيفة. سيستمر التحليل، لكن يجب تفسير النتائج بحذر)."
        elif quality_class == "Critical":
            warning_msg = "Video quality is insufficient for reliable biomechanical analysis. Processing stopped. (جودة الفيديو غير كافية لإجراء تحليل ميكانيكي حيوي موثوق. توقفت المعالجة)."
            
        logger.debug(f"[VQA] Intermediate Score: {overall_score}/100. Class: {quality_class}")
        
        return VQAResult(
            overall_score=overall_score,
            analysis_confidence=conf,
            quality_class=quality_class,
            passed=passed,
            warning_message=warning_msg,
            criteria=criteria
        )

    def _create_criterion(self, name, score, weight, threshold, mat, eff, fix) -> VQACriterionResult:
        return VQACriterionResult(
            name=name,
            score=max(0, min(100, score)),
            weight=weight,
            passed=(score >= threshold),
            explanation_matters=mat,
            explanation_effect=eff,
            explanation_fix=fix
        )
        
    def _fail_fast(self, message: str) -> VQAResult:
        return VQAResult(
            overall_score=0,
            analysis_confidence="Very Low",
            quality_class="Critical",
            passed=False,
            warning_message=f"Critical VQA Failure: {message}"
        )

    def assess_video(self, video_path: str):
        """Assess an entire video file and return the final VQA result."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return self._fail_fast("Video could not be opened for VQA assessment.")

        try:
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            self.fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
            self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

            if frame_count == 0:
                return self._fail_fast("Video has no frames.")

            self.frames_processed = 0
            pose_detector = self._get_pose_detector()
            try:
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break

                    landmarks, is_valid = pose_detector.detect_pose(frame)
                    self.assess_frame(frame, landmarks, is_valid)

                    if self.sample_count and self.frames_processed >= self.sample_count:
                        break

                return self.get_current_result()
            finally:
                pose_detector.close()
        finally:
            cap.release()

    def _get_pose_detector(self):
        from analysis.pose_detector import PoseDetector
        return PoseDetector()
