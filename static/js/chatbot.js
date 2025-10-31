const userId = "user_" + Math.random().toString(36).substr(2, 9);

document.addEventListener("DOMContentLoaded", () => {
  loadLLMStatus();

  document.getElementById("sendBtn").addEventListener("click", sendMessage);
  document.getElementById("userInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });
  document.getElementById("clearChatBtn").addEventListener("click", clearChat);
});

async function loadLLMStatus() {
  try {
    const response = await fetch("/llm/status");
    const data = await response.json();
    const badge = document.getElementById("llmBadge");
    const providerNames = { groq: "⚡ Groq Cloud" };
    badge.textContent = providerNames[data.current] || data.current;
  } catch {
    document.getElementById("llmBadge").textContent = "❌ Non connecté";
  }
}

function addMessage(content, isUser, metadata = {}) {
  const chatBox = document.getElementById("chatBox");
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${isUser ? "user" : "bot"}`;

  let html = `<div class="message-content">${content}</div>`;

  if (!isUser && metadata) {
    const { confidence, provider, retrieval_only } = metadata;
    let metaHtml = '<div class="message-meta">';

    if (confidence !== undefined) {
      const emoji = confidence > 0.7 ? "✅" : confidence > 0.4 ? "⚠️" : "❓";
      const color =
        confidence > 0.7 ? "#4caf50" : confidence > 0.4 ? "#ff9800" : "#f44336";
      metaHtml += `<span class="confidence-badge" style="background: ${color}20; color: ${color};">${emoji} ${(
        confidence * 100
      ).toFixed(0)}%</span>`;
    }

    if (provider && !retrieval_only) {
      const providerEmoji = { groq: "⚡" };
      metaHtml += `<span class="provider-badge">${
        providerEmoji[provider] || "🤖"
      } ${provider}</span>`;
    } else if (retrieval_only) {
      metaHtml += `<span class="provider-badge" style="background: #9e9e9e;">🔍 FAQ directe</span>`;
    }

    metaHtml += "</div>";
    html += metaHtml;
  }

  messageDiv.innerHTML = html;
  chatBox.appendChild(messageDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
  const input = document.getElementById("userInput");
  const sendBtn = document.getElementById("sendBtn");
  const useLLM = document.getElementById("useLLM").checked;
  const message = input.value.trim();

  if (!message) return;

  addMessage(message, true);
  input.value = "";
  sendBtn.disabled = true;

  addMessage(
    '<span class="loading"></span><span class="loading" style="animation-delay:0.2s"></span><span class="loading" style="animation-delay:0.4s"></span>',
    false
  );

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, user_id: userId, use_llm: useLLM }),
    });

    const chatBox = document.getElementById("chatBox");
    chatBox.removeChild(chatBox.lastChild);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: "Erreur inconnue" }));
      throw new Error(errorData.detail || `Erreur ${response.status}`);
    }

    const data = await response.json();
    addMessage(data.response, false, {
      confidence: data.confidence,
      provider: data.provider,
      retrieval_only: data.retrieval_only,
    });
  } catch (error) {
    const chatBox = document.getElementById("chatBox");
    if (chatBox.lastChild) {
      chatBox.removeChild(chatBox.lastChild);
    }
    const errorMessage = error.message || "Erreur de connexion. Veuillez réessayer.";
    addMessage(`❌ ${errorMessage}`, false);
    console.error("Erreur:", error);
  }

  sendBtn.disabled = false;
  input.focus();
}

function clearChat() {
  document.getElementById("chatBox").innerHTML = `
    <div class="message bot">
      <div class="message-content">
        💬 Conversation effacée. Comment puis-je vous aider ?
      </div>
    </div>`;
}
