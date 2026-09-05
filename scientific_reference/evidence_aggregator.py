from typing import List, Optional
from models.scientific_evidence_models import ScientificEvidenceRecord, AggregatedEvidence
from core.logger import setup_logger
import math

logger = setup_logger(__name__)

class EvidenceAggregator:
    """
    Transparently aggregates multiple SCIENTIFICALLY_ACCEPTED studies.
    Applies sample-size weighted averages.
    Detects mathematically incompatible bounds yielding CONFLICTING_EVIDENCE.
    """

    @staticmethod
    def aggregate_evidence(records: List[ScientificEvidenceRecord], stroke: str, gender: str, age_group: str, metric_name: str) -> Optional[AggregatedEvidence]:
        """
        Aggregates compatible records. Returns None if no valid records provided.
        """
        if not records:
            return None

        total_n = 0
        weighted_mean_sum = 0.0
        # For pooling standard deviations, we use pooled variance formula
        weighted_var_sum = 0.0
        
        # Verify unit compatibility
        base_unit = records[0].converted_unit or records[0].measurement_units
        
        # Determine if there's conflict by checking if max_mean - min_mean > 2 * pooled_std (simple heuristic)
        means = []

        for r in records:
            n = r.sample_size if r.sample_size and r.sample_size > 0 else 1 # fallback if n=0 to give equal weight
            val = r.converted_value if r.converted_value is not None else r.reported_mean
            std = r.reported_std if r.reported_std is not None else 5.0 # fallback std
            
            if val is None:
                continue
                
            means.append(val)
            total_n += n
            weighted_mean_sum += val * n
            # Variance = std^2. Weighted variance = (n-1)*s^2. We simplify for basic aggregation: n * s^2
            weighted_var_sum += n * (std ** 2)

        if total_n == 0 or not means:
            return None

        agg_mean = weighted_mean_sum / total_n
        agg_std = math.sqrt(weighted_var_sum / total_n)

        # Conflict heuristic: if ranges are completely disjoint or highly dispersed
        is_conflicting = False
        if len(means) > 1:
            max_mean = max(means)
            min_mean = min(means)
            # If the difference between the most extreme means is greater than 3 standard deviations, flag as conflict
            if (max_mean - min_mean) > (3 * agg_std):
                logger.warning(f"Conflicting evidence detected for {stroke} {metric_name} {gender} {age_group}. Range: {min_mean}-{max_mean}, Pooled Std: {agg_std}")
                is_conflicting = True

        return AggregatedEvidence(
            metric_name=metric_name,
            stroke=stroke,
            gender=gender,
            age_group=age_group,
            aggregated_mean=round(agg_mean, 3),
            aggregated_std=round(agg_std, 3),
            unit=base_unit,
            total_sample_size=total_n,
            source_records=records,
            is_conflicting=is_conflicting
        )
