from models.scientific_evidence_models import DefinitionMatchingStatus
from core.logger import setup_logger

logger = setup_logger(__name__)

class MetricValidator:
    """
    Validates metric definitions and prevents metric leakage (e.g. treating hip roll as torso roll).
    """

    @staticmethod
    def evaluate_definition_match(source_def: str, swimanalyzer_def: str) -> DefinitionMatchingStatus:
        """
        Compares scientific publication measurement definition against SwimAnalyzer definition.
        Prevents treating related but distinct measurements as identical.
        """
        src = (source_def or "").lower().strip()
        sa = (swimanalyzer_def or "").lower().strip()

        if src == sa or (("stroke rate" in src or "cycle frequency" in src) and ("stroke rate" in sa or "stroke_rate" in sa)):
            return DefinitionMatchingStatus.EXACT_MATCH
        elif ("distance per stroke" in src or "stroke length" in src) and ("stroke_length" in sa or "stroke length" in sa):
            return DefinitionMatchingStatus.EXACT_MATCH
        elif "shoulder roll" in src and "torso normal vector" in sa:
            return DefinitionMatchingStatus.DEFINITION_MISMATCH
        elif "hip roll" in src and "torso normal vector" in sa:
            return DefinitionMatchingStatus.DEFINITION_MISMATCH
        elif "symmetry" in src and "symmetry" in sa:
            return DefinitionMatchingStatus.COMPATIBLE_DEFINITION
        elif "kick frequency" in src and "kick_frequency" in sa:
            return DefinitionMatchingStatus.COMPATIBLE_DEFINITION
        else:
            return DefinitionMatchingStatus.UNKNOWN_DEFINITION

    @staticmethod
    def validate_stroke(extracted_stroke: str, source_context: str) -> bool:
        """
        Ensures the stroke extracted by the LLM is explicitly supported by the context.
        """
        if not extracted_stroke or not source_context:
            return False
        return extracted_stroke.lower().strip() in source_context.lower()
