"""
Data leakage protection module for Ground Truth validation cohorts.
Enforces participant-level and video-level isolation across development, tuning, and validation sets.
"""
from typing import List, Dict, Set, Tuple, Any


class DataLeakageValidator:
    """
    Validates that no participant identity or video asset leaks across experimental splits.
    Strictly forbids participants used in heuristic tuning from appearing in official validation.
    """

    @staticmethod
    def check_participant_overlap(
        dev_participants: Set[str],
        val_participants: Set[str]
    ) -> Tuple[bool, Set[str]]:
        """
        Checks for participant-level overlap between development and validation sets.
        Returns (has_leakage, overlapping_participant_ids).
        """
        intersection = dev_participants.intersection(val_participants)
        return len(intersection) > 0, intersection

    @staticmethod
    def check_video_overlap(
        dev_video_ids: Set[str],
        val_video_ids: Set[str]
    ) -> Tuple[bool, Set[str]]:
        """
        Checks for video asset overlap between development and validation sets.
        Returns (has_leakage, overlapping_video_ids).
        """
        intersection = dev_video_ids.intersection(val_video_ids)
        return len(intersection) > 0, intersection

    @classmethod
    def validate_manifest_splits(
        cls,
        manifest_records: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Scans a list of manifest records containing 'split', 'participant_id', and 'video_id'.
        Verifies that no participant or video crosses between VALIDATION_OFFICIAL and non-validation splits.
        """
        errors: List[str] = []
        val_participants: Set[str] = set()
        val_videos: Set[str] = set()
        other_participants: Dict[str, Set[str]] = {} # split -> set of participants
        other_videos: Dict[str, Set[str]] = {}

        for rec in manifest_records:
            split = rec.get("split", "VALIDATION_OFFICIAL")
            pid = rec.get("participant_id")
            vid = rec.get("video_id") or rec.get("video_path")

            if not pid:
                errors.append(f"Record {rec.get('sample_id', 'UNKNOWN')} missing participant_id.")
                continue

            if split == "VALIDATION_OFFICIAL":
                val_participants.add(pid)
                if vid:
                    val_videos.add(vid)
            else:
                if split not in other_participants:
                    other_participants[split] = set()
                    other_videos[split] = set()
                other_participants[split].add(pid)
                if vid:
                    other_videos[split].add(vid)

        # Check overlap
        for split_name, participants in other_participants.items():
            overlap = val_participants.intersection(participants)
            if overlap:
                errors.append(
                    f"CRITICAL DATA LEAKAGE: Participant(s) {sorted(list(overlap))} appear in both "
                    f"VALIDATION_OFFICIAL and '{split_name}' splits."
                )

        for split_name, videos in other_videos.items():
            overlap = val_videos.intersection(videos)
            if overlap:
                errors.append(
                    f"CRITICAL DATA LEAKAGE: Video(s) {sorted(list(overlap))} appear in both "
                    f"VALIDATION_OFFICIAL and '{split_name}' splits."
                )

        is_valid = (len(errors) == 0)
        return is_valid, errors
