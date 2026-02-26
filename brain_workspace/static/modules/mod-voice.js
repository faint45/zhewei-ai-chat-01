/**
 * 模組：語音對話 (STT + TTS)
 * ─────────────────────────────────────
 * 功能：
 * - 語音輸入 (Web Speech API)
 * - 語音輸出 (TTS)
 * - 語音設定控制
 */
window.JarvisModVoice = function (BASE, { ref, computed }) {

    // 語音狀態
    const isListening = ref(false);
    const isSpeaking = ref(false);
    const speechSupported = ref(false);
    const ttsSupported = ref(false);
    const recognitionSupported = ref(false);
    
    // 設定
    const autoSpeak = ref(false);  // 自動朗讀 AI 回應
    const speechRate = ref(1.0);
    const speechPitch = ref(1.0);
    const speechLang = ref('zh-TW');

    // Speech Recognition 實例
    let recognition = null;
    let synthesis = window.speechSynthesis;

    // 初始化
    const init = () => {
        // 檢查瀏覽器支援
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognitionSupported.value = !!SpeechRecognition;
        ttsSupported.value = !!speechSynthesis;

        if (SpeechRecognition) {
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'zh-TW';
            
            recognition.onstart = () => { isListening.value = true; };
            recognition.onend = () => { isListening.value = false; };
            recognition.onerror = (e) => {
                isListening.value = false;
                console.error('Speech recognition error:', e);
            };
            recognition.onresult = (event) => {
                const result = event.results[event.results.length - 1];
                if (result.isFinal) {
                    const transcript = result[0].transcript;
                    handleVoiceInput(transcript);
                }
            };
        }

        // 載入設定
        const saved = localStorage.getItem('jarvis_voice_settings');
        if (saved) {
            try {
                const settings = JSON.parse(saved);
                autoSpeak.value = settings.autoSpeak || false;
                speechRate.value = settings.speechRate || 1.0;
                speechPitch.value = settings.speechPitch || 1.0;
                speechLang.value = settings.speechLang || 'zh-TW';
            } catch {}
        }
    };

    // 儲存設定
    const saveSettings = () => {
        localStorage.setItem('jarvis_voice_settings', JSON.stringify({
            autoSpeak: autoSpeak.value,
            speechRate: speechRate.value,
            speechPitch: speechPitch.value,
            speechLang: speechLang.value
        }));
    };

    // 開始語音輸入
    const startListening = () => {
        if (!recognition) return;
        try {
            recognition.lang = speechLang.value;
            recognition.start();
        } catch (e) {
            console.error('Failed to start recognition:', e);
        }
    };

    // 停止語音輸入
    const stopListening = () => {
        if (!recognition) return;
        try { recognition.stop(); } catch {}
        isListening.value = false;
    };

    // 處理語音輸入結果
    const handleVoiceInput = (text) => {
        console.log('Voice input:', text);
        // 發送自定義事件，讓 chat 模組接收
        window.dispatchEvent(new CustomEvent('jarvis-voice-input', { detail: text }));
    };

    // 語音輸出 (TTS)
    const speak = (text) => {
        if (!ttsSupported.value || !text) return;
        
        // 停止當前朗讀
        stopSpeaking();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = speechLang.value;
        utterance.rate = speechRate.value;
        utterance.pitch = speechPitch.value;
        
        utterance.onstart = () => { isSpeaking.value = true; };
        utterance.onend = () => { isSpeaking.value = false; };
        utterance.onerror = () => { isSpeaking.value = false; };
        
        synthesis.speak(utterance);
    };

    // 停止語音輸出
    const stopSpeaking = () => {
        if (synthesis) {
            synthesis.cancel();
            isSpeaking.value = false;
        }
    };

    // 朗讀 AI 回應
    const speakAiResponse = (text) => {
        if (autoSpeak.value && text) {
            speak(text);
        }
    };

    // 切換自動朗讀
    const toggleAutoSpeak = () => {
        autoSpeak.value = !autoSpeak.value;
        saveSettings();
    };

    return {
        isListening,
        isSpeaking,
        speechSupported: computed(() => recognitionSupported.value || ttsSupported.value),
        ttsSupported,
        recognitionSupported,
        autoSpeak,
        speechRate,
        speechPitch,
        speechLang,
        init,
        startListening,
        stopListening,
        speak,
        stopSpeaking,
        speakAiResponse,
        toggleAutoSpeak,
        saveSettings,
    };
};
