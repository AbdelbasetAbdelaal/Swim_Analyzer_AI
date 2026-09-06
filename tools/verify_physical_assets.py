import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent

CANDIDATES = [
    ("GT-FREE-001", "Freestyle", "data/ground_truth/raw/freestyle/GT-FREE-001.mp4"),
    ("GT-FREE-002", "Freestyle", "data/ground_truth/raw/freestyle/GT-FREE-002.mp4"),
    ("GT-BACK-001", "Backstroke", "data/ground_truth/raw/backstroke/GT-BACK-001.mp4"),
    ("GT-BACK-002", "Backstroke", "data/ground_truth/raw/backstroke/GT-BACK-002.mp4"),
    ("GT-BRST-001", "Breaststroke", "data/ground_truth/raw/breaststroke/GT-BRST-001.mp4"),
    ("GT-BRST-002", "Breaststroke", "data/ground_truth/raw/breaststroke/GT-BRST-002.mp4"),
    ("GT-FLY-001", "Butterfly", "data/ground_truth/raw/butterfly/GT-FLY-001.mp4"),
    ("GT-FLY-002", "Butterfly", "data/ground_truth/raw/butterfly/GT-FLY-002.mp4"),
]


def compute_file_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_asset(sample_id: str, stroke: str, rel_path: str) -> dict:
    full_path = REPO_ROOT / rel_path
    record = {
        "sample_id": sample_id,
        "stroke": stroke,
        "video_path": rel_path,
        "status": "MISSING",
        "frame_count": 0,
        "fps": 0.0,
        "duration_s": 0.0,
        "resolution": "0x0",
        "sha256": None,
        "file_size_bytes": 0,
        "verification_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if not full_path.exists():
        return record

    record["file_size_bytes"] = full_path.stat().st_size
    record["sha256"] = compute_file_sha256(full_path)

    cap = cv2.VideoCapture(str(full_path))
    if not cap.isOpened():
        record["status"] = "CORRUPTED_OR_UNREADABLE"
        return record

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    count = 0
    while True:
        ret, _ = cap.read()
        if not ret:
            break
        count += 1
    cap.release()

    record["status"] = "PRESENT_AND_READABLE"
    record["frame_count"] = count
    record["fps"] = round(fps, 2)
    record["duration_s"] = round(count / fps, 2) if fps > 0 else 0.0
    record["resolution"] = f"{width}x{height}"
    return record


def main():
    results = []
    print("==================================================")
    print("PHYSICAL ASSET VERIFICATION AUDIT")
    print("==================================================")
    for sample_id, stroke, rel_path in CANDIDATES:
        res = verify_asset(sample_id, stroke, rel_path)
        results.append(res)
        print(f"[{res['status']}] {sample_id} ({stroke}): {res['frame_count']} frames, {res['fps']} fps, {res['resolution']}, SHA: {str(res['sha256'])[:12]}...")

    out_file = REPO_ROOT / "data" / "ground_truth" / "metadata" / "asset_verification_audit.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved audit to {out_file}")


if __name__ == "__main__":
    main()
