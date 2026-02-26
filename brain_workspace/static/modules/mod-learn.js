/**
 * 模組：學習大模型精華（問大模型 → 萃取 → 寫入知識庫）
 * ─────────────────────────────────────────────────────────
 * 請勿修改此檔案的既有功能。
 * 後續開發可接入本地模型：修改 askAndLearn / batchLearn 中的 providers 即可。
 */
window.JarvisModLearn = function (BASE, { ref }) {

    const learnQuestion = ref('');
    const learnProvider = ref('groq');
    const learnLoading = ref(false);
    const learnResult = ref(null);
    const batchTopics = ref('');
    const batchLoading = ref(false);
    const batchResult = ref(null);
    const learnStats = ref(null);
    const kbCount = ref('...');
    
    // Token Saver 統計顯示
    const tokenStats = ref(null);
    const updateTokenStats = () => {
        try {
            const keys = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('jarvis_cache_')) keys.push(key);
            }
            let total = 0, chars = 0;
            keys.forEach(k => {
                total++;
                try { chars += JSON.parse(localStorage.getItem(k)).response.length; } catch {}
            });
            tokenStats.value = { cached: total, savedTokens: Math.floor(chars / 4) };
        } catch {}
    };

    // 角色系統
    const roles = ref([]);
    const activeRole = ref('');  // '' = 大智庫（通識）
    const roleStats = ref(null);

    const renderMd = (text) => { try { return marked.parse(text || ''); } catch { return text; } };

    const loadRoles = async () => {
        try {
            const r = await fetch(`${BASE}/api/jarvis/roles`);
            const d = await r.json();
            if (d.ok && d.roles) roles.value = d.roles;
        } catch { }
    };

    const loadRoleStats = async () => {
        try {
            const r = await fetch(`${BASE}/api/jarvis/roles/stats`);
            const d = await r.json();
            if (d.ok) roleStats.value = d;
        } catch { }
    };

    const askAndLearn = async () => {
        learnLoading.value = true; learnResult.value = null;
        try {
            let url, body;
            if (activeRole.value) {
                url = `${BASE}/api/jarvis/roles/${activeRole.value}/ask-and-learn`;
                body = { question: learnQuestion.value, providers: [learnProvider.value] };
            } else {
                url = `${BASE}/api/jarvis/ask-and-learn`;
                body = { question: learnQuestion.value, providers: [learnProvider.value] };
            }
            const r = await fetch(url, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            learnResult.value = await r.json(); loadStats(); loadRoleStats();
        } catch (e) { learnResult.value = { source: 'error', learned: false, essence: e.message, answer: '' }; }
        learnLoading.value = false;
    };

    const batchLearn = async () => {
        batchLoading.value = true; batchResult.value = null;
        const topics = batchTopics.value.split('\n').map(t => t.trim()).filter(Boolean);
        try {
            const r = await fetch(`${BASE}/api/jarvis/batch-learn`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topics, providers: [learnProvider.value] })
            });
            batchResult.value = await r.json(); loadStats(); loadRoleStats();
        } catch (e) { batchResult.value = { total: 0, learned: 0, results: [] }; }
        batchLoading.value = false;
    };

    const loadStats = async () => {
        try {
            const r = await fetch(`${BASE}/api/jarvis/learning-stats`);
            const d = await r.json();
            if (d.ok !== false) learnStats.value = d;
            if (d.total !== undefined) kbCount.value = d.total;
        } catch { }
    };

    // MCP 工作流
    const wfIdea = ref('');
    const wfInput = ref('');
    const wfCreating = ref(false);
    const wfAdvancing = ref(false);
    const activeWf = ref(null);
    const workflows = ref([]);
    const wfSteps = ref([
        { id: 'idea', name: '想法產出', icon: '💡' },
        { id: 'analyze', name: 'AI 分析建議', icon: '🧠' },
        { id: 'confirm', name: '用戶確認方案', icon: '✅' },
        { id: 'execute', name: 'MCP 執行', icon: '⚡' },
        { id: 'review', name: '確認成果', icon: '🔍' },
        { id: 'optimize', name: 'AI 優化建議', icon: '🔧' },
        { id: 'finalize', name: '執行優化/結案', icon: '🏁' },
    ]);

    const createWorkflow = async () => {
        if (!activeRole.value || !wfIdea.value.trim()) return;
        wfCreating.value = true;
        try {
            const r = await fetch(`${BASE}/api/jarvis/workflow/create`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role_id: activeRole.value, idea: wfIdea.value })
            });
            const d = await r.json();
            if (d.ok && d.workflow) { activeWf.value = d.workflow; wfIdea.value = ''; }
            loadWorkflows();
        } catch { }
        wfCreating.value = false;
    };

    const loadWorkflows = async () => {
        try {
            const r = await fetch(`${BASE}/api/jarvis/workflow/list`);
            const d = await r.json();
            if (d.ok) workflows.value = d.workflows || [];
        } catch { }
    };

    const loadWorkflow = async (id) => {
        try {
            const r = await fetch(`${BASE}/api/jarvis/workflow/${id}`);
            const d = await r.json();
            if (d.ok && d.workflow) activeWf.value = d.workflow;
        } catch { }
    };

    const advanceWf = async (approved) => {
        if (!activeWf.value) return;
        wfAdvancing.value = true;
        try {
            const r = await fetch(`${BASE}/api/jarvis/workflow/${activeWf.value.id}/advance`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: wfInput.value, approved })
            });
            const d = await r.json();
            if (d.ok && d.workflow) activeWf.value = d.workflow;
            wfInput.value = '';
            loadWorkflows();
        } catch { }
        wfAdvancing.value = false;
    };

    const init = () => { loadStats(); loadRoles(); loadRoleStats(); loadWorkflows(); updateTokenStats(); };

    return {
        learnQuestion, learnProvider, learnLoading, learnResult, renderMd,
        askAndLearn, batchTopics, batchLoading, batchResult,
        learnStats, kbCount, loadStats, init,
        tokenStats, updateTokenStats,
        roles, activeRole, roleStats, loadRoles, loadRoleStats,
        wfIdea, wfInput, wfCreating, wfAdvancing, activeWf, workflows, wfSteps,
        createWorkflow, loadWorkflows, loadWorkflow, advanceWf,
    };
};
