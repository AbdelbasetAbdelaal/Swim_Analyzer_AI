"""
Tests for ReferenceCSVService import and validation preview.
"""

from services.reference_csv_service import ReferenceCSVService

def test_csv_template_generation():
    template = ReferenceCSVService.generate_sample_csv_template()
    assert "dataset_name" in template
    assert "metric_name" in template
    assert "value_typical" in template
    assert "PEER_REVIEWED_PRIMARY_STUDY" in template

def test_csv_validation_preview_valid_and_malformed():
    csv_text = (
        "dataset_name,stroke,age_min,age_max,sex,skill_level,athlete_category,metric_name,value_min,value_typical,value_median,value_max,unit,measurement_domain,status,method,source_type,source_title,authors,publication_year,doi,pmid,url,sample_size\n"
        "Valid Study,FREESTYLE,18,25,Male,Elite,Adult,stroke_rate,50.0,55.0,55.0,60.0,spm,CALIBRATED_PHYSICAL,available,video,PEER_REVIEWED_PRIMARY_STUDY,Title,Author,2024,10.1016/j.jbiomech,12345,,30\n"
        "Malformed Row,FREESTYLE,18,25,Male,Elite,Adult,stroke_rate,65.0,55.0,,50.0,spm,CALIBRATED_PHYSICAL,available,video,COACH_DEFINED,,,,,,\n"
    )

    preview = ReferenceCSVService.parse_and_validate_csv(csv_text)
    assert preview.total_rows == 2
    assert preview.valid_rows == 1
    assert preview.invalid_rows == 1

    datasets = ReferenceCSVService.convert_csv_to_datasets(preview)
    assert len(datasets) == 1
    assert datasets[0].name == "Valid Study"
    assert datasets[0].validation_status == "DRAFT"
    assert datasets[0].benchmark_eligibility == "CONTEXT_ONLY"
