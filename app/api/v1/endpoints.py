from fastapi import APIRouter
from app.models.schemas import ScanRequest, IntelligenceReport
from app.services.scraper import AsyncScraper
from app.services.search_engine import DomainHunter, CompanySocialsHunter, EmployeeHunter
from app.services.llm_engine import LLMEngine
import logging

router = APIRouter()
logger = logging.getLogger("API_Endpoint")

@router.post("/enrich", response_model=IntelligenceReport)
async def enrich_company(request: ScanRequest):
    logger.info(f"🚀 Starting Cost-Efficient Scan for: {request.company_name}")
    
    # Initialize
    scraper = AsyncScraper()
    llm = LLMEngine()
    
    # 1. Domain (1 Credit ONLY if URL missing)
    target_url = request.website_url
    if not target_url:
        logger.info("URL missing. Searching...")
        target_url = DomainHunter(request.company_name).get_domain()
    
    # 2. Scrape Website (0 Credits)
    scraped_data = {"technologies": [], "emails": [], "phones": [], "raw_text": ""}
    socials_hunter = CompanySocialsHunter(request.company_name)
    
    if target_url:
        logger.info(f"Scraping {target_url}...")
        html = await scraper.fetch_page(target_url)
        scraped_data = scraper.extract_data(html)
        
        # FREE: Extract socials from the website footer/header
        socials_hunter.extract_from_html(html)
    
    # 3. Fill Missing Data (Paid API)
    # Only searches if LinkedIn wasn't found in the scrape
    socials = socials_hunter.run_backup_search() 
    
    # 4. Employees (1 Credit - Combined Query)
    employees = EmployeeHunter(request.company_name).run()

    # 5. AI Analysis
    ai_insights = await llm.analyze(request.company_name, scraped_data, [])

    # 6. Merge
    profile = ai_insights.get("company_profile", {})
    profile["name"] = request.company_name
    profile["website"] = target_url if target_url else "Not Found"

    final_people = employees
    existing_names = {p['name'].lower() for p in employees}
    for p in ai_insights.get("key_people", []):
        if isinstance(p, dict) and p.get("name", "").lower() not in existing_names:
            if "not found" not in p.get("name", "").lower():
                final_people.append(p)

    return {
        "company_profile": profile,
        "technologies": scraped_data["technologies"],
        "services": ai_insights.get("services_offered", []),
        "contact_details": {
            "emails": scraped_data["emails"],
            "phones": scraped_data["phones"],
            "social_links": socials,
            "addresses": []
        },
        "key_people": final_people,
        "sources": [target_url if target_url else "Google Serper"]
    }