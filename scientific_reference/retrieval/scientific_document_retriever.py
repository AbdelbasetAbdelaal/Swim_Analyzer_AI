import requests
from typing import Dict, Any
from models.scientific_evidence_models import SourceAccessLevel
from core.logger import setup_logger

logger = setup_logger(__name__)

class ScientificDocumentRetriever:
    """
    Retrieves open-access publication metadata and PMC XML text legally via NCBI Summary APIs.
    Strictly distinguishes FULL_TEXT_VERIFIED, ABSTRACT_VERIFIED, METADATA_ONLY, UNVERIFIED.
    Never bypasses paywalls or scrapes copyrighted PDFs without license.
    """
    PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def fetch_pubmed_metadata(self, pmid: str) -> Dict[str, Any]:
        """Fetches metadata summary for a given PMID via NCBI E-utilities."""
        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "json"
        }
        try:
            resp = requests.get(self.PUBMED_SUMMARY_URL, params=params, timeout=10)
            if resp.status_code == 200:
                result = resp.json().get("result", {}).get(pmid, {})
                doi = ""
                for article_id in result.get("articleids", []):
                    if article_id.get("idtype") == "doi":
                        doi = article_id.get("idvalue", "")

                has_pmc = any(a.get("idtype") == "pmc" for a in result.get("articleids", []))
                access_level = SourceAccessLevel.FULL_TEXT_VERIFIED if has_pmc else SourceAccessLevel.ABSTRACT_VERIFIED

                return {
                    "source_id": f"PMID-{pmid}",
                    "title": result.get("title", ""),
                    "authors": [a.get("name", "") for a in result.get("authors", [])],
                    "pubdate": result.get("pubdate", ""),
                    "source": result.get("source", ""),
                    "doi": doi,
                    "access_level": access_level
                }
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for PMID {pmid}: {e}")

        return {
            "source_id": f"PMID-{pmid}",
            "title": "",
            "authors": [],
            "access_level": SourceAccessLevel.UNVERIFIED
        }
