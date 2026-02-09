import { useState, useEffect } from 'react';
import { BentoItem } from '@/components/BentoGrid';
import { Book, ChevronRight, History } from 'lucide-react';
import { fetchKnowledgeHistory } from '@/api/client';

const FALLBACK_HISTORIES = [
  { title: '2026-02-06 儲存規範白皮書', tag: 'Architecture' },
  { title: '優良工地主任申請資料表', tag: 'Career' },
  { title: 'RTX 4060 Ti 算力調度邏輯', tag: 'Logic' },
];

function tagFromFileName(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes('arch') || lower.includes('架構')) return 'Architecture';
  if (lower.includes('career') || lower.includes('職涯') || lower.includes('工地')) return 'Career';
  if (lower.includes('logic') || lower.includes('邏輯') || lower.includes('算力')) return 'Logic';
  if (lower.includes('code')) return 'Code';
  return 'Architecture';
}

export default function KnowledgeBase() {
  const [items, setItems] = useState<{ title: string; tag: string }[]>(FALLBACK_HISTORIES);

  useEffect(() => {
    fetchKnowledgeHistory().then((list) => {
      if (list.length > 0) {
        setItems(
          list.map(({ name }) => ({
            title: name.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/\.md$/i, '') || name,
            tag: tagFromFileName(name),
          }))
        );
      }
    });
  }, []);

  return (
    <BentoItem className="col-span-12 md:col-span-4 row-span-2 p-6" spotlight>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-white font-bold flex items-center">
          <Book className="mr-2 text-zhuwei-emerald-500" size={18} /> 築未數位大腦
        </h3>
        <History className="text-slate-600" size={16} />
      </div>

      <div className="space-y-4">
        {items.map((item, idx) => (
          <div
            key={idx}
            className="group flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-zhuwei-emerald-500/10 border border-white/5 transition-all cursor-pointer"
          >
            <div>
              <p className="text-xs text-slate-300 font-medium">{item.title}</p>
              <span className="text-[9px] text-zhuwei-emerald-500/60 uppercase">{item.tag}</span>
            </div>
            <ChevronRight size={14} className="text-slate-700 group-hover:text-zhuwei-emerald-500" />
          </div>
        ))}
      </div>

      <button
        type="button"
        className="w-full mt-6 py-2 text-[10px] text-slate-500 border border-slate-800 rounded-lg hover:text-white transition-colors"
      >
        查看全部對話紀錄
      </button>
    </BentoItem>
  );
}
