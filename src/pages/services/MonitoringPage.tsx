import { MonitorSmartphone, Cpu, HardDrive, Wifi, Bell, BarChart3 } from 'lucide-react';
import { ServicePageLayout } from '../../components/ServicePageLayout';

export function MonitoringPage() {
  return (
    <ServicePageLayout
      title="遠端監控管理"
      subtitle="Remote Monitoring"
      description="即時系統監控、遠端截圖、GPU 狀態追蹤，隨時隨地掌握工程系統運行狀況。"
      icon={MonitorSmartphone}
      color="#0ea5e9"
      bgColor="bg-sky-50"
      ctaText="進入監控台"
      ctaLink="/health-dashboard"
      highlights={[
        'CPU / RAM / GPU 即時監控',
        '遠端桌面截圖與視窗管理',
        'Docker 容器健康檢查',
        'Ntfy 即時推播告警',
        'AI 用量成本追蹤',
      ]}
      features={[
        {
          icon: Cpu,
          title: '系統資源監控',
          desc: '即時追蹤 CPU 使用率、記憶體佔用、GPU 溫度與負載，確保系統穩定運行。',
        },
        {
          icon: MonitorSmartphone,
          title: '遠端桌面管理',
          desc: '透過 Host API 遠端截圖、查看視窗列表、執行本地命令，無需 VPN 即可管理。',
        },
        {
          icon: HardDrive,
          title: 'Docker 容器監控',
          desc: '監控所有 Docker 容器狀態、健康檢查結果、資源使用量，一鍵重啟異常容器。',
        },
        {
          icon: Bell,
          title: '即時告警推播',
          desc: '整合 Ntfy 推播系統，異常狀況即時通知到手機，支援 iOS / Android / 桌面。',
        },
        {
          icon: BarChart3,
          title: 'AI 用量追蹤',
          desc: '追蹤各 AI 提供者的 API 調用次數、Tokens 消耗、成本估算，設定預算警報。',
        },
        {
          icon: Wifi,
          title: '網路狀態監控',
          desc: '監控 Cloudflare Tunnel 連線狀態、API 回應時間、外網可用性。',
        },
      ]}
    />
  );
}
