import React from 'react';

export interface HeaderProps {
  title?: string;
  className?: string;
}

export const Header: React.FC<HeaderProps> = ({ title = '築未科技', className = '' }) => (
  <header className={`bg-zhuwei-emerald-800 text-white py-4 px-6 shadow-md ${className}`}>
    <h1 className="text-xl font-semibold">{title}</h1>
  </header>
);
