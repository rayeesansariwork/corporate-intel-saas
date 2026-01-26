import httpx
import logging
import json
from app.services.pattern_engine import PatternEngine

logger = logging.getLogger("Email_Engine")

class EmailPermutator:
    @staticmethod
    def generate(full_name: str, domain: str):
        """
        Generates corporate email patterns, prioritizing known successful patterns first.
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

        # 1. SMART CHECK: Do we already know the pattern for this domain?
        known_pattern = PatternEngine.get_pattern(domain)
        if known_pattern:
            priority_email = PatternEngine.construct_email(known_pattern, fn, ln, domain)
            candidates.append(priority_email)
            logger.info(f"⚡ Smart Pattern Hit! Prioritizing: {priority_email}")
        else:
            logger.debug(f"No known pattern for domain: {domain}")

        # 2. The "Big 15" Corporate Patterns (Fallback list)
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
            f"{fi}-{ln}@{domain}",          # s-altman@openai.com
            f"{fn}-{li}@{domain}",          # sam-a@openai.com
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
        self.validator_url = "https://beautifully-unpleasing-chasidy.ngrok-free.dev/verify/bulk/stream"

    async def find_valid_email(self, email_list: list):
        """
        Streams email candidates to Validator and returns the first SAFE one.
        Handles SSE format (data: {...})
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
                                    return {"email": email, "status": "safe", "score": 100}
                                
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
                return risky_email
            
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