import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from utils.video_utils import VideoProcessor

def test_ffmpeg_success(tmp_path):
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"A" * (20 * 1024))

    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stderr = b""

    with patch("shutil.which", return_value="ffmpeg"), \
         patch("subprocess.run", return_value=mock_res) as mock_run:

        VideoProcessor.ensure_browser_compatible_mp4(str(video_file))

        assert mock_run.called
        kwargs = mock_run.call_args[1]
        assert kwargs.get("stdin") == subprocess.DEVNULL
        assert kwargs.get("timeout") == 30

def test_ffmpeg_nonzero_failure(tmp_path):
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"A" * (20 * 1024))

    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stderr = b"Invalid data found when processing input"

    with patch("shutil.which", return_value="ffmpeg"), \
         patch("subprocess.run", return_value=mock_res) as mock_run:

        # Should complete safely without raising exception
        VideoProcessor.ensure_browser_compatible_mp4(str(video_file))
        assert mock_run.called

def test_ffmpeg_timeout_handling(tmp_path):
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"A" * (20 * 1024))

    with patch("shutil.which", return_value="ffmpeg"), \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=30)):

        # Should catch TimeoutExpired, log diagnostic, and safely return without hanging or raising
        VideoProcessor.ensure_browser_compatible_mp4(str(video_file))

def test_ffmpeg_timeout_cleans_up_temp_file(tmp_path):
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"A" * (20 * 1024))
    temp_h264 = tmp_path / "test_video_h264.mp4"
    temp_h264.write_bytes(b"incomplete partial file")

    with patch("shutil.which", return_value="ffmpeg"), \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=30)):

        VideoProcessor.ensure_browser_compatible_mp4(str(video_file))
        assert not temp_h264.exists(), "Temporary transcode file must be cleaned up on timeout"
