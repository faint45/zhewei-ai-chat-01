/**
 * 模組：圖片生成與多模態輸入（ComfyUI + Stable Diffusion）
 * ───────────────────────────────────────────────
 * 功能：
 * - 文字生圖（ComfyUI API）
 * - 圖片上傳與分析（多模態輸入）
 * - 圖片描述生成
 */
window.JarvisModImage = function (BASE, { ref }) {

    const imgPrompt = ref('');
    const imgLoading = ref(false);
    const imgResult = ref('');
    const imgError = ref('');
    
    // 圖片上傳相關
    const uploadedImage = ref(null);
    const imageAnalysis = ref('');
    const imagePreview = ref('');

    // 生成圖片
    const generateImage = async () => {
        imgLoading.value = true; imgResult.value = ''; imgError.value = '';
        try {
            const r = await fetch(`${BASE}/api/jarvis/generate-image`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: imgPrompt.value, filename: `jarvis_${Date.now()}.png` })
            });
            const d = await r.json();
            if (d.ok) imgResult.value = d.result; else imgError.value = d.error || '生成失敗';
        } catch (e) { imgError.value = e.message; }
        imgLoading.value = false;
    };

    // 處理圖片上傳
    const handleImageUpload = (event) => {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!file.type.startsWith('image/')) {
            imgError.value = '請上傳圖片檔案';
            return;
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.value = e.target.result;
            uploadedImage.value = e.target.result;
        };
        reader.readAsDataURL(file);
    };

    // 分析上傳的圖片
    const analyzeImage = async () => {
        if (!uploadedImage.value) {
            imgError.value = '請先上傳圖片';
            return;
        }
        
        imgLoading.value = true;
        imageAnalysis.value = '';
        imgError.value = '';
        
        try {
            const r = await fetch(`${BASE}/api/jarvis/analyze-image`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    image: uploadedImage.value,
                    prompt: imgPrompt.value || '請描述這張圖片的內容'
                })
            });
            const d = await r.json();
            if (d.ok) imageAnalysis.value = d.result;
            else imgError.value = d.error || '分析失敗';
        } catch (e) { imgError.value = e.message; }
        imgLoading.value = false;
    };

    // 清除圖片
    const clearImage = () => {
        uploadedImage.value = null;
        imagePreview.value = '';
        imageAnalysis.value = '';
        imgPrompt.value = '';
    };

    return { 
        imgPrompt, imgLoading, imgResult, imgError, 
        generateImage,
        uploadedImage, imageAnalysis, imagePreview,
        handleImageUpload, analyzeImage, clearImage
    };
};
