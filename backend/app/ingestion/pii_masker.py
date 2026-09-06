import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

class PIIMasker:
    def __init__(self):
        self.presidio_available = False
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            from presidio_anonymizer.entities import OperatorConfig
            
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            self.presidio_available = True
            
            self.operators = {
                "PERSON": OperatorConfig("replace", {"new_value": "[NAME]"}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
                "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"})
            }
            self.entities = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN", "IP_ADDRESS"]
        except ImportError:
            logger.warning("presidio-analyzer or presidio-anonymizer not installed. Falling back to basic regex PII masking. Name detection will not work.")

    def mask_text(self, text: str) -> str:
        if self.presidio_available:
            results = self.analyzer.analyze(text=text, entities=self.entities, language='en', score_threshold=0.5)
            anonymized_result = self.anonymizer.anonymize(text=text, analyzer_results=results, operators=self.operators)
            return anonymized_result.text
        else:
            # Fallback regex
            text = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL]', text)
            text = re.sub(r'\+?\d[\d -]{8,12}\d', '[PHONE]', text)
            return text

_masker = None

def get_masker() -> PIIMasker:
    global _masker
    if _masker is None:
        _masker = PIIMasker()
    return _masker
