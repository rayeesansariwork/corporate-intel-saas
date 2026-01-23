from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Corporate Intel SaaS"
    API_V1_STR: str = "/api/v1"
    
    # Security
    API_SECRET_KEY: str = "change_this_to_a_secure_random_string"
    
    # AI Engine
    MISTRAL_API_KEY: str
    MISTRAL_MODEL: str = "mistral-small-latest"

    save_enrichment_url: str
    save_enrichment_token: str
    
    # Search Engine (Serper.dev)
    # I have added your key here as the default
    SERPER_API_KEY: str 

    # Scraper Headers
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    class Config:
        env_file = ".env"

settings = Settings()