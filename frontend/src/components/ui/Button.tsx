import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ai' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
}

const VARIANT_CLASSES: Record<NonNullable<ButtonProps['variant']>, string> = {
  primary:
    'bg-spotify-green text-black font-bold hover:bg-spotify-hover shadow-md shadow-spotify-green/20 border border-transparent',
  secondary:
    'bg-obsidian-bg/90 text-slate-200 font-semibold border border-obsidian-border hover:text-white hover:border-spotify-green/50',
  ai: 'bg-gradient-to-r from-purple-600 to-[#1DB954] text-white font-bold hover:brightness-110 shadow-lg shadow-purple-900/20 border border-transparent',
  ghost:
    'bg-transparent text-slate-300 font-medium border border-transparent hover:text-white hover:bg-obsidian-card',
  danger:
    'bg-rose-500/20 text-rose-100 font-bold border border-rose-500/35 hover:bg-rose-500/30',
};

const SIZE_CLASSES: Record<NonNullable<ButtonProps['size']>, string> = {
  sm: 'min-h-[36px] px-3 py-1.5 text-xs rounded-xl',
  md: 'min-h-[40px] px-4 py-2 text-xs rounded-xl',
  lg: 'min-h-[46px] px-6 py-3 text-sm rounded-xl',
};

/** Nút bấm chuẩn hóa vùng chạm, trạng thái focus-visible và trạng thái vô hiệu hóa. */
export const Button: React.FC<ButtonProps> = ({
  variant = 'secondary',
  size = 'md',
  isLoading = false,
  leftIcon,
  disabled,
  type = 'button',
  className = '',
  children,
  ...rest
}) => {
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green focus-visible:ring-offset-2 focus-visible:ring-offset-obsidian-bg ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
      {...rest}
    >
      {leftIcon}
      {children}
    </button>
  );
};
