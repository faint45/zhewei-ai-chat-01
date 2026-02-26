/**
 * 模組：系統控制 / 遠端截圖 / 系統資訊 / 視窗列表
 * ──────────────────────────────────────────────────
 * 請勿修改此檔案的既有功能。
 * 後續開發可在此擴充更多主機控制功能。
 */
window.JarvisModSystem = function (BASE, { ref }) {

    const healthData = ref(null);
    const loadHealth = async () => {
        try { healthData.value = await (await fetch(`${BASE}/health`)).json(); } catch { }
    };

    // Screenshot
    const ssImage = ref('');
    const ssInfo = ref('');
    const ssError = ref('');
    const ssLoading = ref(false);
    const ssFullscreen = ref(false);
    const takeScreenshot = async () => {
        ssLoading.value = true; ssError.value = ''; ssFullscreen.value = false;
        try {
            const r = await fetch(`${BASE}/api/host/screenshot?format=base64`);
            const d = await r.json();
            if (d.ok && d.image) { ssImage.value = d.image; ssInfo.value = `${d.width}×${d.height}`; }
            else { ssError.value = d.error || '截圖失敗'; }
        } catch (e) { ssError.value = '連線失敗: ' + e.message; }
        ssLoading.value = false;
    };

    // Sysinfo
    const sysData = ref(null);
    const loadSysinfo = async () => {
        try { sysData.value = await (await fetch(`${BASE}/api/host/sysinfo`)).json(); } catch { }
    };

    // Windows
    const winList = ref([]);
    const loadWindows = async () => {
        try {
            const d = await (await fetch(`${BASE}/api/host/windows`)).json();
            if (d.ok) winList.value = d.windows || [];
        } catch { }
    };

    // Self-Check
    const selfCheckData = ref(null);
    const selfCheckLoading = ref(false);
    const selfCheckError = ref('');
    const runSelfCheck = async () => {
        selfCheckLoading.value = true; selfCheckError.value = '';
        try {
            const r = await fetch(`${BASE}/api/jarvis/self-check`);
            selfCheckData.value = await r.json();
        } catch (e) { selfCheckError.value = '連線失敗: ' + e.message; }
        selfCheckLoading.value = false;
    };

    // Self-Repair
    const repairData = ref(null);
    const repairLoading = ref(false);
    const repairError = ref('');
    const runSelfRepair = async () => {
        repairLoading.value = true; repairError.value = '';
        try {
            const r = await fetch(`${BASE}/api/jarvis/self-repair`, { method: 'POST' });
            repairData.value = await r.json();
            // 修復後自動重新自檢
            await runSelfCheck();
        } catch (e) { repairError.value = '連線失敗: ' + e.message; }
        repairLoading.value = false;
    };

    const init = () => { loadHealth(); loadSysinfo(); };

    return {
        healthData, loadHealth,
        ssImage, ssInfo, ssError, ssLoading, ssFullscreen, takeScreenshot,
        sysData, loadSysinfo,
        winList, loadWindows,
        selfCheckData, selfCheckLoading, selfCheckError, runSelfCheck,
        repairData, repairLoading, repairError, runSelfRepair,
        init,
    };
};
