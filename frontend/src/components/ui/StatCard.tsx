import React from 'react';
import { Card } from './Card';
import { Skeleton } from './Skeleton';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: string;
  isLoading?: boolean;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  isLoading = false,
}) => {
  return (
    <Card
      variant="default"
      padding="sm"
      interactive
      className="sm:p-5 group hover:-translate-y-0.5 min-w-0 flex flex-col justify-between"
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <span className="text-[11px] sm:text-xs font-semibold text-text-muted uppercase tracking-wider leading-snug min-w-0">
          {title}
        </span>
        <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-obsidian-bg border border-obsidian-border group-hover:border-spotify-green/35 flex items-center justify-center text-spotify-green transition-all shrink-0">
          {icon}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2 py-1" aria-busy="true">
          <Skeleton className="h-7 sm:h-8 w-24" />
          <Skeleton className="h-3.5 w-32 opacity-75" />
        </div>
      ) : (
        <>
          <div className="flex items-baseline gap-2 min-w-0">
            <span className="text-xl sm:text-3xl font-extrabold text-white tracking-tight truncate">
              {value}
            </span>
            {trend && (
              <span className="text-xs font-semibold text-emerald-400 shrink-0">
                {trend}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-[11px] sm:text-xs text-text-muted mt-1 font-normal truncate">
              {subtitle}
            </p>
          )}
        </>
      )}
    </Card>
  );
};
