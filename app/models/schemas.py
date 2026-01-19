from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any

class ScanRequest(BaseModel):
    company_name: str = Field(..., min_length=2, example="OpenAI")
    website_url: Optional[str] = Field(None, example="openai.com")

class ContactInfo(BaseModel):
    emails: List[str] = []
    phones: List[str] = []
    social_links: Dict[str, str] = {}
    addresses: List[str] = []

class CompanyProfile(BaseModel):
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None
    hq_address: Optional[str] = None
    country: Optional[str] = None
    website: str
    annual_revenue: Optional[str] = None

class IntelligenceReport(BaseModel):
    company_profile: CompanyProfile
    technologies: List[str] = []
    services: List[str] = []
    contact_details: ContactInfo
    # UPDATED: We use List[Dict[str, Any]] to allow flexible fields like 'profile_url'
    key_people: List[Dict[str, Any]] = [] 
    sources: List[str] = []