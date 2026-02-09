import type { ReactNode } from 'react';

export interface BentoItemProps {
  children: ReactNode;
  className?: string;
  spotlight?: boolean;
}

export function BentoItem({ children, className = '', spotlight }: BentoItemProps) {
  return (
    <div
      className={`rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-sm ${spotlight ? 'ring-1 ring-zhuwei-emerald-500/30' : ''} ${className}`}
    >
      {children}
    </div>
  );
}

export interface BentoGridProps {
  children: ReactNode;
  className?: string;
}

export function BentoGrid({ children, className = '' }: BentoGridProps) {
  return (
    <div className={`grid grid-cols-12 gap-4 auto-rows-fill ${className}`}>
      {children}
    </div>
  );
}
