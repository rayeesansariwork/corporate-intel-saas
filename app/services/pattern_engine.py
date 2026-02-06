import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("Pattern_Engine")

class PatternEngine:
    """
    Intelligent Email Pattern Learning Engine with persistent storage.
    
    Features:
    - JSON file-based persistence (survives server restarts)
    - Confidence scoring based on success/failure rates
    - Pattern statistics tracking (usage count, last used, etc.)
    - Automatic pattern learning from successful validations
    - Smart pattern selection with fallback strategies
    """
    
    # Storage file path
    _STORAGE_PATH = Path("data/email_patterns.json")
    
    # In-memory cache (loaded from file)
    _pattern_cache: Dict[str, Dict[str, Any]] = {}
    
    # Confidence threshold for fast-track mode
    CONFIDENCE_THRESHOLD = 0.75
    
    @classmethod
    def _ensure_storage_dir(cls):
        """Ensure the storage directory exists."""
        cls._STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def _load_patterns(cls):
        """Load patterns from JSON file into memory cache."""
        cls._ensure_storage_dir()
        
        if cls._STORAGE_PATH.exists():
            try:
                with open(cls._STORAGE_PATH, 'r') as f:
                    cls._pattern_cache = json.load(f)
                logger.info(f"📖 Loaded {len(cls._pattern_cache)} domain patterns from storage")
            except Exception as e:
                logger.error(f"❌ Failed to load patterns: {e}")
                cls._pattern_cache = {}
        else:
            cls._pattern_cache = {}
    
    @classmethod
    def _save_patterns(cls):
        """Persist patterns from memory cache to JSON file."""
        cls._ensure_storage_dir()
        
        try:
            with open(cls._STORAGE_PATH, 'w') as f:
                json.dump(cls._pattern_cache, f, indent=2)
            logger.debug(f"💾 Saved {len(cls._pattern_cache)} patterns to storage")
        except Exception as e:
            logger.error(f"❌ Failed to save patterns: {e}")
    
    @staticmethod
    def deduce_pattern(valid_email: str, first_name: str, last_name: str, domain: str) -> Optional[str]:
        """
        Reverse-engineers a valid email to find the pattern.
        Example: rohit.kapoor@swiggy.com -> {fn}.{ln}
        """
        if not valid_email or not first_name or not last_name:
            return None
            
        try:
            local_part = valid_email.split("@")[0].lower()
            fn = first_name.lower().strip()
            ln = last_name.lower().strip()
            
            if not fn or not ln:
                return None
                
            fi = fn[0]
            li = ln[0]

            # Check against standard corporate formats
            patterns = [
                (f"{fn}.{ln}", "{fn}.{ln}"),
                (f"{fn}", "{fn}"),
                (f"{fn}{ln}", "{fn}{ln}"),
                (f"{fi}{ln}", "{fi}{ln}"),
                (f"{fi}.{ln}", "{fi}.{ln}"),
                (f"{fn}{li}", "{fn}{li}"),
                (f"{fn}.{li}", "{fn}.{li}"),
                (f"{ln}", "{ln}"),
                (f"{ln}.{fn}", "{ln}.{fn}"),
                (f"{fn}_{ln}", "{fn}_{ln}"),
                (f"{fn}-{ln}", "{fn}-{ln}"),
                (f"{fi}-{ln}", "{fi}-{ln}"),
            ]
            
            for local_format, pattern_template in patterns:
                if local_part == local_format:
                    return pattern_template
            
            return None
        except Exception as e:
            logger.error(f"❌ Pattern deduction error: {e}")
            return None

    @staticmethod
    def construct_email(pattern: str, first_name: str, last_name: str, domain: str) -> str:
        """
        Builds a single email from a stored pattern.
        """
        try:
            fn = first_name.lower().strip()
            ln = last_name.lower().strip()
            fi = fn[0] if fn else ""
            li = ln[0] if ln else ""
            
            local = pattern.format(fn=fn, ln=ln, fi=fi, li=li)
            return f"{local}@{domain}"
        except Exception as e:
            logger.error(f"❌ Email construction error: {e}")
            return f"{fn}@{domain}"  # Fallback

    @classmethod
    def get_pattern(cls, domain: str) -> Optional[str]:
        """
        Retrieves the best known pattern for a domain.
        Returns the pattern string if found, None otherwise.
        """
        # Lazy load patterns on first access
        if not cls._pattern_cache:
            cls._load_patterns()
        
        domain = domain.lower().strip()
        pattern_data = cls._pattern_cache.get(domain)
        
        if pattern_data:
            return pattern_data.get('pattern')
        return None
    
    @classmethod
    def get_pattern_with_confidence(cls, domain: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves pattern with confidence score and statistics.
        
        Returns:
            {
                'pattern': str,
                'confidence': float,
                'success_count': int,
                'total_attempts': int,
                'last_used': str,
                'example_email': str
            }
        """
        # Lazy load patterns on first access
        if not cls._pattern_cache:
            cls._load_patterns()
        
        domain = domain.lower().strip()
        pattern_data = cls._pattern_cache.get(domain)
        
        if pattern_data:
            return pattern_data.copy()
        return None

    @classmethod
    def save_pattern(cls, domain: str, pattern: str, example_email: str = None, success: bool = True):
        """
        Saves or updates a pattern for a domain with statistics tracking.
        
        Args:
            domain: Email domain (e.g., "openai.com")
            pattern: Pattern template (e.g., "{fn}.{ln}")
            example_email: Optional example of a valid email using this pattern
            success: Whether this pattern validation was successful
        """
        if not pattern:
            return
        
        # Lazy load patterns on first access
        if not cls._pattern_cache:
            cls._load_patterns()
        
        domain = domain.lower().strip()
        
        # Get existing data or create new entry
        if domain in cls._pattern_cache:
            data = cls._pattern_cache[domain]
            
            # Update statistics
            data['total_attempts'] = data.get('total_attempts', 1) + 1
            if success:
                data['success_count'] = data.get('success_count', 1) + 1
            
            # Recalculate confidence
            data['confidence'] = data['success_count'] / data['total_attempts']
            data['last_used'] = datetime.now().isoformat()
            
            # Update pattern if this is a successful validation
            if success:
                data['pattern'] = pattern
                if example_email:
                    data['example_email'] = example_email
                
            logger.info(f"📊 Updated pattern for {domain}: {pattern} (confidence: {data['confidence']:.2f})")
        else:
            # Create new pattern entry
            data = {
                'pattern': pattern,
                'success_count': 1 if success else 0,
                'total_attempts': 1,
                'confidence': 1.0 if success else 0.0,
                'first_seen': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat(),
                'example_email': example_email
            }
            cls._pattern_cache[domain] = data
            logger.info(f"🧠 Learned NEW pattern for {domain}: {pattern}")
        
        # Persist to file
        cls._save_patterns()
    
    @classmethod
    def update_pattern_stats(cls, domain: str, success: bool):
        """
        Update pattern statistics without changing the pattern itself.
        Useful for tracking when a known pattern is used.
        
        Args:
            domain: Email domain
            success: Whether the pattern validation succeeded
        """
        # Lazy load patterns on first access
        if not cls._pattern_cache:
            cls._load_patterns()
        
        domain = domain.lower().strip()
        
        if domain in cls._pattern_cache:
            data = cls._pattern_cache[domain]
            data['total_attempts'] = data.get('total_attempts', 0) + 1
            
            if success:
                data['success_count'] = data.get('success_count', 0) + 1
            
            # Recalculate confidence
            if data['total_attempts'] > 0:
                data['confidence'] = data['success_count'] / data['total_attempts']
            
            data['last_used'] = datetime.now().isoformat()
            
            # Persist to file
            cls._save_patterns()
            
            logger.debug(f"📈 Stats updated for {domain}: {data['success_count']}/{data['total_attempts']} (confidence: {data['confidence']:.2f})")
    
    @classmethod
    def should_use_fast_track(cls, domain: str) -> bool:
        """
        Determine if we should use fast-track mode (single pattern) for this domain.
        
        Returns True if pattern confidence is above threshold.
        """
        pattern_data = cls.get_pattern_with_confidence(domain)
        
        if pattern_data:
            confidence = pattern_data.get('confidence', 0.0)
            return confidence >= cls.CONFIDENCE_THRESHOLD
        
        return False
    
    @classmethod
    def get_all_patterns(cls) -> Dict[str, Dict[str, Any]]:
        """Get all stored patterns (for debugging/admin purposes)."""
        if not cls._pattern_cache:
            cls._load_patterns()
        return cls._pattern_cache.copy()
    
    @classmethod
    def clear_patterns(cls):
        """Clear all patterns (for testing purposes)."""
        cls._pattern_cache = {}
        cls._save_patterns()
        logger.warning("🗑️ All patterns cleared")