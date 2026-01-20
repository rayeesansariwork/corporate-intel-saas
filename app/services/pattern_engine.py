import logging

logger = logging.getLogger("Pattern_Engine")

class PatternEngine:
    # In-Memory Database for now.
    # In production, this resets when the server restarts.
    # Upgrade to Redis or Postgres for permanent memory.
    _mock_db = {} 

    @staticmethod
    def deduce_pattern(valid_email: str, first_name: str, last_name: str, domain: str):
        """
        Reverse-engineers a valid email to find the pattern.
        Example: rohit.kapoor@swiggy.com -> {fn}.{ln}
        """
        if not valid_email or not first_name or not last_name:
            return None
            
        local_part = valid_email.split("@")[0].lower()
        fn = first_name.lower().strip()
        ln = last_name.lower().strip()
        fi = fn[0]
        li = ln[0]

        # Check against standard corporate formats
        if local_part == f"{fn}.{ln}": return "{fn}.{ln}"
        if local_part == f"{fn}": return "{fn}"
        if local_part == f"{fn}{ln}": return "{fn}{ln}"
        if local_part == f"{fi}{ln}": return "{fi}{ln}"
        if local_part == f"{fi}.{ln}": return "{fi}.{ln}"
        if local_part == f"{fn}{li}": return "{fn}{li}"
        if local_part == f"{fn}.{li}": return "{fn}.{li}"
        if local_part == f"{ln}": return "{ln}"
        if local_part == f"{ln}.{fn}": return "{ln}.{fn}"
        if local_part == f"{fn}_{ln}": return "{fn}_{ln}"
        
        return None

    @staticmethod
    def construct_email(pattern: str, first_name: str, last_name: str, domain: str):
        """
        Builds a single email from a stored pattern.
        """
        fn = first_name.lower().strip()
        ln = last_name.lower().strip()
        fi = fn[0]
        li = ln[0]
        
        local = pattern.format(fn=fn, ln=ln, fi=fi, li=li)
        return f"{local}@{domain}"

    @classmethod
    def get_pattern(cls, domain: str):
        """
        Retrieves the 'Best Known Pattern' for a domain.
        """
        return cls._mock_db.get(domain)

    @classmethod
    def save_pattern(cls, domain: str, pattern: str):
        """
        Saves a successful pattern for future use.
        """
        if pattern:
            cls._mock_db[domain] = pattern
            logger.info(f"🧠 Learned pattern for {domain}: {pattern}")