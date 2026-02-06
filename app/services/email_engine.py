import httpx
import logging
import json
from app.services.pattern_engine import PatternEngine

logger = logging.getLogger("Email_Engine")

class EmailPermutator:
    @staticmethod
    def generate(full_name: str, domain: str):
        """
        Generates corporate email patterns with intelligent prioritization.
        
        NEW BEHAVIOR:
        - If domain has high-confidence pattern (>75%), returns ONLY that email (fast-track)
        - Otherwise, generates all standard patterns for brute force validation
        - This dramatically reduces API calls for known domains (1 vs 12+)
        """
        logger.debug(f"Generating email patterns for: {full_name} @ {domain}")
        if not full_name or not domain:
            logger.warning("Missing full_name or domain for email generation")
            return []

        # Clean inputs
        domain = domain.lower().strip()
        parts = full_name.lower().strip().split()
        
        if len(parts) < 2:
            return [f"{parts[0]}@{domain}"]

        fn = parts[0]   # First Name
        ln = parts[-1]  # Last Name
        fi = fn[0]      # First Initial
        li = ln[0]      # Last Initial

        candidates = []

        # 🚀 SMART FAST-TRACK MODE: Check if we should use single pattern
        if PatternEngine.should_use_fast_track(domain):
            pattern_data = PatternEngine.get_pattern_with_confidence(domain)
            if pattern_data:
                pattern = pattern_data['pattern']
                confidence = pattern_data['confidence']
                priority_email = PatternEngine.construct_email(pattern, fn, ln, domain)
                
                logger.info(f"⚡ FAST-TRACK MODE! Using high-confidence pattern for {domain}")
                logger.info(f"   Pattern: {pattern} | Confidence: {confidence:.1%} | Email: {priority_email}")
                
                return [priority_email]  # Return ONLY this email for validation
        
        # 🔄 STANDARD MODE: Try known pattern first, then fallback patterns
        known_pattern = PatternEngine.get_pattern(domain)
        if known_pattern:
            priority_email = PatternEngine.construct_email(known_pattern, fn, ln, domain)
            candidates.append(priority_email)
            logger.info(f"⚡ Known Pattern Priority: {priority_email} (pattern: {known_pattern})")
        else:
            logger.debug(f"No known pattern for domain: {domain}")

        # Add standard patterns as fallback (deduplicating if priority email exists)
        standard_patterns = [
            f"{fn}@{domain}",               # sam@openai.com
            f"{fn}.{ln}@{domain}",          # sam.altman@openai.com
            f"{fn}{ln}@{domain}",           # samaltman@openai.com
            f"{fi}{ln}@{domain}",           # saltman@openai.com
            f"{fi}.{ln}@{domain}",          # s.altman@openai.com
            f"{fn}{li}@{domain}",           # sama@openai.com
            f"{fn}.{li}@{domain}",          # sam.a@openai.com
            f"{ln}@{domain}",               # altman@openai.com
            f"{ln}.{fn}@{domain}",          # altman.sam@openai.com
            f"{ln}{fn}@{domain}",           # altmansam@openai.com
            f"{fn}_{ln}@{domain}",          # sam_altman@openai.com
            f"{fn}-{ln}@{domain}",          # sam-altman@openai.com
        ]
        
        # Add standards to list (preserving order, avoiding duplicates)
        for p in standard_patterns:
            if p not in candidates:
                candidates.append(p)
        
        logger.info(f"📧 Generated {len(candidates)} email candidates for {fn} {ln}")
        return candidates


