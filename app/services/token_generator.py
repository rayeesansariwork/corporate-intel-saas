"""
Token Generator Service for Cross-Domain Lead Conversion

Generates and validates signed JWT tokens that encode contact information
for secure transfer between Lead-Gen and CRM platforms.
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import logging

logger = logging.getLogger("TokenGenerator")


class TokenGenerator:
    """
    Handles creation and validation of signed JWT tokens for reveal flow.
    
    Tokens contain:
    - contact_id: The database ID of the contact to reveal
    - company_name: The company name for display purposes
    - exp: Expiration timestamp
    - iat: Issued at timestamp
    """
    
    def __init__(self, secret_key: str, expiration_minutes: int = 5):
        """
        Initialize token generator.
        
        Args:
            secret_key: Secret key for JWT signing (must match CRM backend)
            expiration_minutes: Token validity duration (default: 5 minutes)
        """
        self.secret_key = secret_key
        self.expiration_minutes = expiration_minutes
        self.algorithm = "HS256"
    
    def generate_token(
        self,
        contact_id: int,
        company_name: str,
        contact_name: str,
        company_id: Optional[int] = None  # NEW: For multi-contact reveal
    ) -> str:
        """
        Generate a signed JWT token for cross-domain contact reveal.
        
        Args:
            contact_id: Primary contact ID (for single-contact backward compatibility)
            company_name: Name of the company
            contact_name: Name of the primary contact
            company_id: Optional company ID for fetching all contacts
            
        Returns:
            Signed JWT token string
        """
        # Using timezone-aware UTC to prevent deprecation issues in newer PyJWT
        now = datetime.now(tz=timezone.utc)
        expiration = now + timedelta(minutes=self.expiration_minutes)
        
        payload = {
            "contact_id": contact_id,
            "company_name": company_name,
            "contact_name": contact_name,
            "exp": expiration
        }
        
        # Add company_id if provided (for multi-contact reveal)
        if company_id:
            payload["company_id"] = company_id
        
        # This will now work correctly with PyJWT installed
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.info(
            f"Token generated successfully for {contact_name} @ {company_name} "
            f"(Contact ID: {contact_id}, Company ID: {company_id or 'N/A'})"
        )
        return token
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate and decode a JWT token.
        
        Args:
            token: JWT token string to validate
            
        Returns:
            Decoded payload dict if valid, None if invalid/expired
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            logger.info(
                f"Valid token decoded for contact ID: {payload.get('contact_id')}"
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token validation failed: Token has expired")
            return None
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token validation failed: {str(e)}")
            return None
    
    def is_token_valid(self, token: str) -> bool:
        """
        Quick check if token is valid without decoding.
        
        Args:
            token: JWT token string
            
        Returns:
            True if valid, False otherwise
        """
        return self.validate_token(token) is not None