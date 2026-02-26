import { Layers, Search, Database, Map, TrendingUp, Video, Globe } from 'lucide-react';
import { ServicePageLayout } from '../../components/ServicePageLayout';

export function MCPToolsPage() {
  return (
    <ServicePageLayout
      title="MCP 工具生態"
      subtitle="Model Context Protocol"
      description="26+ 個 MCP 工具整合，涵蓋搜尋、資料庫、地圖、金融、影音等，一站式 AI 工作流。"
      icon={Layers}
      color="#f43f5e"
      bgColor="bg-rose-50"
      highlights={[
        '26+ 個 MCP 工具已整合',
        '涵蓋搜尋、資料庫、地圖、金融、影音',
        '自建 Yahoo Finance + FFmpeg MCP',
        '免費開源工具為主，零額外成本',
        '持續擴充中，每月新增工具',
      ]}
      features={[
        {
          icon: Search,
          title: '多引擎搜尋',
          desc: '整合 Open Web Search、arXiv 學術搜尋，無需 API Key 即可進行多引擎網路搜尋。',
        },
        {
          icon: Database,
          title: '資料庫操作',
          desc: '支援 PostgreSQL、SQLite、ChromaDB 等資料庫操作，AI 可直接查詢和管理資料。',
        },
        {
          icon: Map,
          title: '地圖與地理',
          desc: 'OSM 地理編碼、路線規劃，支援工程現場定位與地理資訊查詢。',
        },
        {
          icon: TrendingUp,
          title: '金融分析',
          desc: '自建 Yahoo Finance MCP，支援股票報價、歷史數據、財報分析、市場概覽。',
        },
        {
          icon: Video,
          title: '影音處理',
          desc: '自建 FFmpeg MCP，支援影片剪輯、轉檔、截圖、音訊提取、字幕嵌入。',
        },
        {
          icon: Globe,
          title: '網頁自動化',
          desc: 'Puppeteer 網頁截圖與自動化操作，支援網頁內容擷取與互動測試。',
        },
      ]}
    />
  );
}
