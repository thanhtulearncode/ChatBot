"""
Gestion de la mémoire conversationnelle
"""
from typing import Dict, List
from datetime import datetime
from collections import defaultdict


class MemoryManager:
    """Gère l'historique des conversations par utilisateur"""
    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.conversations: Dict[str, List[Dict]] = defaultdict(list)
        self.stats = {
            "total_interactions": 0,
            "active_users": 0
        }

    def add_interaction(
        self,
        user_id: str,
        user_message: str,
        bot_response: str,
        confidence: float
    ):
        """Ajoute une interaction à l'historique"""
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "bot_response": bot_response,
            "confidence": confidence
        }

        self.conversations[user_id].append(interaction)

        if len(self.conversations[user_id]) > self.max_history:
            self.conversations[user_id] = self.conversations[user_id][-self.max_history:]

        self.stats["total_interactions"] += 1
        self.stats["active_users"] = len(self.conversations)

    def get_history(self, user_id: str) -> List[Dict]:
        """Récupère l'historique d'un utilisateur"""
        return self.conversations.get(user_id, [])

    def clear_history(self, user_id: str):
        """Efface l'historique d'un utilisateur"""
        if user_id in self.conversations:
            del self.conversations[user_id]
            self.stats["active_users"] = len(self.conversations)

    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        return self.stats

    def get_recent_topics(self, user_id: str, n: int = 3) -> List[str]:
        """Extrait les N derniers sujets abordés"""
        history = self.get_history(user_id)
        return [item["user_message"] for item in history[-n:]]
