import React from 'react';

export interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ title, children, className = '' }) => (
  <div className={`rounded-lg border border-zhuwei-emerald-200 bg-white shadow-sm overflow-hidden ${className}`}>
    {title && <div className="bg-zhuwei-emerald-50 px-4 py-2 border-b border-zhuwei-emerald-200 font-medium text-zhuwei-emerald-800">{title}</div>}
    <div className="p-4">{children}</div>
  </div>
);
