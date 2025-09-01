from fastapi import HTTPException, Depends, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import Config
from typing import Optional

import secrets
import hashlib

security = HTTPBearer()

async def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token d'autorisation manquant")
    
    if not secrets.compare_digest(authorization, Config.PROCESSOR_TOKEN):
        raise HTTPException(status_code=401, detail="Token invalide")
    
    return True

def require_auth():
    return Depends(verify_token)
