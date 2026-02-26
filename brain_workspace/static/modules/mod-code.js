/**
 * 模組：編碼模擬 + 即時預覽（類似 AI Studio）
 * ─────────────────────────────────────────────
 * 請勿修改此檔案的既有功能。
 * 後續開發可接入本地模型：修改 generateCode 中的 API 端點即可。
 */
window.JarvisModCode = function (BASE, { ref, nextTick, watch }) {

    const codePrompt = ref('');
    const codeLang = ref('html');
    const codeLoading = ref(false);
    const codeResult = ref('');
    const codeError = ref('');
    const codeViewMode = ref('split');
    const codeCopied = ref(false);
    const previewFrame = ref(null);

    const generateCode = async () => {
        codeLoading.value = true; codeError.value = ''; codeResult.value = '';
        try {
            const r = await fetch(`${BASE}/api/jarvis/generate-code`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: codePrompt.value, lang: codeLang.value })
            });
            const d = await r.json();
            if (d.ok && d.code) {
                codeResult.value = d.code;
                nextTick(() => updatePreview());
            } else { codeError.value = d.error || '生成失敗'; }
        } catch (e) { codeError.value = '連線失敗: ' + e.message; }
        codeLoading.value = false;
    };

    const updatePreview = () => {
        if (!previewFrame.value || !codeResult.value) return;
        const doc = previewFrame.value.contentDocument || previewFrame.value.contentWindow.document;
        doc.open(); doc.write(codeResult.value); doc.close();
    };

    const copyCode = () => {
        navigator.clipboard.writeText(codeResult.value).then(() => {
            codeCopied.value = true; setTimeout(() => codeCopied.value = false, 2000);
        }).catch(() => { });
    };

    watch(codeResult, () => nextTick(() => updatePreview()));

    return {
        codePrompt, codeLang, codeLoading, codeResult, codeError,
        codeViewMode, codeCopied, previewFrame,
        generateCode, copyCode,
    };
};
