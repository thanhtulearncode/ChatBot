import json
import sys
import os
from pathlib import Path
from sqlmodel import Session, SQLModel, create_engine, select

sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.db.models import FAQItem

def init_db():
    print(f"Connexion à la base de données : {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    # Création des tables
    SQLModel.metadata.create_all(engine)
    print("Tables créées.")
    # Chargement du JSON source
    json_path = Path("data/faq.json")
    if not json_path.exists():
        print(f"Fichier {json_path} introuvable.")
        return
    with open(json_path, "r", encoding="utf-8") as f:
        faq_data = json.load(f)
    print(f"{len(faq_data)} questions trouvées dans le JSON.")
    # Insertion en base
    with Session(engine) as session:
        count = 0
        for item in faq_data:
            # Vérifier si la question existe déjà pour éviter les doublons
            existing_q = session.exec(
                select(FAQItem).where(FAQItem.question == item["question"])
            ).first()
            
            if not existing_q:
                new_faq = FAQItem(
                    question=item["question"],
                    answer=item["answer"],
                    category=item.get("category", "general")
                )
                session.add(new_faq)
                count += 1
        
        session.commit()
        print(f"{count} nouvelles questions importées avec succès !")

if __name__ == "__main__":
    init_db()