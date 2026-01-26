import httpx
import logging
import traceback
import asyncio
from fastapi import APIRouter, BackgroundTasks
from app.models.schemas import (
    ScanRequest, IntelligenceReport, InfrastructureInfo, 
    EmailRevealRequest, EmailRevealResponse
)
from app.config import settings
from app.services.scraper import AsyncScraper
from app.services.search_engine import DomainHunter, CompanySocialsHunter, EmployeeHunter
from app.services.infrastructure import InfrastructureHunter
from app.services.llm_engine import LLMEngine
from app.services.email_engine import EmailValidator, EmailPermutator
from app.services.pattern_engine import PatternEngine
from app.services.tech_hunter import TechHunter
from app.services.token_manager import TokenManager

router = APIRouter()
logger = logging.getLogger("API_Endpoint")

# Initialize Token Manager for dynamic authentication
token_manager = TokenManager(
    token_url=settings.TOKEN_OBTAIN_URL,
    email=settings.SAVE_ENRICHMENT_EMAIL,
    password=settings.SAVE_ENRICHMENT_PASSWORD
)


def mask_email(email):
    """Turns 'kumar@gravityer.com' into 'k****@gravityer.com'"""
    if not email or "@" not in email: return None
    try:
        user, domain = email.split('@')
        # Show first char, mask up to 4 chars of user part
        masked_user = user[0] + "*" * min(4, len(user)-1)
        return f"{masked_user}@{domain}"
    except:
        return "*****"

