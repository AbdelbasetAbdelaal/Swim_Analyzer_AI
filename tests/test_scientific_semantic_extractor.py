import os
import pytest
from services.scientific_semantic_extractor import ScientificSemanticExtractor, HAS_GEMINI

def test_semantic_extractor_degraded_mode():
    extractor = ScientificSemanticExtractor(api_key="INVALID_KEY")
    if not HAS_GEMINI:
        assert extractor.is_degraded() is True
    else:
        # If API key is provided but invalid, it shouldn't necessarily fail on init, 
        # but generate_content would fail.
        pass

def test_extract_evidence_candidates_degraded():
    extractor = ScientificSemanticExtractor(api_key="")
    assert extractor.is_degraded() is True
    
    res = extractor.extract_evidence_candidates("Some text with 0.90 Hz.")
    assert res is None

@pytest.mark.skipif(not HAS_GEMINI or not os.environ.get("GEMINI_API_KEY"), reason="Requires GEMINI_API_KEY and google-generativeai")
def test_extract_evidence_candidates_real():
    extractor = ScientificSemanticExtractor()
    assert not extractor.is_degraded()
    
    # Provide a clear unambiguous table
    context = "Table 2: Kinematics of Elite Male Swimmers. Freestyle Stroke rate was 1.15 Hz ± 0.05 Hz. Body roll was 45 degrees."
    res = extractor.extract_evidence_candidates(context)
    
    assert res is not None
    assert "candidates" in res
    assert isinstance(res["candidates"], list)
    
    # We can't perfectly predict LLM output, but we expect at least one candidate
    found_stroke_rate = False
    for cand in res["candidates"]:
        if "rate" in (cand.get("metric") or "").lower() or cand.get("mean") == 1.15:
            found_stroke_rate = True
            assert cand.get("stroke", "").lower() == "freestyle"
            assert cand.get("population_sex", "").lower() == "male"
            break
            
    assert found_stroke_rate, "Gemini failed to extract the stroke rate correctly."
