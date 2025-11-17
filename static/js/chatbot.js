const userId = "user_" + Math.random().toString(36).substr(2, 9);
let isTyping = false;
let failedMessages = new Map(); // Store failed messages for retry
const MAX_MESSAGE_LENGTH = 2000;
// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  initializeChatbot();
});
/**
 * Initialize chatbot components
 */
function initializeChatbot() {
  loadLLMStatus();
  loadChatHistory();
  setupEventListeners();
  focusInput();
}
/**
 * Setup all event listeners
 */
function setupEventListeners() {
  const sendBtn = document.getElementById("sendBtn");
  const userInput = document.getElementById("userInput");
  const clearChatBtn = document.getElementById("clearChatBtn");
  const settingsBtn = document.getElementById("settingsBtn");
  // Send message on button click
  sendBtn.addEventListener("click", handleSendMessage);
  // Send message on Enter, new line on Shift+Enter
  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });
  // Clear chat
  clearChatBtn.addEventListener("click", clearChat);
  // Settings button - show history options
  settingsBtn.addEventListener("click", () => {
    showHistoryMenu();
  });
  // Character counter
  userInput.addEventListener("input", updateCharacterCounter);
  // Focus input when clicking on chat area
  document.getElementById("chatBox").addEventListener("click", () => {
    userInput.focus();
  });
  // Keyboard shortcuts
  document.addEventListener("keydown", handleKeyboardShortcuts);
  // Handle image load error
  const avatarImg = document.querySelector(".avatar img");
  if (avatarImg) {
    avatarImg.addEventListener("error", () => {
      avatarImg.style.display = "none";
    });
  }
  // Initialize character counter
  updateCharacterCounter();
}
/**
 * Load and display LLM status
 */
async function loadLLMStatus() {
  try {
    const response = await fetch("/llm/status");
    const data = await response.json();
    const badge = document.getElementById("llmBadge");
    const statusText = badge.querySelector(".status-text");
    const statusDot = badge.querySelector(".status-dot");
    const providerNames = {
      groq: "⚡ Groq Cloud",
      openai: "🤖 OpenAI",
      anthropic: "🧠 Claude",
      default: "🤖 LLM",
    };
    if (data.current && data.current !== "none") {
      statusText.textContent = providerNames[data.current] || data.current;
      statusDot.style.background = "var(--success)";
      updateStatusIndicator("online");
    } else {
      statusText.textContent = "❌ Non connecté";
      statusDot.style.background = "var(--error)";
      updateStatusIndicator("offline");
    }
  } catch (error) {
    console.error("Error loading LLM status:", error);
    const badge = document.getElementById("llmBadge");
    const statusText = badge.querySelector(".status-text");
    const statusDot = badge.querySelector(".status-dot");
    statusText.textContent = "❌ Erreur de connexion";
    statusDot.style.background = "var(--error)";
    updateStatusIndicator("error");
  }
}
/**
 * Update status indicator
 */
function updateStatusIndicator(status) {
  const indicator = document.getElementById("statusIndicator");
  const statusText = document.getElementById("statusText");
  const statusConfig = {
    online: {
      color: "var(--success)",
      text: "En ligne",
    },
    offline: {
      color: "var(--error)",
      text: "Hors ligne",
    },
    error: {
      color: "var(--error)",
      text: "Erreur",
    },
    typing: {
      color: "var(--warning)",
      text: "En train d'écrire...",
    },
  };
  const config = statusConfig[status] || statusConfig.online;
  indicator.style.background = config.color;
  statusText.textContent = config.text;
}

/**
 * Format timestamp
 */
function formatTimestamp(date = new Date()) {
  const hours = date.getHours().toString().padStart(2, "0");
  const minutes = date.getMinutes().toString().padStart(2, "0");
  return `${hours}:${minutes}`;
}
/**
 * Get confidence badge class
 */
function getConfidenceClass(confidence) {
  if (confidence > 0.7) return "high";
  if (confidence > 0.4) return "medium";
  return "low";
}
/**
 * Get confidence emoji
 */
function getConfidenceEmoji(confidence) {
  if (confidence > 0.7) return "✅";
  if (confidence > 0.4) return "⚠️";
  return "❓";
}
/**
 * Add message to chat
 */
