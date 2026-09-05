from core.logger import setup_logger

logger = setup_logger(__name__)

class ProvenanceValidator:
    """
    Validates data extraction provenance.
    Prevents LLM hallucination by forcing verbatim string matching between
    the extracted quote and the original XML text block.
    """

    @staticmethod
    def validate_provenance(extracted_quote: str, full_xml_text: str) -> bool:
        """
        Ensures the quoted evidence actually exists verbatim in the parsed source.
        Prevents LLM hallucination of numerical evidence.
        """
        if not extracted_quote or not full_xml_text:
            return False
        # Remove excess whitespace and newlines for robust matching
        clean_quote = " ".join(extracted_quote.split()).lower()
        clean_text = " ".join(full_xml_text.split()).lower()
        return clean_quote in clean_text
