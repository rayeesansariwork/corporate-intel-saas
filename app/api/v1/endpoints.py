from fastapi import APIRouter
from app.models.schemas import ScanRequest, IntelligenceReport, InfrastructureInfo
from app.services.scraper import AsyncScraper
from app.services.search_engine import DomainHunter, CompanySocialsHunter, EmployeeHunter
from app.services.infrastructure import InfrastructureHunter # <-- Import New Service
from app.services.llm_engine import LLMEngine
import logging

router = APIRouter()
logger = logging.getLogger("API_Endpoint")

@router.post("/enrich", response_model=IntelligenceReport)
async def enrich_company(request: ScanRequest):
    logger.info(f"🚀 Starting Deep-Scan for: {request.company_name}")
    
    # Initialize
    scraper = AsyncScraper()
    llm = LLMEngine()
    
    # 1. Domain
    target_url = request.website_url
    if not target_url:
        target_url = DomainHunter(request.company_name).get_domain()
    
    # 2. Infrastructure Scan (The New "Detective" Work)
    # This is fast and cheap, so we do it early
    infra_data = InfrastructureInfo(email_provider="Unknown", cloud_hosting=[])
    if target_url:
        logger.info(f"🕵️ Scanning Infrastructure for {target_url}...")
        infra_hunter = InfrastructureHunter(target_url)
        
        # Get Email Provider (MX Records)
        email_provider = infra_hunter.detect_email_provider()
        
        # Get Server Tech (HTTP Headers)
        server_tech = await infra_hunter.detect_server_tech(target_url)
        
        infra_data = InfrastructureInfo(
            email_provider=email_provider,
            cloud_hosting=server_tech
        )

    # 3. Scrape Website
    scraped_data = {"technologies": [], "emails": [], "phones": [], "raw_text": ""}
    socials_hunter = CompanySocialsHunter(request.company_name)
    
    if target_url:
        html = await scraper.fetch_page(target_url)
        scraped_data = scraper.extract_data(html)
        socials_hunter.extract_from_html(html)
    
    # 4. Fill Missing Data (Paid API)
    socials = socials_hunter.run_backup_search()
    
    # 5. Employees
    employees = EmployeeHunter(request.company_name).run()

    # 6. AI Analysis
    ai_insights = await llm.analyze(request.company_name, scraped_data, [])

    # 7. Merge
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
        "infrastructure": infra_data, # <-- New Data Block
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


@router.post("/reveal-email", response_model=EmailRevealResponse)
async def reveal_email(request: EmailRevealRequest):
    """
    On-Demand Email Discovery with Smart Learning.
    1. Generates permutations (prioritizing known patterns).
    2. Validates via Reacher.
    3. If successful, LEARNS the pattern for next time.
    """
    logger.info(f"🔍 Revealing email for: {request.full_name} @ {request.domain}")
    
    # 1. Generate Candidates
    permutator = EmailPermutator()
    candidates = permutator.generate(request.full_name, request.domain)
    
    if not candidates:
        return {"status": "failed", "email": None, "confidence_score": 0}

    # 2. Validate
    validator = EmailValidator()
    result = await validator.find_valid_email(candidates)
    
    if result and result["status"] == "safe":
        # --- SMART LEARNING LOGIC ---
        try:
            parts = request.full_name.lower().strip().split()
            if len(parts) >= 2:
                fn, ln = parts[0], parts[-1]
                
                # Deduce the pattern from the valid email
                pattern = PatternEngine.deduce_pattern(result["email"], fn, ln, request.domain)
                
                # Save it to our 'Database'
                if pattern:
                    PatternEngine.save_pattern(request.domain, pattern)
        except Exception as e:
            logger.warning(f"Failed to learn pattern: {e}")
        # -----------------------------

        return {
            "email": result["email"],
            "status": result["status"],
            "confidence_score": result["score"]
        }
    
    # If a risky email was found, return it but don't learn from it (safer)
    if result:
         return {
            "email": result["email"],
            "status": result["status"],
            "confidence_score": result["score"]
        }
    
    return {"email": None, "status": "not_found", "confidence_score": 0}