async def push_asset_to_master_db(data: dict):
    """
    Background Task: Sends the UNMASKED data to your Django CRM.
    This builds your asset library automatically.
    Uses TokenManager for automatic token refresh.
    """
    try:
        # Get fresh token dynamically
        token = await token_manager.get_valid_token()
        
        async with httpx.AsyncClient() as client:
            # We assume your Django view accepts this JSON structure
            response = await client.post(
                settings.SAVE_ENRICHMENT_URL, 
                json=data, 
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            if response.status_code < 300:
                logger.info(f"✅ Asset Saved to Master DB: {data.get('company_profile', {}).get('name')}")
            else:
                logger.warning(f"⚠️ Master DB Save Failed: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Asset Push Error: {type(e).__name__}: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")

async def save_enrichment_data(company_data: dict, contact: dict):
    """
    Background Task: Sends individual contact enrichment data to the save endpoint.
    Each contact with a verified email gets its own database record.
    Uses TokenManager for automatic token refresh.
    """
    try:
        # Get fresh token dynamically
        token = await token_manager.get_valid_token()
        
        # Prepare contact payload with company context
        payload = {
            "company_profile": company_data.get("company_profile"),
            "infrastructure": company_data.get("infrastructure"),
            "technologies": company_data.get("technologies"),
            "services": company_data.get("services"),
            "contact_details": company_data.get("contact_details"),
            "key_people": [contact],  # Single contact
            "sources": company_data.get("sources")
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.SAVE_ENRICHMENT_URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            if response.status_code < 300:
                logger.info(
                    f"✅ Contact Saved: {contact.get('name')} @ "
                    f"{company_data.get('company_profile', {}).get('name')}"
                )
            else:
                logger.warning(
                    f"⚠️ Contact Save Failed ({contact.get('name')}): "
                    f"{response.status_code} - {response.text}"
                )
    except Exception as e:
        logger.error(
            f"❌ Contact Save Error ({contact.get('name', 'Unknown')}): "
            f"{type(e).__name__}: {str(e)}"
        )
        logger.error(f"Full traceback: {traceback.format_exc()}")


async def save_all_enriched_contacts(company_data: dict):
    """
    Saves all contacts with verified emails to the database.
    Sends one API request per contact to ensure all are stored.
    """
    key_people = company_data.get("key_people", [])
    verified_contacts = [
        person for person in key_people 
        if person.get("email_status") == "verified"
    ]
    
    if not verified_contacts:
        logger.info(f"⚠️ No verified contacts to save for {company_data.get('company_profile', {}).get('name')}")
        return
    
    logger.info(
        f"💾 Saving {len(verified_contacts)} verified contacts for "
        f"{company_data.get('company_profile', {}).get('name')}"
    )
    
    # Send each contact individually
    tasks = [
        save_enrichment_data(company_data, contact)
        for contact in verified_contacts
    ]
    
    # Execute all saves concurrently
    await asyncio.gather(*tasks, return_exceptions=True)

@router.post("/enrich", response_model=IntelligenceReport)
async def enrich_company(request: ScanRequest, background_tasks: BackgroundTasks):
    logger.info(f"🚀 Starting Deep-Scan for: {request.company_name}")
    
    # --- 1. Initialization & Domain ---
    scraper = AsyncScraper()
    llm = LLMEngine()
    
    target_url = request.website_url
    if not target_url:
        target_url = DomainHunter(request.company_name).get_domain()
    
    # Clean domain for email generation
    clean_domain = ""
    if target_url:
        clean_domain = target_url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]

    # --- 2. Infrastructure Scan ---
    infra_data = InfrastructureInfo(email_provider="Unknown", cloud_hosting=[])
    if target_url:
        infra_hunter = InfrastructureHunter(target_url)
        email_provider = infra_hunter.detect_email_provider()
        server_tech = await infra_hunter.detect_server_tech(target_url)
        infra_data = InfrastructureInfo(email_provider=email_provider, cloud_hosting=server_tech)

    # --- 3. Scrape Website ---
    scraped_data = {"technologies": [], "emails": [], "phones": [], "raw_text": ""}
    socials_hunter = CompanySocialsHunter(request.company_name)
    
    if target_url:
        html = await scraper.fetch_page(target_url)
        scraped_data = scraper.extract_data(html)
        socials_hunter.extract_from_html(html)
        
        tech_hunter = TechHunter()
        marketing_tech = tech_hunter.scan(html)
        current_tech = scraped_data.get("technologies", [])
        scraped_data["technologies"] = list(set(current_tech + marketing_tech))
    
    # --- 4. Socials & Employees ---
    socials = socials_hunter.run_backup_search()
    employees = EmployeeHunter(request.company_name, target_role=request.target_role).run()

    # --- 5. THE TEASER LOGIC (Auto-Enrich Top 5) ---
    email_engine = EmailPermutator()
    validator = EmailValidator()
    
    # We create a deep copy for the Master DB (to keep unmasked emails)
    master_db_employees = [p.copy() for p in employees]

    if clean_domain:
        logger.info(f"🕵️ Auto-Enriching All Employees @ {clean_domain}")
        # Validate ALL employees to save complete contact data
        for i, person in enumerate(employees):
            # Generate & Validate
            candidates = email_engine.generate(person['name'], clean_domain)
            result = await validator.find_valid_email(candidates)
            
            if result and result.get("status") == "safe":
                real_email = result['email']
                
                # A. Update Master List (Real Email)
                master_db_employees[i]['email'] = real_email
                master_db_employees[i]['email_status'] = "verified"
                
                # B. Update Frontend List (Masked Email)
                person['email'] = None # Hide from frontend
                person['email_preview'] = mask_email(real_email)
                person['email_status'] = "verified" # Signals frontend to show Green Lock
            else:
                person['email_status'] = "not_found"
                master_db_employees[i]['email_status'] = "not_found"

    # --- 6. AI Analysis ---
    ai_insights = await llm.analyze(request.company_name, scraped_data, [])

    # --- 7. Merge Response ---
    profile = ai_insights.get("company_profile", {})
    profile["name"] = request.company_name
    profile["website"] = target_url if target_url else "Not Found"

    final_people = employees # This list has MASKED emails
    
    # Add AI-found people if not duplicates
    existing_names = {p['name'].lower() for p in employees}
    for p in ai_insights.get("key_people", []):
        if isinstance(p, dict) and p.get("name", "").lower() not in existing_names:
            if "not found" not in p.get("name", "").lower():
                final_people.append(p)

    # Construct the Public Report (Masked)
    public_report = {
        "company_profile": profile,
        "infrastructure": infra_data.model_dump() if hasattr(infra_data, 'model_dump') else infra_data,
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

    # Construct the Asset Report (Unmasked)
    # We replace the people list with the one containing real emails
    asset_report = public_report.copy()
    asset_report["key_people"] = master_db_employees

    # --- 8. FIRE AND FORGET SAVE ---
    background_tasks.add_task(push_asset_to_master_db, asset_report)
    
    # --- 9. AUTO-SAVE ALL ENRICHED CONTACTS ---
    # Send each verified contact individually to ensure all are stored
    background_tasks.add_task(save_all_enriched_contacts, public_report)

    return public_report

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