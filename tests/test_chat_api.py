def test_chat_endpoint_basic(client):
    """Vérifie que l'API répond bien à un message simple."""
    response = client.post(
        "/chat",
        json={"message": "Bonjour", "user_id": "test_user", "use_llm": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["confidence"] > 0  # Doit avoir un score

def test_chat_history_saving(client, session):
    """Vérifie que le message est bien sauvegardé en base."""
    # Envoyer un message
    client.post(
        "/chat",
        json={"message": "Test history", "user_id": "user_123", "use_llm": False}
    )
    
    # Récupérer l'historique
    response = client.get("/chat/history/user_123")
    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) == 1
    assert data["history"][0]["user_message"] == "Test history"