function addMessage(content, isUser, metadata = {}, messageId = null) {
  const chatBox = document.getElementById("chatBox");
  // Remove welcome message if it exists
  const welcomeMessage = chatBox.querySelector(".welcome-message");
  if (welcomeMessage) {
    welcomeMessage.remove();
  }
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${isUser ? "user" : "bot"}`;
  if (metadata.isError) {
    messageDiv.classList.add("error-message");
  }
  if (messageId) {
    messageDiv.dataset.messageId = messageId;
  }
  const contentWrapper = document.createElement("div");
  contentWrapper.className = "message-content-wrapper";
  // Message content with actions
  const messageContentContainer = document.createElement("div");
  messageContentContainer.style.position = "relative";
  const messageContent = document.createElement("div");
  messageContent.className = "message-content";
  messageContent.textContent = content;
  messageContentContainer.appendChild(messageContent);
  // Message actions (copy button)
  if (!isUser) {
    const messageActions = document.createElement("div");
    messageActions.className = "message-actions";
    const copyBtn = document.createElement("button");
    copyBtn.className = "message-action-btn";
    copyBtn.title = "Copier le message";
    copyBtn.innerHTML = "📋";
    copyBtn.addEventListener("click", () => copyMessage(content));
    messageActions.appendChild(copyBtn);
    messageContentContainer.appendChild(messageActions);
  }
  contentWrapper.appendChild(messageContentContainer);
  // Message metadata (for bot messages)
  if (!isUser && metadata) {
    const metaDiv = document.createElement("div");
    metaDiv.className = "message-meta";
    // Timestamp
    const timestamp = document.createElement("span");
    timestamp.className = "message-timestamp";
    timestamp.textContent = formatTimestamp();
    metaDiv.appendChild(timestamp);
    // Confidence badge
    if (metadata.confidence !== undefined) {
      const confidenceBadge = document.createElement("span");
      confidenceBadge.className = `confidence-badge ${getConfidenceClass(
        metadata.confidence
      )}`;
      confidenceBadge.innerHTML = `${getConfidenceEmoji(
        metadata.confidence
      )} ${Math.round(metadata.confidence * 100)}%`;
      metaDiv.appendChild(confidenceBadge);
    }
    // Provider badge
    if (metadata.provider && !metadata.retrieval_only) {
      const providerBadge = document.createElement("span");
      providerBadge.className = "provider-badge";
      const providerEmoji = {
        groq: "⚡",
        openai: "🤖",
        anthropic: "🧠",
      };
      providerBadge.innerHTML = `${providerEmoji[metadata.provider] || "🤖"} ${
        metadata.provider
      }`;
      metaDiv.appendChild(providerBadge);
    } else if (metadata.retrieval_only) {
      const providerBadge = document.createElement("span");
      providerBadge.className = "provider-badge";
      providerBadge.style.background = "rgba(108, 117, 125, 0.1)";
      providerBadge.style.color = "var(--text-secondary)";
      providerBadge.innerHTML = "🔍 FAQ directe";
      metaDiv.appendChild(providerBadge);
    }
    contentWrapper.appendChild(metaDiv);
  } else if (isUser) {
    // User message timestamp
    const metaDiv = document.createElement("div");
    metaDiv.className = "message-meta";
    const timestamp = document.createElement("span");
    timestamp.className = "message-timestamp";
    timestamp.textContent = formatTimestamp();
    metaDiv.appendChild(timestamp);
    contentWrapper.appendChild(metaDiv);
  }
  // Add retry button for failed messages
  if (metadata.isError && metadata.originalMessage) {
    const retryBtn = document.createElement("button");
    retryBtn.className = "retry-button";
    retryBtn.innerHTML = "🔄 Réessayer";
    retryBtn.addEventListener("click", () =>
      retryMessage(metadata.originalMessage, messageId)
    );
    contentWrapper.appendChild(retryBtn);
  }
  messageDiv.appendChild(contentWrapper);
  chatBox.appendChild(messageDiv);
  // Smooth scroll to bottom
  scrollToBottom();
}
/**
 * Show typing indicator
 */
function showTypingIndicator() {
  if (isTyping) return;
  isTyping = true;
  const indicator = document.getElementById("typingIndicator");
  indicator.style.display = "flex";
  updateStatusIndicator("typing");
  scrollToBottom();
}
/**
 * Hide typing indicator
 */
function hideTypingIndicator() {
  isTyping = false;
  const indicator = document.getElementById("typingIndicator");
  indicator.style.display = "none";
  updateStatusIndicator("online");
}
/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
  const chatBox = document.getElementById("chatBox");
  chatBox.scrollTo({
    top: chatBox.scrollHeight,
    behavior: "smooth",
  });
}
/**
 * Handle send message
 */
async function handleSendMessage() {
  const input = document.getElementById("userInput");
  const sendBtn = document.getElementById("sendBtn");
  const useLLM = document.getElementById("useLLM").checked;
  const message = input.value.trim();

  if (!message || isTyping) return;
  // Validate message length
  if (message.length > MAX_MESSAGE_LENGTH) {
    showToast("Le message est trop long (maximum 2000 caractères)", "error");
    return;
  }
  // Generate unique message ID
  const messageId = Date.now().toString();
  // Add user message
  addMessage(message, true, {}, messageId);
  input.value = "";
  updateCharacterCounter();
  // Disable input and button
  input.disabled = true;
  sendBtn.disabled = true;
  // Show typing indicator
  showTypingIndicator();
  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        user_id: userId,
        use_llm: useLLM,
      }),
    });
    // Hide typing indicator
    hideTypingIndicator();
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: "Erreur inconnue",
      }));
      throw new Error(errorData.detail || `Erreur ${response.status}`);
    }
    const data = await response.json();
    // Add bot response
    addMessage(data.response, false, {
      confidence: data.confidence,
      provider: data.provider,
      retrieval_only: data.retrieval_only,
    });
    // Show notification for new questions
    if (data.is_new_question) {
      showToast("Nouvelle question enregistrée pour amélioration", "info");
    }
  } catch (error) {
    hideTypingIndicator();
    const errorMessage =
      error.message || "Erreur de connexion. Veuillez réessayer.";
    // Store failed message for retry
    failedMessages.set(messageId, { message, useLLM });
    addMessage(
      `❌ ${errorMessage}`,
      false,
      {
        isError: true,
        originalMessage: message,
        useLLM: useLLM,
      },
      messageId
    );
    showToast("Erreur lors de l'envoi du message", "error");
    console.error("Error sending message:", error);
  } finally {
    // Re-enable input and button
    input.disabled = false;
    sendBtn.disabled = false;
    focusInput();
  }
}
/**
 * Clear chat
 */
function clearChat() {
  const chatBox = document.getElementById("chatBox");
  const welcomeMessage = `
    <div class="welcome-message">
      <div class="welcome-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </div>
      <h2 class="welcome-title">Conversation effacée 💬</h2>
      <p class="welcome-text">
        Comment puis-je vous aider aujourd'hui ?
      </p>
    </div>
  `;
  chatBox.innerHTML = welcomeMessage;
  focusInput();
}
/**
 * Focus input field
 */
function focusInput() {
  const input = document.getElementById("userInput");
  input.focus();
}
/**
 * Update character counter
 */
function updateCharacterCounter() {
  const input = document.getElementById("userInput");
  const counter = document.getElementById("charCounter");
  if (!input || !counter) return;
  const length = input.value.length;
  counter.textContent = `${length} / ${MAX_MESSAGE_LENGTH}`;
  // Update counter color based on length
  counter.classList.remove("warning", "error");
  if (length > MAX_MESSAGE_LENGTH * 0.9) {
    counter.classList.add("error");
  } else if (length > MAX_MESSAGE_LENGTH * 0.75) {
    counter.classList.add("warning");
  }
}
/**
 * Copy message to clipboard
 */
async function copyMessage(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast("Message copié dans le presse-papiers", "success");
  } catch (error) {
    // Fallback for older browsers
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.opacity = "0";
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand("copy");
      showToast("Message copié dans le presse-papiers", "success");
    } catch (err) {
      showToast("Impossible de copier le message", "error");
    }
    document.body.removeChild(textArea);
  }
}
/**
 * Retry failed message
 */
async function retryMessage(originalMessage, messageId) {
  // Remove the error message
  const errorMessage = document.querySelector(
    `[data-message-id="${messageId}"]`
  );
  if (errorMessage) {
    errorMessage.remove();
  }
  // Set input value and send
  const input = document.getElementById("userInput");
  input.value = originalMessage;
  updateCharacterCounter();
  // Get the stored LLM preference
  const storedData = failedMessages.get(messageId);
  if (storedData) {
    document.getElementById("useLLM").checked = storedData.useLLM;
  }
  focusInput();
  await handleSendMessage();
  // Clean up
  failedMessages.delete(messageId);
}
/**
 * Show toast notification
 */
function showToast(message, type = "info") {
  // Remove existing toasts
  const existingToasts = document.querySelectorAll(".toast-notification");
  existingToasts.forEach((toast) => toast.remove());

  const toast = document.createElement("div");
  toast.className = `toast-notification ${type}`;

  const icons = {
    success: "✅",
    error: "❌",
    info: "ℹ️",
  };

  toast.innerHTML = `<span>${icons[type] || ""}</span><span>${message}</span>`;
  document.body.appendChild(toast);
  // Auto remove after 3 seconds
  setTimeout(() => {
    toast.style.animation = "slideInRight 0.3s ease-out reverse";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}
/**
 * Show history menu
 */
function showHistoryMenu() {
  const menu = document.createElement("div");
  menu.className = "history-menu";
  menu.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: white;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    min-width: 300px;
  `;
  menu.innerHTML = `
    <h3 style="margin: 0 0 16px 0; font-size: 1.25rem;">Gestion de l'historique</h3>
    <div style="display: flex; flex-direction: column; gap: 8px;">
      <button class="history-menu-btn" onclick="exportChatHistory('json')" style="padding: 10px; background: var(--primary); color: white; border: none; border-radius: 8px; cursor: pointer;">
        📥 Exporter en JSON
      </button>
      <button class="history-menu-btn" onclick="exportChatHistory('txt')" style="padding: 10px; background: var(--primary); color: white; border: none; border-radius: 8px; cursor: pointer;">
        📄 Exporter en TXT
      </button>
      <button class="history-menu-btn" onclick="clearServerHistory()" style="padding: 10px; background: var(--error); color: white; border: none; border-radius: 8px; cursor: pointer;">
        🗑️ Effacer l'historique serveur
      </button>
      <button class="history-menu-btn" onclick="this.closest('.history-menu').remove()" style="padding: 10px; background: var(--bg-tertiary); color: var(--text-primary); border: none; border-radius: 8px; cursor: pointer; margin-top: 8px;">
        Fermer
      </button>
    </div>
  `;
  // Add overlay
  const overlay = document.createElement("div");
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 999;
  `;
  overlay.addEventListener("click", () => {
    menu.remove();
    overlay.remove();
  });
  document.body.appendChild(overlay);
  document.body.appendChild(menu);
}
/**
 * Handle keyboard shortcuts
 */
function handleKeyboardShortcuts(e) {
  // Ctrl/Cmd + K to focus input
  if ((e.ctrlKey || e.metaKey) && e.key === "k") {
    e.preventDefault();
    focusInput();
  }
  // Escape to clear input or close modals
  if (e.key === "Escape") {
    const input = document.getElementById("userInput");
    if (document.activeElement === input && input.value) {
      input.value = "";
      updateCharacterCounter();
    } else {
      // Close any open modals
      const menu = document.querySelector(".history-menu");
      const overlay = document.querySelector(
        "div[style*='rgba(0, 0, 0, 0.5)']"
      );
      if (menu) menu.remove();
      if (overlay) overlay.remove();
    }
  }
}

/**
 * Load chat history on page load
 */
async function loadChatHistory() {
  try {
    const response = await fetch(`/chat/history/${userId}`);
    if (!response.ok) {
      // No history exists yet, that's fine
      return;
    }
    const data = await response.json();
    if (data.history && data.history.length > 0) {
      // Remove welcome message
      const chatBox = document.getElementById("chatBox");
      const welcomeMessage = chatBox.querySelector(".welcome-message");
      if (welcomeMessage) {
        welcomeMessage.remove();
      }
      // Load history messages
      data.history.forEach((item) => {
        // Add user message
        addMessage(item.user_message, true, {}, null);
        // Add bot response
        addMessage(
          item.bot_response,
          false,
          {
            confidence: item.confidence,
            provider: item.provider,
            retrieval_only: item.retrieval_only,
          },
          null
        );
      });
      showToast(`Historique chargé: ${data.total_messages} messages`, "info");
    }
  } catch (error) {
    console.log("No chat history found or error loading:", error);
    // This is fine, user might be new
  }
}
/**
 * Export chat history
 */
async function exportChatHistory(format = "json") {
  try {
    const response = await fetch(
      `/chat/history/${userId}/export?format=${format}`
    );
    if (!response.ok) {
      throw new Error("Erreur lors de l'export");
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chat_history_${userId}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    showToast(`Historique exporté en ${format.toUpperCase()}`, "success");
  } catch (error) {
    showToast("Erreur lors de l'export de l'historique", "error");
    console.error("Export error:", error);
  }
}
/**
 * Clear chat history from server
 */
async function clearServerHistory() {
  if (!confirm("Voulez-vous vraiment effacer l'historique sur le serveur ?")) {
    return;
  }
  try {
    const response = await fetch(`/chat/history/${userId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Erreur lors de l'effacement");
    }
    showToast("Historique effacé avec succès", "success");
    clearChat(); // Also clear local display
  } catch (error) {
    showToast("Erreur lors de l'effacement de l'historique", "error");
    console.error("Clear history error:", error);
  }
}
/**
 * Format message content (for future markdown support)
 */
function formatMessageContent(content) {
  // Future: Add markdown parsing, link detection, etc.
  return content;
}
// Make functions globally accessible for onclick handlers
window.exportChatHistory = exportChatHistory;
window.clearServerHistory = clearServerHistory;
// Export functions for potential external use
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    addMessage,
    clearChat,
    handleSendMessage,
    copyMessage,
    showToast,
    exportChatHistory,
    clearServerHistory,
  };
}
