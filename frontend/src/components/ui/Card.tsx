import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'ai' | 'subtle';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  interactive?: boolean;
}

const VARIANT_CLASSES: Record<NonNullable<CardProps['variant']>, string> = {
  default: 'bg-obsidian-card border-obsidian-border shadow-xl',
  elevated: 'bg-obsidian-elevated border-slate-700/70 shadow-2xl',
  ai: 'bg-gradient-to-br from-[#131B2E] via-[#0F172A] to-[#131B2E] border-purple-900/35 shadow-2xl',
  subtle: 'bg-obsidian-bg/60 border-obsidian-border/80 shadow-none',
};

const PADDING_CLASSES: Record<NonNullable<CardProps['padding']>, string> = {
  none: '',
  sm: 'p-3.5 sm:p-4',
  md: 'p-4 sm:p-6',
  lg: 'p-5 sm:p-8',
};

/** Thẻ bề mặt chuẩn hóa theo Design Tokens Obsidian Dark. */
export const Card: React.FC<CardProps> = ({
  variant = 'default',
  padding = 'md',
  interactive = false,
  className = '',
  children,
  ...rest
}) => {
  return (
    <div
      className={`w-full min-w-0 rounded-2xl border transition-all ${VARIANT_CLASSES[variant]} ${PADDING_CLASSES[padding]} ${
        interactive ? 'hover:border-spotify-green/40' : ''
      } ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
};
