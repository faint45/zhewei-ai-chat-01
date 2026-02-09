import React from 'react';

export interface FooterProps {
  className?: string;
}

export const Footer: React.FC<FooterProps> = ({ className = '' }) => (
  <footer className={`bg-zhuwei-emerald-900 text-zhuwei-emerald-100 py-3 px-6 text-sm text-center ${className}`}>
    築未科技 © {new Date().getFullYear()}
  </footer>
);
