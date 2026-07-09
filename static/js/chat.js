/**
 * Atlas Travel Planner — Chat Interface
 * Handles all chat interactions with the AI backend
 */

let isLoading = false;

// ── Initialize ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initCharCounter();
    focusInput();
});

function focusInput() {
    const input = document.getElementById('userInput');
    if (input) setTimeout(() => input.focus(), 300);
}

// ── Sidebar Toggle (Mobile) ────────────────────────────────────────────────────
function initSidebar() {
    const sidebar  = document.getElementById('chatSidebar');
    const openBtn  = document.getElementById('openSidebar');
    const closeBtn = document.getElementById('closeSidebar');

    if (!sidebar) return;

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    overlay.id = 'sidebarOverlay';
    document.body.appendChild(overlay);

    openBtn?.addEventListener('click', () => {
        sidebar.classList.add('open');
        overlay.classList.add('show');
    });

    const closeSidebar = () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('show');
    };

    closeBtn?.addEventListener('click', closeSidebar);
    overlay.addEventListener('click', closeSidebar);
}

// ── Character Counter ─────────────────────────────────────────────────────────
function initCharCounter() {
    const input   = document.getElementById('userInput');
    const counter = document.getElementById('charCounter');
    if (!input || !counter) return;

    input.addEventListener('input', () => {
        const len = input.value.length;
        counter.textContent = `${len} / 500`;
        counter.style.color = len > 450 ? '#dc2626' : 'var(--text-faint)';
    });
}

// ── Auto-resize Textarea ──────────────────────────────────────────────────────
function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
    // Update char counter
    const counter = document.getElementById('charCounter');
    if (counter) counter.textContent = `${el.value.length} / 500`;
}

// ── Key Handler ───────────────────────────────────────────────────────────────
function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

// ── Send Message ──────────────────────────────────────────────────────────────
async function sendMessage() {
    if (isLoading) return;

    const input   = document.getElementById('userInput');
    const message = input.value.trim();
    if (!message) return;

    if (message.length > 500) {
        showToast('Message too long. Please keep it under 500 characters.', 'warning');
        return;
    }

    // Clear input
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('charCounter').textContent = '0 / 500';

    // Hide suggestion chips after first message
    const suggBar = document.getElementById('suggestionBar');
    if (suggBar) suggBar.style.display = 'none';

    // Append user message
    appendMessage('user', message);
    setLoading(true);

    try {
        const res = await fetch('/api/chat', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ message }),
        });

        const data = await res.json();

        if (data.response) {
            appendMessage('ai', data.response);
        } else {
            appendMessage('ai', '⚠️ Something went wrong. Please try again.');
        }
    } catch (err) {
        console.error('[Chat] Error:', err);
        appendMessage('ai', '⚠️ Connection error. Please check your network and try again.');
    } finally {
        setLoading(false);
        input.focus();
    }
}

// ── Append Message to Chat ────────────────────────────────────────────────────
function appendMessage(role, content) {
    const messages = document.getElementById('chatMessages');
    if (!messages) return;

    const isUser = role === 'user';
    const row    = document.createElement('div');
    row.className = `message-row ${role}`;
    row.setAttribute('data-role', role);

    const avatar = `<div class="msg-avatar">${isUser ? '<i class="bi bi-person"></i>' : '✈️'}</div>`;

    let htmlContent;
    if (isUser) {
        htmlContent = `<div class="msg-bubble user-bubble"><div class="msg-content">${escapeHtml(content)}</div></div>`;
    } else {
        const rendered = typeof marked !== 'undefined' ? marked.parse(content) : escapeHtml(content);
        const time     = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        htmlContent = `
            <div class="msg-bubble ai-bubble">
                <div class="msg-content">${rendered}</div>
                <div class="msg-time">Atlas · ${time}
                    <button class="btn btn-icon copy-msg-btn" style="width:22px;height:22px;border:none;margin-left:.5rem" onclick="copyToClipboard(this.closest('.ai-bubble').querySelector('.msg-content').innerText, 'Message copied!')">
                        <i class="bi bi-copy" style="font-size:.65rem"></i>
                    </button>
                </div>
            </div>`;
    }

    row.innerHTML = isUser ? avatar + htmlContent : avatar + htmlContent;
    messages.appendChild(row);

    // Scroll to bottom
    scrollToBottom();
}

