import React from 'react';
import { Header } from './Header';
import { Footer } from './Footer';

export interface PageLayoutProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
}

export const PageLayout: React.FC<PageLayoutProps> = ({ children, title, className = '' }) => (
  <div className={`min-h-screen flex flex-col bg-zhuwei-emerald-50 ${className}`}>
    <Header title={title} />
    <main className="flex-1 p-6">{children}</main>
    <Footer />
  </div>
);
