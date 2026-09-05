"""
Export Service for Reference Data Manager.
Exports Reference Datasets to CSV, JSON, and YAML formats while preserving
all metadata, metric definitions, scientific provenance, and validation status.
"""

import io
import csv
import json
import yaml
from dataclasses import asdict
from typing import List
from models.reference_data_models import ReferenceDataset

class ReferenceExportService:

    @classmethod
    def export_to_csv(cls, datasets: List[ReferenceDataset]) -> str:
        """Exports datasets and metrics to flat CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)

        headers = [
            "dataset_id", "dataset_name", "description", "stroke", "age_min", "age_max", "sex", "skill_level", "athlete_category",
            "source_type", "evidence_status", "benchmark_eligibility", "validation_status", "is_archived",
            "metric_name", "display_name", "value_min", "value_typical", "value_median", "value_max", "unit",
            "measurement_domain", "status", "method", "metric_notes",
            "source_title", "authors", "publication_year", "doi", "pmid", "url", "sample_size"
        ]
        writer.writerow(headers)

        for ds in datasets:
            src = ds.sources[0] if ds.sources else None
            src_title = src.source_title if src else ""
            authors = src.authors if src else ""
            pub_yr = src.publication_year if src else ""
            doi = src.doi if src else ""
            pmid = src.pmid if src else ""
            url = src.url if src else ""
            sample_size = src.sample_size if src else ""

            if not ds.metrics:
                # Export dataset row even if metrics empty
                writer.writerow([
                    ds.dataset_id, ds.name, ds.description, ds.stroke, ds.age_min, ds.age_max, ds.sex, ds.skill_level, ds.athlete_category,
                    ds.source_type, ds.evidence_status, ds.benchmark_eligibility, ds.validation_status, ds.is_archived,
                    "", "", "", "", "", "", "", "", "", "", "",
                    src_title, authors, pub_yr, doi, pmid, url, sample_size
                ])
            else:
                for m in ds.metrics:
                    writer.writerow([
                        ds.dataset_id, ds.name, ds.description, ds.stroke, ds.age_min, ds.age_max, ds.sex, ds.skill_level, ds.athlete_category,
                        ds.source_type, ds.evidence_status, ds.benchmark_eligibility, ds.validation_status, ds.is_archived,
                        m.metric_name, m.display_name,
                        m.value_min if m.value_min is not None else "",
                        m.value_typical if m.value_typical is not None else "",
                        m.value_median if m.value_median is not None else "",
                        m.value_max if m.value_max is not None else "",
                        m.unit, m.measurement_domain, m.status, m.method, m.notes,
                        src_title, authors, pub_yr, doi, pmid, url, sample_size
                    ])

        return output.getvalue()

    @classmethod
    def export_to_json(cls, datasets: List[ReferenceDataset]) -> str:
        """Exports datasets to formatted JSON string."""
        data = [asdict(ds) for ds in datasets]
        return json.dumps(data, indent=2)

    @classmethod
    def export_to_yaml(cls, datasets: List[ReferenceDataset]) -> str:
        """Exports datasets to structured YAML format compatible with benchmark registry."""
        yaml_dict = {"reference_datasets": []}
        for ds in datasets:
            ds_dict = asdict(ds)
            yaml_dict["reference_datasets"].append(ds_dict)
        return yaml.dump(yaml_dict, sort_keys=False, default_flow_style=False)
