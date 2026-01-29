from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any

class ScanRequest(BaseModel):
    company_name: str = Field(..., min_length=2, example="OpenAI")
    website_url: Optional[str] = Field(None, example="openai.com")
    target_role: Optional[str] = None

class ContactInfo(BaseModel):
    emails: List[str] = []
    phones: List[str] = []
    social_links: Dict[str, str] = {}
    addresses: List[str] = []
    
class InfrastructureInfo(BaseModel):
    email_provider: str = "Unknown"
    cloud_hosting: List[str] = []

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
    infrastructure: InfrastructureInfo 
    technologies: List[str] = []
    services: List[str] = []
    contact_details: ContactInfo
    key_people: List[Dict[str, Any]] = [] 
    sources: List[str] = []

class EmailRevealRequest(BaseModel):
    full_name: str
    domain: str

class EmailRevealResponse(BaseModel):
    email: Optional[str] = None
    status: str = "unknown" # safe, risky, unknown
    confidence_score: int = 0

# Cross-Domain Reveal Token Schemas
class RevealTokenRequest(BaseModel):
    """Request model for generating cross-domain reveal tokens."""
    contact_id: int  # Still keep for backwards compatibility
    company_id: Optional[int] = None  # NEW: For multi-contact reveal
    company_name: str
    contact_name: str


class RevealTokenResponse(BaseModel):
    """Response model containing the signed token and redirect URL."""
    token: str
    redirect_url: str
    expires_in_minutes: int