// ── Loading State ─────────────────────────────────────────────────────────────
function setLoading(state) {
    isLoading = state;
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.disabled = state;
        sendBtn.innerHTML = state
            ? '<span class="spinner-border spinner-border-sm"></span>'
            : '<i class="bi bi-send-fill"></i>';
    }

    if (state) {
        // Show typing indicator
        const messages = document.getElementById('chatMessages');
        const loader   = document.createElement('div');
        loader.id        = 'loadingIndicator';
        loader.className = 'message-row ai';
        loader.innerHTML = `
            <div class="msg-avatar">✈️</div>
            <div class="msg-bubble ai-bubble">
                <div class="loading-bubble">
                    <span></span><span></span><span></span>
                </div>
                <div class="msg-time">Atlas is thinking...</div>
            </div>`;
        messages?.appendChild(loader);
        scrollToBottom();
    } else {
        document.getElementById('loadingIndicator')?.remove();
    }
}

// ── Scroll to Bottom ──────────────────────────────────────────────────────────
function scrollToBottom() {
    const messages = document.getElementById('chatMessages');
    if (messages) {
        setTimeout(() => {
            messages.scrollTop = messages.scrollHeight;
        }, 50);
    }
}

// ── Clear Chat ─────────────────────────────────────────────────────────────────
async function clearChat() {
    if (!confirm('Clear the conversation? This cannot be undone.')) return;
    try {
        await fetch('/api/chat/clear', { method: 'POST' });
        const messages = document.getElementById('chatMessages');
        if (messages) messages.innerHTML = '';
        document.getElementById('suggestionBar').style.display = '';
        showToast('Conversation cleared.', 'info');
        // Re-add welcome message
        appendMessage('ai', '👋 Hello! I\'m **Atlas**, your AI travel companion. Where would you like to go today? 🌍');
    } catch (e) {
        showToast('Failed to clear chat.', 'danger');
    }
}

// ── Quick Prompts ─────────────────────────────────────────────────────────────
function useQuickPrompt(btn) {
    const text  = btn.textContent.trim().replace(/^[^a-zA-Z0-9]/, '').trim();
    const input = document.getElementById('userInput');
    if (input) {
        input.value = text;
        autoResize(input);
        input.focus();
        // On mobile, close sidebar
        document.getElementById('chatSidebar')?.classList.remove('open');
        document.getElementById('sidebarOverlay')?.classList.remove('show');
    }
}

function planByType(type) {
    const input = document.getElementById('userInput');
    if (input) {
        input.value = `I want to plan a ${type} trip. What are the best destinations and tips for this style of travel?`;
        autoResize(input);
        // Close sidebar on mobile then send immediately
        document.getElementById('chatSidebar')?.classList.remove('open');
        document.getElementById('sidebarOverlay')?.classList.remove('show');
        sendMessage();
    }
}

function sendSuggestion(btn) {
    const text  = btn.textContent.trim();
    const input = document.getElementById('userInput');
    if (input) {
        input.value = text;
        autoResize(input);
        sendMessage();
    }
}

// ── Template Shortcuts ─────────────────────────────────────────────────────────
const TEMPLATES = {
    itinerary: 'Plan a detailed [X]-day trip to [DESTINATION] for [N] people with a $[BUDGET] budget. Include day-by-day schedule, hotels, restaurants, and costs.',
    budget:    'Create a detailed budget breakdown for a [X]-day trip to [DESTINATION] for [N] people. Include flights, accommodation, food, activities, and transport.',
    packing:   'Create a comprehensive packing list for a [X]-day trip to [DESTINATION]. The climate is [CLIMATE] and I\'ll be doing [ACTIVITIES].',
    visa:      'What are the visa and entry requirements for [NATIONALITY] passport holders visiting [DESTINATION]? Include costs, processing time, and required documents.',
};

function insertTemplate(type) {
    const input = document.getElementById('userInput');
    if (input && TEMPLATES[type]) {
        input.value = TEMPLATES[type];
        autoResize(input);
        input.focus();
        // Select first placeholder
        const start = input.value.indexOf('[');
        const end   = input.value.indexOf(']') + 1;
        if (start > -1) input.setSelectionRange(start, end);
    }
}

// ── Download Chat ─────────────────────────────────────────────────────────────
function downloadChat() {
    const messages = document.getElementById('chatMessages');
    if (!messages) return;

    let text = 'Atlas Travel Planner — Conversation Export\n';
    text    += '='.repeat(50) + '\n\n';

    messages.querySelectorAll('.message-row').forEach(row => {
        const isUser   = row.classList.contains('user');
        const content  = row.querySelector('.msg-content')?.innerText || '';
        const label    = isUser ? 'You' : 'Atlas';
        const time     = row.querySelector('.msg-time')?.textContent?.replace(/copy.*/i, '').trim() || '';
        text += `[${label}${time ? ' · ' + time : ''}]\n${content}\n\n`;
    });

    const blob = new Blob([text], { type: 'text/plain' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `atlas-chat-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Conversation downloaded!', 'success');
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function escapeHtml(str) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return str.replace(/[&<>"']/g, m => map[m]);
}
