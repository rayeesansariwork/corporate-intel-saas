import logging
import dns.resolver
import httpx
from urllib.parse import urlparse

logger = logging.getLogger("Infrastructure_Hunter")

class InfrastructureHunter:
    def __init__(self, domain: str):
        # Ensure we have a clean domain (e.g., "google.com") without http/www
        if "://" in domain:
            domain = urlparse(domain).netloc
        self.domain = domain.replace("www.", "")
        
    def detect_email_provider(self):
        """
        Scans DNS MX records to find who hosts their email (Google vs Microsoft).
        This is HUGE for sales teams.
        """
        provider = "Unknown"
        try:
            records = dns.resolver.resolve(self.domain, 'MX')
            mx_records = [str(r.exchange).lower() for r in records]
            
            # Simple keyword matching for major providers
            for mx in mx_records:
                if "google" in mx or "aspmx" in mx:
                    return "Google Workspace"
                elif "outlook" in mx or "microsoft" in mx or "protection" in mx:
                    return "Microsoft 365 / Outlook"
                elif "zoho" in mx:
                    return "Zoho Mail"
                elif "proofpoint" in mx:
                    return "Proofpoint (Enterprise Security)"
                elif "mimecast" in mx:
                    return "Mimecast (Enterprise Security)"
            
            # If no major provider found, return the raw MX host
            if mx_records:
                return f"Self-Hosted / Other ({mx_records[0]})"
                
        except Exception as e:
            logger.warning(f"DNS lookup failed for {self.domain}: {e}")
            
        return provider

    async def detect_server_tech(self, url: str):
        """
        Inspects HTTP Headers to find hidden backend tech (AWS, Cloudflare, Nginx).
        """
        tech_stack = []
        try:
            # We use a HEAD request because it's fast (doesn't download body)
            async with httpx.AsyncClient(verify=False, timeout=5) as client:
                resp = await client.head(url, follow_redirects=True)
                headers = resp.headers

                # 1. Check 'Server' header
                server = headers.get("Server", "")
                if server: tech_stack.append(f"Server: {server}")

                # 2. Check 'X-Powered-By' (Often reveals framework)
                powered = headers.get("X-Powered-By", "")
                if powered: tech_stack.append(f"Framework: {powered}")

                # 3. Check for specific cloud signatures
                if "cf-ray" in headers: tech_stack.append("Cloudflare (CDN/Security)")
                if "x-amz-id" in headers: tech_stack.append("AWS (Hosting)")
                if "x-goog-" in headers: tech_stack.append("Google Cloud (Hosting)")
                if "x-azure-" in headers: tech_stack.append("Azure (Hosting)")
                if "shopify" in headers.get("link", ""): tech_stack.append("Shopify (Platform)")

        except Exception as e:
            logger.warning(f"Header scan failed: {e}")
            
        return tech_stack