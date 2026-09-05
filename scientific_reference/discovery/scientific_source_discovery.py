import requests
from typing import List, Dict, Any
from core.logger import setup_logger

logger = setup_logger(__name__)

class ScientificSourceDiscovery:
    """
    Legal scientific publication discovery engine using open APIs (NCBI E-utilities & Europe PMC).
    Does NOT scrape paywalled websites or violate publisher terms.
    """
    PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EUROPE_PMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def search_pubmed(self, query: str = "swimming biomechanics stroke rate", max_results: int = 10) -> List[str]:
        """Queries NCBI PubMed E-utilities for PMIDs matching query."""
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results
        }
        try:
            resp = requests.get(self.PUBMED_SEARCH_URL, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                pmids = data.get("esearchresult", {}).get("idlist", [])
                logger.info(f"PubMed discovery query '{query}' returned {len(pmids)} PMIDs.")
                return pmids
        except Exception as e:
            logger.warning(f"PubMed discovery request failed: {e}")
        return []

    def search_europe_pmc(self, query: str = "swimming stroke length kinematic", max_results: int = 10) -> List[Dict[str, Any]]:
        """Queries Europe PMC REST API for open access swimming literature metadata."""
        params = {
            "query": query,
            "format": "json",
            "pageSize": max_results
        }
        try:
            resp = requests.get(self.EUROPE_PMC_URL, params=params, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get("resultList", {}).get("result", [])
                logger.info(f"Europe PMC discovery returned {len(results)} literature records.")
                return results
        except Exception as e:
            logger.warning(f"Europe PMC discovery request failed: {e}")
        return []
