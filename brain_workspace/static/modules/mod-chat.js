/**
 * 模組：AI 對話 + WebSocket + 對話紀錄 + Agent 記憶
 * ─────────────────────────────────────
 * 功能：
 * - AI 對話與 WebSocket 即時通訊
 * - 對話紀錄儲存與載入
 * - Agent 長期記憶持久化
 * - 上下文摘要自動生成
 */
window.JarvisModChat = function (BASE, { ref, nextTick }) {

    const messages = ref([]);
    const userInput = ref('');
    const aiTyping = ref(false);
    const chatBox = ref(null);
    const quickQ = ['建築法容積率怎麼算？', '什麼是 BIM？', '幫我生成建築渲染圖', '今天天氣如何？'];
    let socket = null;
    
    // Token Saver 模組引用
    let token = null;
    const setTokenModule = (tokenModule) => { token = tokenModule; };

    const scrollBottom = () => nextTick(() => { if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight; });
    const renderMd = (text) => { try { return marked.parse(text || ''); } catch { return text; } };

    const wsConnected = ref(false);
    const connectWs = () => {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        socket = new WebSocket(`${protocol}//${location.host}/ws`);
        socket.onopen = () => { wsConnected.value = true; };
        socket.onclose = () => { wsConnected.value = false; setTimeout(connectWs, 3000); };
        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const content = data.content || data.result || data.text || JSON.stringify(data);
                if (aiTyping.value) aiTyping.value = false;
                messages.value.push({ role: 'ai', content });
                scrollBottom();
            } catch { }
        };
    };

    const sendChat = () => {
        const text = userInput.value.trim();
        if (!text) return;
        
        // ★ Token Saver: 檢查快取
        const cacheKey = token.getCacheKey(text, 'chat');
        const cached = token.getCache(cacheKey);
        if (cached) {
            messages.value.push({ role: 'user', content: text });
            messages.value.push({ role: 'ai', content: cached + '\n\n<small style="color:#64748b">（來自快取）</small>' });
            token.recordHit(cached.length);
            scrollBottom();
            return;
        }
        
        messages.value.push({ role: 'user', content: text });
        userInput.value = '';
        aiTyping.value = true;
        scrollBottom();
        
        // ★ Token Saver: 壓縮對話歷史
        const historyForApi = token.compressionEnabled.value ? token.compressMessages(messages.value) : messages.value;
        
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ text, history: historyForApi }));
        } else {
            fetch(`${BASE}/api/jarvis/ask-and-learn`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text, providers: ['groq', 'deepseek', 'mistral'], learn: false, history: historyForApi })
            }).then(r => r.json()).then(d => {
                aiTyping.value = false;
                const answer = d.answer || d.error || '無回應';
                messages.value.push({ role: 'ai', content: answer });
                scrollBottom();
                // 儲存至 Agent 記憶
                storeMemory(text, answer);
                // ★ Token Saver: 快取回覆
                token.setCache(cacheKey, answer);
                token.recordMiss();
            }).catch(e => {
                aiTyping.value = false;
                messages.value.push({ role: 'ai', content: '❌ 連線失敗: ' + e.message });
                scrollBottom();
            });
        }
    };

    // ── Agent 記憶功能 ──
    const memoryOpen = ref(false);
    const memoryContext = ref('');
    const userPreferences = ref({});

    // 取得記憶上下文
    const getMemoryContext = async () => {
        try {
            const d = await (await fetch(`${BASE}/api/agent/memory/context`)).json();
            if (d.ok) {
                memoryContext.value = d.context || '';
                userPreferences.value = d.preferences || {};
            }
        } catch { }
    };

    // 儲存對話到記憶
    const storeMemory = async (userText, aiText) => {
        try {
            await fetch(`${BASE}/api/agent/memory/store`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_input: userText, ai_response: aiText })
            });
        } catch { }
    };

    // 搜尋記憶
    const searchMemory = async (query) => {
        try {
            const d = await (await fetch(`${BASE}/api/agent/memory/search`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            })).json();
            return d.results || [];
        } catch { return []; }
    };

    // 清除記憶
    const clearMemory = async () => {
        if (!confirm('確定要清除所有記憶嗎？此操作無法復原。')) return;
        try {
            await fetch(`${BASE}/api/agent/memory/clear`, { method: 'POST' });
            memoryContext.value = '';
            userPreferences.value = {};
        } catch { }
    };

    // ── 對話紀錄 ──
    const historyOpen = ref(false);
    const chatHistory = ref([]);
    const currentChatId = ref('');

    const loadChatList = async () => {
        try {
            const d = await (await fetch(`${BASE}/api/jarvis/chat-history`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'list' }) })).json();
            if (d.ok) chatHistory.value = d.chats || [];
        } catch { }
    };

    const saveChatHistory = async () => {
        if (!messages.value.length) return;
        const firstUser = messages.value.find(m => m.role === 'user');
        const title = firstUser ? firstUser.content.slice(0, 30) : '未命名對話';
        try {
            const d = await (await fetch(`${BASE}/api/jarvis/chat-history`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'save', id: currentChatId.value || '', title, messages: messages.value }) })).json();
            if (d.ok) { currentChatId.value = d.id; loadChatList(); }
        } catch { }
    };

    const loadChatHistory = async (id) => {
        try {
            const d = await (await fetch(`${BASE}/api/jarvis/chat-history`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'load', id }) })).json();
            if (d.ok) { messages.value = d.messages || []; currentChatId.value = id; historyOpen.value = false; scrollBottom(); }
            return d.ok;
        } catch { return false; }
    };

    const deleteChatHistory = async (id) => {
        try {
            await fetch(`${BASE}/api/jarvis/chat-history`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'delete', id }) });
            if (currentChatId.value === id) { currentChatId.value = ''; messages.value = []; }
            loadChatList();
        } catch { }
    };

    const newChat = () => { messages.value = []; currentChatId.value = ''; };

    // ── init ──
    const init = () => { connectWs(); loadChatList(); getMemoryContext(); };

    return {
        messages, userInput, aiTyping, chatBox, quickQ, wsConnected,
        scrollBottom, renderMd, sendChat, newChat,
        historyOpen, chatHistory, currentChatId,
        saveChatHistory, loadChatHistory, deleteChatHistory,
        // Agent Memory
        memoryOpen, memoryContext, userPreferences,
        getMemoryContext, storeMemory, searchMemory, clearMemory,
        init,
    };
};
