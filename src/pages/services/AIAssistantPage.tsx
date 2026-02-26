import { Brain, MessageSquare, BookOpen, Cpu, Users, Sparkles, Database } from 'lucide-react';
import { ServicePageLayout } from '../../components/ServicePageLayout';

export function AIAssistantPage() {
  return (
    <ServicePageLayout
      title="AI 智慧助理"
      subtitle="Jarvis AI 大腦"
      description="基於大型語言模型的工程專業助理，整合 14,600+ 筆營建知識庫，即時回答工程問題、生成報告、自動學習進化。"
      icon={Brain}
      color="#059669"
      bgColor="bg-emerald-50"
      ctaText="開始對話"
      ctaLink="/jarvis"
      highlights={[
        '14,600+ 筆營建專業知識庫',
        '11 個 AI 提供者智慧路由',
        '9 大專業角色切換',
        '每日自主學習持續進化',
        '支援多模態輸入（文字+圖片）',
      ]}
      features={[
        {
          icon: MessageSquare,
          title: '自然語言對話',
          desc: '用自然語言提問工程問題，AI 即時回答。支援營建法規、施工技術、品質管理等專業領域。',
        },
        {
          icon: Users,
          title: '9 大專業角色',
          desc: '營建工程師、結構技師、專案管理人、法規顧問等 9 種角色，各自擁有專屬知識庫與系統提示詞。',
        },
        {
          icon: Cpu,
          title: '智慧路由引擎',
          desc: '軍師/士兵分工架構：Gemini 負責思考分析，本地 Ollama 負責執行，自動選擇最佳 AI 提供者。',
        },
        {
          icon: Database,
          title: 'ChromaDB 知識庫',
          desc: '向量資料庫儲存營建專業知識，支援語意搜尋，精準匹配相關知識片段輔助回答。',
        },
        {
          icon: BookOpen,
          title: '自主學習機制',
          desc: '每日自動從大模型萃取精華、夜間自主學習，知識庫持續成長，越用越聰明。',
        },
        {
          icon: Sparkles,
          title: '多模態輸入',
          desc: '支援文字、圖片上傳，透過 Gemini Vision 進行圖片分析，適用於工地現場照片判讀。',
        },
      ]}
    />
  );
}
