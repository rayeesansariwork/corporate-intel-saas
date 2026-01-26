import httpx
import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Set

logger = logging.getLogger("ScraperService")

class AsyncScraper:
    def __init__(self):
        # Browser headers to look real
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }

    async def fetch_page(self, url: str) -> str:
        if not url:
            logger.debug("Empty URL provided to fetch_page")
            return ""
        if not url.startswith("http"): 
            url = f"https://{url}"
            logger.debug(f"Added https:// protocol to URL: {url}")
            
        logger.info(f"🌐 Fetching page: {url}")
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, verify=False) as client:
            try:
                resp = await client.get(url, headers=self.headers)
                content_length = len(resp.text)
                logger.info(f"✅ Successfully fetched {url} ({content_length} characters, status: {resp.status_code})")
                return resp.text
            except httpx.TimeoutException as e:
                logger.error(f"⏱️ Timeout while fetching {url}: {e}")
                return ""
            except httpx.HTTPError as e:
                logger.error(f"🚫 HTTP error for {url}: {type(e).__name__} - {e}")
                return ""
            except Exception as e:
                logger.error(f"❌ Unexpected error while fetching {url}: {type(e).__name__} - {e}", exc_info=True)
                return ""

    def extract_data(self, html: str) -> Dict:
        logger.debug(f"Starting data extraction from HTML ({len(html)} characters)")
        data = {
            "emails": [],
            "phones": [],
            "technologies": [],
            "raw_text": ""
        }
        if not html:
            logger.warning("Empty HTML provided to extract_data")
            return data
            
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(" ", strip=True)
        html_lower = html.lower()
        data["raw_text"] = text[:15000] # Limit for AI

        # --- 1. EMAIL & PHONE REGEX (From Your Script 2) ---
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        data["emails"] = list({e for e in emails if not any(x in e.lower() for x in ['.png', '.jpg', 'sentry', 'example', 'wix'])})
        
        # Simple phone regex
        phones = re.findall(r'\+?\d[\d -]{8,12}\d', text)
        data["phones"] = list({p.strip() for p in phones if len(p.strip()) > 8})

        # --- 2. TECH DETECTION (From Your Script 2) ---
        signatures = {
            "WordPress": ["wp-content", "wp-includes"], 
            "Shopify": ["shopify.com", "cdn.shopify"],
            "React": ["react-dom", "react-root", "_next"], 
            "Vue.js": ["vue.global.js", "data-v-"],
            "Angular": ["ng-version", "app-root"], 
            "Cloudflare": ["__cf_bm", "cf-ray"],
            "Google Analytics": ["UA-", "G-"], 
            "AWS": ["amazonaws.com"],
            "Bootstrap": ["bootstrap.min.css"]
        }
        for tech, patterns in signatures.items():
            if any(p in html_lower for p in patterns):
                data["technologies"].append(tech)
                logger.debug(f"Detected technology: {tech}")

        logger.info(
            f"📊 Extraction complete: {len(data['emails'])} emails, "
            f"{len(data['phones'])} phones, {len(data['technologies'])} technologies detected"
        )
        return data