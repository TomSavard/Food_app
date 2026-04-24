// In-app assistant: floating button + chat panel.
// Posts to /api/chat which streams SSE chunks: {"text": "..."} or {"error": "..."}.

(function () {
    const messages = []; // history kept in memory; refresh = fresh chat

    function el(tag, opts = {}, ...children) {
        const e = document.createElement(tag);
        if (opts.class) e.className = opts.class;
        if (opts.text) e.textContent = opts.text;
        if (opts.id) e.id = opts.id;
        if (opts.onclick) e.onclick = opts.onclick;
        for (const c of children) e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
        return e;
    }

    const fab = el('button', { class: 'chat-fab', id: 'chat-fab', text: '💬' });
    const messagesContainer = el('div', { class: 'chat-messages', id: 'chat-messages' });
    const input = Object.assign(document.createElement('input'), {
        type: 'text',
        placeholder: 'Ask about your recipes…',
    });
    const sendBtn = el('button', { text: 'Send' });
    const inputRow = el('div', { class: 'chat-input-row' }, input, sendBtn);
    const closeBtn = el('button', { class: 'chat-close', text: '×' });
    const header = el('div', { class: 'chat-header' }, el('h3', { text: 'Assistant' }), closeBtn);
    const panel = el('div', { class: 'chat-panel', id: 'chat-panel' }, header, messagesContainer, inputRow);

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    function togglePanel() { panel.classList.toggle('open'); if (panel.classList.contains('open')) input.focus(); }
    fab.onclick = togglePanel;
    closeBtn.onclick = togglePanel;

    function addBubble(role, text) {
        const b = el('div', { class: `chat-msg ${role}`, text });
        messagesContainer.appendChild(b);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return b;
    }

    async function send() {
        const text = input.value.trim();
        if (!text) return;
        input.value = '';
        sendBtn.disabled = true;

        messages.push({ role: 'user', text });
        addBubble('user', text);
        const modelBubble = addBubble('model', '');

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages }),
            });
            if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buf = '';
            let modelText = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buf += decoder.decode(value, { stream: true });
                let idx;
                while ((idx = buf.indexOf('\n\n')) !== -1) {
                    const event = buf.slice(0, idx).trim();
                    buf = buf.slice(idx + 2);
                    if (!event.startsWith('data: ')) continue;
                    const payload = event.slice(6);
                    if (payload === '[DONE]') continue;
                    try {
                        const obj = JSON.parse(payload);
                        if (obj.text) {
                            modelText += obj.text;
                            modelBubble.textContent = modelText;
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        } else if (obj.error) {
                            throw new Error(obj.error);
                        }
                    } catch (e) {
                        if (e instanceof SyntaxError) continue; // partial JSON; skip
                        throw e;
                    }
                }
            }
            messages.push({ role: 'model', text: modelText });
        } catch (err) {
            modelBubble.classList.remove('model');
            modelBubble.classList.add('error');
            modelBubble.textContent = `Error: ${err.message}`;
        } finally {
            sendBtn.disabled = false;
            input.focus();
        }
    }

    sendBtn.onclick = send;
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
})();
