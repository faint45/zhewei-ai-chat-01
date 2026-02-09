import React from 'react';

export interface EmptyStateProps {
  message?: string;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ message = '尚無資料', className = '' }) => (
  <div className={`py-12 text-center text-zhuwei-emerald-600 ${className}`}>{message}</div>
);
