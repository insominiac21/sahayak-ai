"""
Metadata extraction for government scheme chunks.
Extracts structured information from scheme documents for filtering and context.
"""

import re
from typing import Dict, List, Optional


class SchemeMetadataExtractor:
    """Extract and tag metadata from scheme document chunks."""

    # Keywords mapped to categories
    CATEGORY_KEYWORDS = {
        "agriculture": ["kisan", "farmer", "cultivation", "crop", "farm", "agricultural"],
        "health": ["ayushman", "health", "insurance", "medical", "hospital", "disease"],
        "housing": ["awas", "house", "housing", "home", "residential", "shelter"],
        "pension": ["pension", "retirement", "elderly", "atal", "apy", "old age"],
        "employment": ["employment", "job", "work", "skill", "training", "startup"],
        "education": ["education", "student", "school", "college", "sukanya", "scholarship"],
        "general": ["scheme", "yojana", "pradhan mantri", "pm", "government"],
    }

    # Applicability keywords
    APPLICABILITY_KEYWORDS = {
        "rural": ["rural", "village", "gram"],
        "urban": ["urban", "city", "metropolitan"],
        "all": ["all", "universal", "everyone", "citizen"],
    }

    # Benefits type keywords
    BENEFITS_KEYWORDS = {
        "cash": ["cash", "amount", "money", "rupees", "₹"],
        "insurance": ["insurance", "coverage", "cover"],
        "loans": ["loan", "credit", "lending"],
        "subsidy": ["subsidy", "discount", "concession"],
        "pension": ["pension", "monthly", "allowance"],
    }

    def __init__(self):
        self.scheme_names = {
            "pmay-u": ["pradhan mantri awas yojana", "pmay-u", "housing scheme"],
            "pmjdy": ["pradhan mantri jan-dhan yojana", "pmjdy", "zero balance account"],
            "pmuy": ["pradhan mantri ujjwala yojana", "pmuy", "lpg connection"],
            "ayushman bharat": ["ayushman bharat", "pm-jay", "health insurance"],
            "nsap": ["national social assistance", "nsap", "pension"],
            "sukanya samriddhi": ["sukanya samriddhi yojana", "ssy", "girl child"],
            "apy": ["atal pension yojana", "apy", "guaranteed pension"],
            "stand-up india": ["stand-up india", "startup loan"],
        }

    def extract_scheme_name(self, text: str, source: str = "") -> str:
        """
        Extract the primary scheme name from text.
        
        Args:
            text: Chunk text
            source: Source document name (fallback)
        
        Returns:
            Scheme name or "Unknown"
        """
        text_lower = text.lower()
        
        # Check against known schemes
        for scheme_name, keywords in self.scheme_names.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return scheme_name
        
        # Fallback to source
        if source:
            source_lower = source.lower()
            for scheme_name, keywords in self.scheme_names.items():
                for keyword in keywords:
                    if keyword in source_lower:
                        return scheme_name
        
        return "Unknown"

    def extract_category(self, text: str, scheme_name: str = "") -> str:
        """
        Extract category from text.
        
        Args:
            text: Chunk text
            scheme_name: Scheme name for context
        
        Returns:
            Category name
        """
        text_lower = text.lower()
        
        # Score each category
        scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[category] = score
        
        # Return highest scoring category or "general"
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        # Map schemes to default categories
        if "agriculture" in scheme_name.lower() or "kisan" in scheme_name.lower():
            return "agriculture"
        elif "health" in scheme_name.lower() or "ayushman" in scheme_name.lower():
            return "health"
        elif "housing" in scheme_name.lower() or "awas" in scheme_name.lower():
            return "housing"
        
        return "general"

    def extract_applicability(self, text: str) -> List[str]:
        """
        Extract applicability (rural/urban/all).
        
        Args:
            text: Chunk text
        
        Returns:
            List of applicability tags
        """
        text_lower = text.lower()
        result = []
        
        for applicability, keywords in self.APPLICABILITY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                result.append(applicability)
        
        return result if result else ["all"]

    def extract_income_limit(self, text: str) -> Optional[float]:
        """
        Extract income limit if mentioned.
        
        Args:
            text: Chunk text
        
        Returns:
            Income limit in rupees or None
        """
        # Look for patterns like "income < ₹100,000" or "income limit of 200000"
        patterns = [
            r"income[^0-9]*[<≤]*\s*[₹]?\s*(\d{1,3}(?:,\d{3})*)",
            r"income[^0-9]*limit[^0-9]*[₹]?\s*(\d{1,3}(?:,\d{3})*)",
            r"[₹]?\s*(\d{1,3}(?:,\d{3})*)\s*per annum",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(",", "")
                    return float(amount_str)
                except ValueError:
                    continue
        
        return None

    def extract_benefits(self, text: str) -> List[str]:
        """
        Extract benefit types (cash, insurance, loans, subsidy, pension).
        
        Args:
            text: Chunk text
        
        Returns:
            List of benefit types
        """
        text_lower = text.lower()
        result = []
        
        for benefit, keywords in self.BENEFITS_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                result.append(benefit)
        
        return result if result else []

    def extract_chunk_type(self, text: str, chunk_number: int = 0) -> str:
        """
        Infer chunk type (eligibility, benefits, documents, process, etc).
        
        Args:
            text: Chunk text
            chunk_number: Position in document (for heuristics)
        
        Returns:
            Chunk type label
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["eligib", "who can apply", "eligible"]):
            return "eligibility"
        elif any(word in text_lower for word in ["benefit", "amount", "grant", "incentive"]):
            return "benefits"
        elif any(word in text_lower for word in ["document", "require", "submit"]):
            return "documents"
        elif any(word in text_lower for word in ["process", "apply", "application", "step", "how to"]):
            return "process"
        elif any(word in text_lower for word in ["claim", "disbursement", "payment"]):
            return "disbursement"
        else:
            return "overview"

    def extract_all(self, text: str, source: str = "", chunk_number: int = 0) -> Dict:
        """
        Extract all metadata from a chunk.
        
        Args:
            text: Chunk content
            source: Source document name
            chunk_number: Position in document
        
        Returns:
            Dictionary of all extracted metadata
        """
        scheme_name = self.extract_scheme_name(text, source)
        
        return {
            "scheme_name": scheme_name,
            "category": self.extract_category(text, scheme_name),
            "applicability": self.extract_applicability(text),
            "income_limit": self.extract_income_limit(text),
            "benefits": self.extract_benefits(text),
            "chunk_type": self.extract_chunk_type(text, chunk_number),
            "source": source,
        }
