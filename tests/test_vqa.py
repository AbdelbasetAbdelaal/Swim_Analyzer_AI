"""
Unit tests for the Video Quality Assessor (VQA) component.
"""
import unittest
from unittest.mock import patch
import numpy as np

from analysis.video_quality_assessor import VideoQualityAssessor

class DummyLandmark:
    def __init__(self, x, y, visibility):
        self.x = x
        self.y = y
        self.visibility = visibility

class TestVideoQualityAssessor(unittest.TestCase):

    def setUp(self):
        self.vqa = VideoQualityAssessor(sample_count=2)

    @patch('analysis.video_quality_assessor.cv2.VideoCapture')
    @patch('analysis.pose_detector.PoseDetector')
    def test_critical_failure_no_frames(self, mock_pose, mock_cap_class):
        mock_cap = mock_cap_class.return_value
        mock_cap.isOpened.return_value = True
        mock_cap.get.return_value = 0 # 0 frames
        
        result = self.vqa.assess_video("dummy.mp4")
        self.assertEqual(result.quality_class, "Critical")
        self.assertFalse(result.passed)
        self.assertIn("Video has no frames", result.warning_message)

    @patch('analysis.video_quality_assessor.cv2.VideoCapture')
    @patch('analysis.pose_detector.PoseDetector')
    def test_orientation_score(self, mock_pose, mock_cap_class):
        mock_cap = mock_cap_class.return_value
        mock_cap.isOpened.return_value = True
        
        # Mock cap.get for different properties
        def mock_get(prop_id):
            import cv2
            if prop_id == cv2.CAP_PROP_FRAME_COUNT: return 10
            if prop_id == cv2.CAP_PROP_FRAME_WIDTH: return 720  # Portrait (Width < Height)
            if prop_id == cv2.CAP_PROP_FRAME_HEIGHT: return 1280
            if prop_id == cv2.CAP_PROP_FPS: return 30.0
            return 0
            
        mock_cap.get.side_effect = mock_get
        
        # Mock frame reading
        dummy_frame = np.zeros((1280, 720, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, dummy_frame)
        
        # Mock pose detector to return some valid landmarks to prevent fast-fail on confidence
        mock_detector = mock_pose.return_value
        mock_lms = [DummyLandmark(0.5, 0.5, 0.9) for _ in range(33)]
        mock_detector.detect_pose.return_value = (mock_lms, True)
        
        result = self.vqa.assess_video("dummy.mp4")
        
        # Find Video Orientation criterion (Vertical 720x1280 HD smartphone video scores 80)
        orient_crit = next(c for c in result.criteria if c.name == "Video Orientation")
        self.assertEqual(orient_crit.score, 80)
        self.assertTrue(orient_crit.passed)
        
    @patch('analysis.video_quality_assessor.cv2.VideoCapture')
    @patch('analysis.pose_detector.PoseDetector')
    def test_excellent_video(self, mock_pose, mock_cap_class):
        mock_cap = mock_cap_class.return_value
        mock_cap.isOpened.return_value = True
        
        # Mock a perfect 1080p 60fps landscape video
        def mock_get(prop_id):
            import cv2
            if prop_id == cv2.CAP_PROP_FRAME_COUNT: return 10
            if prop_id == cv2.CAP_PROP_FRAME_WIDTH: return 1920 
            if prop_id == cv2.CAP_PROP_FRAME_HEIGHT: return 1080
            if prop_id == cv2.CAP_PROP_FPS: return 60.0
            return 0
            
        mock_cap.get.side_effect = mock_get
        
        # High contrast, sharp frame to pass brightness/sharpness
        # We can mock Laplacian and mean directly
        with patch('analysis.video_quality_assessor.cv2.Laplacian') as mock_lap, \
             patch('analysis.video_quality_assessor.np.mean') as mock_mean:
            
            mock_lap.return_value.var.return_value = 500.0 # High sharpness
            mock_mean.return_value = 130 # Perfect brightness
            
            dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            mock_cap.read.return_value = (True, dummy_frame)
            
            # Perfect pose
            mock_detector = mock_pose.return_value
            # Needs size > 0.15 area ratio (e.g. 0.5 x 0.5 = 0.25)
            # Needs Side angle (ratio < 0.6)
            mock_lms = [DummyLandmark(0.5, 0.5, 0.9) for _ in range(33)]
            # Spread them out for size
            mock_lms[0] = DummyLandmark(0.1, 0.1, 0.9)
            mock_lms[32] = DummyLandmark(0.9, 0.9, 0.9)
            
            # Shoulders (11, 12) narrow width
            mock_lms[11] = DummyLandmark(0.5, 0.3, 0.9)
            mock_lms[12] = DummyLandmark(0.55, 0.3, 0.9) # Width 0.05
            
            # Hips (23, 24) long torso
            mock_lms[23] = DummyLandmark(0.5, 0.6, 0.9)
            mock_lms[24] = DummyLandmark(0.55, 0.6, 0.9) # Torso 0.3
            # Ratio 0.05 / 0.3 = 0.16 -> Side view -> 100 score
            
            mock_detector.detect_pose.return_value = (mock_lms, True)
            
            result = self.vqa.assess_video("dummy.mp4")
            
            self.assertEqual(result.quality_class, "Excellent")
            self.assertTrue(result.passed)
            self.assertGreaterEqual(result.overall_score, 90)

if __name__ == '__main__':
    unittest.main()
