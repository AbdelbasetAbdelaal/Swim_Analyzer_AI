import pytest
import yaml
from pathlib import Path

from scientific_reference.scientific_source_repository import ScientificSourceRepository

@pytest.fixture
def repo():
    return ScientificSourceRepository()

@pytest.fixture
def source_data():
    p = Path("scientific_reference/sources/source_registry.yaml")
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@pytest.fixture
def evidence_data():
    p = Path("scientific_reference/evidence/evidence_registry.yaml")
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_source_pmid_and_title_integrity(source_data):
    """Enforces that every registered source has a valid PMID/DOI and verified title."""
    sources = source_data.get("sources", {})
    assert len(sources) > 0, "Source registry cannot be empty"

    for sid, sdata in sources.items():
        pmid = sdata.get("pmid")
        doi = sdata.get("doi")
        title = sdata.get("title")
        authors = sdata.get("authors", [])

        assert pmid is not None or doi is not None, f"Source {sid} missing both PMID and DOI"
        assert title is not None and len(title) > 10, f"Source {sid} missing descriptive title"
        assert len(authors) > 0, f"Source {sid} must list authors"
        assert sdata.get("verification_status") in ["VERIFIED_CORRECT", "PEER_REVIEWED_ABSTRACT_ONLY"], f"Source {sid} not verified against PubMed/DOI registry"

def test_evidence_records_link_to_verified_sources(repo, evidence_data):
    """Enforces that all evidence records link to verified scientific sources."""
    records = evidence_data.get("evidence_records", {})
    for eid, rec in records.items():
        sid = rec.get("source_id")
        source = repo.get_source(sid)

        assert source is not None, f"Evidence {eid} links to unregistered source {sid}"
        assert source.publication_year == rec.get("year"), f"Year mismatch between evidence {eid} and source {sid}"
        assert source.pmid == rec.get("pmid"), f"PMID mismatch between evidence {eid} ({rec.get('pmid')}) and source {sid} ({source.pmid})"

def test_prohibit_unverified_or_invalid_sources(source_data, evidence_data):
    """Ensures no source tagged INVALID_SOURCE_MAPPING or UNVERIFIED is used in SCIENTIFICALLY_ACCEPTED benchmarks."""
    sources = source_data.get("sources", {})
    records = evidence_data.get("evidence_records", {})

    for eid, rec in records.items():
        if rec.get("scientific_status") == "SCIENTIFICALLY_ACCEPTED":
            sid = rec.get("source_id")
            sdata = sources.get(sid, {})
            assert sdata.get("verification_status") != "INVALID_SOURCE_MAPPING", f"Accepted evidence {eid} uses invalid source {sid}"
            assert sdata.get("access_level") == "FULL_TEXT_VERIFIED", f"Accepted evidence {eid} must be full-text verified"
