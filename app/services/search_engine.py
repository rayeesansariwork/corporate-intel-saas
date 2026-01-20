import logging
import requests
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup # Added for social scraping
from app.config import settings

logger = logging.getLogger("Google_Search_Engine")

class SearchUtils:
    @staticmethod
    def google_search(query, count=10):
        """
        Uses Serper.dev. Returns empty list on failure.
        """
        url = "https://google.serper.dev/search"
        payload = json.dumps({ "q": query, "num": count })
        headers = {
            'X-API-KEY': settings.SERPER_API_KEY,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(url, headers=headers, data=payload, timeout=10)
            if response.status_code == 200:
                return response.json().get("organic", [])
            else:
                logger.error(f"Serper Error: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Serper Connection Error: {e}")
            return []

class DomainHunter:
    def __init__(self, company_name):
        self.company_name = company_name
        self.blacklist = [
            "wikipedia.org", "linkedin.com", "facebook.com", "twitter.com", 
            "instagram.com", "youtube.com", "crunchbase.com", "bloomberg.com", 
            "glassdoor.com", "zoominfo.com", "dnb.com"
        ]

    def get_domain(self):
        # 1 Credit
        results = SearchUtils.google_search(f"{self.company_name} official website", count=3)
        for r in results:
            link = r.get("link", "")
            domain = urlparse(link).netloc.replace("www.", "")
            if any(b in domain for b in self.blacklist): continue
            return link
        return None

class CompanySocialsHunter:
    def __init__(self, company_name):
        self.company_name = company_name
        self.results = {}

    def extract_from_html(self, html_content):
        """
        FREE: Scrapes socials from the homepage footer/header.
        """
        if not html_content: return
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for links in the HTML
        for a in soup.find_all('a', href=True):
            href = a['href']
            if "linkedin.com/company" in href and "LinkedIn" not in self.results:
                self.results["LinkedIn"] = href
            elif "twitter.com" in href or "x.com" in href:
                if "Twitter" not in self.results: self.results["Twitter"] = href
            elif "facebook.com" in href and "Facebook" not in self.results:
                self.results["Facebook"] = href
    
    def run_backup_search(self):
        """
        PAID: Only runs if LinkedIn is missing after scraping.
        """
        # We only really care about LinkedIn for business intel. 
        # Twitter/FB are nice to have, but maybe not worth paying for if missing.
        if "LinkedIn" not in self.results:
            # 1 Credit
            logger.info("LinkedIn not found on site. Using Search API...")
            query = f'site:linkedin.com/company "{self.company_name}"'
            results = SearchUtils.google_search(query, count=1)
            if results:
                self.results["LinkedIn"] = results[0].get("link")
        
        return self.results

class EmployeeHunter:
    def __init__(self, company_name, target_role=None, max_results=10):
        self.company_name = company_name
        self.target_role = target_role 
        self.max_results = max_results
        self.associates = []
        self.seen_urls = set()

    def run(self):
        # 2. Logic Switch: If specific role is provided, search ONLY for that.
        # Otherwise, default to leadership roles.
        if self.target_role and self.target_role.strip():
            role_query = f'"{self.target_role}"'
            logger.info(f"🕵️ Hunting specific target '{self.target_role}' for {self.company_name}...")
        else:
            role_query = '("Founder" OR "CEO" OR "Manager" OR "Director")'
            logger.info(f"🕵️ Hunting leadership for {self.company_name}...")

        combined_query = f'site:linkedin.com/in/ "{self.company_name}" {role_query}'
        
        # 1 Credit (returns up to 15 people at once)
        results = SearchUtils.google_search(combined_query, count=15)
        
        for r in results:
            self._process_snippet(r)
            
        return self.associates

    def _process_snippet(self, raw):
        link = raw.get("link", "")
        title = raw.get("title", "")
        
        if "/in/" not in link or link in self.seen_urls: return

        clean_title = title.replace(" | LinkedIn", "").replace(" - LinkedIn", "")
        parts = clean_title.split(" - ")

        def clean_string(text): return text.encode('ascii', 'ignore').decode('ascii').strip()

        name = clean_string(parts[0]) if parts else "Unknown"
        role = clean_string(parts[1]) if len(parts) > 1 else "Employee"

        if self.company_name.lower() in name.lower(): return
        if "profiles" in name.lower(): return
        if len(name) > 40: return

        self.associates.append({"name": name, "role": role, "profile_url": link})
        self.seen_urls.add(link)