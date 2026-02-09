import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline';
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({ variant = 'primary', children, className = '', ...props }) => {
  const base = 'px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-60';
  const variants = {
    primary: 'bg-zhuwei-emerald-600 text-white hover:bg-zhuwei-emerald-700',
    secondary: 'bg-zhuwei-emerald-100 text-zhuwei-emerald-800 hover:bg-zhuwei-emerald-200',
    outline: 'border border-zhuwei-emerald-600 text-zhuwei-emerald-700 hover:bg-zhuwei-emerald-50',
  };
  return <button className={`${base} ${variants[variant]} ${className}`} {...props}>{children}</button>;
};
