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
        if not url: return ""
        if not url.startswith("http"): url = f"https://{url}"
            
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, verify=False) as client:
            try:
                resp = await client.get(url, headers=self.headers)
                return resp.text
            except Exception as e:
                logger.warning(f"Scrape failed for {url}: {e}")
                return ""

    def extract_data(self, html: str) -> Dict:
        data = {
            "emails": [],
            "phones": [],
            "technologies": [],
            "raw_text": ""
        }
        if not html: return data
            
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

        return data