import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from analysis.validation.ground_truth_qc import (
    GroundTruthQCEngine,
    verify_content_level_blinding,
)
from analysis.validation.ground_truth_ingestion import (
    GroundTruthIngestionService,
    compute_file_sha256,
)
from analysis.validation.ground_truth_models import InclusionStatus

AUDIT_FILE = REPO_ROOT / "data" / "ground_truth" / "metadata" / "asset_verification_audit.json"
QC_DIR = REPO_ROOT / "data" / "ground_truth" / "quality_control"
ANN_DIR = REPO_ROOT / "data" / "ground_truth" / "annotations"
MANIFEST_FILE = REPO_ROOT / "data" / "ground_truth" / "manifests" / "ground_truth_manifest.json"


def is_blank_or_incomplete(data: dict) -> bool:
    cycles = data.get("cycle_annotations", [])
    if not cycles:
        return True
    for c in cycles:
        if c.get("start_frame") is None or c.get("end_frame") is None:
            return True
    metrics = data.get("metric_annotations", {})
    if not metrics:
        return True
    all_none = all(m.get("value") is None for m in metrics.values() if isinstance(m, dict))
    if all_none:
        return True
    return False


def process_sample(sample_id: str, asset_info: dict) -> dict:
    sample_qc_dir = QC_DIR / sample_id
    rater_a_path = sample_qc_dir / "rater_A.json"
    rater_b_path = sample_qc_dir / "rater_B.json"

    result = {
        "sample_id": sample_id,
        "status": "AWAITING_HUMAN_ANNOTATION",
        "errors": [],
    }

    if not rater_a_path.exists() or not rater_b_path.exists():
        missing = []
        if not rater_a_path.exists():
            missing.append("rater_A.json")
        if not rater_b_path.exists():
            missing.append("rater_B.json")
        result["errors"].append(f"Missing human rater files: {', '.join(missing)}")
        return result

    try:
        with open(rater_a_path, "r", encoding="utf-8") as f:
            rater_a = json.load(f)
        with open(rater_b_path, "r", encoding="utf-8") as f:
            rater_b = json.load(f)
    except Exception as e:
        result["status"] = "MALFORMED_JSON"
        result["errors"].append(f"JSON read error: {e}")
        return result

    if is_blank_or_incomplete(rater_a) or is_blank_or_incomplete(rater_b):
        result["status"] = "INCOMPLETE_TEMPLATE"
        result["errors"].append("Rater files contain null values from unedited blank template.")
        return result

    video_path = REPO_ROOT / asset_info["video_path"]
    if not video_path.exists():
        result["status"] = "VIDEO_MISSING"
        result["errors"].append(f"Physical video missing: {video_path}")
        return result

    actual_hash = compute_file_sha256(video_path)
    if rater_a.get("video_sha256") != actual_hash or rater_b.get("video_sha256") != actual_hash:
        result["status"] = "CHECKSUM_MISMATCH"
        result["errors"].append("Rater video SHA-256 does not match physical video file bytes.")
        return result

    if rater_a.get("annotator_id") == rater_b.get("annotator_id"):
        result["status"] = "RATER_INDEPENDENCE_VIOLATION"
        result["errors"].append("Rater A and Rater B have identical annotator_id.")
        return result

    ok_a, v_a = verify_content_level_blinding(rater_a, "Rater A")
    ok_b, v_b = verify_content_level_blinding(rater_b, "Rater B")
    if not ok_a or not ok_b:
        result["status"] = "BLINDING_VIOLATION"
        result["errors"].extend(v_a + v_b)
        return result

    if len(rater_a.get("cycle_annotations", [])) < 3 or len(rater_b.get("cycle_annotations", [])) < 3:
        result["status"] = "INSUFFICIENT_CYCLES"
        result["errors"].append("Protocol requires minimum 3 complete clean cycles.")
        return result

    adj_path = sample_qc_dir / "adjudication.json"
    adj_data = None
    if adj_path.exists():
        try:
            with open(adj_path, "r", encoding="utf-8") as f:
                adj_data = json.load(f)
        except Exception:
            pass

    qc_engine = GroundTruthQCEngine(repo_root=REPO_ROOT)
    ok_qc, consensus_gt, qc_errs = qc_engine.process_and_save_trial_qc(
        sample_id=sample_id,
        rater_a_data=rater_a,
        rater_b_data=rater_b,
        adjudication_data=adj_data,
        save_to_annotations=False,
    )
    if not ok_qc:
        result["status"] = "QC_FAILED"
        result["errors"].extend(qc_errs)
        return result

    ANN_DIR.mkdir(parents=True, exist_ok=True)
    target_ann = ANN_DIR / f"{sample_id}.json"
    with open(target_ann, "w", encoding="utf-8") as f:
        json.dump(consensus_gt, f, indent=2)

    ingestion = GroundTruthIngestionService(repo_root=REPO_ROOT)
    ok_ingest, rec, ing_errs = ingestion.register_trial(
        manifest_path=MANIFEST_FILE,
        video_path=video_path,
        annotation_path=target_ann,
        split="VALIDATION_OFFICIAL",
        save=True,
    )
    if not ok_ingest:
        result["status"] = "INGESTION_FAILED"
        result["errors"].extend(ing_errs)
        return result

    result["status"] = "INGESTED_INCLUDED"
    result["sample_id"] = sample_id
    result["inclusion_status"] = rec.inclusion_status
    return result


def main():
    print("==================================================")
    print("HUMAN GROUND TRUTH ANNOTATION IMPORTER")
    print("==================================================")
    if not AUDIT_FILE.exists():
        print("No asset verification audit found. Run tools/verify_physical_assets.py first.")
        return

    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        audits = json.load(f)

    ingested = 0
    awaiting = 0
    errors = 0

    for asset in audits:
        sample_id = asset["sample_id"]
        res = process_sample(sample_id, asset)
        if res["status"] == "INGESTED_INCLUDED":
            ingested += 1
            print(f"[INCLUDED] {sample_id} successfully verified and ingested.")
        elif res["status"] in ["AWAITING_HUMAN_ANNOTATION", "INCOMPLETE_TEMPLATE"]:
            awaiting += 1
            print(f"[AWAITING] {sample_id}: {res['errors'][0] if res['errors'] else 'Pending human annotation'}")
        else:
            errors += 1
            print(f"[REJECTED] {sample_id} ({res['status']}): {'; '.join(res['errors'])}")

    print(f"\nSummary: {ingested} ingested, {awaiting} awaiting human raters, {errors} rejected/error.")
    if ingested == 0:
        print("\nOfficial manifest contains 0 records. Ground truth collection in progress.")


if __name__ == "__main__":
    main()
