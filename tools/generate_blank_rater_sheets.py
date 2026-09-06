import os
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_FILE = REPO_ROOT / "data" / "ground_truth" / "metadata" / "asset_verification_audit.json"
TEMPLATE_FILE = REPO_ROOT / "data" / "ground_truth" / "templates" / "rater_annotation_template.json"
OUT_DIR = REPO_ROOT / "data" / "ground_truth" / "templates" / "blank_sheets"

def main():
    if not AUDIT_FILE.exists():
        print(f"Error: Asset verification audit file not found at {AUDIT_FILE}")
        sys.exit(1)

    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        audits = json.load(f)

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        base_template = json.load(f)

    count = 0
    for asset in audits:
        if asset.get("status") != "PRESENT_AND_READABLE":
            continue

        sample_id = asset["sample_id"]
        sample_dir = OUT_DIR / sample_id
        sample_dir.mkdir(parents=True, exist_ok=True)

        for rater_id, rater_role, filename in [
            ("HUMAN_RATER_A", "PRIMARY_RATER", "rater_A_blank.json"),
            ("HUMAN_RATER_B", "SECONDARY_RATER", "rater_B_blank.json")
        ]:
            sheet = dict(base_template)
            sheet["sample_id"] = sample_id
            sheet["annotator_id"] = rater_id
            sheet["annotation_role"] = rater_role
            sheet["annotation_timestamp"] = None  # To be filled by human rater
            sheet["video_filename"] = Path(asset["video_path"]).name
            sheet["video_sha256"] = asset["sha256"]
            sheet["video_fps"] = asset["fps"]
            sheet["video_duration"] = asset["duration_s"]
            sheet["frame_count"] = asset["frame_count"]
            sheet["stroke_type"] = asset["stroke"]
            sheet["participant_id"] = f"PARTICIPANT-{sample_id.split('-')[-1]}"
            sheet["session_id"] = f"SESSION-{sample_id.split('-')[-1]}"
            sheet["video_id"] = f"VIDEO-{sample_id.split('-')[-1]}"
            
            target_path = sample_dir / filename
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(sheet, f, indent=2)

        count += 1
        print(f"Created blank sheets for {sample_id} in {sample_dir}")

    print(f"\nGenerated blank rater sheets for {count} verified physical assets.")

if __name__ == "__main__":
    main()
