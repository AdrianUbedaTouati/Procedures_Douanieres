/**
 * TenderAI Chat - Interactive JavaScript
 * Apple-inspired smooth interactions
 */

(function() {
    'use strict';

    // ============================================
    // Configuration
    // ============================================
    const CONFIG = {
        autoScrollThreshold: 100,
        typingIndicatorDelay: 300,
        messageAnimationDelay: 100,
        maxInputHeight: 120,
        autoResizeEnabled: true
    };

    // ============================================
    // DOM Elements
    // ============================================
    let elements = {};

    function initElements() {
        elements = {
            chatMessages: document.getElementById('chatMessages'),
            messageForm: document.getElementById('messageForm'),
            messageInput: document.getElementById('messageInput'),
            sendButton: document.getElementById('sendButton'),
            csrfToken: document.querySelector('[name=csrfmiddlewaretoken]')
        };
    }

    // ============================================
    // Auto-scroll Chat to Bottom
    // ============================================
    function scrollToBottom(smooth = true) {
        if (!elements.chatMessages) return;

        const scrollOptions = {
            top: elements.chatMessages.scrollHeight,
            behavior: smooth ? 'smooth' : 'auto'
        };

        elements.chatMessages.scrollTo(scrollOptions);
    }

    function isNearBottom() {
        if (!elements.chatMessages) return true;

        const threshold = CONFIG.autoScrollThreshold;
        const position = elements.chatMessages.scrollTop + elements.chatMessages.clientHeight;
        const height = elements.chatMessages.scrollHeight;

        return position >= height - threshold;
    }

    // ============================================
    // Textarea Auto-resize
    // ============================================
    function autoResizeTextarea() {
        if (!elements.messageInput || !CONFIG.autoResizeEnabled) return;

        elements.messageInput.style.height = 'auto';
        const newHeight = Math.min(elements.messageInput.scrollHeight, CONFIG.maxInputHeight);
        elements.messageInput.style.height = newHeight + 'px';
    }

    // ============================================
    // Typing Indicator with rotating messages
    // ============================================
    const thinkingMessages = [
        'Pensando',
        'Analizando',
        'Procesando',
        'Buscando',
        'Consultando',
        'Investigando',
        'Examinando'
    ];

    let thinkingInterval = null;

    function showTypingIndicator() {
        if (!elements.chatMessages) return;

        const wasNearBottom = isNearBottom();
        const randomMessage = thinkingMessages[Math.floor(Math.random() * thinkingMessages.length)];

        const typingHTML = `
            <div class="typing-indicator" id="typingIndicator">
                <div class="message-avatar avatar-assistant">
                    <i class="bi bi-robot"></i>
                </div>
                <div class="message-content-wrapper">
                    <div class="typing-message" id="typingMessage" style="color: #6c757d; font-style: italic; padding: 8px 12px;">
                        <span id="thinkingText">${randomMessage}</span><span class="typing-dots-text">...</span>
                    </div>
                </div>
            </div>
        `;

        elements.chatMessages.insertAdjacentHTML('beforeend', typingHTML);

        // Rotate thinking messages every 2 seconds
        let currentIndex = thinkingMessages.indexOf(randomMessage);
        thinkingInterval = setInterval(() => {
            const thinkingText = document.getElementById('thinkingText');
            if (thinkingText) {
                currentIndex = (currentIndex + 1) % thinkingMessages.length;
                thinkingText.textContent = thinkingMessages[currentIndex];
            }
        }, 2000);

        if (wasNearBottom) {
            setTimeout(() => scrollToBottom(), 50);
        }
    }

    function hideTypingIndicator() {
        // Clear the thinking message interval
        if (thinkingInterval) {
            clearInterval(thinkingInterval);
            thinkingInterval = null;
        }

        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    // ============================================
    // Message Rendering
    // ============================================
    function createMessageElement(message, role) {
        const wasNearBottom = isNearBottom();

        // Si el mensaje incluye HTML pre-renderizado, usarlo directamente
        // Esto incluye markdown renderizado y todos los paneles de metadata
        if (message.rendered_html) {
            elements.chatMessages.insertAdjacentHTML('beforeend', message.rendered_html);
        } else {
            // Fallback para retrocompatibilidad si no hay rendered_html
            const isUser = role === 'user';
            const messageHTML = `
                <div class="message-group ${role}" data-message-id="${message.id || ''}">
                    <div class="message-avatar avatar-${role}">
                        ${isUser ? '<i class="bi bi-person-fill"></i>' : '<i class="bi bi-robot"></i>'}
                    </div>
                    <div class="message-content-wrapper">
                        <div class="message-bubble ${role}">
                            ${escapeHtml(message.content)}
                        </div>
                        <div class="message-time">
                            ${formatTime(message.created_at || new Date().toISOString())}
                        </div>
                        ${message.metadata && message.metadata.documents_used ?
                            `<div class="message-metadata">
                                <i class="bi bi-file-text"></i>
                                <span>${message.metadata.documents_used.length} documento(s) consultado(s)</span>
                            </div>` : ''
                        }
                    </div>
                </div>
            `;
            elements.chatMessages.insertAdjacentHTML('beforeend', messageHTML);
        }

        if (wasNearBottom) {
            setTimeout(() => scrollToBottom(), CONFIG.messageAnimationDelay);
        }
    }

    // ============================================
    // AJAX Form Submission
    // ============================================
    async function handleFormSubmit(event) {
        event.preventDefault();

        const message = elements.messageInput.value.trim();
        if (!message) return;

        // Disable input
        setInputState(false);

        // Mostrar mensaje del usuario INMEDIATAMENTE (sin esperar servidor)
        const tempUserMessage = {
            content: message,
            created_at: new Date().toISOString()
        };
        createMessageElement(tempUserMessage, 'user');

        // Clear input
        elements.messageInput.value = '';
        autoResizeTextarea();

        // Show typing indicator INMEDIATAMENTE (sin setTimeout)
        showTypingIndicator();

        try {
            // Send message via AJAX
            const formData = new FormData();
            formData.append('message', message);
            formData.append('csrfmiddlewaretoken', elements.csrfToken.value);

            const response = await fetch(elements.messageForm.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });

            const data = await response.json();

            // Hide typing indicator
            hideTypingIndicator();

            if (data.success) {
                // El mensaje del usuario ya se mostró arriba, solo actualizarlo si hay rendered_html
                // (por ahora lo dejamos como está, el temp es suficiente)

                // Display assistant message with rendered HTML from server
                if (data.assistant_message) {
                    createMessageElement(data.assistant_message, 'assistant');
                }
            } else {
                showError(data.error || 'Error al enviar el mensaje');
            }

        } catch (error) {
            console.error('Error:', error);
            hideTypingIndicator();
            showError('Error de conexión. Por favor, intenta de nuevo.');
        } finally {
            // Re-enable input
            setInputState(true);
            elements.messageInput.focus();
        }
    }

    // ============================================
    // Input State Management
    // ============================================
    function setInputState(enabled) {
        if (!elements.messageInput || !elements.sendButton) return;

        elements.messageInput.disabled = !enabled;
        elements.sendButton.disabled = !enabled;

        if (enabled) {
            elements.sendButton.innerHTML = '<i class="bi bi-send-fill"></i>';
        } else {
            elements.sendButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        }
    }

    // ============================================
    // Error Display
    // ============================================
    function showError(message) {
        const errorHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="bi bi-exclamation-circle"></i> ${escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        const container = document.querySelector('.chat-wrapper');
        if (container) {
            container.insertAdjacentHTML('afterbegin', errorHTML);
            setTimeout(() => {
                const alert = container.querySelector('.alert');
                if (alert) alert.remove();
            }, 5000);
        }
    }

    // ============================================
    // Utility Functions
    // ============================================
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    function formatTime(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diff = now - date;

        // Less than 1 minute
        if (diff < 60000) {
            return 'Ahora';
        }

        // Less than 1 hour
        if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            return `Hace ${minutes} min`;
        }

        // Less than 24 hours
        if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            return `Hace ${hours} h`;
        }

        // Format as date
        return date.toLocaleDateString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // ============================================
    // Keyboard Shortcuts
    // ============================================
    function handleKeyDown(event) {
        // Enter without Shift sends message
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            if (elements.messageForm && elements.messageInput.value.trim()) {
                elements.messageForm.dispatchEvent(new Event('submit'));
            }
        }

        // Escape clears input
        if (event.key === 'Escape') {
            elements.messageInput.value = '';
            autoResizeTextarea();
            elements.messageInput.blur();
        }
    }

    // ============================================
    // Initialize
    // ============================================
    function initialize() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initialize);
            return;
        }

        // Initialize elements
        initElements();

        // Check if we're on a chat page
        if (!elements.messageForm) return;

        // Attach event listeners
        elements.messageForm.addEventListener('submit', handleFormSubmit);

        if (elements.messageInput) {
            elements.messageInput.addEventListener('input', autoResizeTextarea);
            elements.messageInput.addEventListener('keydown', handleKeyDown);
        }

        // Initial scroll to bottom
        scrollToBottom(false);

        // Auto-resize textarea on init
        autoResizeTextarea();

        // Focus on input
        if (elements.messageInput) {
            elements.messageInput.focus();
        }

        console.log('TenderAI Chat initialized ✓');
    }

    // ============================================
    // Export to window for external access
    // ============================================
    window.TenderAIChat = {
        scrollToBottom,
        showTypingIndicator,
        hideTypingIndicator,
        createMessageElement,
        initialize
    };

    // Auto-initialize
    initialize();

})();
