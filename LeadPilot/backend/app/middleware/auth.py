from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import requests
from app.config import settings
from functools import lru_cache

security = HTTPBearer()

@lru_cache()
def get_jwks():
    """Fetch and cache Auth0 public keys"""
    jwks_url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    response = requests.get(jwks_url)
    return response.json()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify Auth0 JWT token"""
    token = credentials.credentials
    
    try:
        # Get the public key
        jwks = get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        
        if rsa_key:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=[settings.AUTH0_ALGORITHMS],
                audience=settings.AUTH0_API_AUDIENCE,
                issuer=settings.AUTH0_ISSUER
            )
            return payload
        
        raise HTTPException(status_code=401, detail="Unable to find appropriate key")
    
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

def get_current_user(token_payload: dict = Depends(verify_token)):
    """Extract user info from token"""
    return {
        "user_id": token_payload.get("sub"),
        "email": token_payload.get("email"),
        "permissions": token_payload.get("permissions", [])
    }
