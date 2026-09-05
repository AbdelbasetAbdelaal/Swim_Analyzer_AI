import math
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from models.benchmark_models import (
    AgeGroup, SkillLevel, PopulationStats,
    MetricBenchmarkComparison, BenchmarkResult
)
from models.data_models import AnalysisResult, ValidatedMetric
from models.athlete_profile import AthleteProfile
from models.scientific_evidence_models import (
    MetricEvidenceMetadata, ValidationStatus, EvidenceLevel,
    SourceRelationship, PopulationCompatibility, DefinitionCompatibility
)
from core.logger import setup_logger

logger = setup_logger(__name__)

def is_youth_cohort(cohort: str) -> bool:
    """Returns True if the cohort string represents a youth age bracket (P0-1)."""
    s = str(cohort).strip().lower()
    return s in ("8-10", "11-13", "14-17", "u10", "u11", "u12", "u13", "u14", "u15", "u16", "u17", "youth")

class BenchmarkEngine:
    """
    Scientific Population Benchmark Engine.
    Calculates Z-scores, normal distribution percentiles, elite deltas,
    and skill level classifications using YAML population datasets.
    Coexists with local database reference datasets managed by ReferenceDataService.
    """
    def __init__(self, benchmark_dir: Optional[Path] = None):
        if benchmark_dir is None:
            benchmark_dir = Path(__file__).resolve().parent.parent.parent / "config" / "benchmarks"
        self.benchmark_dir = benchmark_dir
        self._datasets: Dict[str, dict] = {}
        self.reload_datasets()

    def reload_datasets(self):
        """Loads all YAML benchmark dataset configuration files."""
        self._datasets.clear()
        if not self.benchmark_dir.exists():
            logger.warning(f"Benchmark directory {self.benchmark_dir} does not exist.")
            return

        for yaml_file in self.benchmark_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    stroke = data.get("stroke", yaml_file.stem.capitalize())
                    self._datasets[stroke.lower()] = data
                    logger.info(f"Loaded benchmark dataset for {stroke} (v{data.get('version', '1.0.0')})")
            except Exception as e:
                logger.error(f"Failed to load benchmark YAML {yaml_file}: {e}")

    def _get_dataset(self, stroke_type: str) -> Optional[dict]:
        return self._datasets.get(stroke_type.lower())

    def _get_population_stats(self, stroke_type: str, age_group: str, gender: str, metric_name: str) -> PopulationStats:
        ds = self._get_dataset(stroke_type)
        if not ds:
            return PopulationStats(
                mean=None, std=None, elite_mean=None, unit="",
                evidence=MetricEvidenceMetadata(
                    validation_status=ValidationStatus.INSUFFICIENT_EVIDENCE,
                    evidence_level=EvidenceLevel.LEVEL_E,
                    source_relationship=SourceRelationship.UNVERIFIED,
                    population_compatibility=PopulationCompatibility.POPULATION_MISMATCH,
                    definition_compatibility=DefinitionCompatibility.DEFINITION_MISMATCH
                )
            )

        # Normalize age group representation (P0-7)
        norm_age = age_group
        if age_group in ("Adult", "adult"): norm_age = "18-25"
        elif age_group in ("Senior", "senior"): norm_age = "26-35"
        elif age_group in ("U10", "u10"): norm_age = "8-10"
        elif age_group in ("U13", "u13"): norm_age = "11-13"
        elif age_group in ("U17", "u17"): norm_age = "14-17"
        elif age_group in ("Masters", "masters"): norm_age = "Masters"

        # Explicit youth state definition (P0-1)
        is_youth = is_youth_cohort(norm_age) or is_youth_cohort(age_group)

        pops = ds.get("populations", {})
        raw_age_pop = pops.get(norm_age)
        if raw_age_pop is None and norm_age != age_group:
            raw_age_pop = pops.get(age_group)

        # Strict cohort isolation: if requested age cohort does not exist in dataset,
        # never fall back to another cohort or default (P0-7).
        if not isinstance(raw_age_pop, dict):
            if age_group in ("default", "Mixed"):
                raw_age_pop = pops.get("default", {})
                if not isinstance(raw_age_pop, dict):
                    raw_age_pop = pops.get("Mixed", {})
            else:
                return PopulationStats(
                    mean=None, std=None, elite_mean=None, unit="",
                    evidence=MetricEvidenceMetadata(
                        validation_status=ValidationStatus.INSUFFICIENT_EVIDENCE,
                        evidence_level=EvidenceLevel.LEVEL_E,
                        source_relationship=SourceRelationship.UNVERIFIED,
                        population_compatibility=PopulationCompatibility.POPULATION_MISMATCH,
                        definition_compatibility=DefinitionCompatibility.DEFINITION_MISMATCH
                    )
                )

        if isinstance(raw_age_pop, dict) and raw_age_pop.get("status") == "INSUFFICIENT_EVIDENCE":
            return PopulationStats(
                mean=None, std=None, elite_mean=None, unit="",
                evidence=MetricEvidenceMetadata(
                    validation_status=ValidationStatus.INSUFFICIENT_EVIDENCE,
                    evidence_level=EvidenceLevel.LEVEL_E,
                    source_relationship=SourceRelationship.UNVERIFIED,
                    population_compatibility=PopulationCompatibility.POPULATION_MISMATCH,
                    definition_compatibility=DefinitionCompatibility.DEFINITION_MISMATCH
                )
            )

        age_pop = raw_age_pop if isinstance(raw_age_pop, dict) else {}
        gender_pop = age_pop.get(gender)
        if not isinstance(gender_pop, dict):
            # Only allow unisex/mixed if explicitly declared within this cohort; NEVER cross-sex
            if gender in ("Mixed", "Unisex"):
                gender_pop = age_pop.get("Mixed")
            if not isinstance(gender_pop, dict):
                return PopulationStats(
                    mean=None, std=None, elite_mean=None, unit="",
                    evidence=MetricEvidenceMetadata(
                        validation_status=ValidationStatus.INSUFFICIENT_EVIDENCE,
                        evidence_level=EvidenceLevel.LEVEL_E,
                        source_relationship=SourceRelationship.UNVERIFIED,
                        population_compatibility=PopulationCompatibility.POPULATION_MISMATCH,
                        definition_compatibility=DefinitionCompatibility.DEFINITION_MISMATCH
                    )
                )

        metric_cfg = gender_pop.get(metric_name) if isinstance(gender_pop, dict) else None
        default_cfg = pops.get("default", {}).get(gender, {}).get(metric_name, {}) if isinstance(pops.get("default"), dict) and isinstance(pops.get("default").get(gender), dict) and not is_youth else {}
        
        if not metric_cfg:
            metric_cfg = default_cfg
        elif isinstance(metric_cfg, dict) and isinstance(default_cfg, dict):
            if "evidence" in default_cfg and "evidence" in metric_cfg:
                for k, v in default_cfg["evidence"].items():
                    if k not in metric_cfg["evidence"]:
                        metric_cfg["evidence"][k] = v

        if not metric_cfg or metric_cfg.get("status") in ("CONFLICTING_EVIDENCE", "INSUFFICIENT_EVIDENCE"):
            val_status = ValidationStatus.CONFLICTING_EVIDENCE if metric_cfg and metric_cfg.get("status") == "CONFLICTING_EVIDENCE" else ValidationStatus.INSUFFICIENT_EVIDENCE
            return PopulationStats(
                mean=None, std=None, elite_mean=None, unit="",
                evidence=MetricEvidenceMetadata(
                    validation_status=val_status,
                    evidence_level=EvidenceLevel.LEVEL_E,
                    source_relationship=SourceRelationship.UNVERIFIED,
                    population_compatibility=PopulationCompatibility.POPULATION_MISMATCH,
                    definition_compatibility=DefinitionCompatibility.DEFINITION_MISMATCH
                )
            )

        ev_cfg = metric_cfg.get("evidence", {})
        try:
            val_stat = ValidationStatus(ev_cfg.get("validation_status", ds.get("validation_status", "PARTIALLY_VALIDATED")).upper())
        except ValueError:
            val_stat = ValidationStatus.PARTIALLY_VALIDATED

        try:
            ev_lvl = EvidenceLevel(ev_cfg.get("evidence_level", "LEVEL_A"))
        except ValueError:
            ev_lvl = EvidenceLevel.LEVEL_C

        try:
            raw_source_relationship = ev_cfg.get("source_relationship", ev_cfg.get("relationship", "DIRECTLY_SUPPORTED"))
            if raw_source_relationship == "DIRECT_MEASUREMENT":
                raw_source_relationship = SourceRelationship.DIRECTLY_SUPPORTED.value
            src_rel = SourceRelationship(raw_source_relationship)
        except ValueError:
            src_rel = SourceRelationship.APPROXIMATED

        try:
            pop_comp = PopulationCompatibility(ev_cfg.get("population_compatibility", "COMPATIBLE"))
        except ValueError:
            pop_comp = PopulationCompatibility.COMPATIBLE

        try:
            def_comp = DefinitionCompatibility(ev_cfg.get("definition_compatibility", "COMPATIBLE"))
        except ValueError:
            def_comp = DefinitionCompatibility.COMPATIBLE

        evidence_meta = MetricEvidenceMetadata(
            validation_status=val_stat,
            evidence_level=ev_lvl,
            source_ids=ev_cfg.get("source_ids", [ev_cfg.get("source_id")] if ev_cfg.get("source_id") else []),
            sample_size=int(ev_cfg.get("sample_size", 0)),
            event_distance=str(ev_cfg.get("event_distance", "100m")),
            measurement_method=str(ev_cfg.get("measurement_method", "Kinematic Analysis")),
            source_relationship=src_rel,
            population_compatibility=pop_comp,
            definition_compatibility=def_comp,
            reported_source_value=str(ev_cfg.get("reported_source_value", f"{ev_cfg.get('original_value', '')} {ev_cfg.get('original_unit', '')}".strip())),
            reported_source_std=str(ev_cfg.get("reported_source_std", "")),
            notes=ev_cfg.get("notes", []) if isinstance(ev_cfg.get("notes"), list) else []
        )

        mean = metric_cfg.get("mean")
        std = metric_cfg.get("std")
        elite_mean = metric_cfg.get("elite_mean")
        if mean is None or std is None:
            evidence_meta.validation_status = ValidationStatus.INSUFFICIENT_EVIDENCE
            return PopulationStats(
                mean=None, std=None, elite_mean=None, unit=str(metric_cfg.get("unit", "")),
                evidence=evidence_meta
            )

        return PopulationStats(
            mean=float(mean),
            std=float(std),
            elite_mean=float(elite_mean) if elite_mean is not None else None,
            unit=str(metric_cfg.get("unit", "")),
            higher_is_better=bool(metric_cfg.get("higher_is_better", True)),
            evidence=evidence_meta
        )

    @staticmethod
    def calculate_z_score(raw_value: float, mean: Optional[float], std: Optional[float]) -> Optional[float]:
        """Calculates statistical Z-score: Z = (x - mu) / sigma."""
        if mean is None or std is None or std <= 0:
            return None
        return (raw_value - mean) / std

    @staticmethod
    def calculate_percentile(z_score: Optional[float], higher_is_better: bool = True) -> Optional[float]:
        """Calculates cumulative distribution function (CDF) percentile from Z-score."""
        if z_score is None:
            return None
        cdf = 0.5 * (1.0 + math.erf(z_score / math.sqrt(2.0))) * 100.0
        percentile = cdf if higher_is_better else (100.0 - cdf)
        return float(min(99.9, max(0.1, percentile)))

    def get_skill_level(self, performance_score: Optional[float], stroke_type: str = "Freestyle") -> str:
        """Classifies performance score into skill level tiers."""
        if performance_score is None:
            return "INSUFFICIENT_EVIDENCE"
        ds = self._get_dataset(stroke_type)
        thresholds = ds.get("skill_level_thresholds", {}).get("performance_score", {}) if ds else {}

        if performance_score >= thresholds.get("Olympic", 97.0):
            return SkillLevel.OLYMPIC.value
        elif performance_score >= thresholds.get("Elite", 93.0):
            return SkillLevel.ELITE.value
        elif performance_score >= thresholds.get("National", 86.0):
            return SkillLevel.NATIONAL.value
        elif performance_score >= thresholds.get("Advanced", 78.0):
            return SkillLevel.ADVANCED.value
        elif performance_score >= thresholds.get("Intermediate", 65.0):
            return SkillLevel.INTERMEDIATE.value
        else:
            return SkillLevel.BEGINNER.value

    def get_percentile(self, metric_name: str, raw_value: Optional[float], stroke_type: str = "Freestyle",
                       age_group: str = "18-25", gender: str = "Male") -> Optional[float]:
        if raw_value is None:
            return None
        stats = self._get_population_stats(stroke_type, age_group, gender, metric_name)
        z = self.calculate_z_score(raw_value, stats.mean, stats.std)
        return self.calculate_percentile(z, stats.higher_is_better)

    def compare_with_elite(self, metric_name: str, raw_value: Optional[float], stroke_type: str = "Freestyle",
                           age_group: str = "18-25", gender: str = "Male") -> Dict[str, Optional[float]]:
        stats = self._get_population_stats(stroke_type, age_group, gender, metric_name)
        if raw_value is None or stats.elite_mean is None or stats.elite_mean <= 0:
            return {"raw_value": raw_value, "elite_mean": stats.elite_mean, "delta": None, "pct_of_elite": None}
        delta = raw_value - stats.elite_mean
        pct_of_elite = raw_value / stats.elite_mean * 100.0
        return {"raw_value": raw_value, "elite_mean": stats.elite_mean, "delta": delta, "pct_of_elite": pct_of_elite}

    def compare_with_population(self, metric_name: str, raw_value: Optional[float], stroke_type: str = "Freestyle",
                                age_group: str = "18-25", gender: str = "Male") -> Dict[str, Any]:
        stats = self._get_population_stats(stroke_type, age_group, gender, metric_name)
        z = self.calculate_z_score(raw_value, stats.mean, stats.std) if raw_value is not None else None
        pct = self.calculate_percentile(z, stats.higher_is_better)
        return {
            "metric_name": metric_name,
            "raw_value": raw_value,
            "population_mean": stats.mean,
            "population_std": stats.std,
            "z_score": round(z, 2) if z is not None else None,
            "percentile": round(pct, 1) if pct is not None else None,
            "unit": stats.unit
        }

    def get_expected_range(self, metric_name: str, stroke_type: str = "Freestyle",
                           age_group: str = "18-25", gender: str = "Male") -> Tuple[Optional[float], Optional[float]]:
        stats = self._get_population_stats(stroke_type, age_group, gender, metric_name)
        if stats.mean is None or stats.std is None:
            return (None, None)
        low = stats.mean - 2.0 * stats.std
        high = stats.mean + 2.0 * stats.std
        return (low, high)

    def check_population_compatibility(self, athlete_profile: Optional[AthleteProfile], stroke_type: str = "Freestyle") -> Tuple[bool, str]:
        if not athlete_profile:
            return (True, "Default Adult Male reference cohort applied.")

        age = athlete_profile.age if athlete_profile.age else 20
        gender = athlete_profile.gender if athlete_profile.gender else "Male"

        stats = self._get_population_stats(stroke_type, AgeGroup.from_age(age).value, gender, "stroke_rate")
        if stats.mean is None:
            return (False, f"⚠️ No validated reference population is currently available for {gender} age group '{AgeGroup.from_age(age).value}' in {stroke_type}.")
        return (True, f"Athlete belongs to validated cohort ({gender}, {AgeGroup.from_age(age).value}).")

    def evaluate_analysis(self, result: AnalysisResult, athlete_profile: Optional[AthleteProfile] = None) -> BenchmarkResult:
        """Runs population benchmark evaluation across all available biomechanical metrics."""
        # Single Source of Truth: Resolve stroke from AnalysisResult
        stroke = "Freestyle"
        if getattr(result, 'stroke_type', None):
            stroke = str(result.stroke_type)
        elif getattr(result, 'stroke_selection', None) and getattr(result.stroke_selection, 'selected_stroke', None):
            val = result.stroke_selection.selected_stroke
            stroke = val.value if hasattr(val, 'value') else str(val)
        elif getattr(result, 'stroke_detection', None) and getattr(result.stroke_detection, 'selected_stroke', None):
            val = result.stroke_detection.selected_stroke
            stroke = val.value if hasattr(val, 'value') else str(val)

        # Standardize stroke capitalization (e.g., 'butterfly' -> 'Butterfly')
        stroke = stroke.capitalize()

        age = athlete_profile.age if athlete_profile and athlete_profile.age else 20
        gender = athlete_profile.gender if athlete_profile and athlete_profile.gender else "Male"

        age_grp = AgeGroup.from_age(age).value
        is_pop_compat, _ = self.check_population_compatibility(athlete_profile, stroke)

        overall_score = result.report.overall_score if result.report else None
        overall_skill = self.get_skill_level(overall_score, stroke)

        if not self._get_dataset(stroke):
            return BenchmarkResult(
                stroke_type=stroke,
                age_group=age_grp,
                gender=gender,
                overall_skill_level="INSUFFICIENT_EVIDENCE",
                is_population_compatible=False,
                validation_status="insufficient_evidence"
            )

        bm_res = BenchmarkResult(
            stroke_type=stroke,
            age_group=age_grp,
            gender=gender,
            overall_skill_level=overall_skill if is_pop_compat else "N/A (Unvalidated Cohort)",
            dataset_name=f"{stroke} Population Reference Matrix v2.0",
            dataset_id=f"BM-{stroke[:3].upper()}-2026",
            dataset_version="2.0.0-Hybrid",
            scientific_revision="2026.08",
            is_population_compatible=is_pop_compat,
            validation_status="scientifically_validated" if is_pop_compat else "unvalidated_cohort"
        )

        if not result.report:
            return bm_res

        # Core biomechanical metrics
        metric_sources = {
            "stroke_rate": result.report.stroke_rate if result.report else None,
            "stroke_length": result.report.stroke_length if result.report else None,
            "kick_frequency": result.report.kick_frequency if result.report else None,
            "stroke_symmetry": result.report.stroke_symmetry if result.report else None,
            "performance_score": ValidatedMetric(name="performance_score", value=overall_score, unit="pts") if overall_score is not None else None
        }

        for m_name, m_obj in metric_sources.items():
            if m_obj is None or m_obj.value is None or not getattr(m_obj, 'valid', True):
                continue

            val = m_obj.value
            metric_unit = getattr(m_obj, 'unit', None)
            domain = getattr(m_obj, 'measurement_domain', None)

            pop_stats = self._get_population_stats(stroke, age_grp, gender, m_name)
            expected_unit = pop_stats.unit or ("spm" if m_name == "stroke_rate" else ("m" if m_name == "stroke_length" else ""))

            # Domain & unit compatibility verification (P0-3)
            # Uncalibrated stroke length produces relative_body_normalized / body_length, NOT meters.
            is_domain_incompatible = False
            domain_reason = ""
            if m_name == "stroke_length":
                if domain in ["relative_body_normalized", "image_space", "unavailable"] or metric_unit in ["body_length", "pixels", "unavailable"]:
                    if expected_unit in ["m", "meters"]:
                        is_domain_incompatible = True
                        domain_reason = "Cannot compare relative body length to physical meter benchmark without camera calibration."

            if is_domain_incompatible:
                comp = MetricBenchmarkComparison(
                    metric_name=m_name,
                    raw_value=val,
                    population_mean=None,
                    population_std=None,
                    z_score=None,
                    percentile=None,
                    elite_mean=None,
                    elite_delta=None,
                    skill_level="N/A",
                    unit=metric_unit or "body_length",
                    evidence=pop_stats.evidence,
                    comparison_status="incompatible_domain",
                    reason=domain_reason
                )
                bm_res.comparisons[m_name] = comp
                continue

            z = self.calculate_z_score(val, pop_stats.mean, pop_stats.std)
            pct = self.calculate_percentile(z, pop_stats.higher_is_better)
            e_delta = (val - pop_stats.elite_mean) if pop_stats.elite_mean is not None else None

            # Suppress percentiles and Z-scores if demographic cohort is unvalidated
            comp = MetricBenchmarkComparison(
                metric_name=m_name,
                raw_value=val,
                population_mean=pop_stats.mean if is_pop_compat else None,
                population_std=pop_stats.std if is_pop_compat else None,
                z_score=z if is_pop_compat else None,
                percentile=pct if is_pop_compat else None,
                elite_mean=pop_stats.elite_mean if is_pop_compat else None,
                elite_delta=e_delta if is_pop_compat else None,
                skill_level=self.get_skill_level(val, stroke) if is_pop_compat else "N/A",
                unit=metric_unit or expected_unit,
                evidence=pop_stats.evidence,
                comparison_status="available" if is_pop_compat else "unvalidated_cohort",
                reason="" if is_pop_compat else "Unvalidated demographic cohort"
            )

            bm_res.comparisons[m_name] = comp

        return bm_res
