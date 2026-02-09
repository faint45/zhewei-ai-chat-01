/**
 * 築未科技 - 儲存規範定義 (2026-02-06)
 *
 * 開發守則：儲存路徑合規
 * 1. 禁止在 C:\ 建立任何專案或存放數據。
 * 2. 核心路徑必須以 D:\Projects\zhuwei-center 為根目錄。
 * 3. 暫存檔案、日誌、快取必須導向 Z:\Temp。
 * 4. 任何檔案操作必須調用本檔 PATHS 變數。
 * 5. 嚴禁硬編碼 (Hardcoding) C 槽路徑。
 */
export const ZHUWEI_CONFIG = {
  PROJECT_NAME: "築未指揮中心",
  LOCATION: "嘉義民雄",

  PATHS: {
    // 核心執行區 (D 槽 9TB)
    PROJECT_ROOT: "D:/Projects/zhuwei-center",
    EXECUTIVE_FILES: "D:/Projects/zhuwei-center/dist",

    // 築未科技數位大腦 (brain_workspace)
    BRAIN_WORKSPACE: "D:/Projects/zhuwei-center/brain_workspace",
    BRAIN_HISTORY: "D:/Projects/zhuwei-center/brain_workspace/history",       // 歷次對話紀錄 (.md)
    BRAIN_ARCH_DECISIONS: "D:/Projects/zhuwei-center/brain_workspace/arch_decisions", // 架構決策紀錄 (ADR)
    BRAIN_CODE_SNIPPETS: "D:/Projects/zhuwei-center/brain_workspace/code_snippets",   // 核心程式碼備份
    BRAIN_REPORTS: "D:/Projects/zhuwei-center/brain_workspace/reports",               // AI 任務回報 (JSON)

    // 暫存存放區 (Z 槽 Cloud)
    TEMP_ROOT: "Z:/Temp",
    CACHE_DIR: "Z:/Temp/cache",
    LOG_DIR: "Z:/Temp/logs",

    // 系統警戒區 (僅限 OS，禁止寫入)
    SYSTEM_ROOT: "C:/",
  },

  ENDPOINTS: {
    OLLAMA: "http://127.0.0.1:11434",
    GPU_STATS: "/api/stats/gpu",
  },
} as const;
