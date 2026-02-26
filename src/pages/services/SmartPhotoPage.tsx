import { Camera, MapPin, FileText, Clock, FolderOpen, Share2 } from 'lucide-react';
import { ServicePageLayout } from '../../components/ServicePageLayout';

export function SmartPhotoPage() {
  return (
    <ServicePageLayout
      title="智慧拍照記錄"
      subtitle="Smart Photo Logger"
      description="工程現場拍照自動分類、AI 標註、GPS 定位，一鍵生成施工日誌與進度報告。"
      icon={Camera}
      color="#8b5cf6"
      bgColor="bg-violet-50"
      highlights={[
        '拍照自動 GPS 定位與時間戳記',
        'AI 自動分類（結構、水電、裝修等）',
        '智慧標註與缺陷標記',
        '一鍵生成施工日誌 PDF',
        '雲端同步，多人協作',
      ]}
      features={[
        {
          icon: Camera,
          title: '智慧拍照',
          desc: '工地現場拍照即自動記錄 GPS 座標、時間、樓層等資訊，無需手動填寫。',
        },
        {
          icon: FolderOpen,
          title: 'AI 自動分類',
          desc: '透過影像辨識自動將照片分類至結構、水電、裝修、安全等類別，節省整理時間。',
        },
        {
          icon: MapPin,
          title: 'GPS 定位標記',
          desc: '每張照片自動綁定 GPS 座標，可在地圖上查看拍攝位置，追蹤施工範圍。',
        },
        {
          icon: FileText,
          title: '自動生成日誌',
          desc: '根據當日拍攝照片自動生成施工日誌，包含進度描述、問題記錄、天氣資訊。',
        },
        {
          icon: Clock,
          title: '進度追蹤',
          desc: '以時間軸方式呈現施工進度，對比計畫與實際進度，即時掌握工程狀況。',
        },
        {
          icon: Share2,
          title: '多人協作',
          desc: '支援多人同時拍照上傳，雲端即時同步，業主、監造、承包商共享施工記錄。',
        },
      ]}
    />
  );
}
