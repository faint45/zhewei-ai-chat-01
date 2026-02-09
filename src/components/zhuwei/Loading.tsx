import React from 'react';

export interface LoadingProps {
  message?: string;
  className?: string;
}

export const Loading: React.FC<LoadingProps> = ({ message = '載入中...', className = '' }) => (
  <div className={`flex flex-col items-center justify-center py-8 text-zhuwei-emerald-600 ${className}`}>
    <div className="w-10 h-10 border-2 border-zhuwei-emerald-300 border-t-zhuwei-emerald-600 rounded-full animate-spin" />
    <p className="mt-3 text-sm">{message}</p>
  </div>
);
