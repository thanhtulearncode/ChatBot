from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, JWTError
from sqlmodel import Session, select

from app.core.config import settings
from app.db.models import User
from app.db.session import get_session

# auto_error=False permet de ne pas lever d'erreur automatiquement
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

async def get_token_from_request(
    request: Request,
    token_header: Optional[str] = Depends(oauth2_scheme)
) -> str:
    """Récupère le token soit du Header (API), soit du Cookie (Navigateur)"""
    # Essayer le header Authorization standard
    if token_header:
        return token_header
    # Essayer le cookie 'access_token'
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        # Le cookie peut contenir "Bearer <token>" ou juste "<token>"
        if cookie_token.startswith("Bearer "):
            return cookie_token.split(" ")[1]
        return cookie_token
        
    return None

async def get_current_user(
    token: Annotated[str, Depends(get_token_from_request)],
    db: Session = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou session expirée",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        # Si c'est une requête navigateur vers une page admin, on pourrait rediriger vers /login
        # Mais ici on lève une 401 standard
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    statement = select(User).where(User.email == email)
    user = db.exec(statement).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Utilisateur inactif")
        
    return user

async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user