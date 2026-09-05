"""
Tests for MediaPipe Video Timestamp Lifecycle (P1-8).
Verifies:
1. Strictly monotonic timestamp enforcement prevents MediaPipe graph exceptions.
2. PoseDetector.reset() resets timestamp tracker, smoother state, and underlying detector.
3. Reset allows rewinding video to 0ms without lifecycle errors.
"""

import pytest
import numpy as np
from analysis.pose_detector import PoseDetector

@pytest.fixture
def black_frame():
    return np.zeros((480, 640, 3), dtype=np.uint8)

def test_strictly_monotonic_timestamps(black_frame):
    detector = PoseDetector()
    try:
        # Feed increasing timestamps
        detector.detect_pose(black_frame, timestamp_ms=0)
        assert detector._last_timestamp_ms == 0

        detector.detect_pose(black_frame, timestamp_ms=33)
        assert detector._last_timestamp_ms == 33

        # Feed non-monotonic timestamp (regression to 20ms)
        # Internal tracker must force strictly monotonic increment: _last_timestamp_ms + 1 = 34
        detector.detect_pose(black_frame, timestamp_ms=20)
        assert detector._last_timestamp_ms == 34
        assert detector._last_timestamp_ms > 33

        # Feed duplicate timestamp (34ms)
        detector.detect_pose(black_frame, timestamp_ms=34)
        assert detector._last_timestamp_ms == 35
    finally:
        detector.close()

def test_detector_reset_allows_rewind_to_zero(black_frame):
    detector = PoseDetector()
    try:
        # Simulate VQA precheck running on first 10 frames (~300ms)
        for i in range(10):
            detector.detect_pose(black_frame, timestamp_ms=i * 33)
        assert detector._last_timestamp_ms >= 297

        # Reset detector for main video loop
        detector.reset()
        assert detector._last_timestamp_ms == -1
        assert detector._frame_timestamp_ms == 0

        # Now start main loop at timestamp 0ms without exception
        landmarks, is_valid = detector.detect_pose(black_frame, timestamp_ms=0)
        assert detector._last_timestamp_ms == 0
    finally:
        detector.close()
