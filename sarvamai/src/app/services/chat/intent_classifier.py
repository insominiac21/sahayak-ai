"""
Intent Classifier for Multi-Turn Conversations

Detects user intent to power context-aware responses:
- scheme_inquiry: "Tell me about X scheme"
- eligibility_check: "Am I eligible for X?"
- how_to_apply: "How do I apply?"
- documents_needed: "What documents do I need?"
- benefits_details: "What benefits do I get?"
- follow_up: Reference to previous scheme
- help_menu: Request for menu
"""

from typing import Dict, Tuple, Optional
import re


class IntentClassifier:
    """
    Classify user intent from natural language queries.
    
    Supports English, Hindi, Tamil, Telugu (basic keyword matching).
    Production version would use transformer model, but keywords work
    well for government schemes domain (high lexical specificity).
    """
    
    # Intent patterns
    INTENT_PATTERNS = {
        "eligibility_check": [
            # English
            r"am i eligible|who (is )?eligible|can i (apply|get|receive)",
            r"eligibility (criteria|requirements|for)",
            r"do i qualify|qualification",
            # Hindi
            r"पात्र|पात्रता|eligible|क्या मैं|मुझे मिल सकता है",
            # Tamil
            r"தகுதி|மார்க்கம்",
        ],
        "documents_needed": [
            # English
            r"(what )?documents (do i )?need|document(s)? required|proof|certificate",
            r"aadhar|pan|income|caste",
            # Hindi
            r"दस्तावेज़|कागजात|प्रमाण पत्र|आधार|पैन",
            # Tamil
            r"ஆவணம்|சான்றிதழ்",
        ],
        "how_to_apply": [
            # English
            r"(how )?do i apply|how to apply|apply (for|to|at)|application|register",
            r"where to apply|submit|fill form",
            # Hindi
            r"आवेदन|आवेदन करें|रजिस्ट्रेशन|ऑनलाइन|आवेदन कैसे करें",
            # Tamil
            r"விண்ணப்பம்|பதிவு",
        ],
        "benefits_details": [
            # English
            r"(what )?benefits|how much money|cash|amount|insurance|pension|loan",
            r"what (do i )?get|coverage|grant",
            # Hindi
            r"लाभ|पैसा|नगद|बीमा|पेंशन|ऋण|कितना",
            # Tamil
            r"பலன்|பணம்",
        ],
        "scheme_inquiry": [
            # English
            r"tell me about|what (is|are)|info|information|overview|details|explain",
            r"scheme (for|about)|government (scheme|program)",
            # Hindi
            r"बताएं|योजना|जानकारी|क्या है",
            # Tamil
            r"பற்றி|योजना",
        ],
    }
    
    # Scheme keywords (for extracting scheme name from query)
    SCHEME_KEYWORDS = {
        "pm-kisan": ["pm kisan", "kisan", "farmer", "agriculture"],
        "pmay-u": ["pmay", "housing", "house", "awas", "urban", "home"],
        "pmuy": ["ujjwala", "lpg", "gas", "cylinder", "women"],
        "ayushman bharat": ["ayushman", "health", "insurance", "hospital", "medical", "ab pm-jay"],
        "nsap": ["pension", "old age", "widow", "disability", "nsap"],
        "sukanya samriddhi": ["sukanya", "girl", "daughter", "education", "savings"],
        "apy": ["atal", "apy", "pension", "retirement"],
        "stand-up india": ["stand-up", "standup", "startup", "loan", "business"],
        "pmjdy": ["pradhan mantri", "jan dhan", "bank", "account", "zero balance"],
    }
    
    def __init__(self):
        """Initialize classifier with compiled patterns."""
        self.intent_patterns = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
            self.intent_patterns[intent] = compiled
    
    def classify(self, query: str) -> Tuple[str, float]:
        """
        Classify user intent.
        
        Args:
            query: User query text
            
        Returns:
            (intent_name, confidence) tuple
            - intent_name: Primary intent
            - confidence: 0.0-1.0 (based on pattern matches)
        """
        query_lower = query.lower()
        scores = {}
        
        # Score each intent
        for intent, patterns in self.intent_patterns.items():
            matches = 0
            for pattern in patterns:
                if pattern.search(query_lower):
                    matches += 1
            
            if matches > 0:
                # Confidence = number of patterns matched / total patterns
                confidence = matches / len(patterns)
                scores[intent] = confidence
        
        # Return top intent
        if not scores:
            return "scheme_inquiry", 0.0  # Default
        
        best_intent = max(scores, key=scores.get)
        return best_intent, scores[best_intent]
    
    def extract_scheme(self, query: str) -> Optional[str]:
        """
        Extract scheme name from query if mentioned.
        
        Args:
            query: User query
            
        Returns:
            Scheme name or None
        """
        query_lower = query.lower()
        
        # Check each scheme's keywords
        for scheme, keywords in self.SCHEME_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    return scheme
        
        return None
    
    def is_follow_up(self, current_query: str, previous_context: Dict) -> bool:
        """
        Determine if current query is a follow-up to previous conversation.
        
        Args:
            current_query: Current user query
            previous_context: Dict with previous_scheme, previous_intent, etc.
            
        Returns:
            True if likely a follow-up
        """
        if not previous_context:
            return False
        
        # If no scheme mentioned in current query but context has one
        current_scheme = self.extract_scheme(current_query)
        previous_scheme = previous_context.get("previous_scheme")
        
        if not current_scheme and previous_scheme:
            # Check for follow-up indicators
            follow_up_patterns = [
                r"after|next|then|next step|how|what|where|when|cost|fee",
                r"अगला|फिर|अगले|फिर क्या|कहाँ|कैसे",
                r"பின்பு|அடுத்து|எப்போது",
            ]
            
            for pattern in follow_up_patterns:
                if re.search(pattern, current_query.lower()):
                    return True
        
        return False


def create_intent_classifier() -> IntentClassifier:
    """Factory function to create classifier."""
    return IntentClassifier()


# Global instance
_classifier = None

def get_intent_classifier() -> IntentClassifier:
    """Get or create global classifier."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier
