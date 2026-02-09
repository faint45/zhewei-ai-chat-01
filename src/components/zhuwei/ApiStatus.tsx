import React from 'react';

export interface ApiStatusProps {
  status: 'idle' | 'loading' | 'ok' | 'error';
  message?: string;
  className?: string;
}

export const ApiStatus: React.FC<ApiStatusProps> = ({ status, message, className = '' }) => {
  const labels = { idle: '未連線', loading: '連線中...', ok: 'API 正常', error: 'API 異常' };
  const colors = { idle: 'text-gray-500', loading: 'text-zhuwei-emerald-600', ok: 'text-zhuwei-emerald-700', error: 'text-red-600' };
  return (
    <div className={`text-sm ${colors[status]} ${className}`}>
      {labels[status]}{message ? ` — ${message}` : ''}
    </div>
  );
};
