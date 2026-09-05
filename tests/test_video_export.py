import pytest
import os
import cv2
import numpy as np
from utils.video_utils import VideoProcessor
import tempfile

@pytest.fixture
def dummy_video_path():
    """Generates a valid dummy MP4 video for testing."""
    fd, path = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, 30.0, (100, 100))
    for i in range(10): # 10 frames
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame.fill(i * 20)
        out.write(frame)
    out.release()
    
    yield path
    
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture
def broken_video_path():
    """Generates an empty 0-byte file."""
    fd, path = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_successful_export_validation(dummy_video_path):
    """
    Test that a correctly generated video passes validation.
    Note: The dummy video generated above might be very small (<100KB),
    so we need to adjust our mock or the file size constraint for tests.
    Wait, the validation requires file size > 100KB. Let's create a larger one, 
    or just mock getsize for the test.
    """
    
    # We will generate a video with enough frames/resolution to be > 100KB
    fd, large_path = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)
    
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(large_path, fourcc, 30.0, (640, 480))
        for i in range(90): # 3 seconds
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            out.write(frame)
        out.release()
        
        # Test validation
        is_valid = VideoProcessor.validate_export(large_path)
        assert is_valid is True
        
    finally:
        if os.path.exists(large_path):
            os.remove(large_path)

def test_broken_export_detection_zero_bytes(broken_video_path):
    """
    Test that a 0-byte file fails validation.
    """
    is_valid = VideoProcessor.validate_export(broken_video_path)
    assert is_valid is False

def test_broken_export_detection_small_file():
    """
    Test that a file smaller than 100KB fails validation.
    """
    fd, path = tempfile.mkstemp(suffix='.mp4')
    with open(fd, 'wb') as f:
        f.write(b"0" * (50 * 1024)) # 50 KB
        
    try:
        is_valid = VideoProcessor.validate_export(path)
        assert is_valid is False
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_broken_export_detection_invalid_format():
    """
    Test that a non-video file fails validation.
    """
    fd, path = tempfile.mkstemp(suffix='.mp4')
    with open(fd, 'wb') as f:
        f.write(b"0" * (200 * 1024)) # 200 KB but not a real video
        
    try:
        is_valid = VideoProcessor.validate_export(path)
        assert is_valid is False
    finally:
        if os.path.exists(path):
            os.remove(path)