class EmailValidator:
    def __init__(self):
        # Ensure this matches your Ngrok URL
        self.validator_url = "https://yelping-noelani-gravityer-a1962991.koyeb.app/verify/bulk/stream"

    async def find_valid_email(self, email_list: list, full_name: str = None, domain: str = None):
        """
        Streams email candidates to Validator and returns the first SAFE one.
        Handles SSE format (data: {...})
        
        NEW: Automatically learns and saves email patterns after successful validation
        
        Args:
            email_list: List of email candidates to validate
            full_name: Full name of person (used for pattern learning)
            domain: Email domain (used for pattern learning)
        """
        logger.info(f"🔍 Validating {len(email_list)} email candidates")
        logger.debug(f"Email candidates: {email_list}")
        
        if not email_list:
            logger.warning("Empty email list provided for validation")
            return None

        # Format for your 'BulkEmailRequest' model
        payload = {"emails": email_list}
        
        found_email = None
        risky_email = None
        used_fast_track = len(email_list) == 1  # True if we only validated 1 email

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", self.validator_url, json=payload) as response:
                    async for line in response.aiter_lines():
                        if not line: continue
                        
                        # --- FIX: Handle SSE "data: " prefix ---
                        if line.startswith("data: "):
                            clean_line = line[6:].strip() # Remove 'data: '
                            
                            if clean_line == "[DONE]": 
                                break # End of stream
                            
                            try:
                                result = json.loads(clean_line)
                                email = result.get("email") or result.get("input")
                                status = result.get("is_reachable")
                                
                                # LOGIC: Stop immediately if 'safe'
                                if status == "safe":
                                    logger.info(f"✅ Found SAFE email: {email}")
                                    found_email = {"email": email, "status": "safe", "score": 100}
                                    
                                    # 🧠 PATTERN LEARNING: Learn from this successful validation
                                    if full_name and domain:
                                        self._learn_pattern(email, full_name, domain, used_fast_track)
                                    
                                    return found_email
                                
                                # Backup 'risky'
                                if status == "risky" and not risky_email:
                                    logger.debug(f"Found RISKY email (backup): {email}")
                                    risky_email = {"email": email, "status": "risky", "score": 50}

                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse JSON: {clean_line}")
                                continue
                        # ----------------------------------------

            # If stream finishes without 'safe', return 'risky'
            if risky_email:
                logger.info(f"⚠️ Returning RISKY email: {risky_email['email']}")
                
                # Also learn from risky emails (with lower confidence)
                if full_name and domain:
                    self._learn_pattern(risky_email['email'], full_name, domain, used_fast_track)
                
                return risky_email
            
            # 📉 PATTERN FAILURE: Update stats if fast-track failed
            if used_fast_track and domain:
                PatternEngine.update_pattern_stats(domain, success=False)
                logger.warning(f"❌ Fast-track pattern failed for {domain}. Will use brute force next time.")
            
            logger.warning("No valid or risky emails found in validation")
            return None

        except httpx.TimeoutException as e:
            logger.error(f"⏱️ Validator timeout after 30s: {e}")
            return None
        except httpx.HTTPError as e:
            logger.error(f"🚫 HTTP error connecting to validator: {type(e).__name__} - {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"❌ Validator error: {type(e).__name__} - {e}", exc_info=True)
            return None
    
    def _learn_pattern(self, valid_email: str, full_name: str, domain: str, used_fast_track: bool):
        """
        Learn email pattern from a successful validation.
        
        Args:
            valid_email: The validated email address
            full_name: Full name of the person  
            domain: Email domain
            used_fast_track: Whether we used fast-track mode (single email)
        """
        try:
            parts = full_name.lower().strip().split()
            if len(parts) < 2:
                return  # Can't deduce pattern from single name
            
            fn, ln = parts[0], parts[-1]
            
            # Deduce the pattern from the valid email
            deduced_pattern = PatternEngine.deduce_pattern(valid_email, fn, ln, domain)
            
            if deduced_pattern:
                if used_fast_track:
                    # Fast-track worked! Update success stats
                    PatternEngine.update_pattern_stats(domain, success=True)
                    logger.info(f"✅ Fast-track pattern confirmed for {domain}")
                else:
                    # New pattern learned via brute force
                    PatternEngine.save_pattern(
                        domain=domain,
                        pattern=deduced_pattern,
                        example_email=valid_email,
                        success=True
                    )
                    logger.info(f"🧠 Learned NEW pattern for {domain}: {deduced_pattern}")
            else:
                logger.debug(f"Could not deduce pattern from {valid_email}")
                
        except Exception as e:
            logger.error(f"❌ Pattern learning error: {e}")