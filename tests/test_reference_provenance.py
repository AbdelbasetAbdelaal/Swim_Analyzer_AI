"""
Tests for Reference Provenance tracking (authors, title, DOI, PMID, evidence grade).
"""

from models.reference_data_models import ReferenceDataset, ReferenceSource, ReferenceMetric

def test_provenance_preservation():
    ds = ReferenceDataset(
        name="European Championship Study 2022",
        stroke="BREASTSTROKE",
        sources=[
            ReferenceSource(
                source_title="Performance Development of European Swimmers Across the Olympic Cycle",
                authors="Born DP et al.",
                publication_year=2022,
                doi="10.3389/fspor.2022.894066",
                pmid="35755613"
            )
        ],
        metrics=[
            ReferenceMetric(
                metric_name="Start Time",
                value_typical=6.43,
                unit="s",
                evidence_grade="A",
                course="LCM"
            )
        ]
    )

    assert len(ds.sources) == 1
    src = ds.sources[0]
    assert src.doi == "10.3389/fspor.2022.894066"
    assert src.pmid == "35755613"
    assert src.authors == "Born DP et al."

    m = ds.metrics[0]
    assert m.evidence_grade == "A"
    assert m.course == "LCM"
