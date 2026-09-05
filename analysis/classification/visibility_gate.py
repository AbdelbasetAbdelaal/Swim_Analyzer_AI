"""
Visibility and Quality Gate for Stroke Classification.
Evaluates pose landmark visibility and completeness before passing to classification engines.
"""
from dataclasses import dataclass
from typing import List, Any

@dataclass
class VisibilityGateResult:
    is_sufficient: bool
    total_frames: int
    valid_frames: int
    visibility_ratio: float
    wrist_visibility: float
    shoulder_visibility: float
    ankle_visibility: float
    missing_landmarks: List[str]
    gate_reason: str

class VisibilityGate:
    """Quality & Visibility Gate for Pose Landmark Sequences."""

    def __init__(self, min_visibility_threshold: float = 0.15, min_valid_ratio: float = 0.10):
        self.min_visibility_threshold = min_visibility_threshold
        self.min_valid_ratio = min_valid_ratio

    def evaluate(self, frames: List[Any]) -> VisibilityGateResult:
        if not frames:
            return VisibilityGateResult(
                is_sufficient=False, total_frames=0, valid_frames=0,
                visibility_ratio=0.0, wrist_visibility=0.0, shoulder_visibility=0.0, ankle_visibility=0.0,
                missing_landmarks=["all_frames", "wrists", "shoulders", "ankles"],
                gate_reason="No frames provided to visibility gate."
            )

        total_frames = len(frames)
        valid_frames = []

        for f in frames:
            lms = getattr(f, 'raw_landmarks', None)
            if lms and len(lms) > 28:
                # Require key upper-body landmarks (shoulders or wrists) to exist and be valid
                l_sh, r_sh = lms[11], lms[12]
                if l_sh and r_sh:
                    s_vis1 = getattr(l_sh, 'visibility', 1.0)
                    s_vis2 = getattr(r_sh, 'visibility', 1.0)
                    v1 = 1.0 if (s_vis1 is None or s_vis1 == 0.0) else float(s_vis1)
                    v2 = 1.0 if (s_vis2 is None or s_vis2 == 0.0) else float(s_vis2)
                    if (v1 >= self.min_visibility_threshold or v2 >= self.min_visibility_threshold):
                        valid_frames.append(f)
                else:
                    valid_frames.append(f)

        valid_count = len(valid_frames)
        vis_ratio = valid_count / total_frames if total_frames > 0 else 0.0

        if valid_count < 2:
            return VisibilityGateResult(
                is_sufficient=False, total_frames=total_frames, valid_frames=valid_count,
                visibility_ratio=vis_ratio, wrist_visibility=0.0, shoulder_visibility=0.0, ankle_visibility=0.0,
                missing_landmarks=["valid_pose_landmarks", "wrists", "shoulders", "ankles"],
                gate_reason=f"Insufficient valid landmark frames ({valid_count}/{total_frames})."
            )


        wrist_vis, shoulder_vis, ankle_vis = [], [], []

        for f in valid_frames:
            lms = f.raw_landmarks
            if len(lms) > 16 and lms[15] and lms[16]:
                w1 = getattr(lms[15], 'visibility', 0.0)
                w2 = getattr(lms[16], 'visibility', 0.0)
                wrist_vis.append((w1 + w2) / 2.0)

            if len(lms) > 12 and lms[11] and lms[12]:
                s1 = getattr(lms[11], 'visibility', 0.0)
                s2 = getattr(lms[12], 'visibility', 0.0)
                shoulder_vis.append((s1 + s2) / 2.0)

            if len(lms) > 28 and lms[27] and lms[28]:
                a1 = getattr(lms[27], 'visibility', 0.0)
                a2 = getattr(lms[28], 'visibility', 0.0)
                ankle_vis.append((a1 + a2) / 2.0)

        avg_wrist_vis = sum(wrist_vis) / len(wrist_vis) if wrist_vis else 0.0
        avg_sh_vis = sum(shoulder_vis) / len(shoulder_vis) if shoulder_vis else 0.0
        avg_ak_vis = sum(ankle_vis) / len(ankle_vis) if ankle_vis else 0.0

        missing = []
        if not wrist_vis or avg_wrist_vis < self.min_visibility_threshold:
            missing.append("wrists")
        if not shoulder_vis or avg_sh_vis < self.min_visibility_threshold:
            missing.append("shoulders")
        if not ankle_vis or avg_ak_vis < self.min_visibility_threshold:
            missing.append("ankles")

        is_sufficient = (vis_ratio >= self.min_valid_ratio) and ("wrists" not in missing) and ("shoulders" not in missing)
        reason = f"Visibility ratio: {vis_ratio*100:.1f}%, Wrist Vis: {avg_wrist_vis:.2f}, Shoulder Vis: {avg_sh_vis:.2f}, Ankle Vis: {avg_ak_vis:.2f}"

        return VisibilityGateResult(
            is_sufficient=is_sufficient,
            total_frames=total_frames,
            valid_frames=valid_count,
            visibility_ratio=vis_ratio,
            wrist_visibility=avg_wrist_vis,
            shoulder_visibility=avg_sh_vis,
            ankle_visibility=avg_ak_vis,
            missing_landmarks=missing,
            gate_reason=reason
        )
