"""
Tests for preserving scientific provenance in imported CSV datasets.
"""

from services.reference_csv_service import ReferenceCSVService

def test_provenance_retention_on_import():
    raw_csv = (
        "dataset_name,stroke,metric_name,unit,value_typical,source_type,source_title,authors,publication_year,doi,pmid,population_description\n"
        "Olympic Study,FREESTYLE,Swim Velocity,m/s,2.12,PEER_REVIEWED_PRIMARY_STUDY,European Championship Kinematics,Born DP et al.,2022,10.3389/fspor.2022.894066,35755613,Elite male finalists\n"
    )

    preview = ReferenceCSVService.parse_and_validate_csv(raw_csv)
    assert preview.valid_rows == 1

    datasets = ReferenceCSVService.convert_csv_to_datasets(preview)
    assert len(datasets) == 1
    ds = datasets[0]
    assert len(ds.sources) == 1
    src = ds.sources[0]
    assert src.doi == "10.3389/fspor.2022.894066"
    assert src.pmid == "35755613"
    assert src.authors == "Born DP et al."
