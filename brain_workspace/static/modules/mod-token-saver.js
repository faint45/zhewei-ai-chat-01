/**
 * 模組：Token 省費機制
 * ─────────────────────────────────────
 * 功能：
 * - 回覆快取（相同問題直接返回）
 * - 對話歷史壓縮
 * - 自動切換本地模型
 */
window.JarvisModTokenSaver = function (BASE, { ref, computed }) {

    const cacheEnabled = ref(true);
    const compressionEnabled = ref(true);
    const localFirst = ref(true);
    const cacheStats = ref({ hits: 0, misses: 0, saved: 0 });

    const CACHE_KEY_PREFIX = 'jarvis_cache_';
    const MAX_CACHE_SIZE = 200;
    const CACHE_EXPIRE_HOURS = 24;

    // 取得快取
    const getCache = (key) => {
        if (!cacheEnabled.value) return null;
        try {
            const data = localStorage.getItem(CACHE_KEY_PREFIX + key);
            if (!data) return null;
            const cache = JSON.parse(data);
            const expireTime = new Date(cache.expire).getTime();
            if (Date.now() > expireTime) {
                localStorage.removeItem(CACHE_KEY_PREFIX + key);
                return null;
            }
            return cache.response;
        } catch { return null; }
    };

    // 設定快取
    const setCache = (key, response) => {
        if (!cacheEnabled.value) return;
        try {
            // 清理舊快取
            cleanOldCache();
            const cache = {
                response,
                expire: new Date(Date.now() + CACHE_EXPIRE_HOURS * 60 * 60 * 1000).toISOString(),
                created: new Date().toISOString()
            };
            localStorage.setItem(CACHE_KEY_PREFIX + key, JSON.stringify(cache));
        } catch { }
    };

    // 產生快取 key
    const getCacheKey = (text, provider) => {
        const data = `${provider}:${text.toLowerCase().trim()}`;
        let hash = 0;
        for (let i = 0; i < data.length; i++) {
            const char = data.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash).toString(36);
    };

    // 清理舊快取
    const cleanOldCache = () => {
        let count = 0;
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(CACHE_KEY_PREFIX)) count++;
        }
        if (count > MAX_CACHE_SIZE) {
            const keys = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith(CACHE_KEY_PREFIX)) keys.push(key);
            }
            keys.sort((a, b) => {
                const da = JSON.parse(localStorage.getItem(a) || '{}').created || '';
                const db = JSON.parse(localStorage.getItem(b) || '{}').created || '';
                return da.localeCompare(db);
            });
            const toRemove = keys.slice(0, count - MAX_CACHE_SIZE);
            toRemove.forEach(k => localStorage.removeItem(k));
        }
    };

    // 壓縮對話歷史
    const compressMessages = (messages, maxTokens = 1500) => {
        if (!compressionEnabled.value) return messages;
        if (messages.length <= 4) return messages;

        const compressed = [messages[0]];
        let totalChars = 0;

        for (let i = 1; i < messages.length - 1; i++) {
            const msg = messages[i];
            const content = msg.content || '';
            totalChars += content.length;

            if (content.length > 300) {
                compressed.push({
                    role: msg.role,
                    content: `[摘要] ${content.slice(0, 150)}... (${content.length}字)`
                });
            } else {
                compressed.push(msg);
            }
        }

        compressed.push(messages[messages.length - 1]);

        const originalChars = messages.reduce((sum, m) => sum + (m.content || '').length, 0);
        const compressedChars = compressed.reduce((sum, m) => sum + (m.content || '').length, 0);
        const saved = originalChars - compressedChars;

        if (saved > 100) {
            cacheStats.value.saved += saved;
        }

        return compressed;
    };

    // 估算 token
    const estimateTokens = (text) => {
        return Math.ceil((text.length || 0) / 4);
    };

    // 取得快取統計
    const getStats = () => {
        let total = 0;
        let chars = 0;
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(CACHE_KEY_PREFIX)) {
                total++;
                try {
                    const data = JSON.parse(localStorage.getItem(key));
                    chars += (data.response || '').length;
                } catch { }
            }
        }
        return {
            cached: total,
            totalChars: chars,
            estimatedTokens: Math.floor(chars / 4),
            savings: cacheStats.value
        };
    };

    // 清除快取
    const clearCache = () => {
        const keys = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(CACHE_KEY_PREFIX)) keys.push(key);
        }
        keys.forEach(k => localStorage.removeItem(k));
        cacheStats.value = { hits: 0, misses: 0, saved: 0 };
    };

    // 記錄快取命中
    const recordHit = (responseLength) => {
        cacheStats.value.hits++;
        cacheStats.value.saved += responseLength;
    };

    // 記錄快取未命中
    const recordMiss = () => {
        cacheStats.value.misses++;
    };

    return {
        cacheEnabled,
        compressionEnabled,
        localFirst,
        cacheStats,
        getCache,
        setCache,
        getCacheKey,
        compressMessages,
        estimateTokens,
        getStats,
        clearCache,
        recordHit,
        recordMiss
    };
};
