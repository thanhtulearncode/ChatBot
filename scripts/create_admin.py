import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.db.session import engine
from app.db.models import User
from app.core.security import get_password_hash

def create_admin_user(email: str, password: str):
    with Session(engine) as session:
        # Vérifier si l'utilisateur existe déjà
        existing_user = session.exec(select(User).where(User.email == email)).first()
        if existing_user:
            print(f"L'utilisateur {email} existe déjà.")
            return
        # Création de l'admin
        admin_user = User(
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True,
            full_name="Admin System"
        )
        
        session.add(admin_user)
        session.commit()
        session.refresh(admin_user)
        print(f"Admin créé avec succès : {email} (ID: {admin_user.id})")

if __name__ == "__main__":
    create_admin_user("admin@chatbot.com", "admin123")