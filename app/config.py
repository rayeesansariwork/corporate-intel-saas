from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Corporate Intel SaaS"
    API_V1_STR: str = "/api/v1"
    
    # Security
    API_SECRET_KEY: str = "change_this_to_a_secure_random_string"
    
    # AI Engine
    MISTRAL_API_KEY: str
    MISTRAL_MODEL: str = "mistral-small-latest"

    SAVE_ENRICHMENT_URL: str
    SAVE_ENRICHMENT_EMAIL: str
    SAVE_ENRICHMENT_PASSWORD: str
    TOKEN_OBTAIN_URL: str
    
    # Cross-Domain Reveal Token Settings
    JWT_SECRET_KEY: str = "change_this_to_match_crm_backend_secret"
    JWT_EXPIRATION_MINUTES: int = 5
    # CRM_LANDING_PAGE_URL: str = "http://localhost:3000/agency/dashboard"
    CRM_LANDING_PAGE_URL: str = "https://sales.polluxa.com/agency/dashboard"
    # Search Engine (Serper.dev)
    # I have added your key here as the default
    SERPER_API_KEY: str 

    # Scraper Headers
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    class Config:
        env_file = ".env"

settings = Settings()