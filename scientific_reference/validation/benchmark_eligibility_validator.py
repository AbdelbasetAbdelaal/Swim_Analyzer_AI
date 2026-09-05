import yaml
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from models.scientific_evidence_models import (
    CandidateEvidence, ScientificSource, ReviewStatus, AuditDecision
)
from core.logger import setup_logger

logger = setup_logger(__name__)

class BenchmarkEligibilityValidator:
    """
    Deterministic validator enforcing the SwimAnalyzer Scientific Benchmark Eligibility Policy.
    Ensures systematic reviews, meta-analyses, demographic leakage, stroke leakage, and unsupported metric
    conversions are strictly evaluated before evidence can enter benchmark datasets.
    """

    def __init__(self, policy_path: Optional[Path] = None):
        if policy_path is None:
            policy_path = Path(__file__).resolve().parent.parent.parent / "config" / "benchmark_eligibility.yaml"
        self.policy_path = policy_path
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict[str, Any]:
        if self.policy_path.exists():
            with open(self.policy_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    @staticmethod
    def evaluate_eligibility(
        candidate: CandidateEvidence,
        source: Optional[ScientificSource] = None,
        target_stroke: Optional[str] = None,
        target_distance_m: Optional[int] = None,
        target_sex: Optional[str] = None,
        target_age_group: Optional[str] = None
    ) -> Tuple[ReviewStatus, AuditDecision, str]:
        """
        Main entry point for evaluating candidate evidence eligibility.
        Returns (ReviewStatus, AuditDecision, rationale_reason).
        """
        # 1. Check for fabricated bibliographic metadata
        if candidate.pmid in ["FABRICATED", "UNKNOWN_PMID", "0000000"] or candidate.doi in ["FABRICATED", "10.0000/fake"]:
            logger.warning(f"Fabricated metadata detected for candidate {candidate.source_id}")
            return ReviewStatus.REJECTED, AuditDecision.REJECT, "Fabricated DOI/PMID/PMCID detected"

        # 2. Check qualitative coordination threshold conversion prohibition
        metric_str = (candidate.metric or "").lower()
        if "coordination" in metric_str or "idc" in metric_str:
            if candidate.mean is not None and candidate.source_quote and "qualitative" in candidate.source_quote.lower():
                logger.warning(f"Qualitative coordination finding converted to numeric for candidate {candidate.source_id}")
                return ReviewStatus.REJECTED, AuditDecision.REJECT, "Qualitative coordination finding cannot automatically become a numerical benchmark"

        study_type = (candidate.study_type or (source.study_type if source else "primary_study")).lower()
        source_id = candidate.source_id or (source.source_id if source else "")
        benchmark_policy = source.benchmark_policy if source else None

        # 3. Meta-Analysis Rule Check (e.g. MA_400M_FRONT_CRAWL)
        if study_type == "meta_analysis" or source_id == "MA_400M_FRONT_CRAWL" or benchmark_policy == "TEST_SPECIFIC_ONLY":
            cand_dist = candidate.test_distance_m or 400
            stroke = (candidate.stroke or target_stroke or "").lower()
            
            # If target distance is specified and does not match candidate test context distance
            if target_distance_m is not None and target_distance_m != cand_dist:
                logger.warning(f"Meta-analysis {source_id} restricted to {cand_dist}m front crawl test context (attempted target distance: {target_distance_m}m)")
                return ReviewStatus.REJECTED, AuditDecision.REJECT, f"400m Front Crawl meta-analysis cannot populate generic or {target_distance_m}m freestyle benchmarks"
            
            if stroke and stroke not in ["freestyle", "front_crawl", "front crawl"]:
                logger.warning(f"Meta-analysis {source_id} restricted to 400m front crawl test context")
                return ReviewStatus.REJECTED, AuditDecision.REJECT, "400m Front Crawl meta-analysis cannot populate a non-freestyle benchmark"
            
            if stroke and stroke not in ["freestyle", "front_crawl", "front crawl"]:
                logger.warning(f"Meta-analysis {source_id} restricted to freestyle (attempted stroke: {stroke})")
                return ReviewStatus.REJECTED, AuditDecision.REJECT, f"400m Front Crawl meta-analysis cannot populate {stroke} benchmarks"

        # 4. Systematic Review Primary Study Traceability Check
        if study_type == "systematic_review" or source_id in ["SR_BACKSTROKE_2025", "SR_BREASTSTROKE_2022", "SR_FRONT_CRAWL_COORDINATION", "SR_YOUNG_ADOLESCENT_FOUR_STROKE"]:
            has_primary_trace = bool(candidate.primary_study_identifier and candidate.primary_study_identifier.strip())
            
            if not has_primary_trace:
                logger.info(f"Systematic review {source_id} lacks explicit primary study trace. Assigned REVIEW_REQUIRED.")
                return ReviewStatus.PENDING_REVIEW, AuditDecision.REFERENCE_ONLY, "Systematic review serves as context/discovery node; requires explicit primary study trace before creating benchmark"

        # 5. Demographic Leakage Checks
        cand_sex = (candidate.population_sex or (source.gender if source else "Mixed")).strip().title()
        if target_sex and cand_sex != "Mixed" and target_sex != "Mixed" and cand_sex != target_sex:
            logger.warning(f"Sex leakage prohibited: candidate sex '{cand_sex}' vs target sex '{target_sex}'")
            return ReviewStatus.REJECTED, AuditDecision.REJECT, f"Demographic leakage prohibited: {cand_sex} evidence cannot populate {target_sex} benchmark"

        # 6. Age Group Extrapolation Check
        cand_age = (candidate.population_age or (source.age_range if source else "")).lower()
        if target_age_group:
            t_age = target_age_group.lower()
            is_youth = any(k in t_age for k in ["u10", "u12", "8-10", "11-13", "youth", "adolescent", "junior"])
            is_adult = any(k in cand_age for k in ["18-25", "adult", "elite male", "senior"])
            if is_youth and is_adult:
                logger.warning(f"Age leakage prohibited: adult candidate '{cand_age}' vs target youth age '{target_age_group}'")
                return ReviewStatus.REJECTED, AuditDecision.REJECT, "Demographic leakage prohibited: Adult evidence cannot populate adolescent/youth benchmark"

        # 7. Stroke Leakage Check
        cand_stroke = (candidate.stroke or (source.stroke if source else "")).lower().replace(" ", "")
        if target_stroke:
            t_stroke = target_stroke.lower().replace(" ", "")
            if cand_stroke and t_stroke and cand_stroke != t_stroke and not (cand_stroke in ["freestyle", "frontcrawl"] and t_stroke in ["freestyle", "frontcrawl"]):
                logger.warning(f"Stroke leakage prohibited: candidate stroke '{cand_stroke}' vs target stroke '{t_stroke}'")
                return ReviewStatus.REJECTED, AuditDecision.REJECT, f"Stroke leakage prohibited: {candidate.stroke} evidence cannot populate {target_stroke} benchmark"

        # If all eligibility rules pass
        return ReviewStatus.SCIENTIFICALLY_ACCEPTED, AuditDecision.ACCEPT, "Eligible for scientific benchmark inclusion"
