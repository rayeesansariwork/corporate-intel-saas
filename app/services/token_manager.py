import httpx
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("TokenManager")


class TokenManager:
    """
    Manages JWT token lifecycle for authenticated API requests.
    Automatically fetches and caches access tokens using email/password credentials.
    Handles token expiry and auto-refresh.
    """
    
    def __init__(self, token_url: str, email: str, password: str):
        """
        Initialize TokenManager with authentication credentials.
        
        Args:
            token_url: URL endpoint to obtain tokens
            email: User email for authentication
            password: User password for authentication
        """
        self._token_url = token_url
        self._email = email
        self._password = password
        self._cached_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._lock = asyncio.Lock()
        
    def _is_token_valid(self) -> bool:
        """
        Check if cached token is still valid.
        Considers token expired if within 5 minutes of expiry to prevent edge cases.
        
        Returns:
            True if token exists and is valid, False otherwise
        """
        if not self._cached_token or not self._token_expiry:
            return False
        
        # Refresh 5 minutes before actual expiry for safety
        buffer_time = timedelta(minutes=5)
        return datetime.now() < (self._token_expiry - buffer_time)
    
    async def get_valid_token(self) -> str:
        """
        Get a valid access token. Returns cached token if valid, otherwise fetches new one.
        Thread-safe with async lock.
        
        Returns:
            Valid JWT access token
            
        Raises:
            Exception: If token fetch fails
        """
        # Fast path: return cached token if still valid
        if self._is_token_valid():
            logger.debug("Using cached token")
            return self._cached_token
        
        # Slow path: obtain new token with lock (prevents concurrent token fetches)
        async with self._lock:
            # Double-check after acquiring lock (another thread might have refreshed)
            if self._is_token_valid():
                return self._cached_token
            
            return await self._obtain_token()
    
    async def _obtain_token(self) -> str:
        """
        Fetch a fresh access token from the authentication API.
        Caches the token and calculates expiry time.
        
        Returns:
            Fresh JWT access token
            
        Raises:
            Exception: If API request fails or credentials are invalid
        """
        try:
            logger.info(f"🔑 Fetching fresh access token for {self._email}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._token_url,
                    json={
                        "email": self._email,
                        "password": self._password
                    },
                    timeout=10
                )
                
                if response.status_code != 200:
                    raise Exception(
                        f"Token fetch failed: {response.status_code} - {response.text}"
                    )
                
                data = response.json()
                
                if not data.get("success"):
                    raise Exception(f"Authentication failed: {data}")
                
                # Extract token and expiry information
                self._cached_token = data["access"]
                expires_in_seconds = data.get("expires_in", 28800)  # Default 8 hours
                
                # Calculate expiry timestamp
                self._token_expiry = datetime.now() + timedelta(seconds=expires_in_seconds)
                
                logger.info(
                    f"✅ Token obtained successfully. Expires in {expires_in_seconds/3600:.1f} hours"
                )
                
                return self._cached_token
                
        except Exception as e:
            logger.error(f"❌ Token fetch error: {e}")
            raise
    
    def clear_cache(self):
        """Clear cached token (useful for testing or forced refresh)"""
        self._cached_token = None
        self._token_expiry = None
        logger.info("Token cache cleared")
